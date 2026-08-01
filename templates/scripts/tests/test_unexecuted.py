"""C-07 — a test that did not execute is not a pass.

Measured before this was written: a pytest selection containing only skipped tests
exits 0. Any verdict that rests on the exit code alone therefore reads a stub as a
pass, which would let every pytest criterion in a contract be satisfied by
`@pytest.mark.skip`. The premise is asserted here too, so the day pytest changes that
behaviour this test fails loudly instead of passing for a reason that no longer holds.
"""

import json
import subprocess
import sys

import contract
from conftest import criterion, write_contract

PY = sys.executable


def make_suite(repo, body: str, name: str = "test_thing.py"):
    tests = repo / "tests"
    tests.mkdir(exist_ok=True)
    (tests / name).write_text(body, encoding="utf-8")
    return f"{PY} -m pytest tests/{name} -q -p no:cacheprovider"


def verify_record(repo, cid="C-01", feature="sample"):
    path = repo / "artifacts" / feature / "state" / f"{cid}.verify.json"
    return json.loads(path.read_text(encoding="utf-8"))


def run_verify(repo):
    return contract.main(["verify", "--contract", str(repo / "contract.md")])


SKIP_ONLY = """\
import pytest


@pytest.mark.skip(reason="stub")
def test_stub():
    assert False
"""


def test_unexecuted_not_pass_premise_a_skipped_suite_exits_zero(repo):
    """The behaviour this criterion exists to defeat, asserted rather than assumed."""
    cmd = make_suite(repo, SKIP_ONLY)
    proc = subprocess.run(cmd.split(), cwd=repo, capture_output=True, text=True)
    assert proc.returncode == 0


def test_unexecuted_not_pass_a_skipped_pytest_suite_is_not_a_pass(repo, base_sha):
    cmd = make_suite(repo, SKIP_ONLY)
    write_contract(
        repo,
        [criterion("C-01", verify=cmd, runner="pytest"), criterion("C-02", kind="negative")],
        base=base_sha,
    )
    assert run_verify(repo) != 0
    record = verify_record(repo)
    assert record["status"] == "FAIL"
    assert record["report"]["executed"] == 0


def test_unexecuted_not_pass_an_executed_passing_suite_is_a_pass(repo, base_sha):
    cmd = make_suite(repo, "def test_real():\n    assert True\n")
    write_contract(
        repo,
        [criterion("C-01", verify=cmd, runner="pytest"), criterion("C-02", kind="negative")],
        base=base_sha,
    )
    run_verify(repo)
    record = verify_record(repo)
    assert record["status"] == "PASS"
    assert record["report"]["executed"] == 1


def test_unexecuted_not_pass_a_suite_that_collects_nothing_is_not_a_pass(repo, base_sha):
    cmd = make_suite(repo, "def helper():\n    return 1\n")
    write_contract(
        repo,
        [criterion("C-01", verify=cmd, runner="pytest"), criterion("C-02", kind="negative")],
        base=base_sha,
    )
    assert run_verify(repo) != 0
    assert verify_record(repo)["status"] == "FAIL"


def test_unexecuted_not_pass_a_command_that_never_started_is_not_a_pass(repo, base_sha):
    write_contract(
        repo,
        [
            criterion("C-01", verify="definitely-not-an-installed-command"),
            criterion("C-02", kind="negative"),
        ],
        base=base_sha,
    )
    assert run_verify(repo) != 0
    record = verify_record(repo)
    assert record["status"] == "FAIL"
    assert record["exit_code"] is None


def test_unexecuted_not_pass_distinguishes_never_ran_from_ran_and_failed(repo, base_sha):
    """06 section 3's split: the note must say which of the two happened."""
    write_contract(
        repo,
        [
            criterion("C-01", verify="definitely-not-an-installed-command"),
            criterion("C-02", verify="false"),
            criterion("C-03", kind="negative"),
        ],
        base=base_sha,
    )
    run_verify(repo)
    assert "could not start" in verify_record(repo, "C-01")["note"]
    assert verify_record(repo, "C-02")["note"] == "exit 1"
