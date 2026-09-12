"""The excerpt filler: a generated copy must be verbatim, loud on ambiguity, and idempotent.

The sample run invokes the CLI a consumer repository actually calls, on a stored skeleton under
`tests/fixtures/`, against this repository's own conventions. The unit tests below it reach the
parser edges that skeleton cannot hold without being corrupted.
"""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "fill-excerpts.py"
INPUT = ROOT / "tests" / "fixtures" / "fill-excerpts.input.md"
SOURCE_DOC = ROOT / "conventions" / "01-structure-naming.md"

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


# --- the sample run: the CLI a consumer repository calls ------------------------------------


def cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo", str(ROOT), *argv], capture_output=True, text=True
    )


def core_rules_of(doc: Path) -> str:
    body = doc.read_text(encoding="utf-8")
    return body[body.index("## Core Rules") : body.index("## Details")]


@pytest.fixture(scope="module")
def filled(tmp_path_factory):
    """One run of `--fill`, shared by the assertions below so each can be read on its own."""
    out = tmp_path_factory.mktemp("fill") / "rules.md"
    result = cli("--fill", str(INPUT), str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    return out.read_text(encoding="utf-8")


def test_the_fill_run_writes_the_anchored_bullets_in_anchor_order(filled):
    """The fixture lists its anchors against the document's order, so output following the
    document rather than the anchor list means the anchor list decided nothing.

    Read off the filled bullets, not the whole file: the marker line the run copies through
    quotes both anchors itself, and searching the file would compare that line to itself.
    """
    bullets = [ln for ln in filled.splitlines() if ln.startswith("- ")]
    assert len(bullets) == 2, f"the run filled {len(bullets)} bullets, not 2"
    assert "rename in place" in bullets[0], bullets[0]
    assert "semantic naming" in bullets[1], bullets[1]


def test_the_fill_run_copies_a_bullet_verbatim(filled):
    """A paraphrased or re-wrapped copy is a second wording of the rule, which is what 15
    forbids. The link-free anchor is the one whose source line the output must equal exactly;
    the rewrite the other anchor needs is checked on its own below.
    """
    source = [ln for ln in core_rules_of(SOURCE_DOC).splitlines() if "semantic naming" in ln]
    assert len(source) == 1, "the anchor no longer names one Core Rules line"
    assert source[0] in filled.splitlines(), f"the bullet was not copied as written: {source[0]!r}"


def test_the_fill_run_rewrites_relative_links_to_clone_paths(filled):
    """15 requires a copy to name its source, and the copy lands outside `conventions/`, where
    a relative link resolves to nothing. The clone path is what a reader there can follow.

    The target is read out of the source bullet rather than written here, so rewording 01 moves
    the expectation with it and only the script's own behaviour can fail this.
    """
    source = next(ln for ln in core_rules_of(SOURCE_DOC).splitlines() if "rename in place" in ln)
    targets = re.findall(r"\]\((\d\d-[a-z-]+\.md)\)", source)
    assert targets, f"the anchored bullet carries no relative convention link: {source!r}"
    for target in targets:
        assert f"~/Codes/develop-convention/conventions/{target}" in filled
        assert f"]({target})" not in filled
    assert "/Users/" not in filled, "the rewrite leaked the machine it ran on"


def test_the_fill_run_stamps_the_source_and_the_commit_it_read(filled):
    """The stamp is what makes the copy checkable: which document, at which commit."""
    sha = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert f"<!-- filled from conventions/01-structure-naming.md @ {sha} -->" in filled


def test_the_fill_run_leaves_the_authored_text_outside_the_markers(filled):
    """The skeleton is authored prose with marker blocks in it; everything outside a block is
    the author's and is reproduced as written.
    """
    source = INPUT.read_text(encoding="utf-8")
    head, _, tail = source.partition("<!-- excerpt(")
    assert filled.startswith(head)
    assert filled.endswith(tail.split("<!-- /excerpt -->\n", 1)[1])


def test_the_check_run_passes_on_a_renderable_skeleton_and_fails_on_a_broken_anchor(tmp_path):
    """`--check` is what a consumer's CI calls, so its exit code has to separate the two."""
    ok = cli("--check", str(INPUT))
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "render cleanly" in ok.stdout

    broken = tmp_path / "broken.md"
    broken.write_text(
        INPUT.read_text(encoding="utf-8").replace('"rename in place"', '"no such rule text"'),
        encoding="utf-8",
    )
    bad = cli("--check", str(broken))
    assert bad.returncode == 1, bad.stdout + bad.stderr
    assert "matches 0" in bad.stderr


def skeleton(anchors: str) -> str:
    return (
        "---\nalwaysApply: true\n---\n\n# Rules\n\n"
        f"<!-- excerpt(conventions/99-sample.md): {anchors} -->\n"
        "<!-- /excerpt -->\n\nauthored trailer line\n"
    )


def test_a_bullet_continuing_over_indented_and_unindented_lines_is_taken_whole(repo):
    """A bullet is not a line. The sample run's source has none spilling over, and a skeleton
    could only hold one by corrupting it, so the continuation rule is checked here.
    """
    out = fx.render(skeleton('"Third rule"'), repo, "t", "abc1234")
    assert (
        "- Third rule that continues\n  onto an indented second line"
        "\nand a lazy unindented third line." in out
    )


def test_zero_and_ambiguous_anchors_abort(repo):
    with pytest.raises(fx.FillError, match="matches 0"):
        fx.render(skeleton('"no such text"'), repo, "t", "s")
    with pytest.raises(fx.FillError, match="matches 3"):
        fx.render(skeleton('"naming"'), repo, "t", "s")


def test_details_bullets_are_out_of_reach(repo):
    with pytest.raises(fx.FillError, match="matches 0"):
        fx.render(skeleton('"never be excerpted"'), repo, "t", "s")


def test_link_rewrite_keeps_fragments_and_leaves_schemes_alone(repo):
    out = fx.render(skeleton('"Fifth rule"'), repo, "t", "s")
    assert "details (~/Codes/develop-convention/conventions/02-config.md#run-naming)" in out
    assert "[mail](mailto:user@example.com)" in out


def test_markerless_input_aborts(repo):
    with pytest.raises(fx.FillError, match="no excerpt markers"):
        fx.render("# a rules file whose markers were lost\n", repo, "t", "s")


def test_missing_heading_and_empty_section_abort(repo):
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


def test_rendering_a_filled_file_again_settles(repo):
    """A second pass must replace the block the first wrote, not stack a copy on top of it —
    the reason `bootstrap.sh --sync` can be run on an already-filled tree.
    """
    once = fx.render(skeleton('"First rule"'), repo, "t", "s")
    assert fx.render(once, repo, "t", "s") == once


def test_broken_markers_abort(repo):
    with pytest.raises(fx.FillError, match="never closed"):
        fx.render('<!-- excerpt(conventions/99-sample.md): "First rule" -->\n', repo, "t", "s")
    with pytest.raises(fx.FillError, match="without an opening"):
        fx.render("<!-- /excerpt -->\n", repo, "t", "s")
