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

The tests run FluxGate `v1.2.0` images by default (`FLUXGATE_VERSION` changes the tag) with these defaults:

- **Features**: 1,000 deployed features (`feature=10000` to `feature=10999`), 700 boolean and 300 with variants
- **Breakpoint test**: 100 → 5,000 RPS in 100 RPS steps of 60s, per profile and feature count (100, 400, 1000)
- **Steady-state test**: 10 minutes at 70% of the breakpoint, on a freshly restarted edge
- **SLO per step**: p99 ≤ 50 ms, errors < 1%, dropped requests < 1%

All values can be changed with environment variables (`./run-perf-tests.sh --help`).

## 🚀 Quick Start

### 1. Start Backend and Database
```bash
cd perf-test

# The v1.2.0 backend needs an encryption key (base64 of 32 bytes)
export FLUXGATE_ENCRYPTION_KEY="$(openssl rand -base64 32)"

# Start postgres and backend first
docker-compose -f docker-compose.base.yml -f docker-compose.cgroups.yml up -d postgres backend
```

Keep `FLUXGATE_ENCRYPTION_KEY` exported in the shell that runs `run-perf-tests.sh`: the script recreates the backend for every profile.

To run next to another FluxGate stack, move the host ports and point the scripts at them:

```bash
export DB_PORT=15433 BACKEND_HTTP_PORT=18080 EDGE_HTTP_PORT=18081
export BACKEND_URL=http://localhost:18080 REST_HTTP_URL=http://localhost:18080/api/v1 EDGE_URL=http://localhost:18081
```

### 2. Initialize Edge Server Client
```bash
node init-edge-client.js

# This will:
# - Create the admin user if needed
# - Create the "Performance Test Team" and its "Perf-Test-Prod" environment
# - Create a backend client for that environment
# - Update config/edge-config.toml with the client credentials
# Save the Environment ID from the output
export ENVIRONMENT_ID="your-env-id-from-output"
```

### 3. Start Edge Server
```bash
docker-compose -f docker-compose.base.yml -f docker-compose.cgroups.yml -f docker-compose.tiny.yml up -d edge
```

### 4. Generate Test Data
```bash
# 1,000 features named feature=10000 .. feature=10999, the keys the tests use
node populate-data.js --features=1000 --start=10000

# Give every stage a targeting rule so evaluations do real rule matching
node evaluate-features.js --features=1000 --evals=2
```

`populate-data.js` also creates a `perf-approver` user: deployments to the perf environment need an approval from someone other than the requester.

### 5. Run Performance Tests
```bash
./run-perf-tests.sh --profiles "minimal tiny small medium large"
```

The xlarge profile limits the edge to 8 CPUs; Docker refuses to start it when the Docker Desktop VM has fewer.

### 6. Build Charts for the Site
```bash
./generate-site-charts.py results/perf-results-<timestamp> --prometheus http://localhost:9095
./capture-grafana.sh results/perf-results-<timestamp>/small/round3-1000f/breakpoint.json \
  small-1000f-breakpoint results/perf-results-<timestamp>/site/grafana/small-breakpoint
```

This writes light and dark SVG charts and `perf-summary.{json,csv,md}` to `results/perf-results-<timestamp>/site/`, plus Grafana screenshots taken with headless Chrome.

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

### Before You Start

- Stop other Docker stacks (demo, docs) so they do not compete for CPU or ports 8080/8081/5433.
- Docker Desktop's VM caps what profiles can use: with 4 CPUs, the large (4 CPU) and xlarge (8 CPU) limits are not reachable. Raise the VM CPUs or skip those profiles.
- k6 runs on the same machine, so it shares the CPU with the services. For results you publish, run k6 from a second machine (`EDGE_URL=http://<host>:8081`) or record the machine specs next to the numbers. `SUMMARY.md` records the Docker host and k6 version.

### Automated Test Suite

The `run-perf-tests.sh` script automates testing across different resource profiles.

```bash
# Run all profiles (minimal → xlarge)
export ENVIRONMENT_ID="your-env-id"
./run-perf-tests.sh

# Run specific profiles and feature counts only
./run-perf-tests.sh --profiles "tiny small medium" --features "100 1000"

# Quick test (20s breakpoint steps, 1m steady state)
./run-perf-tests.sh --quick

# Fixed steady-state load instead of 70% of the breakpoint
./run-perf-tests.sh --steady-rps 500

# Skip deployment (use existing containers)
./run-perf-tests.sh --skip-deploy

# Without Prometheus/Grafana (samples docker stats instead)
./run-perf-tests.sh --no-monitoring
```

