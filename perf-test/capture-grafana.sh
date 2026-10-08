#!/usr/bin/env bash
#
# Screenshots the "FluxGate Performance" Grafana dashboard for one test run.
#
# Usage:
#   ./capture-grafana.sh <result.json> <testid> <output-prefix>
#   ./capture-grafana.sh --all <results-dir> [<output-dir>]
#
# --all captures the breakpoint and steady-state run of every profile and
# feature count to <output-dir> (default <results-dir>/site/grafana) as
# <profile>-<features>f-{breakpoint,steady}-{light,dark}.png.
#
# Example:
#   ./capture-grafana.sh results/perf-results-X/small/round3-1000f/breakpoint.json \
#     small-1000f-breakpoint results/perf-results-X/site/grafana/small-breakpoint
#
# Writes <output-prefix>-light.png and <output-prefix>-dark.png. The time range
# is the run's start to the end of its last step, plus 10 seconds on each side.
# Needs Google Chrome and the monitoring stack (docker-compose.monitoring.yml).

set -euo pipefail

if [ "${1:-}" = "--all" ]; then
  results_dir=$2
  out_dir=${3:-$results_dir/site/grafana}
  for round_dir in "$results_dir"/*/round*-*f; do
    profile=$(basename "$(dirname "$round_dir")")
    features=$(basename "$round_dir" | sed -E 's/round[0-9]+-([0-9]+)f/\1/')
    name="${profile}-${features}f"
    [ -f "$round_dir/breakpoint.json" ] && "$0" "$round_dir/breakpoint.json" "${name}-breakpoint" "$out_dir/${name}-breakpoint"
    if [ -f "$round_dir/steady-verify.json" ]; then
      "$0" "$round_dir/steady-verify.json" "${name}-steady-verify" "$out_dir/${name}-steady"
    elif [ -f "$round_dir/steady.json" ]; then
      "$0" "$round_dir/steady.json" "${name}-steady" "$out_dir/${name}-steady"
    fi
  done
  exit 0
fi

RESULT_JSON=$1
TESTID=$2
PREFIX=$3
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3300}"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
WIDTH="${WIDTH:-1600}"
HEIGHT="${HEIGHT:-1640}"
# Seconds to let Grafana load data before the screenshot is taken
SETTLE_SECS="${SETTLE_SECS:-8}"

to_ms() {
  python3 -c "import sys; from datetime import datetime; print(int(datetime.fromisoformat(sys.argv[1].replace('Z', '+00:00')).timestamp() * 1000))" "$1"
}

from_ms=$(( $(to_ms "$(jq -r '.meta.startedAt' "$RESULT_JSON")") - 10000 ))
to_ms=$(( $(to_ms "$(jq -r '.steps[-1].endedAt' "$RESULT_JSON")") + 10000 ))

mkdir -p "$(dirname "$PREFIX")"
profile_dir=$(mktemp -d)
trap 'rm -rf "$profile_dir"' EXIT

for theme in light dark; do
  out="${PREFIX}-${theme}.png"
  rm -f "$out"
  url="${GRAFANA_URL}/d/fluxgate-perf?var-testid=${TESTID}&from=${from_ms}&to=${to_ms}&kiosk&theme=${theme}&refresh="

  # Headless Chrome can keep running after it writes the screenshot, so it is
  # stopped once the file exists.
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --user-data-dir="$profile_dir" \
    --window-size="${WIDTH},${HEIGHT}" --virtual-time-budget=$((SETTLE_SECS * 1000)) \
    --screenshot="$out" "$url" > /dev/null 2>&1 &
  chrome_pid=$!

  for _ in $(seq 1 60); do
    [ -s "$out" ] && break
    sleep 1
  done
  sleep 1
  kill "$chrome_pid" 2> /dev/null || true
  wait "$chrome_pid" 2> /dev/null || true

  if [ -s "$out" ]; then
    echo "Wrote $out"
  else
    echo "No screenshot for $theme ($url)" >&2
  fi
done
