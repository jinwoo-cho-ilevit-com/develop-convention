#!/usr/bin/env python3
"""The invariants this repository states about its own documents, run as one command.

CLAUDE.md carries a verification checklist and the documents state rules about each other:
a `§n` cross reference points at a section that exists, a fact carries a stamp inside the
window 12 sets, a skill routes to a convention instead of copying it, the published nav
lists what a project still takes. Each is mechanical, and this is where they run — for a
person by hand, for pre-commit, and for CI, all through the same entry point.

Every check reports `path:line: what is wrong`, and the command exits 1 when any fires.

Usage:
    check-docs.py [--repo DIR]
"""

from __future__ import annotations

import argparse
import datetime as dt
import functools
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import yaml

SELF = f"{Path(__file__).resolve().parent.name}/{Path(__file__).name}"

# A committed tool-call fragment is invisible in review, so the check is mechanical.
RESIDUE = ("</content>", "</invoke>", "</antml")

# A document sending a reader to a tool that no longer exists is the worst shape a rule
# takes: readable, and doing as told fails. Checked against path as well as body, so a
# retired directory reappearing and a document naming it fail the same way.
RETIRED = (
    "templates/scripts",
    "contract.py",
    "conv-init",
    "templates/contract.md",
    "verify: human",
    "schema_version",
    "last_sync_commit",
    "last_audit_commit",
    "`revision`",
)

# A stamp records when a fact was last checked. 12's own Core Rule requires re-verifying
# one older than three months, so the window here is that rule rather than a taste.
STAMP_MONTHS = 3
STAMP = re.compile(r"\(?as of:? (\d{4})-(\d{2})\)?", re.I)
SECTION = re.compile(r"^### (\d+)\.")
CROSS_REF = re.compile(r"\[([0-9]{2}-[a-z-]+\.md)\]\([^)]*\)\s*§\s*(\d+)")
CONVENTION_LINK = re.compile(r"\.\./\.\./conventions/(\d\d-[a-z-]+\.md)")


class Violation(NamedTuple):
    path: str
    line: int
    message: str


# --- reading the repository ----------------------------------------------------------------


@functools.cache
def conventions(repo: Path) -> list[Path]:
    return sorted((repo / "conventions").glob("*.md"))


@functools.cache
def skills(repo: Path) -> list[Path]:
    return sorted((repo / "skills").glob("*/SKILL.md"))


@functools.cache
def commands(repo: Path) -> list[Path]:
    return sorted((repo / "commands").glob("*.md"))


@functools.cache
def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def numbered(body: str) -> list[tuple[int, str]]:
    return list(enumerate(body.splitlines(), 1))


def where(body: str, needle: str) -> int:
    """The line a marker sits on, for a violation about something that is absent."""
    for number, line in numbered(body):
        if line.startswith(needle):
            return number
    return 1


def section(body: str, opening: str, closing: str) -> tuple[str, int] | None:
    """The lines from one heading up to the next, and the line the heading sits on."""
    lines = body.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(opening)), None)
    if start is None:
        return None
    end = next(
        (i for i, line in enumerate(lines) if i > start and line.startswith(closing)), len(lines)
    )
    return "\n".join(lines[start:end]), start + 1


def tracked_text(repo: Path) -> list[tuple[str, str]]:
    """Every tracked text file as (path, body).

    `tests/` and this script are left out: they spell the retired tokens themselves, and a
    tombstone list cannot be its own violation.
    """
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    files = []
    for name in filter(None, listed):
        path = repo / name
        if name.startswith("tests/") or name == SELF or not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "\0" not in body:
            files.append((name, body))
    return files


def rel(path: Path, repo: Path) -> str:
    return path.relative_to(repo).as_posix()


# --- document format: CLAUDE.md's own checklist ----------------------------------------------


def core_rules_is_the_first_body_heading(repo: Path) -> Iterator[Violation]:
    """The section other projects excerpt verbatim has to be findable at a fixed place."""
    for doc in conventions(repo):
        headings = [(n, line) for n, line in numbered(read(doc)) if line.startswith("## ")]
        if not headings:
            yield Violation(rel(doc, repo), 1, "no `##` heading at all")
            continue
        number, first = headings[0]
        if first.strip() != "## Core Rules":
            yield Violation(
                rel(doc, repo),
                number,
                f"the first body heading is {first.strip()!r}, not `## Core Rules`",
            )


