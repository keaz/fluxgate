# FluxGate Demo Video Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write 16 screen-recording-plus-voiceover scripts and a series README under `docs/demo-videos/`, with every UI label, route and CLI command verified against the code.

**Architecture:** A small Python linter (`docs/demo-videos/tools/check_script.py`) parses each script's Markdown tables and checks structure, voiceover length, UI labels, UI routes, CLI commands, continuity between videos, screen coverage and secret leakage. Scripts are written chapter by chapter; each chapter task ends with the linter passing on its files.

**Tech Stack:** Markdown, Python 3.14 + pytest (already installed at `/opt/homebrew/bin/python3`), React UI source in `feature-toggle-ui/src`, Rust CLI in `feature-toggle-cli-followups/fluxgate-cli`.

**Spec:** `docs/superpowers/specs/2026-10-05-demo-video-series-design.md`

## Global Constraints

- Repo root: `/Users/kasunranasinghe/Projects/FeatureToggle`. Run every command from there. Commit directly on `main`.
- `feature-toggle/`, `feature-toggle-ui/`, `feature-toggle-cli-followups/` and `fluxgate-springboot/` are separate nested repos. Read them; never modify or commit them.
- Production format: screen recording with voiceover.
- Length: 2–4 minutes per video. 16 videos (15 core + optional video 16).
- Speaking rate: 140 words per minute.
- One continuous storyline (spec §2): Juniper Market, team `Checkout`, feature `express-checkout`, supporting flag `holiday-banner`, users `admin` / `priya` (Requester) / `sam` (Approver), Jira project `CHK`, issue `CHK-142`.
- Scripts refer to people by username or role, never by gendered pronoun.
- Voice: second person, developer to developer, present tense, 10-second problem hook, one line of *why* before each *how*, no marketing superlatives, no claims about features that do not exist.
- UI labels are written in straight double quotes exactly as the code renders them, e.g. "Create New Feature". Typed values, keys, routes and commands go in backticks, e.g. `express-checkout`, `/features/create`, `fluxgate flags list`. Never use double quotes for anything except UI labels.
- No `|` characters inside table cells except escaped as `\|`.
- Never show or name committed secret files (TLS private key, edge client secret). Secrets on screen are shown as `<redacted>` or blurred.
- SDK coverage: curl, OFREP, OpenFeature OFREP provider, CLI. Spring Boot appears only in an appendix of video 08 headed "Appendix: Spring Boot (record after starter fix)".
- `/dashboard/rollout` (Feature Rollout) is never shown (hard-coded status, `FeatureRollout.tsx:103`).
- Jira scripts never claim FluxGate transitions Jira issues or that Jira can trigger a kill switch.

## Review Focus

1. **Label drift** — a quoted label anywhere in a scene (On screen, Voiceover or Callout) that the UI no longer renders. Viewer expects to find the button named in the video. Pinned by `test_unknown_label_in_voiceover_is_reported` (Task 1).
2. **Broken continuity** — a video starts from a state the previous video did not leave behind, so a viewer following in order gets stuck. Pinned by `test_continuity_break_is_reported` (Task 1).
3. **Secrets on screen** — a script tells the recorder to open a private key or paste a real-looking token. Viewer expects published videos to be safe. Pinned by `test_private_key_and_long_token_are_reported` (Task 1).
4. **Voiceover overrun** — narration longer than the video's target, so recordings blow past 4 minutes. Pinned by `test_voiceover_too_long_is_reported` (Task 1).
5. **Showing a fake screen** — a script navigates to `/dashboard/rollout`, whose data is hard-coded. Pinned by `test_broken_route_is_reported` (Task 1).

## File Structure

```
docs/demo-videos/
  README.md                         series overview, story bible, recording setup, continuity table, script template
  tools/check_script.py             linter
  tools/test_check_script.py        linter tests
  01-what-is-fluxgate.md
  02-install-and-first-boot.md
  03-teams-users-roles.md
  04-environments-and-pipelines.md
  05-contexts.md
  06-create-your-first-feature.md
  07-targeting-rules.md
  08-clients-and-edge-server.md
  09-cli-and-automation.md
  10-approvals-and-policies.md
  11-safety-nets.md
  12-jira-setup.md
  13-jira-end-to-end.md
  14-jev-ai-assistance.md
  15-dashboards.md
  16-going-to-production.md
```

## Script template (every `NN-*.md` file follows this exactly)

```markdown
# 07 · Targeting rules

| Field | Value |
|---|---|
| Website section | Model your release › Targeting |
| Length target | 4:00 |
| Takeaway | You can target Canadian Plus users first, then split everyone else 20/80. |
| Start state | End of 06: `express-checkout` exists with variants and pipeline, no criteria. |
| End state | Criteria saved on Development and Staging; Development stage deployed. |
| Prerequisites | Signed in as `priya`. |
| Label exceptions | "Priority 1" |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Feature list at `/features`. | You have a flag. Now decide who sees what. | |
| 0:10 | Click `express-checkout`, then "Edit". | ... | Zoom on stage graph |

## Hand-off

Next: connect a real app to the edge server and evaluate `express-checkout` (video 08).

## Gotchas while recording

- ...
```

Rules:
- `Label exceptions` is optional. Use it only for labels built at runtime (e.g. "Priority 1" from `Priority {n}`) and give the source line in a Gotchas bullet.
- `Start state` must begin with `End of NN` (previous video number, two digits) or with `Fresh`.
- `Length target` is `m:ss`.
- Extra sections (e.g. an appendix) may follow "Gotchas while recording".

---

### Task 1: Script linter

**Files:**
- Create: `docs/demo-videos/tools/check_script.py`
- Test: `docs/demo-videos/tools/test_check_script.py`

