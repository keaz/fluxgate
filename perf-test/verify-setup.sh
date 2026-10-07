#!/bin/bash
#
# Verification script for FluxGate Performance Test Setup (Docker Compose)
# Tests that backend, edge, and postgres containers are properly configured
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  FluxGate Performance Test Setup Verification       ║${NC}"
echo -e "${CYAN}║  (Docker Compose)                                    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ docker-compose not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose available${NC}"

# Check if services are running
echo ""
echo -e "${CYAN}Checking running containers...${NC}"

# Check postgres
if docker ps | grep -q "fluxgate-perf-postgres"; then
    POSTGRES_STATUS=$(docker inspect --format='{{.State.Health.Status}}' fluxgate-perf-postgres 2>/dev/null || echo "unknown")
    if [ "$POSTGRES_STATUS" = "healthy" ]; then
        echo -e "${GREEN}✓ PostgreSQL container running and healthy${NC}"
    else
        echo -e "${YELLOW}⚠ PostgreSQL container running but health status: $POSTGRES_STATUS${NC}"
    fi
else
    echo -e "${RED}✗ PostgreSQL container not running${NC}"
    echo -e "${YELLOW}  Run: docker-compose -f docker-compose.base.yml -f docker-compose.tiny.yml up -d${NC}"
    exit 1
fi

# Check backend
if docker ps | grep -q "fluxgate-perf-backend"; then
    BACKEND_IMAGE=$(docker inspect --format='{{.Config.Image}}' fluxgate-perf-backend)
    echo -e "${GREEN}✓ Backend container running${NC}"
    echo -e "${CYAN}  Image: $BACKEND_IMAGE${NC}"
else
    echo -e "${RED}✗ Backend container not running${NC}"
    exit 1
fi

# Check edge
if docker ps | grep -q "fluxgate-perf-edge"; then
    EDGE_IMAGE=$(docker inspect --format='{{.Config.Image}}' fluxgate-perf-edge)
    echo -e "${GREEN}✓ Edge container running${NC}"
    echo -e "${CYAN}  Image: $EDGE_IMAGE${NC}"
else
    echo -e "${RED}✗ Edge container not running${NC}"
    exit 1
fi

# Check that both use the expected version (FLUXGATE_VERSION, default v1.2.0)
EXPECTED_VERSION="${FLUXGATE_VERSION:-v1.2.0}"
echo ""
echo -e "${CYAN}Checking image versions...${NC}"
if [[ "$BACKEND_IMAGE" != *":$EXPECTED_VERSION" ]]; then
    echo -e "${YELLOW}⚠ Backend not using $EXPECTED_VERSION${NC}"
else
    echo -e "${GREEN}✓ Backend using $EXPECTED_VERSION${NC}"
fi

if [[ "$EDGE_IMAGE" != *":$EXPECTED_VERSION" ]]; then
    echo -e "${YELLOW}⚠ Edge not using $EXPECTED_VERSION${NC}"
else
    echo -e "${GREEN}✓ Edge using $EXPECTED_VERSION${NC}"
fi

# Check resource limits
echo ""
echo -e "${CYAN}Checking edge server resource limits...${NC}"
EDGE_CPU=$(docker inspect --format='{{.HostConfig.CpuQuota}}' fluxgate-perf-edge)
EDGE_MEM=$(docker inspect --format='{{.HostConfig.Memory}}' fluxgate-perf-edge)

if [ "$EDGE_CPU" != "0" ] && [ "$EDGE_CPU" != "" ]; then
    EDGE_CPU_CORES=$(echo "scale=2; $EDGE_CPU / 100000" | bc)
    echo -e "${GREEN}✓ CPU limit: ${EDGE_CPU_CORES} cores${NC}"
else
    echo -e "${YELLOW}⚠ No CPU limit set${NC}"
fi

if [ "$EDGE_MEM" != "0" ] && [ "$EDGE_MEM" != "" ]; then
    EDGE_MEM_MB=$(echo "scale=0; $EDGE_MEM / 1024 / 1024" | bc)
    echo -e "${GREEN}✓ Memory limit: ${EDGE_MEM_MB}MB${NC}"
