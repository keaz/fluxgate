#!/usr/bin/env python3
"""
Generates grafana/dashboards/fluxgate-perf.json, the "FluxGate Performance"
Grafana dashboard. Edit this file instead of the JSON, then run:

  python3 monitoring/generate-dashboard.py

Grafana picks up the new JSON within a few seconds (file provisioning).
"""

import json
from pathlib import Path
DS = {"type": "prometheus", "uid": "prometheus"}
T = 'testid=~"$testid"'
panels, pid, y = [], 1, 0

def nid():
    global pid; pid += 1; return pid

def row(title):
    global y
    panels.append({"type": "row", "title": title, "id": nid(), "collapsed": False,
                   "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "panels": []})
    y += 1

def ts(title, targets, unit, x, w, desc="", overrides=None, h=8, stack=False, max_value=None):
    panels.append({
        "type": "timeseries", "title": title, "description": desc, "id": nid(), "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "fieldConfig": {"defaults": {"unit": unit, "min": 0, **({"max": max_value} if max_value is not None else {}),
                                      "custom": {"lineWidth": 2, "fillOpacity": 8, "showPoints": "never",
                                                 "spanNulls": False}},
                        "overrides": overrides or []},
        "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["mean", "max"]},
                    "tooltip": {"mode": "multi", "sort": "desc"}},
        "targets": [{"refId": chr(65 + i), "datasource": DS, "expr": e, "legendFormat": l, "range": True}
                    for i, (e, l) in enumerate(targets)],
    })

def stat(title, expr, unit, x, w, legend="", desc="", text_mode="value"):
    panels.append({
        "type": "stat", "title": title, "description": desc, "id": nid(), "datasource": DS,
        "gridPos": {"h": 4, "w": w, "x": x, "y": y},
        "fieldConfig": {"defaults": {"unit": unit, "decimals": 1, "color": {"mode": "fixed", "fixedColor": "blue"}}, "overrides": []},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "colorMode": "value", "graphMode": "none", "textMode": text_mode, "justifyMode": "auto"},
        "targets": [{"refId": "A", "datasource": DS, "expr": expr, "legendFormat": legend, "instant": True, "range": False}],
    })

dashed = lambda match: {"matcher": {"id": "byRegexp", "options": match},
                        "properties": [{"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 10]}},
                                       {"id": "custom.fillOpacity", "value": 0}]}
red = lambda name: {"matcher": {"id": "byName", "options": name},
                    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]}

# k6 pushes every few seconds and each load step is a new series, so k6 queries
# use a fixed window that always holds at least two pushes.
K6_WINDOW = "15s"


def q(p, w=K6_WINDOW):
    return f'histogram_quantile({p}, sum(rate(k6_http_req_duration_seconds{{{T}}}[{w}])))'

# Summary
stat("Peak RPS", f'max_over_time(sum(rate(k6_http_reqs_total{{{T}}}[{K6_WINDOW}]))[$__range:2s])', "reqps", 0, 4)
stat("Requests", f'sum(increase(k6_http_reqs_total{{{T}}}[$__range]))', "short", 4, 4)
stat("p99 (whole range)", f'histogram_quantile(0.99, sum(increase(k6_http_req_duration_seconds{{{T}}}[$__range])))', "s", 8, 4,
     desc="Includes every step in range, also the failing ones. The breakpoint JSON has per-step values.")
stat("Edge peak CPU", 'max_over_time(sum(rate(container_cpu_usage_seconds_total{service="edge"}[10s]))[$__range:2s])', "short", 12, 4,
     desc="Cores")
stat("Edge peak memory", 'max_over_time(container_memory_working_set_bytes{service="edge"}[$__range])', "bytes", 16, 4)
stat("OOM kills", 'sum by (service) (increase(container_oom_events_total[$__range]))', "short", 20, 4, legend="{{service}}", text_mode="value_and_name")
y += 4

row("Load and latency (k6)")
ts("Throughput", [
    (f'sum(rate(k6_http_reqs_total{{{T}}}[{K6_WINDOW}]))', "achieved RPS"),
    (f'sum(rate(k6_http_reqs_total{{{T},expected_response="false"}}[{K6_WINDOW}]))', "failed RPS"),
    (f'sum(rate(k6_dropped_iterations_total{{{T}}}[{K6_WINDOW}]))', "dropped RPS"),
], "reqps", 0, 12, desc="Dropped = requests k6 could not start because all VUs were busy; the edge is saturated.",
   overrides=[red("failed RPS"), red("dropped RPS")])