**Interfaces:**
- Consumes: nothing.
- Produces: CLI `python3 docs/demo-videos/tools/check_script.py <files...> --ui-src feature-toggle-ui/src [--cli-bin PATH] [--coverage]`. Exit 0 and prints `OK: N scripts` when clean; exit 1 and prints one `file: message` line per error otherwise. Non-script files (names not matching `NN-*.md`) are ignored, so `docs/demo-videos/*.md` is a valid argument.

- [ ] **Step 1: Write the failing tests**

Create `docs/demo-videos/tools/test_check_script.py`:

```python
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import check_script as cs  # noqa: E402


def make_ui(tmp_path: Path) -> Path:
    ui = tmp_path / "ui"
    (ui / "routes").mkdir(parents=True)
    (ui / "pages" / "__tests__").mkdir(parents=True)
    (ui / "App.tsx").write_text('<Route path="/login" />\n<Route path="*" />\n')
    (ui / "routes" / "AppShellRoutes.tsx").write_text(
        '<Route path="/features" />\n'
        '<Route path="/features/:id" />\n'
        '<Route path="/features/create" />\n'
        '<Route path="/dashboard/rollout" />\n'
    )
    (ui / "pages" / "Features.tsx").write_text(
        "<button>Create New Feature</button>\n<h1>OpenFeature &amp; OFREP</h1>\n"
    )
    (ui / "pages" / "__tests__" / "Only.test.tsx").write_text("<b>Test Only Label</b>")
    return ui


def script_text(
    number="02",
    start="End of 01: nothing.",
    on_screen='Go to `/features`, click "Create New Feature".',
    voiceover="word " * 100,
    target="1:00",
    extra_header="",
    sections=("Hand-off", "Gotchas while recording"),
):
    body = [
        f"# {number} · Demo",
        "",
        "| Field | Value |",
        "|---|---|",
        "| Website section | Get started |",
        f"| Length target | {target} |",
        "| Takeaway | Something. |",
        f"| Start state | {start} |",
        "| End state | Something exists. |",
        "| Prerequisites | None. |",
    ]
    if extra_header:
        body.append(extra_header)
    body += [
        "",
        "## Scenes",
        "",
        "| Time | On screen | Voiceover | Callout |",
        "|---|---|---|---|",
        f"| 0:00 | {on_screen} | {voiceover.strip()} | |",
        "",
    ]
    for s in sections:
        body += [f"## {s}", "", "- note", ""]
    return "\n".join(body)


def write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text)
    return p


def test_valid_script_has_no_errors(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text())
    assert cs.lint([p], ui) == []


def test_parse_reads_header_and_scenes(tmp_path):
    s = cs.parse_script(Path("07-x.md"), script_text(number="07", on_screen="A \\| B"))
    assert s.number == 7
    assert s.header["Length target"] == "1:00"
    assert len(s.scenes) == 1
    assert s.scenes[0].on_screen == "A | B"


def test_missing_section_is_reported(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(sections=("Hand-off",)))
    assert any("missing section 'Gotchas while recording'" in e for e in cs.lint([p], ui))


def test_voiceover_too_long_is_reported(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(voiceover="word " * 200))
    assert any("voiceover 200 words" in e for e in cs.lint([p], ui))


def test_voiceover_too_thin_is_reported(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(voiceover="word " * 20))
    assert any("voiceover 20 words" in e for e in cs.lint([p], ui))


def test_unknown_label_in_on_screen_is_reported(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(on_screen='Click "Make Feature".'))
    assert any("label not found in UI: \"Make Feature\"" in e for e in cs.lint([p], ui))


def test_unknown_label_in_voiceover_is_reported(tmp_path):
    ui = make_ui(tmp_path)
    vo = 'Press "Ship It" now. ' + "word " * 96
    p = write(tmp_path, "02-demo.md", script_text(voiceover=vo))
    assert any("\"Ship It\"" in e for e in cs.lint([p], ui))


def test_html_entity_label_matches(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(on_screen='Open "OpenFeature & OFREP".'))
    assert cs.lint([p], ui) == []


def test_test_files_are_not_label_sources(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(on_screen='Click "Test Only Label".'))
    assert any("Test Only Label" in e for e in cs.lint([p], ui))


def test_label_exception_is_skipped(tmp_path):
    ui = make_ui(tmp_path)
    p = write(
        tmp_path,
        "02-demo.md",
        script_text(on_screen='See "Priority 1".', extra_header='| Label exceptions | "Priority 1" |'),
    )
    assert cs.lint([p], ui) == []


def test_unknown_route_is_reported(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(on_screen="Go to `/nowhere`."))
    assert any("unknown UI route `/nowhere`" in e for e in cs.lint([p], ui))


def test_api_paths_are_not_ui_routes(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(on_screen="curl `/api/v1/features` and `/ofrep/v1/evaluate/flags`."))
    assert cs.lint([p], ui) == []


def test_param_route_matches(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(on_screen="Open `/features/:id`."))
    assert cs.lint([p], ui) == []


def test_broken_route_is_reported(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(on_screen="Go to `/dashboard/rollout`."))
    assert any("route `/dashboard/rollout` must not be shown" in e for e in cs.lint([p], ui))


def test_private_key_and_long_token_are_reported(tmp_path):
    ui = make_ui(tmp_path)
    token = "A" * 44
    p = write(tmp_path, "02-demo.md", script_text(on_screen=f"Open `tls.key` and paste `{token}`."))
    errors = cs.lint([p], ui)
    assert any("tls.key" in e for e in errors)
    assert any("secret-like" in e for e in errors)


def test_continuity_break_is_reported(tmp_path):
    ui = make_ui(tmp_path)
    a = write(tmp_path, "02-a.md", script_text(number="02", start="Fresh machine."))
    b = write(tmp_path, "03-b.md", script_text(number="03", start="End of 01: wrong."))
    assert any("03-b.md: Start state must begin with 'End of 02' or 'Fresh'" in e for e in cs.lint([a, b], ui))


def test_continuity_ok(tmp_path):
    ui = make_ui(tmp_path)
    a = write(tmp_path, "02-a.md", script_text(number="02", start="Fresh machine."))
    b = write(tmp_path, "03-b.md", script_text(number="03", start="End of 02: ok."))
    assert cs.lint([a, b], ui) == []


def test_coverage_reports_unvisited_routes(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text())
    errors = cs.lint([p], ui, coverage=True)
    assert "coverage: route `/login` not shown in any script" in errors
    assert "coverage: route `/features/create` not shown in any script" in errors
    assert not any("/dashboard/rollout" in e for e in errors)
    assert not any("`*`" in e for e in errors)


def test_coverage_prefers_literal_route(tmp_path):
    ui = make_ui(tmp_path)
    p = write(tmp_path, "02-demo.md", script_text(on_screen="Go to `/features/create`."))
    errors = cs.lint([p], ui, coverage=True)
    assert "coverage: route `/features/:id` not shown in any script" in errors


def test_cli_commands_are_checked(tmp_path):
    ui = make_ui(tmp_path)
    fake = tmp_path / "fluxgate"
    fake.write_text('#!/bin/sh\ncase "$1" in flags|login) exit 0;; *) exit 2;; esac\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    on = "Run `fluxgate flags list --team Checkout` then `fluxgate bogus thing`."
    p = write(tmp_path, "02-demo.md", script_text(on_screen=on))
    errors = cs.lint([p], ui, cli_bin=fake)
    assert any("CLI command failed: fluxgate bogus thing" in e for e in errors)
    assert not any("flags list" in e for e in errors)


def test_non_script_files_are_ignored(tmp_path):
    ui = make_ui(tmp_path)
    readme = write(tmp_path, "README.md", "# Not a script")
    assert cs.lint(cs.script_paths([readme]), ui) == []


def test_bad_scene_row_raises(tmp_path):
    text = script_text().replace("| 0:00 |", "| 0:00 | extra |", 1)
    with pytest.raises(ValueError, match="scene row 1 has 5 cells"):
        cs.parse_script(Path("02-x.md"), text)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest docs/demo-videos/tools -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'check_script'`.

