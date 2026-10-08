#!/usr/bin/env python3
"""
Builds publishable charts and data from a run-perf-tests.sh results directory.

Output (default: <results>/site/):
  perf-summary.json   every profile x feature count: breakpoint, steady state, resources
  perf-summary.csv    the same, one row per profile and feature count
  perf-summary.md     Markdown table for docs
  charts/<name>-light.svg, charts/<name>-dark.svg
      max-rps            max sustainable RPS per profile, by feature count
      breakpoint-p99     p99 latency per load step (log scale) with the SLO line
      steady-latency     p50 / p95 / p99 in the steady-state run
      edge-cpu           edge CPU used in the steady-state run vs the CPU limit
      edge-memory        edge peak memory in the steady-state run
      edge-cpu-scaling   edge CPU against request rate over all passing load steps
      edge-memory-timeline  edge memory during the steady-state run (needs --prometheus)

The charts are static SVG for <img> tags: light and dark variants use the
FluxGate site card surface and text colors. Colors follow the dataviz
reference palette (validated against both surfaces).

Usage:
  ./generate-site-charts.py results/perf-results-<timestamp> [--out DIR] [--features 1000] [--prometheus URL]

Only the Python standard library is used.
"""

import argparse
import csv
import json
import math
import re
from html import escape
from pathlib import Path

PROFILE_ORDER = ["minimal", "tiny", "small", "medium", "large", "xlarge"]

THEMES = {
    "light": {
        "surface": "#ffffff",
        "text": "#0b1220",
        "muted": "#475569",
        "grid": "#e2e8f0",
        "axis": "#cbd5e1",
        "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"],
        "ordinal": ["#86b6ef", "#3987e5", "#1c5cab"],
        "slo": "#d03b3b",
    },
    "dark": {
        "surface": "#0f1629",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "grid": "#1a2344",
        "axis": "#243056",
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300"],
        "ordinal": ["#184f95", "#3987e5", "#86b6ef"],
        "slo": "#e66767",
    },
}

FONT = "DM Sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
WIDTH, HEIGHT = 1200, 600
MARGIN = {"left": 88, "right": 40, "top": 112, "bottom": 96}

# A profile counts as limited by its CPU when the edge used at least this share
# of its CPU limit, or was throttled in this share of CFS periods.
CPU_BOUND_USAGE = 0.85
CPU_BOUND_THROTTLE = 0.2
# ... and by its memory when the peak working set reached this share of the limit.
MEMORY_BOUND_USAGE = 0.95


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def apply_sustained_breakpoint(bp):
    """Re-derive the breakpoint so one noisy step does not end the curve.

    breakpoint-test.js reports the last step before the first failing step.
    On a shared host one step can miss the SLO and the next steps pass again.
    Here the breakpoint is the first failing step that is followed by another
    failing step (or ends the run); single misses below it are counted.
    The original values stay under firstSloMissRps / k6MaxSustainableRps.
    """
    if "isolatedSloMisses" in bp:
        return bp  # breakpoint-test.js already applied this rule
    steps = bp["steps"]
    bp["k6MaxSustainableRps"] = bp["maxSustainableRps"]
    bp["firstSloMissRps"] = (bp.get("breakingStep") or {}).get("targetRps")
    breaking_index = None
    for i, step in enumerate(steps):
        if not step["passed"] and (i == len(steps) - 1 or not steps[i + 1]["passed"]):
            breaking_index = i
            break
    if breaking_index is None:
        bp["maxSustainableRps"] = steps[-1]["targetRps"] if steps else None
        bp["breakingStep"] = None
        bp["isolatedSloMisses"] = sum(1 for s in steps if not s["passed"])
    else:
        bp["maxSustainableRps"] = steps[breaking_index - 1]["targetRps"] if breaking_index > 0 else None
        bp["breakingStep"] = steps[breaking_index]
        bp["isolatedSloMisses"] = sum(1 for s in steps[:breaking_index] if not s["passed"])
    return bp


def load_results(results_dir):
    rows = []
    for profile_dir in sorted(p for p in results_dir.iterdir() if p.is_dir() and p.name in PROFILE_ORDER):
        for round_dir in sorted(profile_dir.iterdir()):
            match = re.match(r"round\d+-(\d+)f$", round_dir.name)
            bp_file = round_dir / "breakpoint.json"
            if not match or not bp_file.exists():
                continue
            # A verification run (steady-verify.json) replaces the suite's steady run
            steady_file = round_dir / "steady-verify.json"
            if not steady_file.exists():
                steady_file = round_dir / "steady.json"
            rows.append({
                "roundDir": round_dir,
                "steadyFile": steady_file if steady_file.exists() else None,
                "profile": profile_dir.name,
                "features": int(match.group(1)),
                "breakpoint": apply_sustained_breakpoint(json.loads(bp_file.read_text())),
                "steady": json.loads(steady_file.read_text()) if steady_file.exists() else None,
            })
    rows.sort(key=lambda r: (PROFILE_ORDER.index(r["profile"]), r["features"]))
    return rows


