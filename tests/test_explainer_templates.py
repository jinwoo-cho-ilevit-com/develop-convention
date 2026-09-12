"""Invariants for the shipped explainer HTML templates.

These lock in the checks the review lanes ran by hand: self-containment,
snippet-marker pairing, the static-number-vs-embedded-data contract, and the
figure accessibility contract. The shared CSS/JS being generated from `shared/`
rather than copied is decided by the sample run — `render-explainer.py --check`,
the command CLAUDE.md's verification item 8 names — with the marker edges that
command cannot reach checked against `render()` directly. Everything here reads
the files; nothing executes JS, so anything requiring a browser (tooltip
behavior, contrast) stays with the review lanes.
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest
from _repo import ROOT as REPO

SKILL_DIR = Path("skills") / "explainer-docs"
SKELETON = REPO / SKILL_DIR / "explainer-skeleton.html"
GALLERY = REPO / SKILL_DIR / "explainer-gallery.html"
TEMPLATES = {"skeleton": SKELETON, "gallery": GALLERY}

spec = importlib.util.spec_from_file_location(
    "render_explainer", REPO / "scripts" / "render-explainer.py"
)
rx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rx)


@pytest.fixture(params=sorted(TEMPLATES), scope="module")
def template(request):
    path = TEMPLATES[request.param]
    return request.param, path, path.read_text(encoding="utf-8")


def _data_block(text, path):
    m = re.search(
        r'<script type="application/json" id="explainer-data">(.*?)</script>',
        text,
        re.S,
    )
    assert m, f"{path.name}: embedded explainer-data block missing"
    return json.loads(m.group(1))


def _get(data, dotted):
    node = data
    for step in dotted.split("."):
        if isinstance(node, list):
            node = node[int(step)]
        else:
            assert step in node, f"path {dotted!r}: field {step!r} missing"
            node = node[step]
    return node


def test_the_version_stamp_opens_each_file(template):
    name, path, text = template
    first = text.splitlines()[0]
    assert re.fullmatch(rf"<!-- explainer-{name} v\d+ -->", first.strip()), (
        f"{path.name}: first line must be the version stamp, got {first!r}"
    )


def test_no_external_network_references_in_attributes(template):
    name, path, text = template
    hits = []
    for attr, value in re.findall(r'\b(src|href)="([^"]*)"', text):
        if re.match(r"https?://", value):
            hits.append(f'{attr}="{value}"')
    for value in re.findall(r"url\(([^)]*)\)", text):
        if re.match(r"""["']?https?://""", value.strip()):
            hits.append(f"url({value})")
    assert not hits, f"{path.name}: external references in attributes: {hits}"


def test_no_embedded_font_data(template):
    """Fonts come from the system stack: a base64 face is dead weight a model
    copying the file corrupts, and it is not what makes a copy legible."""
    name, path, text = template
    assert "@font-face" not in text and "base64," not in text, (
        f"{path.name}: embedded font data is not allowed"
    )


def test_every_static_number_matches_its_source_field(template):
    """The Core Rule contract: a .num[data-src] element's static text must
    agree with the embedded data block at the precision it displays."""
    name, path, text = template
    data = _data_block(text, path)
    spans = re.findall(
        r'<span[^>]*\bdata-src="([^"]+)"[^>]*\bdata-fmt="([^"]+)"[^>]*>([^<]*)<',
        text,
    )
    tspans = re.findall(
        r'<tspan[^>]*\bdata-src="([^"]+)"[^>]*\bdata-fmt="([^"]+)"[^>]*>([^<]*)<',
        text,
    )
    found = spans + tspans
    if name == "skeleton":
        assert found, f"{path.name}: skeleton must demonstrate data-src numbers"
    for src, fmt, shown in found:
        value = _get(data, src)
        assert isinstance(value, (int, float)), (
            f"{path.name}: {src} is not numeric in the data block"
        )
        cleaned = shown.strip().replace(",", "").rstrip("%°일건")
        assert cleaned, f"{path.name}: {src} has empty static text (JS-only?)"
        displayed = float(cleaned)
        if fmt.startswith("pct"):
            digits = int(fmt[3:] or 0)
            expected = value * 100
        else:
            digits = int(re.sub(r"\D", "", fmt) or 0)
            expected = value
        tolerance = 0.5 * 10**-digits + 1e-9
        assert abs(displayed - expected) <= tolerance, (
            f"{path.name}: {src} shows {shown!r} but data gives {expected} "
            f"(fmt {fmt}, tolerance {tolerance})"
        )