def no_tool_call_residue(repo: Path) -> Iterator[Violation]:
    docs = [repo / "README.md", repo / "CLAUDE.md", *conventions(repo)]
    for doc in docs:
        for number, line in numbered(read(doc)):
            for marker in RESIDUE:
                if marker in line:
                    yield Violation(rel(doc, repo), number, f"tool-call residue {marker!r}")


def doc_map_links_resolve(repo: Path) -> Iterator[Violation]:
    for number, line in numbered(read(repo / "README.md")):
        for match in re.finditer(r"\]\((conventions/[^)#]+|templates/[^)#]+)\)", line):
            target = match.group(1)
            if not (repo / target).exists():
                yield Violation("README.md", number, f"links to {target}, which does not exist")


def every_convention_sits_under_a_doc_map_group(repo: Path) -> Iterator[Violation]:
    """A doc named anywhere in the README is not enough — a prose arrow would count.

    The map is grouped because the numbers are identifiers rather than a reading order,
    so a doc outside every group is unreachable by the only ordering a reader is given.
    """
    body = read(repo / "README.md")
    found = section(body, "## Document Map", "## How to Apply")
    if found is None:
        yield Violation("README.md", 1, "no `## Document Map` section to read the groups from")
        return
    doc_map, at = found
    grouped: set[str] = set()
    for block in re.split(r"^### ", doc_map, flags=re.M)[1:]:
        # Table rows only. Counting every mention inside the section lets a sentence of
        # prose stand in for a row, which is the same hole this check exists to close.
        rows = [line for line in block.splitlines() if line.startswith("| [")]
        grouped |= set(re.findall(r"conventions/(\d\d-[a-z-]+\.md)", "\n".join(rows)))
    for name in sorted({d.name for d in conventions(repo)} - grouped):
        yield Violation("README.md", at, f"no group table row names conventions/{name}")


def links_inside_a_convention_resolve(repo: Path) -> Iterator[Violation]:
    """A convention may point at a deleted file as easily as the README may.

    The strict site build catches this in CI too, but a repository invariant should not
    depend on a docs job that a reader may not run.
    """
    for doc in conventions(repo):
        for number, line in numbered(read(doc)):
            for target in re.findall(r"\]\((?!https?:|#)([^)#]+)", line):
                if not (doc.parent / target).resolve().exists():
                    yield Violation(
                        rel(doc, repo), number, f"links to {target}, which does not exist"
                    )


def every_convention_is_sourced_from_the_rule_summary(repo: Path) -> Iterator[Violation]:
    """The "Full Rule Summary" is a paraphrased copy of every Core Rules section, and 15
    requires a copy to name its source. Paraphrase defeats a copied-line check, so what is
    pinned here is the pointer: each convention is linked from a summary heading, and a
    convention the summary omits is a copy nothing names as its source.
    """
    body = read(repo / "README.md")
    at = where(body, "## Full Rule Summary")
    if at == 1:
        yield Violation("README.md", 1, "no `## Full Rule Summary` section")
        return
    headings = [(n, line) for n, line in numbered(body) if n > at and line.startswith("### ")]
    sourced = set(re.findall(r"conventions/(\d\d-[a-z-]+\.md)", "\n".join(h for _, h in headings)))
    for name in sorted({d.name for d in conventions(repo)} - sourced):
        yield Violation(
            "README.md", at, f"no summary heading names conventions/{name} as its source"
        )
    for number, heading in headings:
        if "conventions/" not in heading:
            yield Violation("README.md", number, f"summary section links no source: {heading!r}")


# --- the published site -----------------------------------------------------------------------


def mkdocs_nav(repo: Path) -> list[str]:
    def walk(node) -> list[str]:
        if isinstance(node, str):
            return [node]
        if isinstance(node, dict):
            return [p for value in node.values() for p in walk(value)]
        if isinstance(node, list):
            return [p for item in node for p in walk(item)]
        return []

    return walk(yaml.safe_load(read(repo / "mkdocs.yml"))["nav"])


