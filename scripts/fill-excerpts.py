#!/usr/bin/env python3
"""Fill excerpt marker blocks from Core Rules bullets, verbatim.

A consumer file (e.g. a deployed rules file) declares what it excerpts with
marker pairs; text outside the markers passes through line-for-line (newlines
are LF-normalized and a trailing newline is ensured):

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
LINK_RE = re.compile(r"\[([^\]]+)\]\((?![a-zA-Z][a-zA-Z0-9+.-]*:|#)([^)#]+)(#[^)]*)?\)")
# `§4.1` numbers a subsection of an external source; `§5.` ends a sentence.
SECTION_REF = re.compile(r"§\s*\d+(?!\d)(?!\.\d)")
MD_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)", re.DOTALL)
CODE_SPAN = re.compile(r"`[^`]*`", re.DOTALL)
# What may sit between a link and a `§n` that still points into that link's target. These
# three and the rule below decide the same thing as `section_references` in
# scripts/check-docs.py: the two must stay in step, or the checker there stops being able to
# flag a bare `§n` this one leaves unnamed.
ATTACHED = re.compile(r"^[\s(→]*(?:§\s*\d+[\s,;]*(?:and\s+)?)*$")
CLONE_HINT = "~/Codes/develop-convention"


class FillError(Exception):
    pass


def core_rules_bullets(doc_text: str, doc: str) -> list[str]:
    lines = doc_text.splitlines()
    try:
        start = lines.index("## Core Rules") + 1
    except ValueError:
        raise FillError(f"{doc}: no '## Core Rules' heading") from None
    # A bullet spans from its "- " line to the next top-level bullet or heading, so
    # indented, tab-indented, lazy, and blank-line-separated continuations all survive.
    bullets: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.startswith("- "):
            bullets.append(line)
        elif bullets:
            bullets[-1] += "\n" + line
    bullets = [b.rstrip("\n ") for b in bullets]
    if not bullets:
        raise FillError(f"{doc}: Core Rules section holds no bullets")
    return bullets


def name_self_sections(bullet: str, doc: str) -> str:
    """Name the source document on a bare `§n`, which means "this document" where the bullet
    was written and nothing at all once it is excerpted into a file assembled from several.

    Runs before rewrite_links, while links are still markdown. Only an unambiguous self
    reference is named: one sitting right after a link points into that link's target, one
    whose sentence holds an earlier link is ambiguous, and one inside a code span or a link's
    own text (`RFC 8259 §7`, `` `§3` ``) is quoted or external. Each is left as written.
    """
    links = [(m.start(), m.end(), m.end()) for m in MD_LINK.finditer(bullet)]
    spans = [(m.start(), m.end()) for m in CODE_SPAN.finditer(bullet)]

    def repl(m: re.Match) -> str:
        at = m.start()
        if any(s <= at < e for s, e in spans) or any(s <= at < e for s, e, _ in links):
            return m.group(0)
        prior = [end for _, end, _ in links if end <= at]
        if prior and ATTACHED.match(bullet[prior[-1] : at]):
            return m.group(0)
        start = max(bullet.rfind(". ", 0, at) + 2, bullet.rfind("\n", 0, at) + 1)
        if prior and prior[-1] > start:
            return m.group(0)
        return f"{CLONE_HINT}/{doc} {m.group(0)}"

    return SECTION_REF.sub(repl, bullet)


def rewrite_links(bullet: str, doc: str) -> str:
    doc_dir = posixpath.dirname(doc)

    def repl(m: re.Match) -> str:
        target = posixpath.normpath(posixpath.join(doc_dir, m.group(2)))
        fragment = m.group(3) or ""
        if m.group(1) == posixpath.basename(target):
            return f"{CLONE_HINT}/{target}{fragment}"
        return f"{m.group(1)} ({CLONE_HINT}/{target}{fragment})"

    return LINK_RE.sub(repl, bullet)


def _closing(lines: list[str], start: int, doc: str, label: str) -> int:
    # A lost '/excerpt' line would otherwise make the next marker's block the body of this
    # one: it is dropped whole, anchors unchecked, and the run still exits 0.
    for j in range(start + 1, len(lines)):
        m = BEGIN_RE.match(lines[j])
        if m:
            raise FillError(f"{label}: marker for {doc} still open when {m.group(1).strip()} opens")
        if lines[j].strip() == END_MARKER:
            return j
    raise FillError(f"{label}: marker for {doc} is never closed with '{END_MARKER}'")


def pick(bullets: list[str], anchor: str, doc: str) -> str:
    hits = [b for b in bullets if anchor in b]
    if len(hits) != 1:
        raise FillError(f'{doc}: anchor "{anchor}" matches {len(hits)} bullets, need exactly 1')
    return hits[0]


def render(text: str, repo: Path, label: str, sha: str) -> str:
    out: list[str] = []
    lines = text.splitlines()
    i = 0
    filled = 0
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
        end = _closing(lines, i, doc, label)
        doc_path = repo / doc
        if not doc_path.is_file():
            raise FillError(f"{label}: {doc} not found under {repo}")
        bullets = core_rules_bullets(doc_path.read_text(encoding="utf-8"), doc)
        out.append(line)
        out.append(f"<!-- filled from {doc} @ {sha} -->")
        out.extend(
            rewrite_links(name_self_sections(pick(bullets, a, doc), doc), doc) for a in anchors
        )
        out.append(END_MARKER)
        i = end + 1
        filled += 1
    if filled == 0:
        # A skeleton whose markers were lost (say, in a conflict resolution) would
        # otherwise deploy a rules file holding no rules, with every light green.
        raise FillError(f"{label}: no excerpt markers found — nothing to fill")
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
    except (FillError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