ts("Latency percentiles", [(q(p), l) for p, l in
                           [(0.5, "p50"), (0.9, "p90"), (0.95, "p95"), (0.99, "p99"), (0.999, "p99.9")]],
   "s", 12, 12, desc="From k6 native histograms, per scrape window.")
y += 8
ts("Latency p99 by step", [(f'histogram_quantile(0.99, sum by (scenario) (rate(k6_http_req_duration_seconds{{{T}}}[{K6_WINDOW}])))', "{{scenario}}")],
   "s", 0, 12)
ts("Virtual users and errors", [
    (f'sum(k6_vus{{{T}}})', "active VUs"),
    (f'max(k6_evaluation_errors_rate{{{T}}}) * 100', "evaluation errors % (cumulative)"),
], "short", 12, 12, desc="Evaluation errors = non-200 or errorCode in the response body.")
y += 8

row("Containers (cAdvisor)")
ts("CPU cores", [
    ('sum by (service) (rate(container_cpu_usage_seconds_total{service!=""}[$__rate_interval]))', "{{service}}"),
    ('max by (service) (container_spec_cpu_quota{service!=""} / container_spec_cpu_period{service!=""})', "{{service}} limit"),
], "short", 0, 8, overrides=[dashed(".* limit")])
ts("CPU throttled periods", [
    ('sum by (service) (rate(container_cpu_cfs_throttled_periods_total{service!=""}[$__rate_interval])) / '
     'sum by (service) (rate(container_cpu_cfs_periods_total{service!=""}[$__rate_interval]))', "{{service}}"),
], "percentunit", 8, 8, desc="Share of CFS periods in which the container hit its CPU limit.", max_value=1)
ts("Memory working set", [
    ('max by (service) (container_memory_working_set_bytes{service!=""})', "{{service}}"),
    ('max by (service) (container_spec_memory_limit_bytes{service!=""} > 0)', "{{service}} limit"),
], "bytes", 16, 8, overrides=[dashed(".* limit")])
y += 8

row("PostgreSQL")
DB = 'datname="feature_toggle"'
ts("Transactions", [
    (f'sum(rate(pg_stat_database_xact_commit{{{DB}}}[$__rate_interval]))', "commits/s"),
    (f'sum(rate(pg_stat_database_xact_rollback{{{DB}}}[$__rate_interval]))', "rollbacks/s"),
], "ops", 0, 6)
ts("Rows written", [
    (f'sum(rate(pg_stat_database_tup_inserted{{{DB}}}[$__rate_interval]))', "inserted/s"),
    (f'sum(rate(pg_stat_database_tup_updated{{{DB}}}[$__rate_interval]))', "updated/s"),
    (f'sum(rate(pg_stat_database_tup_deleted{{{DB}}}[$__rate_interval]))', "deleted/s"),
], "ops", 6, 6, desc="The edge flushes evaluation events to the backend, which stores them here.")
ts("Connections", [(f'sum(pg_stat_database_numbackends{{{DB}}})', "connections")], "short", 12, 6)
ts("Buffer cache hit ratio", [
    (f'sum(rate(pg_stat_database_blks_hit{{{DB}}}[$__rate_interval])) / '
     f'(sum(rate(pg_stat_database_blks_hit{{{DB}}}[$__rate_interval])) + sum(rate(pg_stat_database_blks_read{{{DB}}}[$__rate_interval])))', "hit ratio"),
], "percentunit", 18, 6)
y += 8

dash = {
    "uid": "fluxgate-perf", "title": "FluxGate Performance", "tags": ["fluxgate", "k6", "performance"],
    "timezone": "browser", "schemaVersion": 41, "version": 1, "editable": False, "graphTooltip": 1,
    "refresh": "5s", "time": {"from": "now-30m", "to": "now"},
    "templating": {"list": [{
        "name": "testid", "label": "Test run", "type": "query", "datasource": DS,
        "query": {"query": "label_values(k6_http_reqs_total, testid)", "refId": "testid"},
        "definition": "label_values(k6_http_reqs_total, testid)",
        "refresh": 2, "includeAll": True, "allValue": ".*", "multi": False, "sort": 2,
        "current": {"text": "All", "value": "$__all"},
    }]},
    "annotations": {"list": []},
    "panels": panels,
}
out = Path(__file__).resolve().parent / "grafana" / "dashboards" / "fluxgate-perf.json"
out.write_text(json.dumps(dash, indent=2) + "\n")
print(f"Wrote {out} ({len(panels)} panels)")