def edge(step):
    return ((step or {}).get("resources") or {}).get("edge") or {}


def limits(row):
    """CPU and memory limit of the edge, from any step that has resources."""
    steps = list(row["breakpoint"]["steps"]) + (row["steady"]["steps"] if row["steady"] else [])
    for step in steps:
        e = edge(step)
        if e.get("cpu_limit_cores"):
            return e["cpu_limit_cores"], e.get("memory_limit_bytes")
    return None, None


def bottleneck(row):
    """Why the breakpoint run stopped: edge CPU and/or memory limit, or the test harness.

    Uses the breaking step's CPU when Prometheus has it. An aborted step often
    ends before a sample lands, so otherwise the CPU per request of the last
    passing step is projected to the breaking rate (edge CPU grows linearly
    with the request rate in these runs).
    """
    bp = row["breakpoint"]
    cpu_limit, mem_limit = limits(row)
    breaking = bp.get("breakingStep")
    if not cpu_limit or not breaking:
        return "unknown"
    steps = {s["targetRps"]: s for s in bp["steps"]}

    e = edge(steps.get(breaking["targetRps"]))
    memory_bound = bool(mem_limit and (e.get("memory_max_bytes") or 0) >= MEMORY_BOUND_USAGE * mem_limit)
    if e.get("cpu_avg_cores") is not None:
        used = max(e["cpu_avg_cores"], e.get("cpu_max_cores") or 0)
        throttled = e.get("cpu_throttled_ratio") or 0
    else:
        last = edge(steps.get(bp["maxSustainableRps"]))
        if last.get("cpu_avg_cores") is None:
            return "unknown"
        used = last["cpu_avg_cores"] * breaking["targetRps"] / bp["maxSustainableRps"]
        throttled = last.get("cpu_throttled_ratio") or 0
    cpu_bound = used / cpu_limit >= CPU_BOUND_USAGE or throttled >= CPU_BOUND_THROTTLE
    if cpu_bound and memory_bound:
        return "edge-cpu-memory"
    if cpu_bound:
        return "edge-cpu"
    return "edge-memory" if memory_bound else "harness"


def summarize(rows):
    out = []
    for row in rows:
        bp = row["breakpoint"]
        cpu_limit, mem_limit = limits(row)
        steady_step = row["steady"]["steps"][0] if row["steady"] and row["steady"]["steps"] else None
        se = edge(steady_step)
        out.append({
            "profile": row["profile"],
            "features": row["features"],
            "edgeCpuLimitCores": cpu_limit,
            "edgeMemoryLimitMiB": round(mem_limit / 1048576) if mem_limit else None,
            "maxSustainableRps": bp["maxSustainableRps"],
            "breakingRps": (bp.get("breakingStep") or {}).get("targetRps"),
            "breakingReasons": (bp.get("breakingStep") or {}).get("failures", []),
            "firstSloMissRps": bp["firstSloMissRps"],
            "isolatedSloMisses": bp["isolatedSloMisses"],
            "steadyPassed": steady_step["passed"] if steady_step else None,
            "peakAchievedRps": bp["peakAchievedRps"],
            "limitedBy": bottleneck(row),
            "rpsPerCore": round(bp["maxSustainableRps"] / cpu_limit) if bp["maxSustainableRps"] and cpu_limit else None,
            "steadyRps": steady_step["targetRps"] if steady_step else None,
            "steadyStartedAt": steady_step["startedAt"] if steady_step else None,
            "steadyEndedAt": steady_step["endedAt"] if steady_step else None,
            "steadyLatencyMs": steady_step["latencyMs"] if steady_step else None,
            "steadyErrorRate": steady_step["errorRate"] if steady_step else None,
            "steadyEdgeCpuAvgCores": se.get("cpu_avg_cores"),
            "steadyEdgeCpuThrottledRatio": se.get("cpu_throttled_ratio"),
            "steadyEdgeMemoryMaxMiB": round(se["memory_max_bytes"] / 1048576, 1) if se.get("memory_max_bytes") else None,
            "breakpointSteps": [
                {
                    "targetRps": s["targetRps"],
                    "achievedRps": s["achievedRps"],
                    "p50Ms": s["latencyMs"]["p50"],
                    "p99Ms": s["latencyMs"]["p99"],
                    "errorRate": s["errorRate"],
                    "dropped": s["dropped"],
                    "passed": s["passed"],
                    "edgeCpuAvgCores": edge(s).get("cpu_avg_cores"),
                    "edgeCpuThrottledRatio": edge(s).get("cpu_throttled_ratio"),
                }
                for s in bp["steps"]
            ],
        })
    return out


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

