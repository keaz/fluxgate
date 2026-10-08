#!/bin/bash
#
# FluxGate Performance Test Automation Script (Docker Compose Version)
#
# This script automates the entire performance testing workflow using Docker Compose:
# 1. Starts the monitoring stack (Prometheus, Grafana, cAdvisor, postgres_exporter)
# 2. Deploys each resource profile sequentially
# 3. Runs a breakpoint test per feature count to find the max sustainable RPS
# 4. Runs a steady-state test at STEADY_FRACTION of that RPS
# 5. Collects per-step CPU/memory from Prometheus, logs and k6 HTML reports
# 6. Generates summary report
#
# Usage:
#   export ENVIRONMENT_ID="your-env-id-here"
#   ./run-perf-tests.sh
#
# Options:
#   --profiles "tiny small medium"  # Test specific profiles only
#   --features "100 1000"           # Feature counts to test (default: 100 400 1000)
#   --steady-rps 500                # Fixed steady-state RPS instead of a share of the breakpoint
#   --skip-deploy                   # Skip deployment (use existing)
#   --no-monitoring                 # Skip Prometheus/Grafana, sample docker stats instead
#   --quick                         # Run shorter tests for quick validation
#

set -e

# Configuration
ENVIRONMENT_ID="${ENVIRONMENT_ID}"
EDGE_URL="${EDGE_URL:-http://localhost:8081}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8080}"
RESULTS_DIR="./results/perf-results-$(date +%Y%m%d-%H%M%S)"
K6_TESTS_DIR="../k6-tests"
COMPOSE_DIR="."
# Database configuration (used for seeding evaluations)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-root123}"
DB_NAME="${DB_NAME:-feature_toggle}"
SEED_FEATURE_LIMIT="${SEED_FEATURE_LIMIT:-1000}"

# Default profiles to test
DEFAULT_PROFILES=("minimal" "tiny" "small" "medium" "large" "xlarge")
PROFILES=("${DEFAULT_PROFILES[@]}")

# Multi-round feature counts for progressive testing
FEATURE_ROUNDS=(100 400 1000)

# Test configuration
SKIP_DEPLOY=false
QUICK_MODE=false
STABILIZATION_TIME=30

# Breakpoint test: step the rate from BP_START_RPS by BP_STEP_RPS up to BP_MAX_RPS
BP_START_RPS="${BP_START_RPS:-100}"
BP_STEP_RPS="${BP_STEP_RPS:-100}"
BP_MAX_RPS="${BP_MAX_RPS:-5000}"
BP_STEP_DURATION="${BP_STEP_DURATION:-60s}"
SLO_P99_MS="${SLO_P99_MS:-50}"
K6_MAX_VUS="${K6_MAX_VUS:-500}"

# Steady-state test: STEADY_RPS, or STEADY_FRACTION of the max sustainable RPS
STEADY_RPS="${STEADY_RPS:-}"
STEADY_FRACTION="${STEADY_FRACTION:-0.7}"
STEADY_DURATION="${STEADY_DURATION:-10m}"

# Monitoring stack (docker-compose.monitoring.yml)
MONITORING=true
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9095}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3300}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --profiles)
      IFS=' ' read -r -a PROFILES <<< "$2"
      shift 2
      ;;
    --skip-deploy)
      SKIP_DEPLOY=true
      shift
      ;;
    --features)
      IFS=' ' read -r -a FEATURE_ROUNDS <<< "$2"
      shift 2
      ;;
    --steady-rps)
      STEADY_RPS="$2"
      shift 2
      ;;
    --no-monitoring)
      MONITORING=false
      shift
      ;;
    --quick)
      QUICK_MODE=true
      STABILIZATION_TIME=10
      BP_STEP_DURATION=20s
      STEADY_DURATION=1m
      shift
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --profiles \"profile1 profile2\"  Test specific profiles (default: all)"
      echo "  --features \"100 1000\"           Feature counts to test (default: ${FEATURE_ROUNDS[*]})"
      echo "  --steady-rps N                   Fixed steady-state RPS (default: ${STEADY_FRACTION} x breakpoint)"
      echo "  --skip-deploy                    Skip deployment step"
      echo "  --no-monitoring                  Do not start Prometheus/Grafana"
      echo "  --quick                          Run quick tests (reduced duration)"
      echo "  --help                           Show this help message"
      echo ""
      echo "Environment Variables:"
      echo "  ENVIRONMENT_ID    (required) Environment ID for testing"
      echo "  EDGE_URL          (optional) Edge server URL (default: http://localhost:8081)"
      echo "  BACKEND_URL       (optional) Backend URL (default: http://localhost:8080)"
      echo "  BP_START_RPS, BP_STEP_RPS, BP_MAX_RPS, BP_STEP_DURATION  Breakpoint steps (default: 100, 100, 5000, 60s)"
      echo "  SLO_P99_MS        p99 latency SLO per step (default: 50)"
      echo "  <NAME>_<profile>  Per-profile override of BP_* and K6_MAX_VUS, e.g. BP_STEP_RPS_xlarge=1000"
      echo "  STEADY_FRACTION, STEADY_DURATION  Steady-state load and length (default: 0.7, 10m)"
      echo ""
      echo "Example:"
      echo "  export ENVIRONMENT_ID=\"78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017\""
      echo "  $0 --profiles \"tiny small medium\""
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Print colored message
print_msg() {
  local color=$1
  local msg=$2
  echo -e "${color}${msg}${NC}"
}

