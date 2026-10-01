#!/bin/bash
#
# FluxGate Performance Test Automation Script (Docker Compose Version)
#
# This script automates the entire performance testing workflow using Docker Compose:
# 1. Deploys each resource profile sequentially
# 2. Runs steady-state tests at multiple load levels
# 3. Runs stress test to find max capacity
# 4. Collects metrics and logs
# 5. Generates summary report
#
# Usage:
#   export ENVIRONMENT_ID="your-env-id-here"
#   ./run-perf-tests.sh
#
# Options:
#   --profiles "tiny small medium"  # Test specific profiles only
#   --skip-deploy                   # Skip deployment (use existing)
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
STEADY_TESTS=(500)
STABILIZATION_TIME=30

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
    --quick)
      QUICK_MODE=true
      STEADY_TESTS=(500)
      STABILIZATION_TIME=10
      shift
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --profiles \"profile1 profile2\"  Test specific profiles (default: all)"
      echo "  --skip-deploy                    Skip deployment step"
      echo "  --quick                          Run quick tests (reduced duration)"
      echo "  --help                           Show this help message"
      echo ""
      echo "Environment Variables:"
      echo "  ENVIRONMENT_ID    (required) Environment ID for testing"
      echo "  EDGE_URL          (optional) Edge server URL (default: http://localhost:8081)"
      echo "  BACKEND_URL       (optional) Backend URL (default: http://localhost:8080)"
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
  docker-compose -f docker-compose.base.yml -f docker-compose.${profile}.yml up -d

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

# Run steady-state test
run_steady_test() {
  local profile=$1
  local rps=$2
  local profile_dir=$3
  local feature_count=$4
  local round_name=$5

  print_msg "$BLUE" "Running Steady State Test @ ${rps} RPS with ${feature_count} features (${round_name})..."

  local test_name="steady-${rps}-${round_name}"
  local extra_args=""

  if [ "$QUICK_MODE" = true ]; then
    extra_args="-e RAMP_UP_DURATION=30s -e STEADY_DURATION=2m -e RAMP_DOWN_DURATION=30s"
  fi

  k6 run \
    -e EDGE_URL="$EDGE_URL" \
    -e ENVIRONMENT_ID="$ENVIRONMENT_ID" \
    -e TARGET_RPS="$rps" \
    -e TOTAL_FEATURES="$feature_count" \
    $extra_args \
    --out json="${profile_dir}/${test_name}-raw.json" \
    "${K6_TESTS_DIR}/steady-state-test.js" \
    > "${profile_dir}/${test_name}.log" 2>&1

  # Copy summary if exists
  if [ -f "summary.json" ]; then
    mv summary.json "${profile_dir}/${test_name}-summary.json"
  fi

  print_success "Steady state test @ ${rps} RPS with ${feature_count} features completed"
}

