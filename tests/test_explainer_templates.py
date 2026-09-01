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


def test_the_shared_renderer_is_identical_in_both_files():
    """Both files claim their renderBarsH copies are identical up to
    indentation; this makes the claim mechanical."""
    bodies = {}
    for name, path in TEMPLATES.items():
        bodies[name] = _function_body(path.read_text(encoding="utf-8"), "renderBarsH", path)
    assert bodies["skeleton"] == bodies["gallery"], (
        "renderBarsH drifted between skeleton and gallery"
    )


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


def test_every_figure_declares_its_accessibility_contract(template):
    name, path, text = template
    # Strip comments and script/style bodies: the files quote sample markup
    # (e.g. the accessibility-contract comment) that must not scan as real.
    markup = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    markup = re.sub(r"<(script|style)\b.*?</\1>", "", markup, flags=re.S)
    for figure in re.findall(r"<figure\b[^>]*>.*?</figure>", markup, re.S):
        opening = figure[: figure.index(">") + 1]
        assert 'role="img"' in opening or 'role="group"' in opening, (
            f"{path.name}: figure without role: {opening}"
        )
        assert "<figcaption" in figure, f"{path.name}: figure without figcaption: {opening}"
        if 'role="img"' in opening:
            assert "tabindex" not in figure, (
                f"{path.name}: role='img' figure contains focusable marks "
                f"(contract: interactive figures use role='group'): {opening}"
            )
