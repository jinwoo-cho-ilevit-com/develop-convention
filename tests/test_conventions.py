"""Invariants across the conventions themselves.

These are the checks the repository's own audit had to be run by hand to find: a cross
reference to a section that does not exist, a numbering that skips, a stamp older than
the rule that governs stamps. Each one held a real defect when it was first written.
"""

import datetime as dt
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONVENTIONS = sorted((ROOT / "conventions").glob("*.md"))
BY_NAME = {p.name: p for p in CONVENTIONS}

# A stamp records when a fact was last checked. 12's own Core Rule requires re-verifying
# one older than three months, so the window here is that rule rather than a taste.
STAMP_MONTHS = 3
STAMP = re.compile(r"\(?as of:? (\d{4})-(\d{2})\)?", re.I)
SECTION = re.compile(r"^### (\d+)\.", re.M)
CROSS_REF = re.compile(r"\[([0-9]{2}-[a-z-]+\.md)\]\([^)]*\)\s*§\s*(\d+)")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sections_of(name: str) -> set[int]:
    return {int(n) for n in SECTION.findall(read(BY_NAME[name]))}


# --- cross references point at something that exists -------------------------------------


@pytest.mark.parametrize("doc", CONVENTIONS, ids=lambda p: p.name)
def test_section_cross_references_resolve(doc):
    """`18` pointed at `09 §5` for a whole release; 09 has four sections."""
    broken = [
        f"{doc.name} -> {target} §{number}"
        for target, number in CROSS_REF.findall(read(doc))
        if target in BY_NAME and int(number) not in sections_of(target)
    ]
    assert not broken, f"cross references to sections that do not exist: {broken}"


@pytest.mark.parametrize("doc", CONVENTIONS, ids=lambda p: p.name)
def test_section_numbering_is_contiguous(doc):
    """`15` ran 1,2,3,4,5,7 — a reader looking for §6 finds nothing and cannot tell why."""
    numbers = sorted(sections_of(doc.name)) if doc.name in BY_NAME else []
    if not numbers:
        pytest.skip("no numbered sections")
    assert numbers == list(range(1, len(numbers) + 1)), f"{doc.name} numbering: {numbers}"


# --- facts carry a date, and the date is inside the window the rules set ------------------


def stale_stamps(body: str, today: dt.date) -> list[str]:
    cutoff = today - dt.timedelta(days=31 * STAMP_MONTHS)
    found = []
    for year, month in STAMP.findall(body):
        stamped = dt.date(int(year), int(month), 1)
        if stamped < cutoff:
            found.append(f"{year}-{month}")
    return found


@pytest.mark.parametrize("doc", CONVENTIONS, ids=lambda p: p.name)
def test_as_of_stamps_are_inside_the_reverification_window(doc):
    """12's Core Rule requires re-verifying a fact whose stamp is over three months old.

    Nothing enforced it, so three stamps sat expired while the rule that governs them was
    itself one of the documents carrying one.
    """
    stale = stale_stamps(read(doc), dt.date.today())
    assert not stale, (
        f"{doc.name} carries stamps older than {STAMP_MONTHS} months: {stale} — "
        "re-verify the claim and move the stamp, or mark the claim unverified"
    )


def test_the_stamp_check_would_catch_an_old_stamp():
    """A check that has never failed is a check nobody has seen work."""
    assert stale_stamps("(as of: 2024-01)", dt.date(2026, 8, 2)) == ["2024-01"]
    assert stale_stamps("(as of: 2026-08)", dt.date(2026, 8, 2)) == []


# There is deliberately no check on the spelling of unverified markers. Separating a claim
# that carries one from prose that discusses verification is not mechanically decidable,
# and the version that tried needed a list of exempt filenames — the same enumerate-the-
# exceptions shape these documents warn against. Three checks that mean something beat
# four where one cries wolf.