- [ ] **Step 3: Write the linter**

Create `docs/demo-videos/tools/check_script.py`:

```python
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
    return sum(len(re.findall(r"[A-Za-z0-9'’-]+", s.voiceover)) for s in script.scenes)


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest docs/demo-videos/tools -q`
Expected: all tests pass (22 passed).

- [ ] **Step 5: Run against the real UI source to confirm route loading**

Run: `python3 -c "import sys; sys.path.insert(0,'docs/demo-videos/tools'); import check_script as c; from pathlib import Path; p=c.load_route_patterns(Path('feature-toggle-ui/src')); print(len(p)); print('/settings/jira' in p, '/developer/setup' in p)"`
Expected: a count of at least 40, then `True True`.

- [ ] **Step 6: Commit**

```bash
git add docs/demo-videos/tools/check_script.py docs/demo-videos/tools/test_check_script.py
git commit -m "docs: add demo video script linter

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Series README and CLI build

**Files:**
- Create: `docs/demo-videos/README.md`

**Interfaces:**
- Consumes: spec §2–§6.
- Produces: the continuity table (start/end state per video) that Tasks 3–8 copy verbatim into each script header, and the built CLI binary path used by Tasks 5 and 7 (`feature-toggle-cli-followups/target/debug/fluxgate`).

- [ ] **Step 1: Build the CLI for command verification**

Run: `cd feature-toggle-cli-followups && cargo build -p fluxgate-cli && ls target/debug/fluxgate; cd ..`
Expected: build succeeds and the path prints. If the binary name differs, find it with `ls feature-toggle-cli-followups/target/debug/` and record the real name in the README "Recording setup" section. Do not commit anything in `feature-toggle-cli-followups/`.

- [ ] **Step 2: Write `docs/demo-videos/README.md`**

Sections, in this order:

1. `# FluxGate demo video series` — two-sentence purpose (from spec §1).
2. `## Chapters and website sections` — table: Chapter, Videos, Website section. Chapters: 1 Get started (01–03), 2 Model your release (04–07), 3 Connect your app (08–09), 4 Ship safely (10–11), 5 Integrations (12–14), 6 Observe and operate (15–16).
3. `## Story bible` — copy spec §2 verbatim (company, team, features, cast table, environments, pipeline, contexts, clients, Jira, story arc).
4. `## Recording setup` — copy spec §5 bullets, plus the CLI binary path from Step 1, plus "Run `python3 docs/demo-videos/tools/check_script.py docs/demo-videos/*.md --cli-bin <path> --coverage` before recording".
5. `## Before you publish` — spec §6 blocker table.
6. `## Continuity` — table with columns Video, Start state, End state, using exactly these rows:

