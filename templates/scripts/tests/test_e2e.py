"""C-09 — the five phases in order, and no phase erasing an earlier one's record.

This is the test whose absence let the previous version ship. Every phase had a unit
test and all of them passed; nothing ran the phases in the order the documents
prescribe, so nobody noticed that `verify` deleted what `red` had written. Here each
phase's record is snapshotted byte for byte and re-checked after every later phase.
"""

import json
import sys

import contract
from conftest import git, write_contract

PY = sys.executable

HUMAN = {
    "id": "C-03",
    "text": "A judgment a machine cannot make.",
    "verify": "human",
    "kind": "nonfunctional",
}


def build(repo):
    """A repository where one criterion is red at base and green at head."""
    base = git("rev-parse", "HEAD", cwd=repo)

    tests = repo / "tests"
    tests.mkdir()
    # The subject sits beside its test: pytest puts the test's own directory on
    # sys.path, not the repository root. Only the test file is carried into the base
    # checkout, so `mod` is missing there and the import fails — which is the ordinary
    # red case 06 §3 describes.
    (tests / "mod.py").write_text("def value():\n    return 41 + 1\n", encoding="utf-8")
    (tests / "test_mod.py").write_text(
        "from mod import value\n\n\ndef test_value():\n    assert value() == 42\n",
        encoding="utf-8",
    )
    (repo / "marker").write_text("present\n", encoding="utf-8")
    git("add", "-A", cwd=repo)
    git("commit", "--quiet", "-m", "add the feature, its test and a marker", cwd=repo)

    write_contract(
        repo,
        [
            {
                "id": "C-01",
                "text": "THE module SHALL return 42.",
                "verify": f"{PY} -m pytest tests/test_mod.py -q -p no:cacheprovider",
                "kind": "functional",
                "runner": "pytest",
            },
            {
                "id": "C-02",
                "text": "THE marker SHALL NOT be absent.",
                "verify": "test -f marker",
                "kind": "negative",
                "runner": "command",
            },
            HUMAN,
        ],
        base=base,
    )
    return base


def art(repo):
    return repo / "artifacts" / "sample"


PHASES = ("red", "verify", "human")


def snapshot(repo):
    """The per-criterion phase records, which are what no phase may lose.

    Only those: the state directory also holds a run log and the creation stamp, and an
    assertion that enumerated every file in it would fail the next time the manifest
    gained a field — which is a different property from the one this test is about.
    """
    state = art(repo) / "state"
    return {
        p.name: p.read_bytes()
        for p in sorted(state.glob("*.json"))
        if p.name.rsplit(".", 2)[-2:-1] and p.name.rsplit(".", 2)[-2] in PHASES
    }


def run(repo, *argv):
    return contract.main([*argv, "--contract", str(repo / "contract.md")])


def test_e2e_drives_every_phase_in_order_without_losing_a_record(repo):
    build(repo)

    assert run(repo, "lint") == 0

    assert run(repo, "red") == 0
    after_red = snapshot(repo)
    assert set(after_red) == {"C-01.red.json", "C-02.red.json"}
    assert all(json.loads(v)["status"] == "RED" for v in after_red.values())

    assert run(repo, "verify") == 0
    after_verify = snapshot(repo)
    assert {k: v for k, v in after_verify.items() if k in after_red} == after_red

    assert run(repo, "human", "--id", "C-03", "--verdict", "pass", "--author", "tester") == 0
    after_human = snapshot(repo)
    assert {k: v for k, v in after_human.items() if k in after_verify} == after_verify

    assert run(repo, "status") == 0
    assert snapshot(repo) == after_human


def test_e2e_status_blocks_while_the_human_verdict_is_outstanding(repo):
    build(repo)
    run(repo, "red")
    run(repo, "verify")
    assert run(repo, "status") == 1

    report = (art(repo) / "REPORT.md").read_text(encoding="utf-8")
    assert "PENDING-HUMAN" in report


def test_e2e_a_rejected_verdict_blocks_completion(repo):
    build(repo)
    run(repo, "red")
    run(repo, "verify")
    assert run(repo, "human", "--id", "C-03", "--verdict", "reject", "--author", "t") == 1
    assert run(repo, "status") == 1


def test_e2e_the_base_worktree_is_removed(repo):
    build(repo)
    run(repo, "red")
    worktrees = git("worktree", "list", cwd=repo).splitlines()
    assert len(worktrees) == 1, worktrees
