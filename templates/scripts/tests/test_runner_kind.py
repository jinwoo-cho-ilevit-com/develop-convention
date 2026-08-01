"""C-03 — the runner kind comes from the contract, never from the command text.

Two of the withdrawn runner's seven blockers came from `is_pytest = "pytest" in verify`.
The defence is structural: parsing replaces the verify string with a tagged check, so
after `load_contract` there is no command string left to inspect. These tests assert
that property directly rather than sampling commands that happen to classify correctly.
"""

from dataclasses import fields

import contract
from conftest import criterion, write_contract


def load(repo):
    return contract.load_contract(repo / "contract.md")


def check_of(repo, cid="C-01"):
    return next(c for c in load(repo).criteria if c.id == cid).check


def test_runner_kind_command_wins_over_the_word_pytest_in_the_command(repo):
    """`grep -rq pytest src/` is a command criterion, whatever it says."""
    write_contract(repo, [criterion("C-01", verify="grep -rq pytest src/", runner="command")])
    assert isinstance(check_of(repo), contract.CommandCheck)


def test_runner_kind_pytest_wins_when_the_command_never_says_pytest(repo):
    write_contract(repo, [criterion("C-01", verify="uv run -m nox -s tests", runner="pytest")])
    assert isinstance(check_of(repo), contract.PytestCheck)


def test_runner_kind_human_is_its_own_check(repo):
    crit = {"id": "C-01", "text": "a judgment", "verify": "human", "kind": "nonfunctional"}
    write_contract(repo, [crit])
    assert isinstance(check_of(repo), contract.HumanCheck)


def test_runner_kind_leaves_no_command_string_to_inspect(repo):
    """The structural claim: a substring test has nothing to run against.

    If a future change reintroduces a raw verify string on the criterion, this fails
    and the reviewer is pointed at the blocker it would revive.
    """
    write_contract(repo, [criterion("C-01", verify="uv run pytest -q", runner="pytest")])
    crit = next(c for c in load(repo).criteria)
    assert not hasattr(crit, "verify")
    strings = [
        getattr(crit, f.name) for f in fields(crit) if isinstance(getattr(crit, f.name), str)
    ]
    assert not any("pytest" in s for s in strings)


def test_runner_kind_argv_is_split_not_shelled(repo):
    write_contract(
        repo, [criterion("C-01", verify="uv run --group dev pytest -q", runner="pytest")]
    )
    assert check_of(repo).argv == ("uv", "run", "--group", "dev", "pytest", "-q")


def test_runner_kind_display_is_rebuilt_from_argv(repo):
    """REPORT.md needs a readable command; it is regenerated, not carried."""
    write_contract(repo, [criterion("C-01", verify="echo  a   b", runner="command")])
    assert contract.display_command(check_of(repo)) == "echo a b"