| Video | Start state | End state |
|---|---|---|
| 01 | Fresh: no install needed; concept video. | No data created. |
| 02 | Fresh machine with Docker. | FluxGate running (backend 8080, edge 8081, UI 3000); `admin` signed in; no team. |
| 03 | End of 02: `admin` signed in, no team. | Team `Checkout`; users `priya` (Requester) and `sam` (Approver) in `Checkout`; `priya` has set a permanent password. |
| 04 | End of 03: team and users exist. | Environments Development, Staging, Production; pipeline `checkout-release` (Dev → Staging → Production). |
| 05 | End of 04: environments and pipeline exist. | Contexts `country` (US, CA, UK) and `user_tier` (free, plus). |
| 06 | End of 05: contexts exist. | Feature `express-checkout` (CONTEXTUAL, kind Release, variants `classic` and `express`, pipeline `checkout-release`, no criteria); feature `holiday-banner` (SIMPLE). |
| 07 | End of 06: features exist without criteria. | `express-checkout` criteria on Development and Staging: CA + plus → `express` (priority 1), 20/80 `express`/`classic` split (priority 2); Development stage deployed; rollout template `plus-first-then-20` saved. |
| 08 | End of 07: Development stage deployed. | Clients `checkout-service` (Backend) and `juniper-web` (Web, origin `http://localhost:5173`) on Development; evaluations recorded. |
| 09 | End of 08: clients exist. | CLI signed in as `priya`; automation client `ci-bot` exists; config exported to `fluxgate-config.yaml`. |
| 10 | End of 09: no approval policy yet. | Policy `Release approvals` (All Environments, Approver role); `express-checkout` deployed to Staging after `sam` approved; Production request rejected by `sam` with comment "Ship Production through CHK-142 so QA sign-off is tracked." |
| 11 | End of 10: Staging deployed, Production rejected. | Freeze window `Holiday freeze` created then ended (no active freeze); `holiday-banner` emergency-disabled then re-enabled; one scheduled change on `holiday-banner` cancelled; `holiday-banner` restored from Version History. |
| 12 | End of 11: no active freeze. | Jira integration `Juniper Jira` with rules In Review → request Production, Approved → approve Production, Done → deploy Production; Jira Automation rule active; write-back connected. |
| 13 | End of 12: Jira integration ready. | `CHK-142` linked and Done; `express-checkout` deployed to Production; FluxGate comments on `CHK-142`. |
| 14 | End of 13: Production deployed. | All four AI toggles on; `Release approvals` AI risk mode "Require one extra approver when high"; flags classified; a `holiday-banner` Staging request with an AI risk assessment, approved. |
| 15 | End of 14 plus traffic generator run. | No changes. |
| 16 | Fresh Kubernetes cluster. | FluxGate on k8s production overlay with TLS and SSO configured. |

7. `## Script template` — copy the "Script template" block and its rules from this plan.

- [ ] **Step 3: Verify the README against the spec**

Check by reading: every chapter, cast member, environment, context, client and blocker in spec §2–§6 appears in the README. The continuity table has 16 rows.

- [ ] **Step 4: Commit**

```bash
git add docs/demo-videos/README.md
git commit -m "docs: add demo video series README

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Workflow for every chapter task (Tasks 3–8)

Each chapter task repeats these steps for its videos. They are spelled out inside each task.

1. **Verify facts first.** Open the listed source files. Copy exact labels, field names and order of fields from the code. Where the plan's beat list uses a label the code does not render, use the code's label and note it in "Gotchas while recording".
2. **Write the script files** using the Script template, header Start/End state copied from the README continuity table, beats in the order listed, timecodes cumulative.
3. **Lint** with the command in the task. Fix every error. Repeat until `OK`.
4. **Read the voiceover aloud** (or count words) once per script to make sure it sounds like one developer talking to another.
5. **Commit.**

---

### Task 3: Chapter 1 — Get started (videos 01–03)

**Files:**
- Create: `docs/demo-videos/01-what-is-fluxgate.md`
- Create: `docs/demo-videos/02-install-and-first-boot.md`
- Create: `docs/demo-videos/03-teams-users-roles.md`

**Interfaces:**
- Consumes: linter (Task 1), continuity rows 01–03 (Task 2).
- Produces: end state of 03 (team and users) that video 04 starts from.

- [ ] **Step 1: Verify facts**

Read:
- `feature-toggle-ui/src/layout/navConfig.ts` — sidebar group names and item labels.
- `feature-toggle-ui/src/pages/CreateAdmin.tsx`, `feature-toggle-ui/src/pages/Login.tsx` — titles, field labels, button text.
- `docker-compose.yml`, `feature-toggle/docker-compose.yml`, `feature-toggle/feature-toggle-backend/config.toml`, `feature-toggle/feature-toggle-backend/src/config.rs`, `feature-toggle/feature-edge-server/CONFIG.md` — services, ports, env var names.
- Settings pages for teams, users, roles: find with `grep -rln "Create New Team\|Create User\|Global Roles\|Set Temporary Password\|Update Your Password" feature-toggle-ui/src --include=*.tsx`.
- SSO and notifications page titles: `grep -rn "Single sign-on\|Notification Settings" feature-toggle-ui/src --include=*.tsx`.

- [ ] **Step 2: Write `01-what-is-fluxgate.md`** — Length target `2:00`, website section "Get started › Overview".

Beats:
1. Hook: deploying code and releasing a feature are different events; FluxGate lets you separate them.
2. Architecture: UI → backend (REST 8080, gRPC 50051) → Postgres; edge server (8081) serves evaluations to apps from a cached feature set streamed over gRPC. Callout: architecture diagram (use `media/` system overview image if present; otherwise note "diagram needed" in Gotchas).
3. Sidebar tour at `/dashboard/overview`: Observe, Build, Connect, Govern, Settings — one sentence each.
4. Story: Juniper Market's Checkout team wants to ship `express-checkout` safely.
5. Hand-off to video 02.

- [ ] **Step 3: Write `02-install-and-first-boot.md`** — Length target `3:30`, website section "Get started › Install".

Beats:
1. Hook: running locally in under five minutes.
2. Terminal: generate key `openssl rand -base64 32`, export as `FLUXGATE_ENCRYPTION_KEY`; mention `TYPESAFE_API_KEY` is optional and needed for video 14.
3. Show `config.toml` keys `allowed_origin`, `http_addr`, `grpc_addr`, `public_base_url` (why `public_base_url` matters: Jira Events URL in video 12).
4. `docker compose up -d`; show backend, UI, Postgres, edge containers; migrations run on startup.
5. Browser `http://localhost:8080/docs` Swagger — one sentence.
6. Browser to UI: redirected to `/create-admin`; fill fields; "Create Admin".
7. `/login`; "Sign in"; empty System Overview.
8. Hand-off to video 03.

