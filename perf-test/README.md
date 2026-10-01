# FluxGate Performance Testing with Docker Compose

Complete performance benchmarking setup using Docker Compose for easy local testing with direct localhost access.

## 📋 Table of Contents

- [Default Configuration](#-default-configuration)
- [Quick Start](#-quick-start)
- [Test Data Generation](#-test-data-generation)
- [Running Performance Tests](#-running-performance-tests)
- [Cleanup](#-cleanup)
- [Directory Structure](#-directory-structure)
- [Resource Profiles](#-resource-profiles)
- [Detailed Usage](#-usage)
- [Monitoring](#-monitoring)
- [Troubleshooting](#-troubleshooting)

## ⚙️ Default Configuration

The performance tests are configured with the following defaults:

- **Total Features**: 1,000 features
- **Target RPS**: 500 requests per second
- **Virtual Users (VUs)**: 20 (max 50 for steady-state, max 100 for stress tests)
- **Test Duration**: 15 minutes per steady-state test (2m ramp + 10m steady + 3m ramp down)
- **Stress Test**: Ramps from 100 RPS to 1000 RPS in 100 RPS increments

All values can be customized via environment variables (see test files for details).

## 🚀 Quick Start

### 1. Start Backend and Database
```bash
cd perf-test

# Start postgres and backend first
docker-compose -f docker-compose.base.yml up -d postgres backend

# Wait for backend to be ready (30 seconds)
sleep 30
```

### 2. Initialize Edge Server Client
```bash
# Create client credentials for edge server
node init-edge-client.js

# This will:
# - Create admin user if needed
# - Create a team for performance testing
# - Create a client for the edge server
# - Update edge-config.toml with the credentials
```

### 3. Start Edge Server
```bash
# Now start edge server with client credentials
docker-compose -f docker-compose.base.yml -f docker-compose.tiny.yml up -d edge

# Verify setup
./verify-setup.sh
```

### 4. Generate Test Data
```bash
# Multi-threaded (recommended) - much faster!
node populate-data-mt.js --features=1000 --threads=8

# Or single-threaded
node populate-data.js --features=1000

# Save the Environment ID from output
export ENVIRONMENT_ID="your-env-id-from-output"
```

### 5. Run Performance Tests
```bash
./run-perf-tests.sh
```

## 📊 Test Data Generation

The performance test suite includes scripts to populate your FluxGate instance with test data.

### Multi-Threaded Generation (Recommended)

**Much faster** than single-threaded - uses worker threads to create features in parallel.

```bash
# Generate 1,000 features using 8 threads
node populate-data-mt.js --features=1000 --threads=8

# Generate 100,000 features using 12 threads
node populate-data-mt.js --features=100000 --threads=12

# Generate 1M features using 16 threads (advanced - takes ~2-3 hours)
node populate-data-mt.js --features=1000000 --threads=16

# Resume from a specific index if interrupted
node populate-data-mt.js --features=500000 --threads=16 --start=500000
```

**Options:**
- `--features=N` - Number of features to create (default: 1000)
- `--threads=N` - Number of worker threads (default: 8)
- `--start=N` - Starting feature index (default: 0, useful for resuming)

**Performance:** With 8 threads, expect ~10-15 features/sec (varies by system).

### Single-Threaded Generation

Simpler but slower option - useful for debugging or small datasets.

```bash
# Generate 1,000 features
node populate-data.js --features=1000

# Generate 10,000 features (quick test)
node populate-data.js --features=10000

# Resume from a specific index if interrupted
node populate-data.js --features=500000 --start=500000
```

**Options:**
- `--features=N` - Number of features to create (default: 1000)
- `--start=N` - Starting feature index (default: 0)

**Performance:** Expect ~3-5 features/sec (varies by system).

### What Gets Created

Both scripts create:

- **1 admin user** - Username: `admin`, Password: `password123` (with Approver + Requester roles)
- **1 team** - "Performance Test Team"
- **1 environment** - "Perf-Test-Prod"
- **1 pipeline** - Simple single-stage pipeline
- **10 contexts** - For varied testing with different attributes
- **N features** - Named sequentially: `feature=0`, `feature=1`, ..., `feature=N-1` (default: 1,000)
  - 70% Simple features (boolean on/off flags)
  - 30% Contextual features (with variants and criteria)
  - All features auto-deployed and enabled

### Important Notes

**Save the Environment ID!** After data generation completes, you'll see output like:

```
Test Environment Ready!
  - Team ID: 12345678-1234-1234-1234-123456789abc
  - Environment ID: 87654321-4321-4321-4321-cba987654321  ← SAVE THIS!
  - Feature Range: feature=0 to feature=999
```

Export this for testing:
```bash
export ENVIRONMENT_ID="87654321-4321-4321-4321-cba987654321"
```

## 🧪 Running Performance Tests

### Automated Test Suite

The `run-perf-tests.sh` script automates testing across different resource profiles.

```bash
# Run all profiles (tiny → xlarge)
export ENVIRONMENT_ID="your-env-id"
./run-perf-tests.sh

# Run specific profiles only
./run-perf-tests.sh --profiles "tiny small medium"

# Quick test (shorter duration, faster results)
./run-perf-tests.sh --quick

# Skip deployment (use existing containers)
./run-perf-tests.sh --skip-deploy
```

The script:
1. Deploys each resource profile sequentially
2. Waits for stabilization (30s)
3. Runs steady-state tests (default: 100 RPS)
4. Runs stress test (ramping load from 100 to 1000 RPS)
5. Collects metrics, logs, and container stats
6. Saves results to `results/perf-results-<timestamp>/`

### Manual Testing

```bash
# Start services with desired profile
docker-compose -f docker-compose.base.yml -f docker-compose.tiny.yml up -d

# Run individual k6 test
k6 run \
  -e EDGE_URL=http://localhost:8081 \
  -e ENVIRONMENT_ID=your-env-id \
  -e TARGET_RPS=100 \
  ../k6-tests/steady-state-test.js

# View real-time stats
docker stats fluxgate-perf-edge fluxgate-perf-backend
```

### Test Types

**Steady-State Tests** (`../k6-tests/steady-state-test.js`)
- Constant load at specified RPS (default: 500 RPS)
- 15-minute duration (2 minutes ramp + 10 minutes steady + 3 minutes ramp down)
- Uses 20 VUs (Virtual Users) with max 50 VUs
- Measures latency (p50, p95, p99) and error rate
- Tests with 1K features (default, configurable)

**Stress Tests** (`../k6-tests/stress-test.js`)
- Ramping load from 100 → 1000 RPS (100 RPS increments every 2 minutes)
- Uses 20 VUs (Virtual Users) with max 100 VUs
- Identifies breaking point and resource limits
- Tests with 1K features (default, configurable)

## 🧹 Cleanup

### Clean Performance Test Data

Remove all generated test features from the database:

```bash
./cleanup-data.sh
```

This script:
- Shows current database stats (total features, index range, gaps)
- Asks for confirmation before deletion
- Deletes all features with `feature=` pattern
- Verifies cleanup completion

**Safe to run** - only deletes features matching the `feature=` naming pattern.

### Clean Docker Resources

```bash
# Stop and remove containers
docker-compose -f docker-compose.base.yml down

# Stop and remove containers + volumes (full reset)
docker-compose -f docker-compose.base.yml down -v
```

## 📁 Directory Structure

```
perf-test/
├── docker-compose.base.yml       # Base infrastructure (postgres, backend, edge)
├── docker-compose.minimal.yml    # 100m CPU, 64Mi RAM
├── docker-compose.tiny.yml       # 250m CPU, 128Mi RAM (baseline)
├── docker-compose.small.yml      # 500m CPU, 256Mi RAM
├── docker-compose.medium.yml     # 1000m CPU, 512Mi RAM
├── docker-compose.large.yml      # 2000m CPU, 1024Mi RAM
├── docker-compose.xlarge.yml     # 4000m CPU, 2048Mi RAM
├── populate-data.js              # Single-threaded test data generation
├── populate-data-mt.js           # Multi-threaded test data generation
├── populate-data-worker.js       # Worker thread for multi-threaded generation
├── cleanup-data.sh               # Clean test data from database
├── run-perf-tests.sh             # Automated test execution
├── verify-setup.sh               # Setup verification
├── init-edge-client.js           # Initialize edge server credentials
├── .env.example                  # Environment variables template
├── .env                          # Your environment variables
├── config/
│   ├── backend-config.toml       # Backend configuration
│   ├── backend-log4rs.yaml       # Backend logging
│   └── edge-config.toml          # Edge configuration
└── results/                      # Test results directory
    └── perf-results-<timestamp>/ # Results for each test run
```

## 📊 Resource Profiles

| Profile | CPU Limit | Memory Limit | Use Case |
|---------|-----------|--------------|----------|
| **minimal** | 0.25 cores | 64MB | Absolute minimum |
| **tiny** | 0.5 cores | 128MB | Baseline (recommended start) |
| **small** | 1.0 cores | 256MB | Moderate traffic |
| **medium** | 2.0 cores | 512MB | High traffic |
| **large** | 4.0 cores | 1024MB | Very high traffic |
| **xlarge** | 8.0 cores | 2048MB | Extreme load testing |

## 🔧 Usage

### Starting Services with Different Profiles

```bash
# Tiny profile (baseline)
docker-compose -f docker-compose.base.yml -f docker-compose.tiny.yml up -d

# Small profile
docker-compose -f docker-compose.base.yml -f docker-compose.small.yml up -d

# Medium profile
docker-compose -f docker-compose.base.yml -f docker-compose.medium.yml up -d

# Stop services
docker-compose -f docker-compose.base.yml down
```

### Services Access

All services are directly accessible on localhost:

- **Backend API**: http://localhost:8080/api/v1
- **Backend gRPC**: localhost:50051
- **Edge Evaluation**: http://localhost:8081/evaluate
- **PostgreSQL**: localhost:5432
- **Backend Metrics**: http://localhost:9091/metrics (if exposed)
- **Edge Metrics**: http://localhost:9090/metrics (if exposed)

### Running Tests

#### All Profiles
```bash
export ENVIRONMENT_ID="your-env-id"
./run-perf-tests.sh
```

#### Specific Profiles
```bash
./run-perf-tests.sh --profiles "tiny small medium"
```

#### Quick Test (shorter duration)
```bash
./run-perf-tests.sh --quick
```

#### Skip Deployment (use existing containers)
```bash
./run-perf-tests.sh --skip-deploy
```

### Manual Testing

```bash
# Start services
docker-compose -f docker-compose.base.yml -f docker-compose.tiny.yml up -d

# Run individual k6 test
k6 run \
  -e EDGE_URL=http://localhost:8081 \
  -e ENVIRONMENT_ID=your-env-id \
  -e TARGET_RPS=500 \
  ../k6-tests/steady-state-test.js
```

## 📈 Monitoring

### View Logs
```bash
# All services
docker-compose -f docker-compose.base.yml logs -f

# Specific service
docker-compose -f docker-compose.base.yml logs -f edge
docker-compose -f docker-compose.base.yml logs -f backend
```

### Check Resource Usage
```bash
# Real-time stats
docker stats fluxgate-perf-edge fluxgate-perf-backend

# Container details
docker inspect fluxgate-perf-edge
```

### Health Checks
```bash
# Backend REST (should respond)
curl -s http://localhost:8080/api/v1/health

# Edge evaluation endpoint
curl -s http://localhost:8081/health

# Check if edge is connected to backend
docker logs fluxgate-perf-edge | grep "Stream connection established"
```

## 🛠️ Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose -f docker-compose.base.yml logs

# Check if ports are in use
lsof -i :8080  # Backend
lsof -i :8081  # Edge
lsof -i :5432  # Postgres

# Clean restart
docker-compose -f docker-compose.base.yml down -v
docker-compose -f docker-compose.base.yml -f docker-compose.tiny.yml up -d
```

### Edge Server Can't Connect to Backend

```bash
# Check backend is running
docker ps | grep backend

# Check edge logs
docker logs fluxgate-perf-edge

# Verify config
cat config/edge-config.toml | grep backend_grpc
# Should be: backend_grpc = "http://backend:50051"

# Restart edge
docker-compose -f docker-compose.base.yml restart edge
```

### Database Connection Issues

```bash
# Check postgres health
docker inspect --format='{{.State.Health.Status}}' fluxgate-perf-postgres

# Connect to database
docker exec -it fluxgate-perf-postgres psql -U postgres -d feature_toggle

# Check backend database connection
docker logs fluxgate-perf-backend | grep -i "database\|postgres"
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8080

# Kill process if needed
kill -9 <PID>

# Or change port in docker-compose
# Edit docker-compose.base.yml ports section
```

## 🧪 Legacy Test Data Generation Info

These examples are for reference. See the [Test Data Generation](#-test-data-generation) section above for the current approach.

### Large Dataset (Optional - for advanced testing)
```bash
# Generate 1M features (takes ~2-3 hours)
node populate-data-mt.js --features=1000000 --threads=16
```

### Smaller Dataset for Quick Tests
```bash
# 10,000 features
node populate-data.js --features=10000

# 100,000 features
node populate-data-mt.js --features=100000 --threads=8
```

### Resume Interrupted Generation
```bash
# If stopped at feature 500000
node populate-data-mt.js --start=500000 --features=500000 --threads=16
```

## 📋 Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
# Database
DB_PASSWORD=root123
DB_NAME=feature_toggle

# Logging
BACKEND_LOG_LEVEL=info
EDGE_LOG_LEVEL=info

# Test Configuration
ENVIRONMENT_ID=<set-after-data-generation>
TOTAL_FEATURES=1000
```

## 🔍 Verification

Run the verification script to check setup:

```bash
./verify-setup.sh
```

This checks:
- ✓ Docker services running
- ✓ Image versions (v0.0.11-alpha-arm64)
- ✓ Resource limits applied
- ✓ gRPC connection established
- ✓ Ports accessible
- ✓ Configuration files present

## 📊 Results

Test results are saved in `results/perf-results-<timestamp>/`:

```
results/perf-results-20251108-163000/
├── tiny/
│   ├── steady-1000-summary.json
│   ├── steady-5000-summary.json
│   ├── stress-summary.json
│   ├── container-stats.txt
│   ├── backend-logs.txt
│   └── edge-logs.txt
├── small/
│   └── ...
└── SUMMARY.md
```

## 🔄 Workflow

1. **Start Services**: `docker-compose -f docker-compose.base.yml up -d postgres backend`
2. **Initialize Client**: `node init-edge-client.js`
3. **Start Edge**: `docker-compose -f docker-compose.base.yml -f docker-compose.tiny.yml up -d edge`
4. **Verify Setup**: `./verify-setup.sh`
5. **Generate Data**: `node populate-data-mt.js --features=1000 --threads=8`
6. **Run Tests**: `ENVIRONMENT_ID=xxx ./run-perf-tests.sh`
7. **Analyze Results**: Review `results/perf-results-*/SUMMARY.md`
8. **Cleanup**: `./cleanup-data.sh` (optional, to remove test data)
9. **Stop Services**: `docker-compose -f docker-compose.base.yml down`

## 🎯 Best Practices

1. **Start with tiny profile** to establish baseline
2. **Monitor resource usage** during tests with `docker stats`
3. **Allow stabilization time** (30s) after starting services
4. **Run tests sequentially** for consistent results
5. **Clean up between profiles** to avoid interference
6. **Save results** before testing next profile

## 🐛 Common Issues

### Issue: "Error response from daemon: Conflict. Container already exists"
**Solution**:
```bash
docker-compose -f docker-compose.base.yml down
docker-compose -f docker-compose.base.yml -f docker-compose.tiny.yml up -d
```

### Issue: "Backend returns 404 for all requests"
**Solution**: Backend might still be starting. Wait 30-60 seconds and try again.

### Issue: "Resource limits not applied"
**Solution**: Ensure Docker Desktop has resource limits enabled in settings.

### Issue: "k6 connection refused"
**Solution**: Check if services are running and accessible on localhost.

## 📚 Additional Resources

- [Performance Benchmark Plan](../PERFORMANCE_BENCHMARK_PLAN.md)
- [Performance Benchmark Guide](../PERFORMANCE_BENCHMARK_GUIDE.md)
- [k6 Documentation](https://k6.io/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🤝 Support

For issues or questions:
- Check logs: `docker-compose -f docker-compose.base.yml logs`
- Run verification: `./verify-setup.sh`
- Review troubleshooting section above

---

**Ready to test?** Start with the Quick Start section above! 🚀