# Print section header
print_header() {
  local msg=$1
  echo ""
  print_msg "$CYAN" "========================================"
  print_msg "$CYAN" "$msg"
  print_msg "$CYAN" "========================================"
}

# Print success
print_success() {
  print_msg "$GREEN" "✓ $1"
}

# Print error
print_error() {
  print_msg "$RED" "✗ $1"
}

# Print warning
print_warning() {
  print_msg "$YELLOW" "⚠ $1"
}

# Execute a SQL query against the performance database
psql_query() {
  local sql=$1
  local output
  if ! output=$(PGPASSWORD="$DB_PASSWORD" psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      -At -c "$sql" 2>/dev/null); then
    return 1
  fi
  echo "$output"
}

# Fetch deployed feature keys for the active environment
# Uses features starting from feature=10000 for consistent perf testing
fetch_deployed_feature_keys() {
  local limit=${1:-$SEED_FEATURE_LIMIT}
  local start_index=10000
  if [ -z "$ENVIRONMENT_ID" ]; then
    return 1
  fi

  # Generate feature keys: feature=10000, feature=10001, ..., feature=10000+N-1
  # This matches the keys used in k6 tests and Postman data
  local keys=""
  for (( i=0; i<limit; i++ )); do
    local feature_num=$((start_index + i))
    keys="${keys}feature=${feature_num}"$'\n'
  done

  echo "$keys"
}