Gotchas must include: record from branch `cli-followups` (first-admin 401 bug on main); secrets typed on screen are `<redacted>`.

- [ ] **Step 4: Write `03-teams-users-roles.md`** — Length target `3:30`, website section "Get started › Teams and users".

Beats:
1. Hook: approvals only mean something when requesters and approvers are different people.
2. `/settings/teams` → "Create New Team" → `Checkout`. Team selector in header.
3. `/settings/users` → `/users/create`: create `priya` with Team Assignment `Checkout`, Role Assignment Requester, "Set Temporary Password"; repeat quickly for `sam` with Approver.
4. `/settings/roles` → "Global Roles": what Approver, Requester, Team Admin can do.
5. Sign out; sign in as `priya` → `/temporary-password-reset` "Update Your Password".
6. 20-second mention: `/settings/sso` (OIDC, group-to-role mapping; full setup in video 16) and `/settings/notifications` (email/SMS); `/reset-password` from the avatar menu.
7. Hand-off to video 04.

- [ ] **Step 5: Lint**

Run: `python3 docs/demo-videos/tools/check_script.py docs/demo-videos/0[1-3]-*.md`
Expected: `OK: 3 scripts`. Fix and re-run until clean.

- [ ] **Step 6: Commit**

```bash
git add docs/demo-videos/01-*.md docs/demo-videos/02-*.md docs/demo-videos/03-*.md
git commit -m "docs: add demo video scripts 01-03 (get started)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Chapter 2 — Model your release (videos 04–07)

**Files:**
- Create: `docs/demo-videos/04-environments-and-pipelines.md`
- Create: `docs/demo-videos/05-contexts.md`
- Create: `docs/demo-videos/06-create-your-first-feature.md`
- Create: `docs/demo-videos/07-targeting-rules.md`

**Interfaces:**
- Consumes: linter, continuity rows 04–07.
- Produces: end state of 07 (Development stage deployed with criteria) that video 08 evaluates against.

- [ ] **Step 1: Verify facts**

Read:
- `feature-toggle-ui/src/components/modals/CreateEnvironmentModal.tsx`; environments page (`grep -rln "Create New Environment" feature-toggle-ui/src`).
- Pipeline pages: `grep -rln "Create New Pipeline\|Design your release workflow\|Pipeline Stages" feature-toggle-ui/src`.
- Contexts pages: `grep -rln "Define context variables" feature-toggle-ui/src`.
- `feature-toggle-ui/src/pages/FeatureCreate.tsx` and components it imports: VariantManager, RolloutTemplatePicker, Stage Editor, criteria/rule editor, Blast Radius, Scheduled Changes. Record exact section titles, field labels, select option labels (Feature Type, Kind via `src/lib/flagKind.ts`, Lifecycle) and button text ("Add Variant", "Add Criterion", "Add Rule Group", "Add Condition", "Save Stage Criteria", "Distribute Evenly", "Apply Template", "Save Current As Template").
- `feature-toggle-ui/src/components/features/FeatureTable.tsx` — status badges, Saved Views, row actions.
- `fluxgate.wiki/Criteria.md`, `fluxgate.wiki/Priority-Evaluation.md`, `fluxgate.wiki/Feature-Variants.md` — concepts for voiceover.
- Deployment without a policy: read `feature-toggle/feature-toggle-backend/src/` stage request-change and approval-policy logic (`grep -rn "request-change\|request_change" feature-toggle/feature-toggle-backend/src | head`). Decide the exact clicks to take the Development stage to DEPLOYED when no policy exists (expected: "Request Deployment" auto-approves, then "Deploy"). Script exactly what the code does.

- [ ] **Step 2: Write `04-environments-and-pipelines.md`** — Length target `3:00`, section "Model your release › Environments and pipelines".

Beats: hook (one flag, many environments, enforced promotion order) → `/environments` "Create New Environment" modal ×3 (Development/Staging/Production types; record first in full, speed-ramp the other two) → `/pipelines` "Create New Pipeline" → `/pipelines/create` name `checkout-release`, three stages each bound to an environment → why order matters → hand-off.

- [ ] **Step 3: Write `05-contexts.md`** — Length target `2:30`, section "Model your release › Contexts".

Beats: hook (rules need facts about the request) → `/contexts` → `/contexts/create` `country` with "Add Value" US, CA, UK → `user_tier` free, plus → how your app sends `context` at evaluation time (show JSON snippet `{"bucketingKey":"user-42","country":"CA","user_tier":"plus"}` as a callout) → `bucketingKey` keeps a user in the same split bucket → hand-off.

- [ ] **Step 4: Write `06-create-your-first-feature.md`** — Length target `4:00`, section "Model your release › Features".

Beats: hook → `/features` "Create New Feature" → `/features/create` Basic Information (Name `express-checkout`, Description, Purpose, Ticket / Reference URL `https://juniper.atlassian.net/browse/CHK-142`, Feature Type CONTEXTUAL, Kind Release, Lifecycle, Owner `priya`, Expiry, Tags `checkout`, `q4`) → "Feature Variants" "Add Variant" `classic`, `express` (String) → "Pipeline Template" `checkout-release`, graph appears → "Blast Radius" panel, one sentence → save → `/features` list: badges, Saved Views, "View Details" to `/features/:id` (tabs one line) → quick second flag `holiday-banner` (SIMPLE), speed-ramped → hand-off.