def nav_lists_every_convention_doc(repo: Path) -> Iterator[Violation]:
    """`templates/AGENTS.md` sends an agent with no local clone to the published site, so a
    convention the nav omits is one that agent never receives.
    """
    at = where(read(repo / "mkdocs.yml"), "nav:")
    listed = set(mkdocs_nav(repo))
    for doc in conventions(repo):
        if f"conventions/{doc.name}" not in listed:
            yield Violation("mkdocs.yml", at, f"the nav omits conventions/{doc.name}")


def nav_lists_what_a_project_still_takes(repo: Path) -> Iterator[Violation]:
    """15: when something ships, update what distributes it in the same change.

    The published site is one of those distribution paths: what it lists is what a project
    still takes, so a retired template or skill left in the nav keeps being taken.
    """
    at = where(read(repo / "mkdocs.yml"), "nav:")
    listed = set(mkdocs_nav(repo))
    if "templates/AGENTS.md" not in listed:
        yield Violation("mkdocs.yml", at, "the nav omits templates/AGENTS.md")
    if not skills(repo):
        yield Violation("mkdocs.yml", at, "there is no skill to publish")
    for skill in skills(repo):
        page = f"skills/{skill.parent.name}/SKILL.md"
        if page not in listed:
            yield Violation("mkdocs.yml", at, f"the nav omits {page}")


# --- nothing in the tree still names a mechanism that was retired -------------------------------


def nothing_names_a_retired_mechanism(repo: Path) -> Iterator[Violation]:
    for name, body in tracked_text(repo):
        for token in RETIRED:
            if token in name:
                yield Violation(name, 1, f"the path names the retired mechanism {token!r}")
        for number, line in numbered(body):
            for token in RETIRED:
                if token in line:
                    yield Violation(name, number, f"names the retired mechanism {token!r}")


# --- the skills and commands the plugin ships ---------------------------------------------------


def front_matter(path: Path) -> str | None:
    body = read(path)
    return body.split("---", 2)[1] if body.startswith("---\n") else None


def readme_skill_table_names_every_skill(repo: Path) -> Iterator[Violation]:
    """The routing map is generated; the README's reader-facing table is the copy left by hand."""
    body = read(repo / "README.md")
    at = where(body, "| Skill | Loads when |")
    if at == 1:
        yield Violation("README.md", 1, "no skill table to check")
        return
    rows = "\n".join(body.splitlines()[at:]).split("\n\n")[0]
    for skill in skills(repo):
        if f"`{skill.parent.name}`" not in rows:
            yield Violation("README.md", at, f"the skill table omits `{skill.parent.name}`")


def every_command_declares_a_description(repo: Path) -> Iterator[Violation]:
    """Without one the command is listed with no way to tell what it does."""
    for path in commands(repo):
        front = front_matter(path)
        if front is None:
            yield Violation(rel(path, repo), 1, "no front matter")
        elif "description:" not in front:
            yield Violation(rel(path, repo), 1, "declares no description")


def every_skill_declares_its_directory_as_its_name(repo: Path) -> Iterator[Violation]:
    """The name has to be the directory name: the two disagreeing installs a skill under a
    name nothing points at. The description is checked where it is used, against the routing
    map (tests/test_plugin.py).
    """
    for path in skills(repo):
        front = front_matter(path)
        if front is None:
            yield Violation(rel(path, repo), 1, "no front matter")
        elif f"name: {path.parent.name}\n" not in front:
            yield Violation(
                rel(path, repo),
                1,
                f"declares a name that is not its directory {path.parent.name!r}",
            )


def every_skill_link_resolves(repo: Path) -> Iterator[Violation]:
    """A skill routes rather than restates, so a dead link is the content gone."""
    for path in skills(repo):
        for number, line in numbered(read(path)):
            for target in re.findall(r"\]\(([^)]+)\)", line):
                if target.startswith(("http://", "https://", "#")):
                    continue
                if not (path.parent / target).exists():
                    yield Violation(
                        rel(path, repo), number, f"links to {target}, which does not exist"
                    )


def no_skill_or_command_copies_convention_text(repo: Path) -> Iterator[Violation]:
    """A skill or command routes to a convention; the rule text itself stays there.

    This catches copied sentences, not paraphrase — a short restatement still needs the
    review lens (CLAUDE.md, verification item 6).
    """
    corpus = " ".join(read(doc) for doc in conventions(repo))
    for path in skills(repo) + commands(repo):
        for number, raw in numbered(read(path)):
            line = raw.strip().lstrip("|-*# ").strip()
            if len(line) >= 40 and line in corpus:
                yield Violation(rel(path, repo), number, f"copies convention text: {line!r}")