class Svg:
    def __init__(self, theme, title, subtitle, alt):
        self.t = THEMES[theme]
        self.parts = []
        self.title, self.subtitle, self.alt = title, subtitle, alt

    def text(self, x, y, s, size=14, color=None, anchor="start", weight=400, baseline="auto"):
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{color or self.t["muted"]}" '
            f'text-anchor="{anchor}" dominant-baseline="{baseline}">{escape(str(s))}</text>'
        )

    def line(self, x1, y1, x2, y2, color, width=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}"{d}/>')

    def bar(self, x, y_top, w, y_base, color, radius=4):
        """Vertical bar with rounded data end, square at the baseline."""
        h = y_base - y_top
        if h <= 0:
            return
        r = min(radius, w / 2, h)
        self.parts.append(
            f'<path d="M{x:.1f},{y_base:.1f} V{y_top + r:.1f} Q{x:.1f},{y_top:.1f} {x + r:.1f},{y_top:.1f} '
            f'H{x + w - r:.1f} Q{x + w:.1f},{y_top:.1f} {x + w:.1f},{y_top + r:.1f} V{y_base:.1f} Z" fill="{color}"/>'
        )

    def polyline(self, points, color, width=2):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        self.parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')

    def circle(self, x, y, r, color):
        self.parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="{self.t["surface"]}" stroke-width="2"/>')

    def legend(self, items, y=86):
        x = MARGIN["left"]
        for label, color in items:
            self.parts.append(f'<rect x="{x}" y="{y - 10}" width="12" height="12" rx="3" fill="{color}"/>')
            self.text(x + 18, y, label, size=14, color=self.t["text"])
            x += 26 + 8 * len(label) + 24

    def render(self, source_note):
        head = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
            f'font-family="{escape(FONT)}" role="img" aria-label="{escape(self.alt)}">',
            f"<title>{escape(self.title)}</title>",
            f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{self.t["surface"]}"/>',
        ]
        self.text(MARGIN["left"], 40, self.title, size=22, color=self.t["text"], weight=600)
        self.text(MARGIN["left"], 64, self.subtitle, size=15)
        self.text(WIDTH - MARGIN["right"], HEIGHT - 16, source_note, size=12, anchor="end")
        return "\n".join(head + self.parts + ["</svg>"]) + "\n"


def nice_max(value):
    if value <= 0:
        return 1
    exp = 10 ** math.floor(math.log10(value))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * exp >= value:
            return m * exp
    return 10 * exp


def fmt_num(v):
    if v is None:
        return "-"
    if v >= 1000:
        return f"{v / 1000:.1f}k".replace(".0k", "k")
    return f"{v:g}"


def fmt_cpu(v):
    return f"{v:g} CPU" if v is not None else "?"


def plot_area():
    return MARGIN["left"], MARGIN["top"], WIDTH - MARGIN["right"], HEIGHT - MARGIN["bottom"]


def y_axis_linear(svg, top, unit_fmt, y_of):
    x0, y0, x1, y1 = plot_area()
    for i in range(6):
        v = top * i / 5
        y = y_of(v)
        svg.line(x0, y, x1, y, svg.t["grid"] if i else svg.t["axis"])
        svg.text(x0 - 10, y + 5, unit_fmt(v), size=13, anchor="end")


def profile_label(svg, x, profile, cpu, mem):
    _, _, _, y1 = plot_area()
    svg.text(x, y1 + 26, profile, size=15, color=svg.t["text"], anchor="middle", weight=600)
    detail = f"{fmt_cpu(cpu)} · {mem} MiB" if mem else fmt_cpu(cpu)
    svg.text(x, y1 + 46, detail, size=13, anchor="middle")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def grouped_bars(svg, groups, series, value_of, top, unit_fmt, label_series=None, label_fmt=fmt_num, notes=None):
    """groups: [(profile, cpu, mem)], series: [(key, label, color)]."""
    x0, y0, x1, y1 = plot_area()
    y_of = lambda v: y1 - (v / top) * (y1 - y0)
    y_axis_linear(svg, top, unit_fmt, y_of)
    slot = (x1 - x0) / len(groups)
    bar_w = min(44, slot * 0.7 / len(series))
    gap = 2
    for gi, (profile, cpu, mem) in enumerate(groups):
        cx = x0 + slot * (gi + 0.5)
        total = len(series) * bar_w + (len(series) - 1) * gap
        for si, (key, _, color) in enumerate(series):
            v = value_of(profile, key)
            if v is None:
                continue
            bx = cx - total / 2 + si * (bar_w + gap)
            svg.bar(bx, y_of(v), bar_w, y1, color)
            if key == label_series:
                svg.text(bx + bar_w / 2, y_of(v) - 8, label_fmt(v), size=13, color=svg.t["text"], anchor="middle", weight=600)
        profile_label(svg, cx, profile, cpu, mem)
        if notes and notes.get(profile):
            svg.text(cx, y0 - 4, notes[profile], size=12, anchor="middle")