The script:
1. Starts the monitoring stack (see [Monitoring](#-monitoring))
2. Deploys each resource profile sequentially and waits for stabilization (30s)
3. For each feature count (default: 100, 400, 1000):
   - Runs a **breakpoint test**: 100 → 5000 RPS in 100 RPS steps of 60s each, stops once the edge is saturated
   - Runs a **steady-state test** for 10 minutes at 70% of the max sustainable RPS
   - Adds per-step CPU, memory and CPU throttling for edge, backend and postgres from Prometheus
4. Saves results to `results/perf-results-<timestamp>/` with a `SUMMARY.md` table

Tune the runs with environment variables: `BP_START_RPS`, `BP_STEP_RPS`, `BP_MAX_RPS`, `BP_STEP_DURATION`, `SLO_P99_MS`, `STEADY_FRACTION`, `STEADY_DURATION`.

### Breakpoint Test

`../k6-tests/breakpoint-test.js` sends `POST /evaluate` requests for the keys `feature=10000` onwards. Each rate step is its own k6 scenario, so every step gets its own latency percentiles, error rate and dropped-request count. They are not averaged over the whole run.

A step passes when it meets the SLO:
- p99 latency ≤ `SLO_P99_MS` (default 50 ms)
- evaluation errors ≤ 1%. A non-200 response or an `errorCode` in the body (for example `FLAG_NOT_FOUND`) counts as an error.
- dropped requests ≤ 1%. k6 drops a request when all virtual users are busy, which means the edge cannot keep up.

**Max sustainable RPS** is the last step before the first failing step. The run stops early when a step exceeds p99 1000 ms, 20% errors or 5% dropped requests. When the run ends this way, k6 exits with code 99, and the script treats it as a normal finish.

The same script runs the steady-state test, as one step: `START_RPS=MAX_RPS=<rps>`, `STEP_DURATION=10m`.

```bash
mkdir -p results/manual
k6 run \
  -e EDGE_URL=http://localhost:8081 \
  -e ENVIRONMENT_ID=your-env-id \
  -e TOTAL_FEATURES=1000 \
  -e START_RPS=100 -e STEP_RPS=100 -e MAX_RPS=3000 -e STEP_DURATION=60s \
  -e RESULTS_DIR=results/manual -e TEST_NAME=tiny-breakpoint \
  ../k6-tests/breakpoint-test.js
```

The script header lists every option. Each run writes:

| File | Content |
|---|---|
| `<name>.json` | Per-step results, max sustainable RPS, breaking step, resources per step |
| `<name>.md` | The same as Markdown tables |
| `<name>-k6-summary.json` | Full k6 end-of-test summary |
| `<name>-report.html` | k6 web dashboard report (self-contained, shareable) |

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
├── docker-compose.cgroups.yml    # Named cgroup parents so cAdvisor can see the containers
├── docker-compose.monitoring.yml # Prometheus, Grafana, cAdvisor, postgres_exporter
├── docker-compose.minimal.yml    # Edge limit 0.25 CPU, 64Mi RAM
├── docker-compose.tiny.yml       # Edge limit 0.5 CPU, 128Mi RAM (baseline)
├── docker-compose.small.yml      # Edge limit 1 CPU, 256Mi RAM
├── docker-compose.medium.yml     # Edge limit 2 CPU, 512Mi RAM
├── docker-compose.large.yml      # Edge limit 4 CPU, 1024Mi RAM
├── docker-compose.xlarge.yml     # Edge limit 8 CPU, 2048Mi RAM
├── populate-data.js              # Single-threaded test data generation
├── populate-data-mt.js           # Multi-threaded test data generation
├── populate-data-worker.js       # Worker thread for multi-threaded generation
├── cleanup-data.sh               # Clean test data from database
├── run-perf-tests.sh             # Automated test execution
├── collect-resource-metrics.py   # Adds per-step CPU/memory from Prometheus to a result
├── generate-site-charts.py       # Site charts (SVG) and summary tables from a results directory
├── capture-grafana.sh            # Grafana dashboard screenshots for one test run
├── verify-setup.sh               # Setup verification
├── init-edge-client.js           # Initialize edge server credentials
├── .env.example                  # Environment variables template
├── .env                          # Your environment variables
├── config/
│   ├── backend-config.toml       # Backend configuration
│   ├── backend-log4rs.yaml       # Backend logging
│   └── edge-config.toml          # Edge configuration
├── monitoring/
│   ├── prometheus.yml            # Scrape config (cAdvisor, postgres_exporter)
│   ├── generate-dashboard.py     # Source of the Grafana dashboard JSON
│   └── grafana/                  # Provisioned datasource and dashboard
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
- **PostgreSQL**: localhost:5433
- **Grafana**: http://localhost:3300 (monitoring stack)
- **Prometheus**: http://localhost:9095 (monitoring stack)

Ports 9090/9091 are mapped for edge and backend metrics, but the services do not serve a Prometheus `/metrics` endpoint yet.

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

# Steady state: one 10 minute step at 500 RPS
mkdir -p results/manual
k6 run \
  -e EDGE_URL=http://localhost:8081 \
  -e ENVIRONMENT_ID=your-env-id \
  -e START_RPS=500 -e MAX_RPS=500 -e STEP_RPS=0 -e STEP_DURATION=10m \
  -e RESULTS_DIR=results/manual -e TEST_NAME=tiny-steady-500 \
  ../k6-tests/breakpoint-test.js
```

## 📈 Monitoring

### Prometheus and Grafana

`run-perf-tests.sh` starts the monitoring stack automatically. To use it by hand:

```bash
docker-compose -f docker-compose.monitoring.yml up -d

# The test stack needs the cgroups overlay so cAdvisor can report its containers
docker-compose -f docker-compose.base.yml -f docker-compose.cgroups.yml -f docker-compose.tiny.yml up -d

# Stream k6 metrics into Prometheus, tagged with a run id
K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9095/api/v1/write K6_FEATURES=native-histograms \
  k6 run -o experimental-prometheus-rw --tag testid=tiny-manual ../k6-tests/breakpoint-test.js

# Add per-step CPU/memory to the result file
./collect-resource-metrics.py results/manual/tiny-manual.json
```

Open http://localhost:3300 (anonymous read access; admin login `admin`/`admin`). The **FluxGate Performance** dashboard shows:

| Section | Metrics | Source |
|---|---|---|
| Load and latency | Achieved, failed and dropped RPS; p50/p90/p95/p99/p99.9 latency; p99 per step; active VUs | k6 remote write (native histograms) |
| Containers | CPU cores used vs limit, CPU throttling, memory working set vs limit, OOM kills | cAdvisor |
| PostgreSQL | Commits, rows written, connections, buffer cache hit ratio | postgres_exporter |

Pick a run in the **Test run** variable (`<profile>-<features>f-breakpoint` or `-steady`). To change the dashboard, edit `monitoring/generate-dashboard.py` and run it; do not edit the JSON by hand.

cAdvisor runs in raw cgroup mode, because Docker Desktop's containerd image store breaks its Docker integration. `docker-compose.cgroups.yml` puts each test container under a fixed cgroup (`/fluxgate-perf-edge` etc.), and Prometheus turns that into a `service` label. On Linux hosts with the systemd cgroup driver, Docker rejects these cgroup paths.

```bash
# Stop the monitoring stack; add -v to also delete the stored metrics
docker-compose -f docker-compose.monitoring.yml down
```

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
- ✓ Image versions (`FLUXGATE_VERSION`, default v1.2.0)
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

1. **Start Services**: `docker-compose -f docker-compose.base.yml -f docker-compose.cgroups.yml up -d postgres backend` (with `FLUXGATE_ENCRYPTION_KEY` set)
2. **Initialize Client**: `node init-edge-client.js`
3. **Start Edge**: `docker-compose -f docker-compose.base.yml -f docker-compose.cgroups.yml -f docker-compose.tiny.yml up -d edge`
4. **Verify Setup**: `./verify-setup.sh`
5. **Generate Data**: `node populate-data.js --features=1000 --start=10000`, then `node evaluate-features.js --features=1000 --evals=2`
6. **Run Tests**: `ENVIRONMENT_ID=xxx ./run-perf-tests.sh`
7. **Analyze Results**: Review `results/perf-results-*/SUMMARY.md`, build charts with `./generate-site-charts.py`
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