# Run stress test
run_stress_test() {
  local profile=$1
  local profile_dir=$2
  local feature_count=$3
  local round_name=$4

  print_msg "$BLUE" "Running Stress Test with ${feature_count} features (${round_name})..."

  local test_name="stress-${round_name}"
  local extra_args=""
  if [ "$QUICK_MODE" = true ]; then
    extra_args="-e STAGE_DURATION=30s -e MAX_RPS=1000"
  fi

  k6 run \
    -e EDGE_URL="$EDGE_URL" \
    -e ENVIRONMENT_ID="$ENVIRONMENT_ID" \
    -e TOTAL_FEATURES="$feature_count" \
    $extra_args \
    --out json="${profile_dir}/${test_name}-raw.json" \
    "${K6_TESTS_DIR}/stress-test.js" \
    > "${profile_dir}/${test_name}.log" 2>&1

  # Copy summary if exists
  if [ -f "stress-test-summary.json" ]; then
    mv stress-test-summary.json "${profile_dir}/${test_name}-summary.json"
  fi

  print_success "Stress test with ${feature_count} features completed"
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
  docker-compose -f docker-compose.base.yml restart edge
  sleep 5  # Wait for edge to reconnect

  # Run steady-state tests at different RPS levels
  for rps in "${STEADY_TESTS[@]}"; do
    run_steady_test "$profile" "$rps" "$round_dir" "$feature_count" "$round_name"
  done

  # Run stress test
  run_stress_test "$profile" "$round_dir" "$feature_count" "$round_name"

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

  # Start resource monitoring in background
  local metrics_file="${profile_dir}/resource-metrics.csv"
  local monitor_pid=""

  print_msg "$BLUE" "Starting resource monitoring (1s interval)..."
  ./monitor-resources.sh "$metrics_file" 1 > /dev/null 2>&1 &
  monitor_pid=$!
  echo "$monitor_pid" > "${profile_dir}/.monitor_pid"
  print_msg "$GREEN" "✓ Resource monitoring started (PID: $monitor_pid)"

  # Wait a moment for monitoring to initialize
  sleep 2

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

# Generate summary report
generate_report() {
  print_header "Generating Summary Report"

  local report_file="${RESULTS_DIR}/SUMMARY.md"

  cat > "$report_file" << EOF
# FluxGate Performance Test Results (Docker Compose)

**Test Date**: $(date)
**Environment ID**: $ENVIRONMENT_ID
**Deployment**: Docker Compose

## Test Configuration

- **Edge URL**: $EDGE_URL
- **Backend URL**: $BACKEND_URL
- **Profiles Tested**: ${PROFILES[*]}
- **Feature Rounds**: ${FEATURE_ROUNDS[*]}
- **Steady State RPS Levels**: ${STEADY_TESTS[*]}
- **Quick Mode**: $QUICK_MODE

## Multi-Round Testing Strategy

Each profile is tested with progressive feature counts to demonstrate cache behavior:
- **Round 1**: ${FEATURE_ROUNDS[0]} features (baseline)
- **Round 2**: ${FEATURE_ROUNDS[1]} features (medium scale)
- **Round 3**: ${FEATURE_ROUNDS[2]} features (full scale)

This approach shows how cache hit rates and latency change with feature set size under weighted Pareto distribution (80/20 rule).

## Results by Profile

EOF

  for profile in "${PROFILES[@]}"; do
    local profile_dir="${RESULTS_DIR}/${profile}"

    if [ ! -d "$profile_dir" ]; then
      continue
    fi

    cat >> "$report_file" << EOF
### Profile: $profile

EOF

    # Iterate through each round
    local round_num=1
    for feature_count in "${FEATURE_ROUNDS[@]}"; do
      local round_name="round${round_num}-${feature_count}f"
      local round_dir="${profile_dir}/${round_name}"

      if [ ! -d "$round_dir" ]; then
        round_num=$((round_num + 1))
        continue
      fi

      cat >> "$report_file" << EOF
#### Round ${round_num}: ${feature_count} Features

EOF

      # Extract metrics from steady-state tests
      for rps in "${STEADY_TESTS[@]}"; do
        local summary_file="${round_dir}/steady-${rps}-${round_name}-summary.json"

        if [ -f "$summary_file" ] && command -v jq &> /dev/null; then
          cat >> "$report_file" << EOF
**Steady State @ ${rps} RPS**

\`\`\`
$(jq -r '
  "Total Requests:    " + (.metrics.http_reqs.values.count | tostring) + "\n" +
  "Request Rate:      " + (.metrics.http_reqs.values.rate | tostring) + " RPS\n" +
  "P50 Latency:       " + (.metrics.http_req_duration.values["p(50)"] | tostring) + " ms\n" +
  "P95 Latency:       " + (.metrics.http_req_duration.values["p(95)"] | tostring) + " ms\n" +
  "P99 Latency:       " + (.metrics.http_req_duration.values["p(99)"] | tostring) + " ms\n" +
  "Error Rate:        " + ((.metrics.http_req_failed.values.rate * 100) | tostring) + " %"
' "$summary_file")
\`\`\`

EOF
        fi
      done

      round_num=$((round_num + 1))
    done

    echo "" >> "$report_file"
  done

  cat >> "$report_file" << EOF
## Expected Cache Performance by Round

| Round | Features | Hot Set (20%) | Expected Hit Rate | Expected P95 |
|-------|----------|---------------|-------------------|--------------|
| 1 | ${FEATURE_ROUNDS[0]} | ${FEATURE_ROUNDS[0]}/5 (20 features) | ~90% | 4-6ms |
| 2 | ${FEATURE_ROUNDS[1]} | ${FEATURE_ROUNDS[1]}/5 (80 features) | ~85% | 5-7ms |
| 3 | ${FEATURE_ROUNDS[2]} | ${FEATURE_ROUNDS[2]}/5 (200 features) | ~82% | 6-8ms |

With weighted Pareto distribution (80/20 rule):
- 80% of requests target the hot 20% of features
- Hot features see high cache hit rates
- As feature count increases, cache pressure increases slightly

## Files Generated

- Individual test results in \`${RESULTS_DIR}/<profile>/<round>/\`
- Container stats and logs
- Raw k6 JSON output per round

## Docker Compose Details

All tests run using Docker Compose with resource limits applied via deploy.resources configuration.

EOF

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
  echo "  Quick Mode:     $QUICK_MODE"
  echo "  Skip Deploy:    $SKIP_DEPLOY"
  echo "  DB Host:        ${DB_HOST}:${DB_PORT} (${DB_NAME})"
  echo "  Seed Limit:     $SEED_FEATURE_LIMIT features"
  echo ""

  # Check prerequisites
  check_prerequisites

  # Create results directory
  mkdir -p "$RESULTS_DIR"
  print_success "Results directory created: $RESULTS_DIR"

  # Save test configuration
  cat > "${RESULTS_DIR}/test-config.txt" << EOF
Test Date: $(date)
Environment ID: $ENVIRONMENT_ID
Edge URL: $EDGE_URL
Backend URL: $BACKEND_URL
Profiles: ${PROFILES[*]}
Feature Rounds: ${FEATURE_ROUNDS[*]}
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