def render_cli(repo, *argv):
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "render-explainer.py"), "--repo", str(repo), *argv],
        capture_output=True,
        text=True,
    )


def test_the_check_run_passes_on_the_shipped_templates():
    """The sample run: `--check` is what CLAUDE.md's verification item 8 and the review lanes
    call, so it is the entry point that decides whether the shared blocks are current. Each
    template must be byte-identical to what the script writes from `shared/`.
    """
    result = render_cli(REPO, "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    # The count, not just the phrase: a template dropped from the script's own list is then a
    # template nothing checks, and the run would still report a clean match over the rest.
    assert f"OK: {len(TEMPLATES)} template(s) match" in result.stdout, result.stdout


def test_the_check_run_fails_on_a_template_stale_against_shared(tmp_path):
    """The other half: a check that only ever passes says nothing about the tree it read. An
    edited fragment has to come back as a non-zero exit naming the template it no longer matches.
    """
    shutil.copytree(REPO / SKILL_DIR, tmp_path / SKILL_DIR)
    css = tmp_path / SKILL_DIR / "shared" / "explainer.css"
    css.write_text(css.read_text(encoding="utf-8") + ".sabotaged{color:red}\n", encoding="utf-8")
    result = render_cli(tmp_path, "--check")
    assert result.returncode == 1, result.stdout
    assert "stale" in result.stderr
    # Both templates carry the fragment, so both are stale. Naming only one leaves the other as
    # a template the run no longer reads at all.
    for name in (SKELETON.name, GALLERY.name):
        assert name in result.stderr, result.stderr


def test_rendering_replaces_a_stale_block_and_settles():
    """A second pass must replace the whole block the first pass wrote — the
    provenance line included — not stack another copy on top of it."""
    fragments = {"css": ("shared/x.css", "body{}\n")}
    once = rx.render("/* shared:start:css */\nOLD\n/* shared:end:css */\n", fragments, "t")
    assert "OLD" not in once
    assert rx.render(once, fragments, "t") == once


BROKEN = {
    "missing end marker": "/* shared:start:css */\n",
    "end without start": "/* shared:end:css */\n",
    "duplicate start": (
        "/* shared:start:css */\n/* shared:end:css */\n"
        "/* shared:start:css */\n/* shared:end:css */\n"
    ),
    "unknown block": "/* shared:start:nope */\n/* shared:end:nope */\n",
    "unplaced fragment": "body{}\n",
}


@pytest.mark.parametrize("case", sorted(BROKEN))
def test_a_broken_marker_set_aborts(case):
    """A marker lost in an edit must fail loudly, not ship a template whose
    shared half silently went missing."""
    with pytest.raises(rx.RenderError):
        rx.render(BROKEN[case], {"css": ("shared/x.css", "body{}\n")}, case)


def test_snippet_markers_pair_up_and_match_their_code_blocks():
    text = GALLERY.read_text(encoding="utf-8")
    starts = re.findall(r"<!-- snippet:start:([\w-]+) -->", text)
    ends = re.findall(r"<!-- snippet:end:([\w-]+) -->", text)
    targets = re.findall(r'data-snippet-for="([\w-]+)"', text)
    assert len(starts) == len(set(starts)), "duplicate snippet:start ids"
    assert sorted(starts) == sorted(ends), (
        f"unpaired snippet markers: starts={sorted(set(starts) - set(ends))} "
        f"ends={sorted(set(ends) - set(starts))}"
    )
    assert sorted(targets) == sorted(starts), (
        f"code blocks and markers disagree: "
        f"only-markers={sorted(set(starts) - set(targets))} "
        f"only-code={sorted(set(targets) - set(starts))}"
    )


def _style_block(text, path):
    m = re.search(r"<style\b[^>]*>(.*?)</style>", text, re.S)
    assert m, f"{path.name}: no style block"
    return m.group(1)


def test_main_is_a_single_column(template):
    """The Core Rule contract: <main> lays sections out as a single column;
    no rule whose selector ends on the main element may reintroduce a
    multi-column layout through grid or CSS columns."""
    name, path, text = template
    style = re.sub(r"/\*.*?\*/", "", _style_block(text, path), flags=re.S)
    # The last compound of the selector is `main` (optionally with a class, id,
    # attribute, or pseudo suffix): `main`, `main.x`, `body > main`, `.page main:hover`.
    targets_main = re.compile(r"(?:^|[\s>+~])main(?![\w-])[^\s>+~]*$")
    multi_column = re.compile(r"\b(grid-template(?:-columns)?|grid|columns|column-count)\s*:")
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style):
        for selector in (s.strip() for s in selectors.split(",")):
            if targets_main.search(selector):
                assert not multi_column.search(body), (
                    f"{path.name}: main declares a multi-column layout: "
                    f"{selector}{{{body.strip()}}}"
                )


