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
