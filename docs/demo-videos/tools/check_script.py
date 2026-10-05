#!/usr/bin/env python3
"""Lint FluxGate demo video scripts against the UI and CLI source."""
from __future__ import annotations

import argparse
import html
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WPM = 140
MIN_FILL = 0.6
REQUIRED_FIELDS = ("Website section", "Length target", "Takeaway", "Start state", "End state", "Prerequisites")
REQUIRED_SECTIONS = ("Scenes", "Hand-off", "Gotchas while recording")
NON_UI_PREFIXES = ("/api", "/ofrep", "/evaluate", "/health", "/docs")
UNCOVERED_ROUTES = {
    "*",
    "/",
    "/auth/sso/complete",
    "/approval-policies",
    "/pipelines/:id/edit",
    "/clients/:id/edit",
    "/system-clients/:id/edit",
    "/contexts/:id/edit",
    "/users/:id/edit",
}
BROKEN_ROUTES = {"/dashboard/rollout"}
ROUTE_FILES = ("App.tsx", "routes/AppShellRoutes.tsx")
SCRIPT_NAME = re.compile(r"^(\d\d)-.+\.md$")
FENCE = "`" * 3


@dataclass
class Scene:
    time: str
    on_screen: str
    voiceover: str
    callout: str

    def cells(self) -> list[str]:
        return [self.on_screen, self.voiceover, self.callout]


@dataclass
class Script:
    path: Path
    number: int
    header: dict[str, str]
    scenes: list[Scene]
    sections: list[str]
    text: str


def _table_rows(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)[1:-1]]
        if cells and all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows


def parse_script(path: Path, text: str) -> Script:
    m = SCRIPT_NAME.match(path.name)
    if not m:
        raise ValueError("file name must match NN-slug.md")
    lines = text.splitlines()
    heads = [i for i, line in enumerate(lines) if line.startswith("## ")]
    sections = [lines[i][3:].strip() for i in heads]
    first = heads[0] if heads else len(lines)
    header = {}
    for row in _table_rows(lines[:first])[1:]:
        if len(row) >= 2:
            header[row[0]] = row[1]
    scenes = []
    if "Scenes" in sections:
        start = heads[sections.index("Scenes")]
        nxt = [i for i in heads if i > start]
        end = nxt[0] if nxt else len(lines)
        for n, row in enumerate(_table_rows(lines[start + 1 : end])[1:], 1):
            if len(row) != 4:
                raise ValueError(f"scene row {n} has {len(row)} cells, expected 4")
            scenes.append(Scene(*row))
    return Script(path, int(m.group(1)), header, scenes, sections, text)


def voiceover_word_count(script: Script) -> int:
    return sum(len(re.findall(r"[A-Za-z0-9''-]+", s.voiceover)) for s in script.scenes)


def parse_duration(value: str) -> int:
    minutes, seconds = value.strip().split(":")
    return int(minutes) * 60 + int(seconds)


def check_structure(script: Script) -> list[str]:
    errors = [f"missing header field '{f}'" for f in REQUIRED_FIELDS if not script.header.get(f)]
    errors += [f"missing section '{s}'" for s in REQUIRED_SECTIONS if s not in script.sections]
    if "Scenes" in script.sections and not script.scenes:
        errors.append("Scenes table is empty")
    return errors


def check_length(script: Script) -> list[str]:
    target = script.header.get("Length target")
    if not target:
        return []
    try:
        seconds = parse_duration(target)
    except ValueError:
        return [f"Length target '{target}' is not m:ss"]
    words = voiceover_word_count(script)
    spoken = words / WPM * 60
    if spoken > seconds or spoken < seconds * MIN_FILL:
        return [
            f"voiceover {words} words ≈ {spoken:.0f}s at {WPM} wpm; "
            f"target {seconds}s needs {int(seconds * MIN_FILL * WPM / 60)}–{int(seconds * WPM / 60)} words"
        ]
    return []


def load_ui_corpus(ui_src: Path) -> str:
    parts = []
    for p in sorted(ui_src.rglob("*")):
        if p.suffix not in (".ts", ".tsx") or "__tests__" in p.parts or ".test." in p.name:
            continue
        parts.append(p.read_text(errors="ignore"))
    return html.unescape("\n".join(parts))


def extract_labels(cell: str) -> list[str]:
    return re.findall(r'"([^"]+)"', cell)


def check_labels(script: Script, corpus: str) -> list[str]:
    allowed = set(extract_labels(script.header.get("Label exceptions", "")))
    errors = []
    for scene in script.scenes:
        for cell in scene.cells():
            for label in extract_labels(cell):
                if label not in allowed and label not in corpus:
                    errors.append(f'{scene.time}: label not found in UI: "{label}"')
    return errors


def load_route_patterns(ui_src: Path) -> list[str]:
    patterns = []
    for rel in ROUTE_FILES:
        p = ui_src / rel
        if p.exists():
            patterns += re.findall(r'path="([^"]+)"', p.read_text())
    return patterns