def chart_max_rps(summary, theme, feature_counts):
    t = THEMES[theme]
    groups = profile_groups(summary)
    by = {(r["profile"], r["features"]): r for r in summary}
    series = [(f, f"{f:,} flags", t["series"][i]) for i, f in enumerate(feature_counts)]
    peak = max((r["maxSustainableRps"] or 0) for r in summary)
    notes = {p: "load generator limit" for p, _, _ in groups if any(by.get((p, f), {}).get("limitedBy") == "harness" for f in feature_counts)}
    svg = Svg(theme, "Breakpoint: evaluations per second before the SLO breaks",
              "Last 20-second load step before p99 > 50 ms, errors or dropped requests persisted, by edge resource profile",
              "Bar chart of the breakpoint evaluation rate of the FluxGate edge server per resource profile")
    svg.legend([(label, color) for _, label, color in series])
    grouped_bars(svg, groups, series, lambda p, f: (by.get((p, f)) or {}).get("maxSustainableRps"),
                 nice_max(peak * 1.1), lambda v: fmt_num(v), label_series=feature_counts[-1], notes=notes)
    return svg


def chart_breakpoint(summary, theme, features):
    t = THEMES[theme]
    rows = [r for r in summary if r["features"] == features]
    x0, y0, x1, y1 = plot_area()
    x1 -= 70  # room for line-end labels
    max_x = nice_max(max(s["targetRps"] for r in rows for s in r["breakpointSteps"]))
    lo, hi = 0.1, 1000.0
    x_of = lambda v: x0 + v / max_x * (x1 - x0)
    y_of = lambda v: y1 - (math.log10(min(max(v, lo), hi)) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (y1 - y0)

    svg = Svg(theme, "p99 latency as load increases",
              f"Each point is one load step; {features:,} flags; log scale",
              "Line chart of p99 evaluation latency against request rate for each edge resource profile")
    for v in (0.1, 1, 10, 100, 1000):
        y = y_of(v)
        svg.line(x0, y, x1, y, t["grid"] if v != lo else t["axis"])
        svg.text(x0 - 10, y + 5, f"{v:g} ms", size=13, anchor="end")
    for i in range(6):
        v = max_x * i / 5
        svg.text(x_of(v), y1 + 24, fmt_num(v), size=13, anchor="middle")
    svg.text((x0 + x1) / 2, y1 + 52, "Requested evaluations per second", size=14, anchor="middle")

    slo_y = y_of(50)
    svg.line(x0, slo_y, x1, slo_y, t["slo"], width=1.5, dash="6 5")
    svg.text(x0 + 8, slo_y - 8, "SLO: p99 50 ms", size=13, color=t["text"])

    legend = []
    for i, r in enumerate(sorted(rows, key=lambda r: PROFILE_ORDER.index(r["profile"]))):
        color = t["series"][i]
        pts = [(x_of(s["targetRps"]), y_of(s["p99Ms"])) for s in r["breakpointSteps"] if s["p99Ms"] is not None]
        if not pts:
            continue
        svg.polyline(pts, color)
        for (px, py), s in zip(pts, r["breakpointSteps"]):
            if not s["passed"]:
                svg.circle(px, py, 4, color)
        lx, ly = pts[-1]
        svg.text(lx + 8, ly + 5, r["profile"], size=13, color=t["text"], weight=600)
        legend.append((f'{r["profile"]} ({fmt_cpu(r["edgeCpuLimitCores"])})', color))
    svg.legend(legend)
    return svg


def chart_steady_latency(summary, theme, features):
    t = THEMES[theme]
    rows = {r["profile"]: r for r in summary if r["features"] == features and r["steadyLatencyMs"]}
    groups = [g for g in profile_groups(summary) if g[0] in rows]
    series = [("p50", "p50", t["ordinal"][0]), ("p95", "p95", t["ordinal"][1]), ("p99", "p99", t["ordinal"][2])]
    peak = max(rows[p]["steadyLatencyMs"]["p99"] for p, _, _ in groups)
    p50s = [rows[p]["steadyLatencyMs"]["p50"] for p, _, _ in groups]
    notes = {p: f'at {fmt_num(rows[p]["steadyRps"])} req/s' for p, _, _ in groups}
    svg = Svg(theme, "Latency under steady load",
              f"5 minutes at 70% of each profile's breakpoint; {features:,} flags; p50 {min(p50s):.2f}–{max(p50s):.2f} ms on every profile",
              "Grouped bar chart of p50, p95 and p99 evaluation latency per edge resource profile under steady load")
    svg.legend([(label, color) for _, label, color in series])
    grouped_bars(svg, groups, series, lambda p, k: rows[p]["steadyLatencyMs"][k], nice_max(peak * 1.15),
                 lambda v: f"{v:g} ms", label_series="p99", label_fmt=lambda v: f"{v:.2f} ms", notes=notes)
    return svg


def chart_edge_cpu(summary, theme, features):
    t = THEMES[theme]
    rows = {r["profile"]: r for r in summary if r["features"] == features and r["steadyEdgeCpuAvgCores"] is not None}
    groups = [g for g in profile_groups(summary) if g[0] in rows]
    x0, y0, x1, y1 = plot_area()
    top = nice_max(max(r["edgeCpuLimitCores"] or 0 for r in rows.values()) * 1.1)
    y_of = lambda v: y1 - (v / top) * (y1 - y0)
    svg = Svg(theme, "Edge CPU used under steady load",
              f"Average CPU cores used during the steady-state run vs the container CPU limit (dashed); {features:,} flags",
              "Bar chart of edge server CPU usage per resource profile under steady load, with the CPU limit marked")
    svg.legend([("CPU used", t["series"][0]), ("CPU limit", t["muted"])])
    y_axis_linear(svg, top, lambda v: f"{v:g}", y_of)
    slot = (x1 - x0) / len(groups)
    for gi, (profile, cpu, mem) in enumerate(groups):
        r = rows[profile]
        cx = x0 + slot * (gi + 0.5)
        w = min(64, slot * 0.5)
        used = r["steadyEdgeCpuAvgCores"]
        svg.bar(cx - w / 2, y_of(used), w, y1, t["series"][0])
        if cpu:
            svg.line(cx - w / 2 - 10, y_of(cpu), cx + w / 2 + 10, y_of(cpu), t["muted"], width=2, dash="5 4")
        svg.text(cx, y_of(max(used, cpu or 0)) - 10, f"{used:.2f} of {cpu:g}" if cpu else f"{used:.2f}",
                 size=13, color=t["text"], anchor="middle", weight=600)
        svg.text(cx, y0 - 4, f'at {fmt_num(r["steadyRps"])} req/s', size=12, anchor="middle")
        profile_label(svg, cx, profile, cpu, mem)
    return svg


def chart_edge_memory(summary, theme, features):
    t = THEMES[theme]
    rows = {r["profile"]: r for r in summary if r["features"] == features and r["steadyEdgeMemoryMaxMiB"] is not None}
    groups = [g for g in profile_groups(summary) if g[0] in rows]
    x0, y0, x1, y1 = plot_area()
    top = nice_max(max(r["steadyEdgeMemoryMaxMiB"] for r in rows.values()) * 1.25)
    y_of = lambda v: y1 - (v / top) * (y1 - y0)
    svg = Svg(theme, "Edge memory under steady load",
              f"Peak memory working set during the steady-state run; container limit below each bar; {features:,} flags",
              "Bar chart of edge server peak memory per resource profile under steady load")
    y_axis_linear(svg, top, lambda v: f"{v:g} MiB", y_of)
    slot = (x1 - x0) / len(groups)
    for gi, (profile, cpu, mem) in enumerate(groups):
        r = rows[profile]
        cx = x0 + slot * (gi + 0.5)
        w = min(64, slot * 0.5)
        v = r["steadyEdgeMemoryMaxMiB"]
        svg.bar(cx - w / 2, y_of(v), w, y1, t["series"][2])
        svg.text(cx, y_of(v) - 10, f"{v:.1f} MiB", size=13, color=t["text"], anchor="middle", weight=600)
        svg.text(cx, y0 - 4, f'at {fmt_num(r["steadyRps"])} req/s', size=12, anchor="middle")
        profile_label(svg, cx, profile, cpu, mem)
    return svg


def chart_cpu_scaling(summary, theme):
    """Edge CPU against achieved rate for every unthrottled load step."""
    t = THEMES[theme]
    points = [
        (s["achievedRps"], s["edgeCpuAvgCores"])
        for r in summary for s in r["breakpointSteps"]
        if s["passed"] and s["edgeCpuAvgCores"] is not None and (s["edgeCpuThrottledRatio"] or 0) < 0.05
    ]
    if not points:
        raise ValueError("no CPU samples")
    # Least squares through the origin: cores = k * rps
    k = sum(x * y for x, y in points) / sum(x * x for x, _ in points)
    x0, y0, x1, y1 = plot_area()
    max_x = nice_max(max(x for x, _ in points))
    max_y = nice_max(max(y for _, y in points) * 1.1)
    x_of = lambda v: x0 + v / max_x * (x1 - x0)
    y_of = lambda v: y1 - v / max_y * (y1 - y0)
    svg = Svg(theme, "Edge CPU grows linearly with load",
              f"Average edge CPU per load step that met the SLO, all profiles and flag counts; about {k * 1000:.3f} cores per 1,000 evaluations/s",
              "Scatter plot of edge server CPU cores used against evaluations per second, with a linear fit")
    y_axis_linear(svg, max_y, lambda v: f"{v:g}", y_of)
    for i in range(6):
        v = max_x * i / 5
        svg.text(x_of(v), y1 + 24, fmt_num(v), size=13, anchor="middle")
    svg.text((x0 + x1) / 2, y1 + 52, "Evaluations per second", size=14, anchor="middle")
    svg.text(x0 - 60, y0 - 16, "CPU cores", size=13)
    for x, y in points:
        svg.circle(x_of(x), y_of(y), 4, t["series"][0])
    fit_end = min(max_x, max_y / k)
    svg.line(x_of(0), y_of(0), x_of(fit_end), y_of(k * fit_end), t["text"], width=1.5, dash="6 5")
    svg.text(x_of(fit_end) - 8, y_of(k * fit_end) - 10, f"{k * 1000:.3f} cores per 1k req/s", size=13,
             color=t["text"], anchor="end", weight=600)
    return svg


def chart_memory_timeline(summary, theme, features):
    """Edge memory during the steady-state run, one line per profile, with limits."""
    t = THEMES[theme]
    rows = [r for r in summary if r["features"] == features and r.get("steadyEdgeMemorySeries")]
    if not rows:
        raise ValueError("no memory series (run with --prometheus)")
    x0, y0, x1, y1 = plot_area()
    x1 -= 150
    lo, hi = 1.0, 2048.0
    max_t = max(pt[0] for r in rows for pt in r["steadyEdgeMemorySeries"])
    x_of = lambda v: x0 + v / max_t * (x1 - x0)
    y_of = lambda v: y1 - (math.log2(min(max(v, lo), hi)) - math.log2(lo)) / (math.log2(hi) - math.log2(lo)) * (y1 - y0)
    svg = Svg(theme, "Edge memory during a 5-minute steady run",
              f"Memory working set at constant load, {features:,} flags and 10,000 distinct users; dashed = container limit; log scale",
              "Line chart of edge server memory over five minutes of steady load per resource profile, with each memory limit")
    for v in (1, 4, 16, 64, 256, 1024):
        y = y_of(v)
        svg.line(x0, y, x1, y, t["grid"] if v != lo else t["axis"])
        svg.text(x0 - 10, y + 5, f"{v:g} MiB", size=13, anchor="end")
    for m in range(0, int(max_t // 60) + 1):
        svg.text(x_of(m * 60), y1 + 24, f"{m} min", size=13, anchor="middle")
    legend = []
    for i, r in enumerate(sorted(rows, key=lambda r: PROFILE_ORDER.index(r["profile"]))):
        color = t["series"][i]
        if r["edgeMemoryLimitMiB"]:
            ly = y_of(r["edgeMemoryLimitMiB"])
            svg.line(x0, ly, x1, ly, color, width=1.5, dash="6 5")
        pts = [(x_of(sec), y_of(mib)) for sec, mib in r["steadyEdgeMemorySeries"]]
        svg.polyline(pts, color)
        lx, ly = pts[-1]
        svg.text(x1 + 10, ly + 5, f'{r["profile"]} @ {fmt_num(r["steadyRps"])} req/s', size=13, color=t["text"], weight=600)
        legend.append((f'{r["profile"]} ({r["edgeMemoryLimitMiB"]} MiB)', color))
    svg.legend(legend)
    return svg


def fetch_memory_series(prometheus, summary, features):
    import urllib.parse
    import urllib.request
    from datetime import datetime

    def ts(value):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()

    for r in summary:
        if r["features"] != features or not r["steadyStartedAt"]:
            continue
        start, end = ts(r["steadyStartedAt"]), ts(r["steadyEndedAt"])
        query = urllib.parse.urlencode({
            "query": 'max(container_memory_working_set_bytes{service="edge"}) / 1048576',
            "start": start, "end": end, "step": 5,
        })
        with urllib.request.urlopen(f"{prometheus}/api/v1/query_range?{query}", timeout=10) as response:
            result = json.load(response)["data"]["result"]
        if result:
            r["steadyEdgeMemorySeries"] = [[round(float(t_) - start), round(float(v), 1)] for t_, v in result[0]["values"]]


# Series exported per test run: name -> PromQL (TESTID and SERVICE are filled in)
K6_SERIES = {
    "achievedRps": 'sum(rate(k6_http_reqs_total{testid="TESTID"}[15s]))',
    "failedRps": 'sum(rate(k6_http_reqs_total{testid="TESTID",expected_response="false"}[15s]))',
    "droppedRps": 'sum(rate(k6_dropped_iterations_total{testid="TESTID"}[15s]))',
    "p50Ms": 'histogram_quantile(0.5, sum(rate(k6_http_req_duration_seconds{testid="TESTID"}[15s]))) * 1000',
    "p95Ms": 'histogram_quantile(0.95, sum(rate(k6_http_req_duration_seconds{testid="TESTID"}[15s]))) * 1000',
    "p99Ms": 'histogram_quantile(0.99, sum(rate(k6_http_req_duration_seconds{testid="TESTID"}[15s]))) * 1000',
    "activeVus": 'sum(k6_vus{testid="TESTID"})',
}
CONTAINER_SERIES = {
    "CpuCores": 'sum(rate(container_cpu_usage_seconds_total{service="SERVICE"}[10s]))',
    "CpuThrottledRatio": 'sum(rate(container_cpu_cfs_throttled_periods_total{service="SERVICE"}[10s])) / '
                         'sum(rate(container_cpu_cfs_periods_total{service="SERVICE"}[10s]))',
    "MemoryMiB": 'max(container_memory_working_set_bytes{service="SERVICE"}) / 1048576',
}
POSTGRES_SERIES = {
    "postgresCommitsPerSec": 'sum(rate(pg_stat_database_xact_commit{datname="feature_toggle"}[10s]))',
    "postgresRowsInsertedPerSec": 'sum(rate(pg_stat_database_tup_inserted{datname="feature_toggle"}[10s]))',
}
SERIES_STEP_SECS = 5


def prom_range(prometheus, expr, start, end, step=SERIES_STEP_SECS):
    import urllib.parse
    import urllib.request

    query = urllib.parse.urlencode({"query": expr, "start": start, "end": end, "step": step})
    with urllib.request.urlopen(f"{prometheus}/api/v1/query_range?{query}", timeout=30) as response:
        result = json.load(response)["data"]["result"]
    if not result:
        return []
    out = []
    for t_, v in result[0]["values"]:
        value = float(v)
        out.append([round(float(t_) - start), None if value != value or math.isinf(value) else round(value, 4)])
    return out


def run_timeseries(prometheus, result, testid):
    """Every series for one test run, from 10 s before its start to 10 s after its last step."""
    from datetime import datetime, timezone

    def ts(value):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()

    def iso(seconds):
        return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    start = ts(result["meta"]["startedAt"]) - 10
    end = ts(result["steps"][-1]["endedAt"]) + 10
    series = {name: prom_range(prometheus, expr.replace("TESTID", testid), start, end) for name, expr in K6_SERIES.items()}
    for service in ("edge", "backend", "postgres"):
        for suffix, expr in CONTAINER_SERIES.items():
            if suffix == "CpuThrottledRatio" and service != "edge":
                continue  # only the edge has a CPU limit
            series[f"{service}{suffix}"] = prom_range(prometheus, expr.replace("SERVICE", service), start, end)
    for name, expr in POSTGRES_SERIES.items():
        series[name] = prom_range(prometheus, expr, start, end)
    return {
        "testid": testid,
        "from": iso(start),
        "to": iso(end),
        "stepSeconds": SERIES_STEP_SECS,
        "note": "Each point is [seconds since 'from', value]; null where Prometheus had no value. "
                "Latency percentiles here come from k6 native histogram buckets and are approximate; "
                "the step tables (breakpoint.json, steady.json) hold the exact per-step percentiles.",
        "series": series,
    }


def export_configurations(prometheus, rows, summary, out):
    """One folder per profile and flag count: results, step tables and time series."""
    import shutil

    by_key = {(r["profile"], r["features"]): r for r in summary}
    for row in rows:
        name = f'{row["profile"]}-{row["features"]}f'
        target = out / "configurations" / name
        target.mkdir(parents=True, exist_ok=True)
        files = {}
        runs = [("breakpoint", row["roundDir"] / "breakpoint.json", f"{name}-breakpoint")]
        if row["steadyFile"]:
            suffix = "-verify" if row["steadyFile"].name == "steady-verify.json" else ""
            runs.append(("steady", row["steadyFile"], f"{name}-steady{suffix}"))
        for kind, source, testid in runs:
            shutil.copy(source, target / f"{kind}.json")
            if source.with_suffix(".md").exists():
                shutil.copy(source.with_suffix(".md"), target / f"{kind}.md")
            files[kind] = f"configurations/{name}/{kind}.json"
            files[f"{kind}Table"] = f"configurations/{name}/{kind}.md"
            if prometheus:
                result = json.loads(source.read_text())
                (target / f"timeseries-{kind}.json").write_text(
                    json.dumps(run_timeseries(prometheus, result, testid), indent=1) + "\n")
                files[f"{kind}Timeseries"] = f"configurations/{name}/timeseries-{kind}.json"
            grafana = out / "grafana" / f"{name}-{kind}-light.png"
            if grafana.exists():
                files[f"{kind}Grafana"] = {
                    "light": f"grafana/{name}-{kind}-light.png",
                    "dark": f"grafana/{name}-{kind}-dark.png",
                }
        entry = by_key[(row["profile"], row["features"])]
        entry["files"] = files
        (target / "summary.json").write_text(json.dumps(entry, indent=2) + "\n")


def profile_groups(summary):
    seen = {}
    for r in summary:
        seen.setdefault(r["profile"], (r["profile"], r["edgeCpuLimitCores"], r["edgeMemoryLimitMiB"]))
    return sorted(seen.values(), key=lambda g: PROFILE_ORDER.index(g[0]))


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

LIMITED_BY_LABELS = {
    "edge-cpu": "edge CPU limit",
    "edge-memory": "edge memory limit",
    "edge-cpu-memory": "edge CPU and memory limits",
    "harness": "load generator",
    "unknown": "-",
}

CSV_FIELDS = [
    "profile", "features", "edgeCpuLimitCores", "edgeMemoryLimitMiB", "maxSustainableRps", "breakingRps",
    "limitedBy", "rpsPerCore", "firstSloMissRps", "isolatedSloMisses", "steadyRps", "steadyPassed", "p50Ms", "p95Ms", "p99Ms", "p999Ms", "steadyErrorRate",
    "steadyEdgeCpuAvgCores", "steadyEdgeCpuThrottledRatio", "steadyEdgeMemoryMaxMiB",
]


def flat(r):
    lat = r["steadyLatencyMs"] or {}
    row = {k: r.get(k) for k in CSV_FIELDS}
    row.update({"p50Ms": lat.get("p50"), "p95Ms": lat.get("p95"), "p99Ms": lat.get("p99"), "p999Ms": lat.get("p999")})
    return row


def steady_verdict(r):
    if r["steadyPassed"] is None:
        return "-"
    return "met" if r["steadyPassed"] else "missed"


def markdown(summary, meta):
    lines = [
        "| Profile | Edge limits | Flags | Breakpoint RPS | Breakpoint limited by | 5-min steady RPS | Steady SLO | p50 ms | p95 ms | p99 ms | Edge CPU used | Edge memory |",
        "|---|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        lat = r["steadyLatencyMs"] or {}
        limited = LIMITED_BY_LABELS[r["limitedBy"]]
        lines.append(
            f'| {r["profile"]} | {fmt_cpu(r["edgeCpuLimitCores"])}, {r["edgeMemoryLimitMiB"]} MiB | {r["features"]:,} | '
            f'{r["maxSustainableRps"] or "none":,} | {limited} | {r["steadyRps"] or "-"} | {steady_verdict(r)} | {lat.get("p50", "-")} | '
            f'{lat.get("p95", "-")} | {lat.get("p99", "-")} | {r["steadyEdgeCpuAvgCores"] if r["steadyEdgeCpuAvgCores"] is not None else "-"} | '
            f'{r["steadyEdgeMemoryMaxMiB"] if r["steadyEdgeMemoryMaxMiB"] is not None else "-"} MiB |'
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--features", type=int, default=1000, help="feature count for the single-round charts")
    parser.add_argument("--prometheus", help="Prometheus URL; adds time series per test run and the memory timeline chart")
    parser.add_argument("--note", default="FluxGate edge server · k6 · Docker Desktop", help="source line on each chart")
    args = parser.parse_args()

    out = args.out or args.results / "site"
    (out / "charts").mkdir(parents=True, exist_ok=True)

    rows = load_results(args.results)
    if not rows:
        raise SystemExit(f"No breakpoint results under {args.results}")
    summary = summarize(rows)
    prometheus = args.prometheus.rstrip("/") if args.prometheus else None
    if prometheus:
        fetch_memory_series(prometheus, summary, args.features)
    export_configurations(prometheus, rows, summary, out)
    feature_counts = sorted({r["features"] for r in summary})

    meta = {}
    summary_md = args.results / "SUMMARY.md"
    if summary_md.exists():
        meta["summary"] = summary_md.name

    (out / "perf-summary.json").write_text(json.dumps({"results": summary}, indent=2) + "\n")
    with (out / "perf-summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(flat(r) for r in summary)
    (out / "perf-summary.md").write_text(markdown(summary, meta))

    charts = {
        "max-rps": lambda th: chart_max_rps(summary, th, feature_counts),
        "breakpoint-p99": lambda th: chart_breakpoint(summary, th, args.features),
        "steady-latency": lambda th: chart_steady_latency(summary, th, args.features),
        "edge-cpu": lambda th: chart_edge_cpu(summary, th, args.features),
        "edge-memory": lambda th: chart_edge_memory(summary, th, args.features),
        "edge-cpu-scaling": lambda th: chart_cpu_scaling(summary, th),
        "edge-memory-timeline": lambda th: chart_memory_timeline(summary, th, args.features),
    }
    for name, build in charts.items():
        for theme in THEMES:
            try:
                svg = build(theme)
            except (ValueError, KeyError) as error:
                print(f"Skipped {name}: {error}")
                break
            (out / "charts" / f"{name}-{theme}.svg").write_text(svg.render(args.note))

    environment_file = args.results / "environment.json"
    bundle = {
        "generatedFrom": args.results.name,
        "environment": json.loads(environment_file.read_text()) if environment_file.exists() else None,
        "method": {
            "endpoint": "POST /evaluate on the edge server",
            "breakpoint": "Request rate rises in fixed steps; the breakpoint is the first SLO miss that repeats in "
                          "the next step (or ends the run); maxSustainableRps is the step before it",
            "steadyState": "A freshly restarted edge holds a fraction of its breakpoint for a fixed duration",
            "slo": "Per step: p99 <= SLO, errors < 1%, dropped requests < 1%",
            "limitedBy": {k: v for k, v in LIMITED_BY_LABELS.items() if k != "unknown"},
        },
        "charts": sorted(f"charts/{f.name}" for f in (out / "charts").glob("*.svg")),
        "summaryTables": ["perf-summary.json", "perf-summary.csv", "perf-summary.md"],
        "configurations": [
            {k: r[k] for k in ("profile", "features", "edgeCpuLimitCores", "edgeMemoryLimitMiB", "maxSustainableRps",
                               "limitedBy", "steadyRps", "steadyPassed", "steadyLatencyMs", "files")}
            for r in summary
        ],
    }
    (out / "bundle.json").write_text(json.dumps(bundle, indent=2) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