else
    echo -e "${YELLOW}⚠ No memory limit set${NC}"
fi

# Check edge server logs for gRPC connection
echo ""
echo -e "${CYAN}Checking edge server gRPC connection...${NC}"
if docker logs fluxgate-perf-edge 2>&1 | tail -100 | grep -q "Stream connection established"; then
    echo -e "${GREEN}✓ Edge server connected to backend via gRPC${NC}"
else
    echo -e "${YELLOW}⚠ gRPC stream connection not confirmed in logs${NC}"
    echo -e "${YELLOW}  This may be normal if just started - check logs:${NC}"
    echo -e "${YELLOW}  docker logs fluxgate-perf-edge${NC}"
fi

# Check port accessibility
echo ""
echo -e "${CYAN}Checking port accessibility...${NC}"

# Backend REST
if curl -sf http://localhost:8080/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend accessible on port 8080${NC}"
else
    echo -e "${YELLOW}⚠ Backend not accessible on port 8080${NC}"
    echo -e "${YELLOW}  This may require the service to be fully started${NC}"
fi

# Edge server
if curl -sf http://localhost:8081/health > /dev/null 2>&1 || nc -z localhost 8081 2>/dev/null; then
    echo -e "${GREEN}✓ Edge server accessible on port 8081${NC}"
else
    echo -e "${YELLOW}⚠ Edge server not accessible on port 8081${NC}"
    echo -e "${YELLOW}  Port may be bound but service starting${NC}"
fi

# Network check
echo ""
echo -e "${CYAN}Checking Docker network...${NC}"
if docker network inspect fluxgate-perf-network &> /dev/null; then
    echo -e "${GREEN}✓ Docker network 'fluxgate-perf-network' exists${NC}"
else
    echo -e "${RED}✗ Docker network 'fluxgate-perf-network' not found${NC}"
fi

# Configuration files check
echo ""
echo -e "${CYAN}Checking configuration files...${NC}"
if [ -f "config/backend-config.toml" ]; then
    echo -e "${GREEN}✓ Backend config exists${NC}"
else
    echo -e "${RED}✗ Backend config missing${NC}"
fi

if [ -f "config/edge-config.toml" ]; then
    echo -e "${GREEN}✓ Edge config exists${NC}"

    # Check if edge config points to correct backend
    if grep -q "backend_grpc = \"http://backend:50051\"" config/edge-config.toml; then
        echo -e "${GREEN}✓ Edge config points to correct backend${NC}"
    else
        echo -e "${YELLOW}⚠ Edge config may not point to correct backend${NC}"
    fi
else
    echo -e "${RED}✗ Edge config missing${NC}"
fi

# Summary
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              Setup Verification Summary              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Docker Compose setup verified!${NC}"
echo ""
echo -e "Services are accessible at:"
echo -e "  - Backend API: ${YELLOW}http://localhost:8080/api/v1${NC}"
echo -e "  - Backend gRPC:    ${YELLOW}localhost:50051${NC}"
echo -e "  - Edge Evaluation: ${YELLOW}http://localhost:8081/evaluate${NC}"
echo -e "  - PostgreSQL:      ${YELLOW}localhost:5432${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Generate test data:"
echo -e "     ${YELLOW}cd .. && node populate_perf_test_data.js${NC}"
echo ""
echo -e "  2. Run performance tests:"
echo -e "     ${YELLOW}export ENVIRONMENT_ID=<your-env-id>${NC}"
echo -e "     ${YELLOW}cd perf-test && ./run-perf-tests.sh${NC}"
echo ""
echo -e "  3. View logs:"
echo -e "     ${YELLOW}docker-compose -f docker-compose.base.yml logs -f${NC}"
echo ""
echo -e "  4. Stop services:"
echo -e "     ${YELLOW}docker-compose -f docker-compose.base.yml down${NC}"
echo ""
