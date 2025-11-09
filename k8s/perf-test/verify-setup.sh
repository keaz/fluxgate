#!/bin/bash
#
# Verification script for FluxGate Performance Test Setup
# Tests that backend, edge, and services are properly configured
#

set -e

NAMESPACE="fluxgate"
BACKEND_SVC="fluxgate-backend-perf"
EDGE_SVC="fluxgate-edge-perf"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  FluxGate Performance Test Setup Verification       ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ kubectl available${NC}"

# Check namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${RED}✗ Namespace $NAMESPACE not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Namespace $NAMESPACE exists${NC}"

# Check backend pod
BACKEND_POD=$(kubectl get pods -n "$NAMESPACE" -l app=fluxgate-backend-perf -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$BACKEND_POD" ]; then
    echo -e "${RED}✗ Backend pod not found${NC}"
    exit 1
fi

BACKEND_STATUS=$(kubectl get pod "$BACKEND_POD" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
if [ "$BACKEND_STATUS" != "Running" ]; then
    echo -e "${RED}✗ Backend pod not running (status: $BACKEND_STATUS)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Backend pod running: $BACKEND_POD${NC}"

# Check edge pod
EDGE_POD=$(kubectl get pods -n "$NAMESPACE" -l app=fluxgate-edge-perf -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$EDGE_POD" ]; then
    echo -e "${RED}✗ Edge pod not found${NC}"
    exit 1
fi

EDGE_STATUS=$(kubectl get pod "$EDGE_POD" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
if [ "$EDGE_STATUS" != "Running" ]; then
    echo -e "${RED}✗ Edge pod not running (status: $EDGE_STATUS)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Edge pod running: $EDGE_POD${NC}"

# Check backend service
if ! kubectl get svc "$BACKEND_SVC" -n "$NAMESPACE" &> /dev/null; then
    echo -e "${RED}✗ Backend service not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Backend service exists: $BACKEND_SVC${NC}"

# Check edge service
if ! kubectl get svc "$EDGE_SVC" -n "$NAMESPACE" &> /dev/null; then
    echo -e "${RED}✗ Edge service not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Edge service exists: $EDGE_SVC${NC}"

# Check backend image version
BACKEND_IMAGE=$(kubectl get pod "$BACKEND_POD" -n "$NAMESPACE" -o jsonpath='{.spec.containers[0].image}')
echo -e "${CYAN}  Backend image: $BACKEND_IMAGE${NC}"

# Check edge image version
EDGE_IMAGE=$(kubectl get pod "$EDGE_POD" -n "$NAMESPACE" -o jsonpath='{.spec.containers[0].image}')
echo -e "${CYAN}  Edge image: $EDGE_IMAGE${NC}"

# Check if both use v0.0.11-alpha-arm64
if [[ "$BACKEND_IMAGE" != *"v0.0.11-alpha-arm64"* ]]; then
    echo -e "${YELLOW}⚠ Backend not using v0.0.11-alpha-arm64${NC}"
fi

if [[ "$EDGE_IMAGE" != *"v0.0.11-alpha-arm64"* ]]; then
    echo -e "${YELLOW}⚠ Edge not using v0.0.11-alpha-arm64${NC}"
fi

# Check edge server logs for gRPC connection
echo ""
echo -e "${CYAN}Checking edge server gRPC connection...${NC}"
if kubectl logs "$EDGE_POD" -n "$NAMESPACE" --tail=100 | grep -q "Stream connection established"; then
    echo -e "${GREEN}✓ Edge server connected to backend via gRPC${NC}"
else
    echo -e "${YELLOW}⚠ gRPC stream connection not confirmed in logs${NC}"
fi

# Check ConfigMaps
echo ""
echo -e "${CYAN}Checking ConfigMaps...${NC}"
if kubectl get configmap fluxgate-backend-config -n "$NAMESPACE" &> /dev/null; then
    echo -e "${GREEN}✓ Backend ConfigMap exists${NC}"
else
    echo -e "${RED}✗ Backend ConfigMap missing${NC}"
fi

if kubectl get configmap fluxgate-edge-config -n "$NAMESPACE" &> /dev/null; then
    echo -e "${GREEN}✓ Edge ConfigMap exists${NC}"
else
    echo -e "${RED}✗ Edge ConfigMap missing${NC}"
fi

# Check Secret
if kubectl get secret fluxgate-db -n "$NAMESPACE" &> /dev/null; then
    echo -e "${GREEN}✓ Database Secret exists${NC}"
else
    echo -e "${RED}✗ Database Secret missing${NC}"
fi

# Summary
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              Setup Verification Summary              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}All components are deployed and running!${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Set up port forwarding:"
echo -e "     ${YELLOW}kubectl port-forward -n $NAMESPACE svc/$BACKEND_SVC 8080:8080 &${NC}"
echo -e "     ${YELLOW}kubectl port-forward -n $NAMESPACE svc/$EDGE_SVC 8081:8081 &${NC}"
echo ""
echo -e "  2. Generate test data:"
echo -e "     ${YELLOW}node populate_perf_test_data.js${NC}"
echo ""
echo -e "  3. Run performance tests:"
echo -e "     ${YELLOW}export ENVIRONMENT_ID=<your-env-id>${NC}"
echo -e "     ${YELLOW}./run-perf-tests.sh${NC}"
echo ""