- [ ] **Step 5: Write `07-targeting-rules.md`** — Length target `4:00`, section "Model your release › Targeting".

Beats: hook (Canadian Plus users first, then 20/80) → `/features/:id/edit` → click Development stage → "Stage Editor" → "Add Criterion": "Add Rule Group" AND, conditions `country` equals `CA`, `user_tier` equals `plus`; Variant Selection Mode Specific Variant `express` → second criterion: Weighted Split 20/80 `express`/`classic` ("Distribute Evenly" shown then adjusted) → drag to reorder; lower priority number evaluates first (use `Label exceptions` for "Priority 1"/"Priority 2" if built at runtime) → "Save Stage Criteria" → "Save Current As Template" `plus-first-then-20` → click Staging stage, "Apply Template", save → Development stage "Actions" → deploy steps verified in Step 1 → hand-off.

- [ ] **Step 6: Lint**

Run: `python3 docs/demo-videos/tools/check_script.py docs/demo-videos/0[1-7]-*.md`
Expected: `OK: 7 scripts`. (Includes 01–03 so continuity 03→04 is checked.)

- [ ] **Step 7: Commit**

```bash
git add docs/demo-videos/0[4-7]-*.md
git commit -m "docs: add demo video scripts 04-07 (model your release)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Chapter 3 — Connect your app (videos 08–09)

**Files:**
- Create: `docs/demo-videos/08-clients-and-edge-server.md`
- Create: `docs/demo-videos/09-cli-and-automation.md`

**Interfaces:**
- Consumes: linter, continuity rows 08–09, CLI binary from Task 2.
- Produces: end state of 09 (clients, CLI login, `ci-bot`).

- [ ] **Step 1: Verify facts**

Read:
- Client pages: `grep -rln "Create Client\|Manage client applications" feature-toggle-ui/src`. Record Client Type options, environment selection, web origins field, how the SDK key is displayed.
- `feature-toggle-ui/src` Developer Setup Wizard and Integrations pages (`grep -rln "SDK Setup Wizard\|OpenFeature & OFREP\|OpenFeature &amp; OFREP" feature-toggle-ui/src`).
- System clients pages (`grep -rln "Create Automation Client" feature-toggle-ui/src`) — confirm whether the button navigates to `/system-clients/create`.
- `feature-toggle/docs/edge-server-api.md`, `feature-toggle/feature-edge-server/src/handlers.rs` — exact request/response JSON for `POST /evaluate` and OFREP endpoints, auth header forms, ETag behaviour.
- `feature-toggle-cli-followups/fluxgate-cli/README.md` and `feature-toggle-cli-followups/fluxgate-cli/src/cli.rs` — exact subcommands and flags for `login --use-device-code`, `flags list/get/search`, `evaluate --exit-code`, `config export/import`, `watch`, `system-clients`. Run `feature-toggle-cli-followups/target/debug/fluxgate <cmd> --help` for each.
- `DeviceLogin.tsx` — "Approve a CLI login" page text.
- For the OpenFeature OFREP provider: use the official `@openfeature/server-sdk` with `@openfeature/ofrep-provider` (Node). Check the provider's constructor options with `npm view @openfeature/ofrep-provider readme` or its GitHub README; script the exact code.
- `fluxgate-springboot/README.md` — for the appendix only.

- [ ] **Step 2: Write `08-clients-and-edge-server.md`** — Length target `4:00`, section "Connect your app › Edge server and SDKs".

Beats: hook (your app asks the edge, not the backend) → `/clients` → `/clients/create` `checkout-service` Backend on Development; copy SDK key (shown as `<redacted>` in voiceover callouts) → `juniper-web` Web with origin `http://localhost:5173` (CORS reason) → `/developer/setup` "SDK Setup Wizard" Ready Snippets → terminal curl `POST http://localhost:8081/evaluate` with CA/plus context returns `express`; repeat with US/free to show split → OFREP bulk `POST /ofrep/v1/evaluate/flags`, second call returns 304 with ETag → `/developer/integrations` → 15-line Node app with OpenFeature OFREP provider evaluating `express-checkout` → hand-off.

Add a final section `## Appendix: Spring Boot (record after starter fix)` with a 60-second scene table using `fluxgate.*` properties and `FluxGateClient` from `fluxgate-springboot/README.md`, and a note that the starter currently uses the old edge contract.

- [ ] **Step 3: Write `09-cli-and-automation.md`** — Length target `3:30`, section "Connect your app › CLI and CI".

Beats: hook (flags in your terminal and pipeline) → `fluxgate login --use-device-code` → browser `/device` approve → `fluxgate whoami` → `fluxgate flags list`, `fluxgate flags get express-checkout` → CI gate snippet in a fenced block: `fluxgate evaluate express-checkout ... --exit-code` with `FLUXGATE_URL` / `FLUXGATE_TOKEN`; exit 10 means off → `/system-clients` "Create Automation Client" `ci-bot`, Token Scope, token shown as `<redacted>` → `fluxgate config export` to `fluxgate-config.yaml`, one line on `config import` → `fluxgate watch` stream while toggling in UI → hand-off.

- [ ] **Step 4: Lint with CLI verification**

Run: `python3 docs/demo-videos/tools/check_script.py docs/demo-videos/0[1-9]-*.md --cli-bin feature-toggle-cli-followups/target/debug/fluxgate`
Expected: `OK: 9 scripts`.

- [ ] **Step 5: Commit**