# Warm up the system by evaluating a subset of deployed features
seed_feature_evaluations() {
  local profile=$1
  local feature_keys

  feature_keys=$(fetch_deployed_feature_keys "$SEED_FEATURE_LIMIT") || {
    print_warning "Could not fetch deployed features for environment $ENVIRONMENT_ID"
    return
  }

  if [ -z "$feature_keys" ]; then
    print_warning "No deployed features found in features_pipeline_stages for environment $ENVIRONMENT_ID"
    return
  fi

  print_msg "$BLUE" "Seeding evaluation events for profile '$profile' using deployed features..."

  local total=0
  local success=0

  while IFS= read -r feature_key; do
    [ -z "$feature_key" ] && continue
    total=$((total + 1))
    local bucketing_key="seed-user-${profile}-${RANDOM}-${total}"
    local payload
    payload=$(cat <<EOF
{
  "flagKey": "$feature_key",
  "context": {
    "bucketingKey": "$bucketing_key",
    "environment_id": "$ENVIRONMENT_ID",
    "region": "us-east",
    "tier": "pro",
    "userRole": "admin",
    "deviceType": "desktop",
    "osType": "linux",
    "appVersion": "v2.0",
    "language": "en",
    "country": "US",
    "beta": "true"
  }
EOF
)

    if [ -n "$CLIENT_ID" ] && [ -n "$CLIENT_SECRET" ]; then
      payload+=$(cat <<EOF
,
  "client_id": "$CLIENT_ID",
  "client_secret": "$CLIENT_SECRET"
EOF
)
    fi
    payload+="}"

    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Content-Type: application/json" \
      -d "$payload" \
      "$EDGE_URL/evaluate" || true)

    if [ "$status" = "200" ]; then
      success=$((success + 1))
    fi
  done <<< "$feature_keys"

  if [ "$success" -gt 0 ]; then
    print_success "Seeded $success/$total deployed features (profile: $profile)"
  else
    print_warning "Seeding requests completed but no successful responses were recorded"
  fi
}

# Verify prerequisites
check_prerequisites() {
  print_header "Checking Prerequisites"

  # Check environment ID
  if [ -z "$ENVIRONMENT_ID" ]; then
    print_error "ENVIRONMENT_ID not set!"
    echo "Please set ENVIRONMENT_ID environment variable:"
    echo "  export ENVIRONMENT_ID=\"your-env-id-here\""
    exit 1
  fi
  print_success "Environment ID: $ENVIRONMENT_ID"

  # Check docker-compose
  if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    print_error "docker-compose not found!"
    exit 1
  fi
  print_success "docker-compose available"

  # Check k6
  if ! command -v k6 &> /dev/null; then
    print_error "k6 not found!"
    echo "Install k6: https://k6.io/docs/get-started/installation/"
    exit 1
  fi
  print_success "k6 installed: $(k6 version --quiet)"

  # Check jq and python3 for result processing
  for tool in jq python3; do
    if ! command -v "$tool" &> /dev/null; then
      print_error "$tool not found!"
      exit 1
    fi
  done
  print_success "jq and python3 available"

  # Check psql for database queries
  if ! command -v psql &> /dev/null; then
    print_error "psql not found!"
    exit 1
  fi
  print_success "psql available"
}

# Deploy with specific profile
deploy_profile() {
  local profile=$1

  print_header "Deploying Profile: $profile"

  if [ "$SKIP_DEPLOY" = true ]; then
    print_warning "Skipping deployment (--skip-deploy flag set)"
    return
  fi

  # Stop any existing containers and clear edge server cache
  print_msg "$BLUE" "Stopping existing containers and clearing cache..."
  docker-compose -f docker-compose.base.yml down 2>/dev/null || true

  # Remove edge container to ensure fresh cache (in-memory cache only, no volumes)
  docker rm -f fluxgate-perf-edge 2>/dev/null || true

  # Start with specific profile
  print_msg "$BLUE" "Starting services with $profile profile..."
  docker-compose $(compose_files "$profile") up -d

  # Wait for services to be healthy
  print_msg "$BLUE" "Waiting for services to be healthy..."
  local max_wait=120
  local elapsed=0
  while [ $elapsed -lt $max_wait ]; do
    if docker ps | grep "fluxgate-perf-backend" | grep -q "Up" && docker ps | grep "fluxgate-perf-edge" | grep -q "Up"; then
      break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  if [ $elapsed -ge $max_wait ]; then
    print_error "Services failed to start within ${max_wait}s"
    docker-compose -f docker-compose.base.yml logs
    return 1
  fi

  # Stabilization period
  print_msg "$BLUE" "Stabilizing for ${STABILIZATION_TIME}s..."
  sleep "$STABILIZATION_TIME"

  # Verify backend is accessible
  print_msg "$BLUE" "Checking backend..."
  if curl -sf "$BACKEND_URL/api/v1/health" > /dev/null 2>&1; then
    print_success "Backend is accessible"
  else
    print_warning "Backend may not be fully ready"
  fi

  # Display container info
  print_msg "$BLUE" "Container status:"
  docker-compose -f docker-compose.base.yml ps
  echo ""

  print_success "Profile $profile deployed"
}

# Compose files for the test stack. The cgroups overlay lets cAdvisor report
# per-container CPU and memory (see docker-compose.cgroups.yml).
compose_files() {
  local profile=$1
  local files="-f docker-compose.base.yml"
  if [ "$MONITORING" = true ]; then
    files="$files -f docker-compose.cgroups.yml"
  fi
  if [ -n "$profile" ]; then
    files="$files -f docker-compose.${profile}.yml"
  fi
  echo "$files"
}

# Start Prometheus, Grafana, cAdvisor and postgres_exporter
start_monitoring() {
  if [ "$MONITORING" != true ]; then
    return
  fi

  print_header "Starting Monitoring Stack"
  docker-compose -f docker-compose.monitoring.yml up -d

  local elapsed=0
  until curl -sf "$PROMETHEUS_URL/-/ready" > /dev/null 2>&1; do
    if [ $elapsed -ge 60 ]; then
      print_error "Prometheus not ready at $PROMETHEUS_URL after 60s"
      exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  print_success "Prometheus ready: $PROMETHEUS_URL"
  print_success "Grafana dashboard: $GRAFANA_URL/d/fluxgate-perf"
}

# Run k6-tests/breakpoint-test.js
#   run_k6 <out_dir> <test_name> <testid> <feature_count> [-e KEY=VALUE ...]
# k6 exits with 99 when an abort threshold stops a breakpoint run; that is the
# expected way for the run to end, so only other exit codes are reported.
run_k6() {
  local out_dir=$1
  local test_name=$2
  local testid=$3
  local feature_count=$4
  shift 4

  local outputs=(-o web-dashboard)
  if [ "$MONITORING" = true ]; then
    outputs+=(-o experimental-prometheus-rw)
  fi

  local status=0
  K6_WEB_DASHBOARD_EXPORT="${out_dir}/${test_name}-report.html" \
  K6_WEB_DASHBOARD_PORT=-1 \
  K6_PROMETHEUS_RW_SERVER_URL="${PROMETHEUS_URL}/api/v1/write" \
  K6_PROMETHEUS_RW_PUSH_INTERVAL=2s \
  K6_FEATURES=native-histograms \
  k6 run --quiet \
    "${outputs[@]}" \
    --tag testid="$testid" \
    -e EDGE_URL="$EDGE_URL" \
    -e ENVIRONMENT_ID="$ENVIRONMENT_ID" \
    -e TOTAL_FEATURES="$feature_count" \
    -e SLO_P99_MS="$SLO_P99_MS" \
    -e RESULTS_DIR="$out_dir" \
    -e TEST_NAME="$test_name" \
    "$@" \
    "${K6_TESTS_DIR}/breakpoint-test.js" \
    > "${out_dir}/${test_name}.log" 2>&1 || status=$?

  if [ "$status" -ne 0 ] && [ "$status" -ne 99 ]; then
    print_warning "k6 exited with code $status, see ${out_dir}/${test_name}.log"
  fi

  if [ "$MONITORING" = true ] && [ -f "${out_dir}/${test_name}.json" ]; then
    python3 ./collect-resource-metrics.py "${out_dir}/${test_name}.json" --prometheus "$PROMETHEUS_URL" > /dev/null \
      || print_warning "Could not add resource metrics to ${test_name}.json"
  fi
}

# Value of a setting for one profile: <NAME>_<profile> when set, else <NAME>.
# Example: BP_STEP_RPS_xlarge=1000 BP_MAX_RPS_xlarge=40000
profile_setting() {
  local name=$1
  local profile=$2
  local override="${name}_${profile}"
  echo "${!override:-${!name}}"
}

# Step the load up until the edge breaks the SLO
run_breakpoint_test() {
  local profile=$1
  local round_dir=$2
  local feature_count=$3

  local start_rps step_rps max_rps step_duration
  start_rps=$(profile_setting BP_START_RPS "$profile")
  step_rps=$(profile_setting BP_STEP_RPS "$profile")
  max_rps=$(profile_setting BP_MAX_RPS "$profile")
  step_duration=$(profile_setting BP_STEP_DURATION "$profile")

  print_msg "$BLUE" "Running breakpoint test with ${feature_count} features (${start_rps} to ${max_rps} RPS by ${step_rps}, ${step_duration} per step)..."

  run_k6 "$round_dir" "breakpoint" "${profile}-${feature_count}f-breakpoint" "$feature_count" \
    -e START_RPS="$start_rps" \
    -e STEP_RPS="$step_rps" \
    -e MAX_RPS="$max_rps" \
    -e STEP_DURATION="$step_duration" \
    -e MAX_VUS="$(profile_setting K6_MAX_VUS "$profile")"

  local max_rps
  max_rps=$(jq -r '.maxSustainableRps // "none"' "${round_dir}/breakpoint.json" 2>/dev/null || echo "none")
  print_success "Breakpoint test completed: max sustainable RPS = ${max_rps}"
}

# Hold a constant load: STEADY_RPS, or STEADY_FRACTION of the breakpoint
run_steady_test() {
  local profile=$1
  local round_dir=$2
  local feature_count=$3

  local rps="$STEADY_RPS"
  if [ -z "$rps" ]; then
    local max_rps
    max_rps=$(jq -r '.maxSustainableRps // 0' "${round_dir}/breakpoint.json" 2>/dev/null || echo 0)
    rps=$(awk -v max="$max_rps" -v fraction="$STEADY_FRACTION" 'BEGIN { printf "%d", int(max * fraction / 10) * 10 }')
  fi

  if [ "$rps" -le 0 ]; then
    print_warning "No sustainable RPS found, skipping steady-state test"
    return
  fi

  # Start from a fresh edge: its memory grows with the users and flags it has
  # seen, so a steady run right after the breakpoint run would inherit that.
  print_msg "$BLUE" "Restarting edge for a clean steady-state run..."
  docker-compose $(compose_files "$profile") restart edge > /dev/null
  sleep 15

  print_msg "$BLUE" "Running steady-state test @ ${rps} RPS for ${STEADY_DURATION} with ${feature_count} features..."

  run_k6 "$round_dir" "steady" "${profile}-${feature_count}f-steady" "$feature_count" \
    -e START_RPS="$rps" \
    -e STEP_RPS=0 \
    -e MAX_RPS="$rps" \
    -e STEP_DURATION="$STEADY_DURATION" \
    -e MAX_VUS="$(profile_setting K6_MAX_VUS "$profile")"

  print_success "Steady-state test @ ${rps} RPS completed"
}

# Collect metrics and logs
collect_metrics() {
  local profile=$1
  local profile_dir=$2

  print_msg "$BLUE" "Collecting metrics and logs..."

  # Container stats (final snapshot)
  docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
    fluxgate-perf-edge fluxgate-perf-backend > "${profile_dir}/container-stats.txt" 2>&1 || echo "Stats not available" > "${profile_dir}/container-stats.txt"

  # Container logs
  docker-compose -f docker-compose.base.yml logs backend --tail=1000 > "${profile_dir}/backend-logs.txt"
  docker-compose -f docker-compose.base.yml logs edge --tail=1000 > "${profile_dir}/edge-logs.txt"

  # Container inspect
  docker inspect fluxgate-perf-edge > "${profile_dir}/edge-inspect.json"
  docker inspect fluxgate-perf-backend > "${profile_dir}/backend-inspect.json"

  # Generate resource visualizations if metrics file exists
  local metrics_file="${profile_dir}/resource-metrics.csv"
  if [ -f "$metrics_file" ]; then
    print_msg "$BLUE" "Generating resource visualizations..."

    # Check if Python and required libraries are available
    if command -v python3 &> /dev/null; then
      if python3 -c "import pandas, matplotlib" 2>/dev/null; then
        python3 ./visualize-metrics.py "$metrics_file" "$profile_dir" 2>&1 | while read line; do
          echo "  $line"
        done
        print_msg "$GREEN" "✓ Resource visualizations generated"
      else
        print_warning "Python pandas/matplotlib not available, skipping visualization"
        print_msg "$YELLOW" "  Install with: pip3 install pandas matplotlib"
      fi
    else
      print_warning "Python3 not available, skipping visualization"
    fi
  fi

  print_success "Metrics collected"
}

# Run single test round with specific feature count
run_test_round() {
  local profile=$1
  local profile_dir=$2
  local feature_count=$3
  local round_num=$4

  local round_name="round${round_num}-${feature_count}f"
  local round_dir="${profile_dir}/${round_name}"

  mkdir -p "$round_dir"

  print_header "Round ${round_num}: Testing with ${feature_count} features"

  # Clear edge cache before each round (restart edge container)
  print_msg "$BLUE" "Clearing edge cache for fresh round..."
  docker-compose $(compose_files "$profile") restart edge
  sleep 5  # Wait for edge to reconnect

  run_breakpoint_test "$profile" "$round_dir" "$feature_count"

  # Let the edge recover from saturation before the steady-state run
  print_msg "$YELLOW" "Cooling down for 30 seconds..."
  sleep 30

  run_steady_test "$profile" "$round_dir" "$feature_count"

  print_success "Round ${round_num} (${feature_count} features) completed"
}

# Run all tests for a profile
run_tests_for_profile() {
  local profile=$1
  local profile_dir="${RESULTS_DIR}/${profile}"

  mkdir -p "$profile_dir"

  print_header "Testing Profile: $profile"

  # Deploy profile
  if ! deploy_profile "$profile"; then
    print_error "Failed to deploy profile $profile, skipping tests"
    return 1
  fi

  # Seed successful evaluations so analytics tables record activity
  seed_feature_evaluations "$profile"

  # Without the monitoring stack, sample docker stats in the background
  local metrics_file="${profile_dir}/resource-metrics.csv"
  local monitor_pid=""

  if [ "$MONITORING" != true ]; then
    print_msg "$BLUE" "Starting resource monitoring (1s interval)..."
    ./monitor-resources.sh "$metrics_file" 1 > /dev/null 2>&1 &
    monitor_pid=$!
    echo "$monitor_pid" > "${profile_dir}/.monitor_pid"
    print_msg "$GREEN" "✓ Resource monitoring started (PID: $monitor_pid)"

    # Wait a moment for monitoring to initialize
    sleep 2
  fi

  # Run multiple rounds with different feature counts
  local round_num=1
  for feature_count in "${FEATURE_ROUNDS[@]}"; do
    run_test_round "$profile" "$profile_dir" "$feature_count" "$round_num"

    # Cool down between rounds
    if [ "$round_num" -lt "${#FEATURE_ROUNDS[@]}" ]; then
      print_msg "$YELLOW" "Cooling down for 30 seconds before next round..."
      sleep 30
    fi

    round_num=$((round_num + 1))
  done

  # Stop resource monitoring
  if [ -n "$monitor_pid" ] && kill -0 "$monitor_pid" 2>/dev/null; then
    print_msg "$BLUE" "Stopping resource monitoring..."
    kill -SIGTERM "$monitor_pid" 2>/dev/null || true
    wait "$monitor_pid" 2>/dev/null || true
    rm -f "${profile_dir}/.monitor_pid"
    print_msg "$GREEN" "✓ Resource monitoring stopped"
  fi

  # Collect final metrics and logs
  collect_metrics "$profile" "$profile_dir"

  print_success "All tests completed for profile: $profile"

  # Cool down before next profile
  if [ "$QUICK_MODE" = false ]; then
    print_msg "$YELLOW" "Cooling down for 60 seconds before next profile..."
    sleep 60
  fi
}

# Record what was tested: images, host, tools and test settings
write_environment() {
  local compose_json
  compose_json=$(docker-compose -f docker-compose.base.yml config --format json 2>/dev/null)
  local images=()
  local service image
  for service in edge backend postgres; do
    image=$(jq -r --arg s "$service" '.services[$s].image' <<< "$compose_json")
    images+=("$(jq -n --arg service "$service" --arg image "$image" \
      --arg id "$(docker image inspect --format '{{.Id}}' "$image" 2>/dev/null)" \
      --arg created "$(docker image inspect --format '{{.Created}}' "$image" 2>/dev/null)" \
      '{service: $service, image: $image, id: $id, created: $created}')")
  done

  local profiles_json="[]"
  local profile
  for profile in "${PROFILES[@]}"; do
    profiles_json=$(jq --arg p "$profile" \
      --arg start "$(profile_setting BP_START_RPS "$profile")" \
      --arg step "$(profile_setting BP_STEP_RPS "$profile")" \
      --arg max "$(profile_setting BP_MAX_RPS "$profile")" \
      --arg dur "$(profile_setting BP_STEP_DURATION "$profile")" \
      --arg vus "$(profile_setting K6_MAX_VUS "$profile")" \
      --argjson limits "$(docker-compose -f docker-compose.base.yml -f "docker-compose.${profile}.yml" config --format json 2>/dev/null | jq '.services.edge.deploy.resources')" \
      '. + [{profile: $p, edgeResources: $limits, breakpoint: {startRps: ($start | tonumber), stepRps: ($step | tonumber), maxRps: ($max | tonumber), stepDuration: $dur}, k6MaxVus: ($vus | tonumber)}]' \
      <<< "$profiles_json")
  done

  jq -n \
    --arg date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson images "$(printf '%s\n' "${images[@]}" | jq -s .)" \
    --arg docker "$(docker version --format '{{.Server.Version}} ({{.Server.Os}}/{{.Server.Arch}})' 2>/dev/null)" \
    --arg dockerHost "$(docker info --format '{{.OperatingSystem}}' 2>/dev/null)" \
    --arg dockerCpus "$(docker info --format '{{.NCPU}}' 2>/dev/null)" \
    --arg dockerMemory "$(docker info --format '{{.MemTotal}}' 2>/dev/null)" \
    --arg hostCpu "$(sysctl -n machdep.cpu.brand_string 2>/dev/null || grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2)" \
    --arg hostOs "$(uname -srm)" \
    --arg k6 "$(k6 version --quiet 2>/dev/null | head -1)" \
    --arg edgeConfig "$(grep -vE '^(client_id|client_secret)' config/edge-config.toml)" \
    --argjson features "$(printf '%s\n' "${FEATURE_ROUNDS[@]}" | jq -s .)" \
    --argjson profiles "$profiles_json" \
    --arg sloP99 "$SLO_P99_MS" --arg steadyFraction "$STEADY_FRACTION" --arg steadyDuration "$STEADY_DURATION" \
    '{
      date: $date,
      images: $images,
      docker: {version: $docker, host: $dockerHost, cpus: ($dockerCpus | tonumber), memoryBytes: ($dockerMemory | tonumber)},
      host: {cpu: ($hostCpu | gsub("^ +"; "")), os: $hostOs},
      loadGenerator: $k6,
      edgeConfig: $edgeConfig,
      featureCounts: $features,
      profiles: $profiles,
      slo: {p99Ms: ($sloP99 | tonumber), errorRate: 0.01, droppedRatio: 0.01},
      steadyState: {fractionOfBreakpoint: ($steadyFraction | tonumber), duration: $steadyDuration}
    }' > "${RESULTS_DIR}/environment.json"
  print_success "Environment recorded: ${RESULTS_DIR}/environment.json"
}

