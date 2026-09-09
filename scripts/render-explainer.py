#!/usr/bin/env python3
"""Render the shared stylesheet and helper script into the explainer templates.

`skills/explainer-docs/shared/` holds the single source of the styling and the
JS helpers that both shipped templates carry. Each template declares where a
fragment goes with a marker pair inside its <style> or <script>; the lines
between the markers are replaced verbatim, re-indented to the start marker:

    /* shared:start:css */
    (replaced with shared/explainer.css)
    /* shared:end:css */

The markers are CSS/JS comments, not HTML comments: inside <style> the text of
an HTML comment parses as the prelude of a CSS rule and swallows what follows.

Every block name must appear exactly once in a template and every fragment must
find a marker pair, so a marker lost in an edit fails loudly instead of shipping
a template whose shared half silently went missing.

Usage:
    render-explainer.py [--repo DIR]            rewrite both templates
    render-explainer.py [--repo DIR] --check    render, compare, exit 0/1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MARKER_RE = re.compile(r"^([ \t]*)/\* shared:(start|end):([\w-]+) \*/[ \t]*$")
SKILL_DIR = Path("skills") / "explainer-docs"
SHARED_DIR = SKILL_DIR / "shared"
FRAGMENTS = {"css": SHARED_DIR / "explainer.css", "js": SHARED_DIR / "explainer-helpers.js"}
TEMPLATES = ("explainer-skeleton.html", "explainer-gallery.html")


class RenderError(Exception):
    pass


def load_fragments(repo: Path) -> dict[str, tuple[str, str]]:
    out = {}
    for name, rel in FRAGMENTS.items():
        path = repo / rel
        if not path.is_file():
            raise RenderError(f"shared fragment {rel.as_posix()} not found under {repo}")
        out[name] = (rel.as_posix(), path.read_text(encoding="utf-8"))
    return out


def block(source: str, text: str, indent: str) -> list[str]:
    # The provenance line travels with the copy, as 15 requires of any copy.
    header = (
        f"/* 생성된 사본이다 — 원본은 {source} 이고,"
        " 고친 뒤 scripts/render-explainer.py 를 실행한다. */"
    )
    return [indent + line if line.strip() else "" for line in [header] + text.splitlines()]


def _closing(lines: list[str], start: int, name: str, label: str) -> int:
    for j in range(start + 1, len(lines)):
        m = MARKER_RE.match(lines[j])
        if not m:
            continue
        if m.group(2) == "start":
            raise RenderError(f"{label}: block {name!r} still open when {m.group(3)!r} opens")
        if m.group(3) != name:
            raise RenderError(f"{label}: block {name!r} closed by 'shared:end:{m.group(3)}'")
        return j
    raise RenderError(f"{label}: block {name!r} is never closed")


def render(text: str, fragments: dict[str, tuple[str, str]], label: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    placed: set[str] = set()
    i = 0
    while i < len(lines):
        m = MARKER_RE.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        indent, kind, name = m.groups()
        if kind == "end":
            raise RenderError(f"{label}: 'shared:end:{name}' without an opening marker")
        if name not in fragments:
            raise RenderError(f"{label}: unknown block {name!r}; known: {sorted(fragments)}")
        if name in placed:
            raise RenderError(f"{label}: block {name!r} opens more than once")
        end = _closing(lines, i, name, label)
        source, fragment = fragments[name]
        out.append(lines[i])
        out.extend(block(source, fragment, indent))
        out.append(lines[end])
        placed.add(name)
        i = end + 1
    missing = sorted(set(fragments) - placed)
    if missing:
        raise RenderError(f"{label}: no marker pair for block(s) {missing} — nothing rendered")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="render and compare; write nothing")
    args = parser.parse_args(argv)

    try:
        fragments = load_fragments(args.repo)
        stale = []
        for name in TEMPLATES:
            path = args.repo / SKILL_DIR / name
            current = path.read_text(encoding="utf-8")
            rendered = render(current, fragments, name)
            if rendered == current:
                continue
            if args.check:
                stale.append(name)
            else:
                path.write_text(rendered, encoding="utf-8")
        if args.check:
            if stale:
                print(
                    f"ERROR: stale against {SKILL_DIR.as_posix()}/shared: {', '.join(stale)}"
                    " — run scripts/render-explainer.py",
                    file=sys.stderr,
                )
                return 1
            print(f"OK: {len(TEMPLATES)} template(s) match {SKILL_DIR.as_posix()}/shared")
    except (RenderError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