```bash
git add docs/demo-videos/08-*.md docs/demo-videos/09-*.md
git commit -m "docs: add demo video scripts 08-09 (connect your app)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Chapter 4 — Ship safely (videos 10–11)

**Files:**
- Create: `docs/demo-videos/10-approvals-and-policies.md`
- Create: `docs/demo-videos/11-safety-nets.md`

**Interfaces:**
- Consumes: linter, continuity rows 10–11.
- Produces: end state of 11 (policy exists, Staging deployed, Production rejected, no active freeze).

- [ ] **Step 1: Verify facts**

Read:
- `feature-toggle-ui/src/components/modals/ApprovalPolicyFormModal.tsx` — Scope options, approver fields, "Auto-approve After (hours)".
- `ApprovalsPage.tsx` and its detail components — filter labels, section titles, "Approve with comment", "Reject with comment".
- Stage Actions menu in `FeatureCreate.tsx` — "Request Deployment", "Deploy", fields Reason, External Reference; policy preview banner text.
- Header pending-approvals badge component.
- Freeze windows page (`grep -rln "Freeze Windows" feature-toggle-ui/src`) and the "Active change freeze" banner; Override Reason field.
- `feature-toggle-ui/src/components/modals/FeatureEmergencyActionModal.tsx`; `FeatureDetail.tsx` badges, tabs, "Rollback"; Version History tab; Scheduled Changes section.
- `fluxgate.wiki/Approval-Policies.md`, `fluxgate.wiki/Approvals.md`.

- [ ] **Step 2: Write `10-approvals-and-policies.md`** — Length target `4:00`, section "Ship safely › Approvals".

Beats: hook (no one ships to customers alone) → as `admin`, `/settings/approval-policies` "Create Policy" `Release approvals`, Scope "All Environments", Approver Roles Approver → as `priya`, `/features/:id/edit`, Staging stage "Actions" → "Request Deployment" with Reason and External Reference `CHK-142`; policy preview banner → as `sam`, header badge → `/approvals` Pending → detail: Blast radius, Dependency impact, Structured diff, Approval policy, Status timeline, Votes → "Approve with comment" → as `priya`, "Deploy" → `priya` requests Production → `sam` "Reject with comment" with comment `Ship Production through CHK-142 so QA sign-off is tracked.` → hand-off teases Jira.

- [ ] **Step 3: Write `11-safety-nets.md`** — Length target `3:30`, section "Ship safely › Safety nets".

Beats: hook (when things go wrong at 2 a.m.) → `/settings/freeze-windows` "New Window" `Holiday freeze` active now → "Active change freeze" banner on a stage action, Override Reason → end the window → `/features` row action "Emergency Disable" on `holiday-banner` → modal "Disable immediately" → EMERGENCY OVERRIDE badge → "Emergency Enable" → Scheduled Changes: schedule a disable for next week, then cancel it → `/features/:id/edit` History tab "Version History", diff two versions, roll back `holiday-banner` → `/features/:id` Activity tab → hand-off.

- [ ] **Step 4: Lint**

Run: `python3 docs/demo-videos/tools/check_script.py docs/demo-videos/0*.md docs/demo-videos/1[01]-*.md --cli-bin feature-toggle-cli-followups/target/debug/fluxgate`
Expected: `OK: 11 scripts`.

- [ ] **Step 5: Commit**

```bash
git add docs/demo-videos/10-*.md docs/demo-videos/11-*.md
git commit -m "docs: add demo video scripts 10-11 (ship safely)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Chapter 5 — Integrations (videos 12–14)

**Files:**
- Create: `docs/demo-videos/12-jira-setup.md`
- Create: `docs/demo-videos/13-jira-end-to-end.md`
- Create: `docs/demo-videos/14-jev-ai-assistance.md`

**Interfaces:**
- Consumes: linter, continuity rows 12–14, CLI binary.
- Produces: end state of 14.

- [ ] **Step 1: Verify facts**

Read:
- `feature-toggle/docs/jira-integration/setup-guide.md`, `feature-toggle/docs/jira-integration/README.md`, `feature-toggle/docs/jira-integration/screenshots/README.md` — exact Jira Automation steps, header format, status rule actions (`request`, `approve`, `deploy`, `rollback`), Jira-approved environments, write-back setup, event log, outbound jobs.
- Jira settings page (`grep -rln "New integration\|Rotate secret\|Event log" feature-toggle-ui/src`) and `JiraLinksCard` ("Add Jira issue").
- `feature-toggle/feature-toggle-backend/src/rest/jira_events.rs` and `logic/jira_*.rs` — confirm that an Approved transition approves the pending Production request and Done deploys it, and what comments write-back posts.
- `feature-toggle/docs/ai-judgments/README.md`, `design.md`, `HANDOFF.md` §4 — the four AI features, fail-open behaviour, known gaps.
- AI settings page (`grep -rln "AI assistance\|Classify existing flags" feature-toggle-ui/src`), approval "AI risk assessment" panel, `ReasonQualityHint`, `FlagKindField` ("AI suggested"), command palette "Ask FluxGate", `hooks/useAiFeatures.ts`, policy "AI risk mode" option labels.
- CLI: `fluxgate jira --help`, `fluxgate ai --help`.

- [ ] **Step 2: Write `12-jira-setup.md`** — Length target `4:00`, section "Integrations › Jira setup".

Beats: hook (your release process already lives in Jira) → `/settings/jira` "New integration" `Juniper Jira`, base URL, environment field, aliases, "Jira approves in" Production → Connection: Events URL, secret shown once (`<redacted>`), "Rotate secret" → Jira: Project settings › Automation, rule "Work item transitioned" → Send web request to Events URL with header `Authorization: Bearer <secret>` → alternative native webhook with HMAC `X-Hub-Signature`, one line → back in FluxGate, Status rules "Add rule" ×3 (In Review → `request` Production; Approved → `approve` Production; Done → `deploy` Production) → Write-back: Jira Cloud, API token `<redacted>`, "Post comments", test connection → hand-off.

Gotchas: Events URL must be reachable from Jira Cloud (tunnel when local; `public_base_url` from video 02); `deploy` is refused unless the request is already approved.