def every_convention_is_routed_by_exactly_one_skill(repo: Path) -> Iterator[Violation]:
    """The skills are how a convention reaches an agent, so one nothing routes to is one
    nobody loads. Two skills claiming it is the same rule arriving under two triggers.

    00 is the exception by design: it takes precedence over all of them, so every skill
    points back at it.
    """
    routed: dict[str, dict[str, Path]] = {}
    for path in skills(repo):
        for name in set(CONVENTION_LINK.findall(read(path))):
            routed.setdefault(name, {})[path.parent.name] = path

    for doc in conventions(repo):
        if doc.name == "00-principles.md":
            continue
        owners = routed.get(doc.name, {})
        if not owners:
            yield Violation(rel(doc, repo), 1, "no skill routes to this convention")
        elif len(owners) > 1:
            named = ", ".join(sorted(owners))
            yield Violation(
                rel(owners[sorted(owners)[0]], repo),
                1,
                f"{doc.name} is routed by more than one skill: {named}",
            )


# --- cross references, numbering and stamps ------------------------------------------------------


@functools.cache
def sections_of(doc: Path) -> frozenset[int]:
    found = (SECTION.match(line) for line in read(doc).splitlines())
    return frozenset(int(m.group(1)) for m in found if m)


def section_cross_references_resolve(repo: Path) -> Iterator[Violation]:
    """A `§n` pointing past the target document's last section sends a reader nowhere."""
    by_name = {doc.name: doc for doc in conventions(repo)}
    for doc in conventions(repo):
        for number, line in numbered(read(doc)):
            for target, wanted in CROSS_REF.findall(line):
                if target in by_name and int(wanted) not in sections_of(by_name[target]):
                    yield Violation(
                        rel(doc, repo), number, f"{target} has no §{wanted} to point at"
                    )


def section_numbering_is_contiguous(repo: Path) -> Iterator[Violation]:
    """A gap in the numbering leaves a reader looking for the missing §n unable to tell why."""
    for doc in conventions(repo):
        numbers = sorted(sections_of(doc))
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            yield Violation(
                rel(doc, repo), where(read(doc), "### "), f"section numbering skips: {numbers}"
            )


def as_of_stamps_are_inside_the_reverification_window(repo: Path) -> Iterator[Violation]:
    """12's Core Rule requires re-verifying a fact whose stamp is over three months old, and
    the rule that governs stamps is itself one of the documents carrying one.
    """
    cutoff = dt.date.today() - dt.timedelta(days=31 * STAMP_MONTHS)
    for doc in conventions(repo):
        for number, line in numbered(read(doc)):
            for year, month in STAMP.findall(line):
                if dt.date(int(year), int(month), 1) < cutoff:
                    yield Violation(
                        rel(doc, repo),
                        number,
                        f"the stamp {year}-{month} is older than {STAMP_MONTHS} months — "
                        "re-verify the claim and move it, or mark the claim unverified",
                    )


CHECKS = (
    core_rules_is_the_first_body_heading,
    no_tool_call_residue,
    doc_map_links_resolve,
    every_convention_sits_under_a_doc_map_group,
    links_inside_a_convention_resolve,
    every_convention_is_sourced_from_the_rule_summary,
    nav_lists_every_convention_doc,
    nav_lists_what_a_project_still_takes,
    nothing_names_a_retired_mechanism,
    readme_skill_table_names_every_skill,
    every_command_declares_a_description,
    every_skill_declares_its_directory_as_its_name,
    every_skill_link_resolves,
    no_skill_or_command_copies_convention_text,
    every_convention_is_routed_by_exactly_one_skill,
    section_cross_references_resolve,
    section_numbering_is_contiguous,
    as_of_stamps_are_inside_the_reverification_window,
)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    repo = args.repo.resolve()

    violations = sorted(v for check in CHECKS for v in check(repo))
    for violation in violations:
        print(f"{violation.path}:{violation.line}: {violation.message}")
    if violations:
        print(f"\n{len(violations)} violation(s) from {len(CHECKS)} checks", file=sys.stderr)
        return 1
    print(f"{len(CHECKS)} document checks clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