def extract_routes(cell: str) -> list[str]:
    routes = []
    for token in re.findall(r"`(/[a-z][^`\s]*)`", cell):
        token = token.split("?")[0]
        if not token.startswith(NON_UI_PREFIXES):
            routes.append(token)
    return routes


def route_matches(route: str, pattern: str) -> bool:
    if pattern == "*":
        return False
    r, p = route.strip("/").split("/"), pattern.strip("/").split("/")
    return len(r) == len(p) and all(ps.startswith(":") or ps == rs for rs, ps in zip(r, p))


def resolve_route(route: str, patterns: list[str]) -> str | None:
    matches = [p for p in patterns if route_matches(route, p)]
    if not matches:
        return None
    return min(matches, key=lambda p: p.count(":"))


def script_routes(script: Script) -> list[tuple[str, str]]:
    return [(s.time, r) for s in script.scenes for r in extract_routes(s.on_screen)]


def check_routes(script: Script, patterns: list[str]) -> list[str]:
    errors = []
    for time, route in script_routes(script):
        resolved = resolve_route(route, patterns)
        if resolved is None:
            errors.append(f"{time}: unknown UI route `{route}`")
        elif resolved in BROKEN_ROUTES:
            errors.append(f"{time}: route `{route}` must not be shown (hard-coded data)")
    return errors


def check_secrets(script: Script) -> list[str]:
    errors = []
    if re.search(r"BEGIN [A-Z ]*PRIVATE KEY", script.text):
        errors.append("contains a private key block")
    if re.search(r"\btls\.key\b", script.text):
        errors.append("mentions tls.key; never show committed key files")
    for token in re.findall(r"[A-Za-z0-9+/_]{40,}={0,2}", script.text):
        errors.append(f"secret-like token: {token[:8]}…; use <redacted>")
    return errors


def extract_cli_commands(text: str) -> list[str]:
    commands = re.findall(r"(?<!`)`(fluxgate [^`\n]+)`(?!`)", text)
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith(FENCE):
            in_fence = not in_fence
            continue
        if in_fence:
            m = re.search(r"(?:^|\s)(fluxgate\s.*)$", line)
            if m:
                commands.append(m.group(1).strip())
    return commands


def check_cli(script: Script, cli_bin: Path) -> list[str]:
    errors = []
    for command in extract_cli_commands(script.text):
        words = []
        for word in shlex.split(command.split("|")[0])[1:]:
            if word.startswith("-"):
                break
            words.append(word)
        result = subprocess.run([str(cli_bin), *words, "--help"], capture_output=True)
        if result.returncode != 0:
            errors.append(f"CLI command failed: {command}")
    return errors


def check_continuity(scripts: list[Script]) -> list[str]:
    errors = []
    for s in scripts:
        start = s.header.get("Start state", "")
        expected = f"End of {s.number - 1:02d}"
        if not (start.startswith(expected) or start.startswith("Fresh")):
            errors.append(f"{s.path.name}: Start state must begin with '{expected}' or 'Fresh'")
    return errors


def check_coverage(scripts: list[Script], patterns: list[str]) -> list[str]:
    shown = set()
    for s in scripts:
        for _, route in script_routes(s):
            resolved = resolve_route(route, patterns)
            if resolved:
                shown.add(resolved)
    skip = UNCOVERED_ROUTES | BROKEN_ROUTES
    return [f"coverage: route `{p}` not shown in any script" for p in patterns if p not in skip and p not in shown]


def script_paths(paths: list[Path]) -> list[Path]:
    return sorted(p for p in paths if SCRIPT_NAME.match(p.name))


def lint(paths: list[Path], ui_src: Path, cli_bin: Path | None = None, coverage: bool = False) -> list[str]:
    patterns = load_route_patterns(ui_src)
    corpus = load_ui_corpus(ui_src)
    scripts, errors = [], []
    for p in script_paths(paths):
        try:
            s = parse_script(p, p.read_text())
        except ValueError as e:
            errors.append(f"{p.name}: {e}")
            continue
        scripts.append(s)
        found = check_structure(s) + check_length(s) + check_labels(s, corpus)
        found += check_routes(s, patterns) + check_secrets(s)
        if cli_bin:
            found += check_cli(s, cli_bin)
        errors += [f"{p.name}: {m}" for m in found]
    errors += check_continuity(scripts)
    if coverage:
        errors += check_coverage(scripts, patterns)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--ui-src", type=Path, default=Path("feature-toggle-ui/src"))
    parser.add_argument("--cli-bin", type=Path)
    parser.add_argument("--coverage", action="store_true")
    args = parser.parse_args(argv)
    errors = lint(args.paths, args.ui_src, args.cli_bin, args.coverage)
    for e in errors:
        print(e)
    if errors:
        return 1
    print(f"OK: {len(script_paths(args.paths))} scripts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
