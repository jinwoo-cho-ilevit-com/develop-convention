"""C-14 — a human criterion stays PENDING-HUMAN until a usable verdict is recorded.

19 requires the verdict, its author and its timestamp, because a verdict with no
author is indistinguishable from one the tooling granted itself. The check is applied
on read as well as on write: a record that lost its author does not become a pass by
having been written once.
"""

import json

import contract
import pytest
from conftest import criterion, write_contract

HUMAN = {
    "id": "C-01",
    "text": "A judgment a machine cannot make.",
    "verify": "human",
    "kind": "nonfunctional",
}


def setup(repo, base_sha):
    write_contract(repo, [HUMAN, criterion("C-02", kind="negative")], base=base_sha)
    return contract.load_contract(repo / "contract.md")


def art(repo, feature="sample"):
    return repo / "artifacts" / feature


def status_of(repo, loaded, cid="C-01"):
    crit = next(c for c in loaded.criteria if c.id == cid)
    return contract.criterion_status(art(repo), crit)[0]


def run(repo, *argv):
    return contract.main([*argv, "--contract", str(repo / "contract.md")])


def test_human_verdict_starts_pending(repo, base_sha):
    loaded = setup(repo, base_sha)
    assert status_of(repo, loaded) == "PENDING-HUMAN"


def test_human_verdict_recorded_pass_carries_author_and_utc_timestamp(repo, base_sha):
    loaded = setup(repo, base_sha)
    assert run(repo, "human", "--id", "C-01", "--verdict", "pass", "--author", "tester") == 0
    record = json.loads((art(repo) / "state" / "C-01.human.json").read_text())
    assert record["author"] == "tester"
    assert contract.is_iso_utc(record["at"])
    assert status_of(repo, loaded) == "PASS"


def test_human_verdict_reject_is_a_failure_not_a_pending(repo, base_sha):
    loaded = setup(repo, base_sha)
    assert run(repo, "human", "--id", "C-01", "--verdict", "reject", "--author", "tester") == 1
    assert status_of(repo, loaded) == "FAIL"


def test_human_verdict_without_an_author_is_refused(repo, base_sha):
    setup(repo, base_sha)
    with pytest.raises(SystemExit):
        run(repo, "human", "--id", "C-01", "--verdict", "pass")


def test_human_verdict_on_a_machine_criterion_is_refused(repo, base_sha):
    write_contract(repo, [criterion("C-01"), criterion("C-02", kind="negative")], base=base_sha)
    assert run(repo, "human", "--id", "C-01", "--verdict", "pass", "--author", "t") == 2


def test_human_verdict_on_an_unknown_criterion_is_refused(repo, base_sha):
    setup(repo, base_sha)
    assert run(repo, "human", "--id", "C-99", "--verdict", "pass", "--author", "t") == 2


@pytest.mark.parametrize(
    "broken",
    [
        {"verdict": "pass", "author": "", "at": "2026-08-01T00:00:00Z"},
        {"verdict": "pass", "author": "t", "at": "2026-08-01 09:00:00"},
        {"verdict": "pass", "author": "t", "at": "not a timestamp"},
    ],
)
def test_human_verdict_an_unusable_record_does_not_read_as_a_pass(repo, base_sha, broken):
    """Enforced on read, so a record written by hand cannot buy a pass."""
    loaded = setup(repo, base_sha)
    state = art(repo) / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "C-01.human.json").write_text(
        json.dumps({"criterion": "C-01", "phase": "human", **broken}), encoding="utf-8"
    )
    assert status_of(repo, loaded) == "PENDING-HUMAN"