def test_series_tokens_are_exactly_five(template):
    """The Core Rule contract: the categorical series token set is --c1..--c5,
    each defined in both the light and dark theme blocks."""
    name, path, text = template
    style = _style_block(text, path)
    expected = {f"--c{n}" for n in range(1, 6)}
    assert set(re.findall(r"--c\d+(?=:)", style)) == expected, (
        f"{path.name}: series token set is not exactly --c1..--c5"
    )
    # Every theme block (light :root, system dark, explicit dark) declares each token once.
    blocks = re.findall(r":root(?:[^{]*)\{([^{}]*)\}", style)
    assert len(blocks) == 3, f"{path.name}: expected 3 :root theme blocks, found {len(blocks)}"
    for body in blocks:
        for token in sorted(expected):
            count = body.count(f"{token}:")
            assert count == 1, f"{path.name}: {token} declared {count} times in a theme block"


def test_every_figure_declares_its_accessibility_contract(template):
    """The Core Rule contract: an interactive figure (declares role="group",
    or has a focusable mark in its source; runtime-rendered charts add their
    marks later, so the declaration is what the source can show) carries its
    own role="group"/aria-labelledby/figcaption id triple; a static figure
    carries none of that on <figure> and instead names itself through its
    <svg role="img" aria-label="...">."""
    name, path, text = template
    # Strip comments and script/style bodies: the files quote sample markup
    # (e.g. the accessibility-contract comment) that must not scan as real.
    markup = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    markup = re.sub(r"<(script|style)\b.*?</\1>", "", markup, flags=re.S)
    ids = re.findall(r'\bid="([^"]+)"', markup)
    duplicates = sorted(i for i, n in Counter(ids).items() if n > 1)
    assert not duplicates, (
        f"{path.name}: duplicate ids make aria references ambiguous: {duplicates}"
    )
    for figure in re.findall(r"<figure\b[^>]*>.*?</figure>", markup, re.S):
        opening = figure[: figure.index(">") + 1]
        if 'role="group"' in opening or "tabindex" in figure:
            assert 'role="group"' in opening, (
                f'{path.name}: interactive figure missing role="group": {opening}'
            )
            m = re.search(r'aria-labelledby="([^"]+)"', opening)
            assert m, f"{path.name}: interactive figure missing aria-labelledby: {opening}"
            cap_id = m.group(1)
            assert re.search(rf'<figcaption\b[^>]*\bid="{re.escape(cap_id)}"', figure), (
                f"{path.name}: no figcaption with id={cap_id!r} for {opening}"
            )
        else:
            assert "role=" not in opening, f"{path.name}: static figure declares a role: {opening}"
            assert "<figcaption" in figure, f"{path.name}: figure without figcaption: {opening}"
            svg_m = re.search(r"<svg\b[^>]*>", figure)
            assert svg_m, f"{path.name}: static figure has no svg: {opening}"
            svg_open = svg_m.group(0)
            assert 'role="img"' in svg_open, (
                f'{path.name}: static figure\'s svg missing role="img": {svg_open}'
            )
            label_m = re.search(r'aria-label="([^"]*)"', svg_open)
            assert label_m and label_m.group(1).strip(), (
                f"{path.name}: static figure's svg missing non-empty aria-label: {svg_open}"
            )
