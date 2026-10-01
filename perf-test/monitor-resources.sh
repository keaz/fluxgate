#!/usr/bin/env bash

# Resource Monitoring Script for FluxGate Performance Tests
# Captures CPU and memory usage over time during test execution
#
# Usage:
#   ./monitor-resources.sh <output_file> <interval_seconds>
#
# Example:
#   ./monitor-resources.sh ./results/metrics.csv 1

set -euo pipefail

OUTPUT_FILE="${1:-metrics.csv}"
INTERVAL="${2:-1}"  # Default: 1 second

# Containers to monitor
CONTAINERS=(
  "fluxgate-perf-edge"
  "fluxgate-perf-backend"
  "fluxgate-perf-postgres"
)

# Create output directory if it doesn't exist
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
mkdir -p "$OUTPUT_DIR"

# Write CSV header
echo "timestamp,container,cpu_percent,memory_usage_mb,memory_limit_mb,memory_percent,net_io_rx_mb,net_io_tx_mb,block_io_read_mb,block_io_write_mb" > "$OUTPUT_FILE"

echo "Starting resource monitoring..."
echo "Output: $OUTPUT_FILE"
echo "Interval: ${INTERVAL}s"
echo "Monitoring containers: ${CONTAINERS[*]}"
echo "Press Ctrl+C to stop"
echo ""

# Function to parse size (handles KB, MB, GB, etc.)
parse_size_to_mb() {
  local size=$1
  local value=$(echo "$size" | grep -oE '[0-9.]+')
  local unit=$(echo "$size" | grep -oE '[A-Za-z]+')

  case "$unit" in
    B|b)
      echo "scale=2; $value / 1024 / 1024" | bc
      ;;
    KB|KiB|kb|kib)
      echo "scale=2; $value / 1024" | bc
      ;;
    MB|MiB|mb|mib)
      echo "$value"
      ;;
    GB|GiB|gb|gib)
      echo "scale=2; $value * 1024" | bc
      ;;
    *)
      echo "0"
      ;;
  esac
}

# Cleanup function
cleanup() {
  echo ""
  echo "Monitoring stopped. Results saved to: $OUTPUT_FILE"
  exit 0
}

trap cleanup SIGINT SIGTERM

# Main monitoring loop
while true; do
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")

  # Get stats for all containers in one call for efficiency
  stats_output=$(docker stats --no-stream --format "{{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" 2>/dev/null || true)

  # Parse stats for each monitored container
  for container in "${CONTAINERS[@]}"; do
    # Check if container is running
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
      continue
    fi

    # Extract stats for this container
    container_stats=$(echo "$stats_output" | grep "$container" || true)

    if [ -z "$container_stats" ]; then
      continue
    fi

    # Parse fields
    cpu_percent=$(echo "$container_stats" | awk '{print $2}' | tr -d '%')
    mem_usage=$(echo "$container_stats" | awk '{print $3}' | cut -d'/' -f1 | tr -d ' ')
    mem_limit=$(echo "$container_stats" | awk '{print $3}' | cut -d'/' -f2 | tr -d ' ')
    mem_percent=$(echo "$container_stats" | awk '{print $4}' | tr -d '%')
    net_io=$(echo "$container_stats" | awk '{print $5}')
    block_io=$(echo "$container_stats" | awk '{print $6}')

    # Parse network I/O (format: "1.5MB / 2.3MB")
    net_rx=$(echo "$net_io" | cut -d'/' -f1 | tr -d ' ')
    net_tx=$(echo "$net_io" | cut -d'/' -f2 | tr -d ' ')
    net_rx_mb=$(parse_size_to_mb "$net_rx")
    net_tx_mb=$(parse_size_to_mb "$net_tx")

    # Parse block I/O (format: "10MB / 5MB")
    block_read=$(echo "$block_io" | cut -d'/' -f1 | tr -d ' ')
    block_write=$(echo "$block_io" | cut -d'/' -f2 | tr -d ' ')
    block_read_mb=$(parse_size_to_mb "$block_read")
    block_write_mb=$(parse_size_to_mb "$block_write")

    # Convert memory to MB
    mem_usage_mb=$(parse_size_to_mb "$mem_usage")
    mem_limit_mb=$(parse_size_to_mb "$mem_limit")

    # Write to CSV
    echo "${timestamp},${container},${cpu_percent},${mem_usage_mb},${mem_limit_mb},${mem_percent},${net_rx_mb},${net_tx_mb},${block_read_mb},${block_write_mb}" >> "$OUTPUT_FILE"
  done

  sleep "$INTERVAL"
done