- [ ] **Step 3: Write `13-jira-end-to-end.md`** — Length target `4:00`, section "Integrations › Jira end to end". Split-screen: Jira left, FluxGate right.

Beats: hook (move the ticket, ship the feature) → `/features/:id` Jira card "Add Jira issue" `CHK-142` → move `CHK-142` To Do → In Review → FluxGate `/approvals` shows a new Production request with External Reference `CHK-142` → move to Approved → request approved (Jira-approved environment; explain `sam` set this up) → move to Done → Production stage DEPLOYED → Jira issue shows FluxGate comments and remote link → `/settings/jira` Event log and outbound jobs → terminal `fluxgate jira events` → boundary line: Jira drives FluxGate; FluxGate never transitions your issues → hand-off.

- [ ] **Step 4: Write `14-jev-ai-assistance.md`** — Length target `4:00`, section "Integrations › Jev AI".

Beats: hook (a second pair of eyes on every risky change) → `/settings/ai` "AI assistance", four toggles on (requires `TYPESAFE_API_KEY`, set in video 02) → as `priya`, `holiday-banner` Staging "Request Deployment" with reason `fix` → reason quality hint; rewrite the reason → as `sam`, `/approvals` detail "AI risk assessment" panel: level and reasons (includes Jira key when linked) → `/settings/approval-policies` edit `Release approvals`: "AI risk mode" options; choose "Require one extra approver when high" → `/settings/ai` "Classify existing flags"; `/features` shows AI-suggested kind on `holiday-banner` → ⌘K "Ask FluxGate": `which checkout flags are on in production for Canada?` → fail-open: if Jev is down, approvals proceed without AI → `sam` approves → hand-off.

Gotchas: AI UI is hidden without `TYPESAFE_API_KEY` and team toggles; avoid filming the auto-approve path (HANDOFF §4 stall bug).

- [ ] **Step 5: Lint**

Run: `python3 docs/demo-videos/tools/check_script.py docs/demo-videos/0*.md docs/demo-videos/1[0-4]-*.md --cli-bin feature-toggle-cli-followups/target/debug/fluxgate`
Expected: `OK: 14 scripts`.

- [ ] **Step 6: Commit**

```bash
git add docs/demo-videos/1[2-4]-*.md
git commit -m "docs: add demo video scripts 12-14 (integrations)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Chapter 6 — Observe and operate (videos 15–16) and full-series check

**Files:**
- Create: `docs/demo-videos/15-dashboards.md`
- Create: `docs/demo-videos/16-going-to-production.md`
- Modify: `docs/demo-videos/README.md` (only if the coverage run forces a fix)

**Interfaces:**
- Consumes: linter, continuity rows 15–16, all earlier scripts.
- Produces: complete series passing `--coverage`.

- [ ] **Step 1: Verify facts**

Read:
- `feature-toggle-ui/src/pages/Dashboard/SystemOverview.tsx`, evaluation analytics page, `Metrics.tsx`, audit analytics page — card and panel titles.
- `FeatureExperimentPanel` — Experiment tab content on `/features/:id/edit`.
- Command palette component (`grep -rln "Search or jump to" feature-toggle-ui/src`).
- `perf-test/README.md`, `k6-tests/` — the traffic-generator command to run before recording.
- `k8s/KUSTOMIZE_README.md`, `k8s/TLS_SETUP.md`, `k8s/QUICK_REFERENCE.md`; SSO page (`/settings/sso`) and JWT page (`/settings/jwt`, "JWT Secret Management", "Emergency Actions").

- [ ] **Step 2: Write `15-dashboards.md`** — Length target `3:30`, section "Observe and operate › Dashboards".

Beats: hook (did the rollout actually work?) → `/dashboard/overview` "System Overview": the four cards, Activity Feed → `/dashboard/evaluation-analytics`: Evaluation Timeline, Evaluations By Feature → `/dashboard/metrics` "Metrics & Experiments": Variant Comparison `classic` vs `express` → `/features/:id/edit` Experiment tab → `/dashboard/audit-analytics`: Top Changed Flags, Actors, Recent Audit Events (shows `sam`, `priya`, Jira) → ⌘K quick links → series wrap-up line → hand-off to optional video 16.

Gotchas: run the traffic generator from Step 1 first; never open `/dashboard/rollout`.

- [ ] **Step 3: Write `16-going-to-production.md`** — Length target `3:30`, section "Observe and operate › Production deployment". Audience: platform/ops.

Beats: hook → `kubectl apply -k k8s/overlays/production`; 3 backends with clustering → TLS from `k8s/TLS_SETUP.md` (generate your own cert; never show repo key files) → required env: `DATABASE_URL`, `FLUXGATE_ENCRYPTION_KEY`, `TYPESAFE_API_KEY`, edge `EDGE_*` vars → `/settings/sso` "Single sign-on": OIDC provider, group-to-role mappings, enforce SSO → `/settings/jwt` "JWT Secret Management", "Emergency Actions" → closing line.

Gotchas: k8s configs have stale `jwt_secret` and edge env names, and lack encryption/TypeSafe env (spec §6 #5) — fix before recording.

- [ ] **Step 4: Full-series lint with coverage**

Run: `python3 docs/demo-videos/tools/check_script.py docs/demo-videos/*.md --cli-bin feature-toggle-cli-followups/target/debug/fluxgate --coverage`
Expected: `OK: 16 scripts`. Any `coverage:` error means a routed screen is missing; add a scene to the video named in spec §7 for that route.

- [ ] **Step 5: Run linter tests again**

Run: `python3 -m pytest docs/demo-videos/tools -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add docs/demo-videos/
git commit -m "docs: add demo video scripts 15-16 and complete series

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
