"""Invariants across the conventions themselves.

What a by-hand audit is needed to find otherwise: a cross reference to a section that does not
exist, a numbering that skips, a stamp older than the rule that governs stamps.
"""

import datetime as dt
import functools
import re

import pytest
from _repo import CONVENTIONS, read

BY_NAME = {p.name: p for p in CONVENTIONS}

# A stamp records when a fact was last checked. 12's own Core Rule requires re-verifying
# one older than three months, so the window here is that rule rather than a taste.
STAMP_MONTHS = 3
STAMP = re.compile(r"\(?as of:? (\d{4})-(\d{2})\)?", re.I)
SECTION = re.compile(r"^### (\d+)\.", re.M)
CROSS_REF = re.compile(r"\[([0-9]{2}-[a-z-]+\.md)\]\([^)]*\)\s*§\s*(\d+)")


@functools.cache
def sections_of(name: str) -> set[int]:
    return {int(n) for n in SECTION.findall(read(BY_NAME[name]))}


# --- cross references point at something that exists -------------------------------------


@pytest.mark.parametrize("doc", CONVENTIONS, ids=lambda p: p.name)
def test_section_cross_references_resolve(doc):
    """A `§n` pointing past the target document's last section sends a reader nowhere."""
    broken = [
        f"{doc.name} -> {target} §{number}"
        for target, number in CROSS_REF.findall(read(doc))
        if target in BY_NAME and int(number) not in sections_of(target)
    ]
    assert not broken, f"cross references to sections that do not exist: {broken}"


@pytest.mark.parametrize("doc", CONVENTIONS, ids=lambda p: p.name)
def test_section_numbering_is_contiguous(doc):
    """A gap in the numbering leaves a reader looking for the missing §n unable to tell why."""
    numbers = sorted(sections_of(doc.name))
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
    """12's Core Rule requires re-verifying a fact whose stamp is over three months old, and
    the rule that governs stamps is itself one of the documents carrying one.
    """
    stale = stale_stamps(read(doc), dt.date.today())
    assert not stale, (
        f"{doc.name} carries stamps older than {STAMP_MONTHS} months: {stale} — "
        "re-verify the claim and move the stamp, or mark the claim unverified"
    )


def test_the_stamp_check_separates_an_expired_stamp_from_a_current_one():
    """The only red this helper has. Every stamp in the tree is inside the window, so the check
    above passes on real data whatever `stale_stamps` returns — including `[]` for everything.
    """
    assert stale_stamps("(as of: 2024-01)", dt.date(2026, 8, 2)) == ["2024-01"]
    assert stale_stamps("(as of: 2026-08)", dt.date(2026, 8, 2)) == []


# There is deliberately no check on the spelling of unverified markers. Separating a claim
# that carries one from prose that discusses verification is not mechanically decidable,
# and the version that tried needed a list of exempt filenames — the same enumerate-the-
# exceptions shape these documents warn against. Three checks that mean something beat
# four where one cries wolf.