# Generate summary report
generate_report() {
  print_header "Generating Summary Report"

  local report_file="${RESULTS_DIR}/SUMMARY.md"
  local edge_image
  edge_image=$(docker-compose -f docker-compose.base.yml config --format json 2>/dev/null | jq -r '.services.edge.image')

  cat > "$report_file" << EOF
# FluxGate Performance Test Results

**Test Date**: $(date)
**Environment ID**: $ENVIRONMENT_ID

## Test Environment

- **Edge image**: ${edge_image}
- **Docker**: $(docker version --format '{{.Server.Version}} ({{.Server.Os}}/{{.Server.Arch}})' 2>/dev/null)
- **Docker host**: $(docker info --format '{{.OperatingSystem}}, {{.NCPU}} CPUs, {{.MemTotal}} bytes memory' 2>/dev/null)
- **Load generator**: $(k6 version --quiet 2>/dev/null | head -1), on $(uname -sm)

## Test Configuration

- **Profiles tested**: ${PROFILES[*]}
- **Feature counts**: ${FEATURE_ROUNDS[*]}
- **Breakpoint steps**: ${BP_START_RPS} to ${BP_MAX_RPS} RPS by ${BP_STEP_RPS}, ${BP_STEP_DURATION} per step
- **SLO per step**: p99 <= ${SLO_P99_MS} ms, errors <= 1%, dropped requests <= 1%
- **Steady state**: ${STEADY_RPS:-${STEADY_FRACTION} x max sustainable RPS} for ${STEADY_DURATION}
- **Quick mode**: $QUICK_MODE

Max sustainable RPS is the step before the first SLO miss that repeats in the next step (or ends the run).
Latency and resource columns come from the steady-state run.

## Results

| Profile | Features | Max sustainable RPS | Broke at | Steady RPS | p50 ms | p95 ms | p99 ms | Edge CPU avg / limit | Edge throttled | Edge mem max / limit |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
EOF

  local details=""
  for profile in "${PROFILES[@]}"; do
    local profile_dir="${RESULTS_DIR}/${profile}"
    [ -d "$profile_dir" ] || continue

    local round_num=1
    for feature_count in "${FEATURE_ROUNDS[@]}"; do
      local round_name="round${round_num}-${feature_count}f"
      local round_dir="${profile_dir}/${round_name}"
      round_num=$((round_num + 1))
      [ -f "${round_dir}/breakpoint.json" ] || continue

      local steady_file="${round_dir}/steady.json"
      [ -f "$steady_file" ] || steady_file="/dev/null"

      jq -r -n \
        --arg profile "$profile" \
        --arg features "$feature_count" \
        --slurpfile bp "${round_dir}/breakpoint.json" \
        --slurpfile steady "$steady_file" '
        def num(v; d): if v == null then "-" else (v * pow(10; d) | round / pow(10; d) | tostring) end;
        def mib(v): if v == null then "-" else ((v / 1048576 | round | tostring) + " MiB") end;
        ($bp[0]) as $b
        | ($steady[0].steps[0] // {}) as $s
        | ($s.resources.edge // {}) as $e
        | "| \($profile) | \($features) | \($b.maxSustainableRps // "none") | "
          + (if $b.breakingStep then "\($b.breakingStep.targetRps) RPS: \($b.breakingStep.failures | join(", "))" else "not reached" end)
          + " | \($s.targetRps // "-") | \(num($s.latencyMs.p50; 2)) | \(num($s.latencyMs.p95; 2)) | \(num($s.latencyMs.p99; 2))"
          + " | \(num($e.cpu_avg_cores; 2)) / \(num($e.cpu_limit_cores; 2))"
          + " | " + (if $e.cpu_throttled_ratio == null then "-" else num($e.cpu_throttled_ratio * 100; 1) + "%" end)
          + " | \(mib($e.memory_max_bytes)) / \(mib($e.memory_limit_bytes)) |"
        ' >> "$report_file"

      details+="- **${profile}, ${feature_count} features**: [breakpoint](${profile}/${round_name}/breakpoint.md)"
      details+=" ([HTML report](${profile}/${round_name}/breakpoint-report.html))"
      if [ -f "${round_dir}/steady.json" ]; then
        details+=", [steady state](${profile}/${round_name}/steady.md)"
        details+=" ([HTML report](${profile}/${round_name}/steady-report.html))"
      fi
      details+=$'\n'
    done
  done

  cat >> "$report_file" << EOF

## Per-step Details

${details}
Each test directory also holds the full k6 summary (\`*-k6-summary.json\`), the k6 log,
and per-step CPU and memory for edge, backend and postgres inside the result JSON.
EOF

  if [ "$MONITORING" = true ]; then
    cat >> "$report_file" << EOF

Live and historical graphs: ${GRAFANA_URL}/d/fluxgate-perf (select a run in the "Test run" variable).
EOF
  fi

  print_success "Summary report generated: $report_file"
  echo ""
  print_msg "$CYAN" "View report: cat $report_file"
}

# Main execution
main() {
  print_header "FluxGate Performance Test Suite (Docker Compose)"

  echo "Configuration:"
  echo "  Environment ID: $ENVIRONMENT_ID"
  echo "  Edge URL:       $EDGE_URL"
  echo "  Backend URL:    $BACKEND_URL"
  echo "  Results Dir:    $RESULTS_DIR"
  echo "  Profiles:       ${PROFILES[*]}"
  echo "  Feature Rounds: ${FEATURE_ROUNDS[*]}"
  echo "  Breakpoint:     ${BP_START_RPS}..${BP_MAX_RPS} RPS by ${BP_STEP_RPS}, ${BP_STEP_DURATION}/step, SLO p99 ${SLO_P99_MS}ms"
  echo "  Steady State:   ${STEADY_RPS:-${STEADY_FRACTION} x breakpoint} for ${STEADY_DURATION}"
  echo "  Monitoring:     $MONITORING"
  echo "  Quick Mode:     $QUICK_MODE"
  echo "  Skip Deploy:    $SKIP_DEPLOY"
  echo "  DB Host:        ${DB_HOST}:${DB_PORT} (${DB_NAME})"
  echo "  Seed Limit:     $SEED_FEATURE_LIMIT features"
  echo ""

  # Check prerequisites
  check_prerequisites

  start_monitoring

  # Create results directory
  mkdir -p "$RESULTS_DIR"
  print_success "Results directory created: $RESULTS_DIR"

  # Save test configuration
  write_environment

  cat > "${RESULTS_DIR}/test-config.txt" << EOF
Test Date: $(date)
Environment ID: $ENVIRONMENT_ID
Edge URL: $EDGE_URL
Backend URL: $BACKEND_URL
Profiles: ${PROFILES[*]}
Feature Rounds: ${FEATURE_ROUNDS[*]}
Breakpoint: ${BP_START_RPS}..${BP_MAX_RPS} RPS by ${BP_STEP_RPS}, ${BP_STEP_DURATION} per step
SLO p99: ${SLO_P99_MS} ms
Steady State: ${STEADY_RPS:-${STEADY_FRACTION} x breakpoint} for ${STEADY_DURATION}
Monitoring: $MONITORING
Quick Mode: $QUICK_MODE
Skip Deploy: $SKIP_DEPLOY
Deployment: Docker Compose
DB Host: ${DB_HOST}:${DB_PORT}
DB Name: ${DB_NAME}
Seeded Features Per Profile: $SEED_FEATURE_LIMIT
EOF

  # Run tests for each profile
  local start_time=$(date +%s)
  local failed_profiles=()

  for profile in "${PROFILES[@]}"; do
    if ! run_tests_for_profile "$profile"; then
      failed_profiles+=("$profile")
    fi
  done

  local end_time=$(date +%s)
  local duration=$((end_time - start_time))

  # Cleanup - stop containers
  print_header "Cleanup"
  docker-compose -f docker-compose.base.yml down
  print_success "Containers stopped"

  # Generate summary report
  generate_report

  # Print final summary
  print_header "Test Suite Complete!"

  print_success "Total duration: $((duration / 60)) minutes $((duration % 60)) seconds"
  print_success "Results saved to: $RESULTS_DIR"

  if [ ${#failed_profiles[@]} -gt 0 ]; then
    print_warning "Some profiles failed: ${failed_profiles[*]}"
    echo ""
    echo "Review logs in respective profile directories for details"
  fi

  echo ""
  print_msg "$GREEN" "Next steps:"
  echo "1. Review summary report: cat ${RESULTS_DIR}/SUMMARY.md"
  echo "2. Analyze detailed results in profile directories"
  echo "3. Compare performance across profiles"
  echo "4. Document recommendations"
  echo ""
}

# Run main function
main
