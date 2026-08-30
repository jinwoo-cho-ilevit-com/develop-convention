#!/usr/bin/env python3
"""Fill excerpt marker blocks from Core Rules bullets, verbatim.

A consumer file (e.g. a deployed rules file) declares what it excerpts with
marker pairs; everything outside the markers is preserved byte-for-byte:

    <!-- excerpt(conventions/01-structure-naming.md): "anchor one" || "anchor two" -->
    (replaced with the matching Core Rules bullets)
    <!-- /excerpt -->

Each anchor must match exactly one top-level bullet in that document's
"## Core Rules" section; zero or multiple matches abort the whole run, so a
reworded source bullet fails loudly instead of drifting silently.

Usage:
    fill-excerpts.py [--repo DIR] --check FILE...      render, discard, exit 0/1
    fill-excerpts.py [--repo DIR] --fill SRC DST       render SRC, write DST
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from pathlib import Path

BEGIN_RE = re.compile(r"<!--\s*excerpt\(([^)]+)\):\s*(.+?)\s*-->\s*$")
END_MARKER = "<!-- /excerpt -->"
ANCHOR_RE = re.compile(r'"([^"]+)"')
LINK_RE = re.compile(r"\[([^\]]+)\]\((?!https?://|#)([^)]+?)(?:#[^)]*)?\)")
CLONE_HINT = "~/Codes/develop-convention"


class FillError(Exception):
    pass


def core_rules_bullets(doc_text: str, doc: str) -> list[str]:
    lines = doc_text.splitlines()
    try:
        start = lines.index("## Core Rules") + 1
    except ValueError:
        raise FillError(f"{doc}: no '## Core Rules' heading") from None
    bullets: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.startswith("- "):
            bullets.append(line)
        elif bullets and line.startswith("  ") and line.strip():
            bullets[-1] += "\n" + line
    if not bullets:
        raise FillError(f"{doc}: Core Rules section holds no bullets")
    return bullets


def rewrite_links(bullet: str, doc: str) -> str:
    doc_dir = posixpath.dirname(doc)

    def repl(m: re.Match) -> str:
        target = posixpath.normpath(posixpath.join(doc_dir, m.group(2)))
        if m.group(1) == posixpath.basename(target):
            return f"{CLONE_HINT}/{target}"
        return f"{m.group(1)} ({CLONE_HINT}/{target})"

    return LINK_RE.sub(repl, bullet)


def pick(bullets: list[str], anchor: str, doc: str) -> str:
    hits = [b for b in bullets if anchor in b]
    if len(hits) != 1:
        raise FillError(f'{doc}: anchor "{anchor}" matches {len(hits)} bullets, need exactly 1')
    return hits[0]


def render(text: str, repo: Path, label: str, sha: str) -> str:
    out: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = BEGIN_RE.match(line)
        if not m:
            if line.strip() == END_MARKER:
                raise FillError(f"{label}: '{END_MARKER}' without an opening marker")
            out.append(line)
            i += 1
            continue
        doc, anchor_src = m.group(1).strip(), m.group(2)
        anchors = ANCHOR_RE.findall(anchor_src)
        if not anchors:
            raise FillError(f"{label}: marker for {doc} declares no quoted anchors")
        try:
            end = next(j for j in range(i + 1, len(lines)) if lines[j].strip() == END_MARKER)
        except StopIteration:
            msg = f"{label}: marker for {doc} is never closed with '{END_MARKER}'"
            raise FillError(msg) from None
        doc_path = repo / doc
        if not doc_path.is_file():
            raise FillError(f"{label}: {doc} not found under {repo}")
        bullets = core_rules_bullets(doc_path.read_text(encoding="utf-8"), doc)
        out.append(line)
        out.append(f"<!-- filled from {doc} @ {sha} -->")
        out.extend(rewrite_links(pick(bullets, a, doc), doc) for a in anchors)
        out.append(END_MARKER)
        i = end + 1
    return "\n".join(out) + "\n"


def repo_sha(repo: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", nargs="+", type=Path, metavar="FILE")
    mode.add_argument("--fill", nargs=2, type=Path, metavar=("SRC", "DST"))
    args = parser.parse_args(argv)

    sha = repo_sha(args.repo)
    try:
        if args.check:
            for f in args.check:
                render(f.read_text(encoding="utf-8"), args.repo, str(f), sha)
            print(f"OK: {len(args.check)} file(s) render cleanly against {args.repo} @ {sha}")
        else:
            src, dst = args.fill
            rendered = render(src.read_text(encoding="utf-8"), args.repo, str(src), sha)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(rendered, encoding="utf-8")
    except FillError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
