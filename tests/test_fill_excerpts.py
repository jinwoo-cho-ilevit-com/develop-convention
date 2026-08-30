"""The excerpt filler: a generated copy must be verbatim, loud on ambiguity, and idempotent."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "fill_excerpts", ROOT / "scripts" / "fill-excerpts.py"
)
fx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fx)

DOC = """# 99. Sample

## Core Rules

- First rule about naming, stated plainly.
- Second rule about config with a link (→ [02-config.md](02-config.md)).
- Third rule that continues
  onto an indented second line
and a lazy unindented third line.
- Fourth rule that also mentions naming in passing.
- Fifth rule with a section link ([details](02-config.md#run-naming)) and a
  [mail](mailto:user@example.com) address.

## Details

- A Details bullet that must never be excerpted.
"""


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "conventions").mkdir()
    (tmp_path / "conventions" / "99-sample.md").write_text(DOC, encoding="utf-8")
    return tmp_path


def skeleton(anchors: str) -> str:
    return (
        "---\nalwaysApply: true\n---\n\n# Rules\n\n"
        f"<!-- excerpt(conventions/99-sample.md): {anchors} -->\n"
        "<!-- /excerpt -->\n\nauthored trailer line\n"
    )


def test_fills_verbatim_in_anchor_order(repo):
    out = fx.render(skeleton('"Third rule" || "First rule"'), repo, "t", "abc1234")
    body = out.split("-->\n", 2)[2]
    assert body.index("Third rule") < body.index("First rule")
    assert (
        "- Third rule that continues\n  onto an indented second line"
        "\nand a lazy unindented third line." in out
    )
    assert "filled from conventions/99-sample.md @ abc1234" in out


def test_zero_and_ambiguous_anchors_abort(repo):
    with pytest.raises(fx.FillError, match="matches 0"):
        fx.render(skeleton('"no such text"'), repo, "t", "s")
    with pytest.raises(fx.FillError, match="matches 3"):
        fx.render(skeleton('"naming"'), repo, "t", "s")


def test_details_bullets_are_out_of_reach(repo):
    with pytest.raises(fx.FillError, match="matches 0"):
        fx.render(skeleton('"never be excerpted"'), repo, "t", "s")


def test_relative_links_become_clone_paths(repo):
    out = fx.render(skeleton('"Second rule"'), repo, "t", "s")
    assert "(→ ~/Codes/develop-convention/conventions/02-config.md)" in out
    assert "](02-config.md)" not in out


def test_link_rewrite_keeps_fragments_and_leaves_schemes_alone(repo):
    out = fx.render(skeleton('"Fifth rule"'), repo, "t", "s")
    assert "details (~/Codes/develop-convention/conventions/02-config.md#run-naming)" in out
    assert "[mail](mailto:user@example.com)" in out


def test_markerless_input_aborts(repo):
    with pytest.raises(fx.FillError, match="no excerpt markers"):
        fx.render("# a rules file whose markers were lost\n", repo, "t", "s")


def test_missing_heading_and_empty_section_abort(repo, tmp_path):
    (repo / "conventions" / "98-empty.md").write_text("# 98\n\n## Core Rules\n\n## Details\n")
    with pytest.raises(fx.FillError, match="no bullets"):
        fx.render(
            '<!-- excerpt(conventions/98-empty.md): "x" -->\n<!-- /excerpt -->\n', repo, "t", "s"
        )
    (repo / "conventions" / "97-headless.md").write_text("# 97\n\nprose only\n")
    with pytest.raises(fx.FillError, match="no '## Core Rules'"):
        fx.render(
            '<!-- excerpt(conventions/97-headless.md): "x" -->\n<!-- /excerpt -->\n', repo, "t", "s"
        )


def test_idempotent_and_preserves_text_outside_markers(repo):
    src = skeleton('"First rule"')
    once = fx.render(src, repo, "t", "s")
    assert fx.render(once, repo, "t", "s") == once
    assert once.startswith("---\nalwaysApply: true\n---\n\n# Rules\n\n")
    assert once.endswith("authored trailer line\n")


def test_broken_markers_abort(repo):
    with pytest.raises(fx.FillError, match="never closed"):
        fx.render('<!-- excerpt(conventions/99-sample.md): "First rule" -->\n', repo, "t", "s")
    with pytest.raises(fx.FillError, match="without an opening"):
        fx.render("<!-- /excerpt -->\n", repo, "t", "s")


def test_renders_against_the_real_repo():
    marker = '<!-- excerpt(conventions/01-structure-naming.md): "semantic naming" -->'
    out = fx.render(marker + "\n<!-- /excerpt -->\n", ROOT, "t", "s")
    assert any(ln.startswith("- ") and "semantic naming" in ln for ln in out.splitlines())
    assert "/Users/" not in out
