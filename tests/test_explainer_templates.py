"""Invariants for the shipped explainer HTML templates.

These lock in the checks the review lanes ran by hand: self-containment,
snippet-marker pairing, the static-number-vs-embedded-data contract, and the
figure accessibility contract. They read the files; they do not execute JS,
so anything requiring a browser (tooltip behavior, contrast) stays with the
review lanes.
"""

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKELETON = REPO / "skills" / "explainer-docs" / "explainer-skeleton.html"
GALLERY = REPO / "skills" / "explainer-docs" / "explainer-gallery.html"
TEMPLATES = {"skeleton": SKELETON, "gallery": GALLERY}


@pytest.fixture(params=sorted(TEMPLATES))
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


def test_the_embedded_data_block_parses(template):
    name, path, text = template
    _data_block(text, path)


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


def _function_body(text, name, path):
    start = text.index(f"function {name}(")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                # The first line starts at the sliced "function" keyword, so
                # only continuation lines carry the file's block indentation.
                head, *rest = text[start : i + 1].splitlines()
                indented = [line for line in rest if line.strip()]
                indent = min(len(line) - len(line.lstrip()) for line in indented) if indented else 0
                dedented = [line[indent:] if line.strip() else line for line in rest]
                return "\n".join([head] + dedented)
    raise AssertionError(f"{path.name}: could not extract {name}")


def test_shared_helpers_are_identical_in_both_files():
    """Both files claim their renderBarsH and axes copies are identical up to
    indentation; this makes the claim mechanical."""
    for fn in ("renderBarsH", "axes"):
        bodies = {}
        for name, path in TEMPLATES.items():
            bodies[name] = _function_body(path.read_text(encoding="utf-8"), fn, path)
        assert bodies["skeleton"] == bodies["gallery"], f"{fn} drifted between skeleton and gallery"


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
    no rule targeting it standalone may reintroduce a multi-column grid."""
    name, path, text = template
    style = re.sub(r"/\*.*?\*/", "", _style_block(text, path), flags=re.S)
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style):
        items = [s.strip() for s in selectors.split(",")]
        if "main" in items:
            assert "grid-template-columns" not in body, (
                f"{path.name}: main declares grid-template-columns: "
                f"{selectors.strip()}{{{body.strip()}}}"
            )


def test_series_tokens_are_exactly_five(template):
    """The Core Rule contract: the categorical series token set is --c1..--c5,
    each defined in both the light and dark theme blocks."""
    name, path, text = template
    style = _style_block(text, path)
    for n in range(1, 6):
        count = len(re.findall(rf"--c{n}:", style))
        assert count >= 2, f"{path.name}: --c{n}: declared {count} times, need at least 2"
    for n in (6, 7, 8):
        assert f"--c{n}:" not in style, f"{path.name}: --c{n}: must not exist"


def test_series_tokens_are_identical_across_files():
    """The categorical and two-series palette tokens must be the same
    color set, in the same order, in both templates."""

    def tokens(path):
        style = _style_block(path.read_text(encoding="utf-8"), path)
        return [
            (name, value.strip())
            for name, value in re.findall(r"(--c\d+|--series-[ab]):\s*([^;]+);", style)
        ]

    skeleton_tokens = tokens(SKELETON)
    gallery_tokens = tokens(GALLERY)
    assert skeleton_tokens == gallery_tokens, (
        f"series tokens differ: skeleton={skeleton_tokens} gallery={gallery_tokens}"
    )


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
