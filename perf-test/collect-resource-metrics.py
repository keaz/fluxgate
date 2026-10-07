#!/usr/bin/env python3
"""
Adds per-step container resource usage to a breakpoint test result.

Reads the JSON written by k6-tests/breakpoint-test.js, queries Prometheus
(docker-compose.monitoring.yml) for every step window and stores the result
under steps[].resources. A resource table is appended to the matching .md file.

Per service (edge, backend, postgres) and step:
  cpu_avg_cores, cpu_max_cores   CPU used, average and peak (1s resolution)
  cpu_limit_cores                CPU limit, null when unlimited
  cpu_throttled_ratio            share of CFS periods that hit the CPU limit
  memory_max_bytes               peak memory working set
  memory_limit_bytes             memory limit, null when unlimited
  oom_events                     OOM kills during the step

Usage:
  ./collect-resource-metrics.py results/.../breakpoint.json [--prometheus http://localhost:9095]

Only the Python standard library is used.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

SERVICES = ("edge", "backend", "postgres")

# Seconds skipped at the start of each step so the previous step's tail and
# the rate() window do not leak into the numbers.
SETTLE_SECS = 5


def query(prometheus, expr, at):
    url = f"{prometheus}/api/v1/query?" + urllib.parse.urlencode({"query": expr, "time": at})
    with urllib.request.urlopen(url, timeout=10) as response:
        body = json.load(response)
    if body.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed: {expr}: {body}")
    result = body["data"]["result"]
    if not result:
        return None
    value = float(result[0]["value"][1])
    return value if value == value else None  # NaN -> None


def step_resources(prometheus, service, start, end):
    window = int(end - start)
    if window < 2:
        # Short (aborted) step: use the whole step instead of skipping the start
        window = int(end - start + SETTLE_SECS)
    if window < 2:
        return None
    sel = f'service="{service}"'
    w = f"{window}s"
    queries = {
        "cpu_avg_cores": f"sum(increase(container_cpu_usage_seconds_total{{{sel}}}[{w}])) / {window}",
        "cpu_max_cores": f"max_over_time(sum(rate(container_cpu_usage_seconds_total{{{sel}}}[3s]))[{w}:1s])",
        "cpu_limit_cores": f"max(container_spec_cpu_quota{{{sel}}} / container_spec_cpu_period{{{sel}}})",
        "cpu_throttled_ratio": (
            f"sum(increase(container_cpu_cfs_throttled_periods_total{{{sel}}}[{w}])) / "
            f"sum(increase(container_cpu_cfs_periods_total{{{sel}}}[{w}]))"
        ),
        "memory_max_bytes": f"max(max_over_time(container_memory_working_set_bytes{{{sel}}}[{w}]))",
        "memory_limit_bytes": f"max(container_spec_memory_limit_bytes{{{sel}}} > 0)",
        "oom_events": f"sum(increase(container_oom_events_total{{{sel}}}[{w}]))",
    }
    values = {name: query(prometheus, expr, end) for name, expr in queries.items()}
    if all(v is None for v in values.values()):
        return None
    return {name: (round(v, 4) if v is not None else None) for name, v in values.items()}


def fmt(value, scale=1.0, digits=2, suffix=""):
    return "-" if value is None else f"{value / scale:.{digits}f}{suffix}"


def markdown(result):
    lines = [
        "",
        "## Resources per step",
        "",
        "| Target RPS | Service | CPU avg | CPU max | CPU limit | Throttled | Mem max | Mem limit | OOM |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    mib = 1024 * 1024
    for step in result["steps"]:
        for service, r in (step.get("resources") or {}).items():
            if r is None:
                continue
            lines.append(
                f"| {step['targetRps']} | {service} | {fmt(r['cpu_avg_cores'])} | {fmt(r['cpu_max_cores'])} | "
                f"{fmt(r['cpu_limit_cores'])} | {fmt(r['cpu_throttled_ratio'], 0.01, 1, '%')} | "
                f"{fmt(r['memory_max_bytes'], mib, 1, ' MiB')} | {fmt(r['memory_limit_bytes'], mib, 0, ' MiB')} | "
                f"{fmt(r['oom_events'], digits=0)} |"
            )
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("result", type=Path, help="JSON written by breakpoint-test.js")
    parser.add_argument("--prometheus", default="http://localhost:9095")
    args = parser.parse_args()

    result = json.loads(args.result.read_text())
    prometheus = args.prometheus.rstrip("/")

    try:
        for step in result["steps"]:
            if not step.get("startedAt"):
                continue
            start = datetime.fromisoformat(step["startedAt"].replace("Z", "+00:00")).timestamp() + SETTLE_SECS
            end = datetime.fromisoformat(step["endedAt"].replace("Z", "+00:00")).timestamp()
            step["resources"] = {s: step_resources(prometheus, s, start, end) for s in SERVICES}
    except OSError as error:
        print(f"Could not reach Prometheus at {prometheus}: {error}", file=sys.stderr)
        return 1

    args.result.write_text(json.dumps(result, indent=2) + "\n")
    md_path = args.result.with_suffix(".md")
    if md_path.exists():
        text = md_path.read_text().split("\n## Resources per step")[0].rstrip("\n") + "\n"
        md_path.write_text(text + markdown(result))
    print(f"Resource metrics added to {args.result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
