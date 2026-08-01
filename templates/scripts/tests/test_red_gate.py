"""The four properties whose absence caused the previous runner to be withdrawn.

C-04 phase isolation, C-05 the status gate, C-06 a check that cannot run at base,
C-13 a check that runs and passes at base. 06 §3 splits the red outcomes exactly that
way and the withdrawn version got two of the three wrong.
"""

import json
import sys

import contract
from conftest import criterion, git, passing_at_head_only, write_contract


def state_path(repo, feature, cid, phase):
    return repo / "artifacts" / feature / "state" / f"{cid}.{phase}.json"


def run(repo, *argv):
    return contract.main([*argv, "--contract", str(repo / "contract.md")])


# --- C-04: the verify phase must not touch the red phase's record -------------------


def test_phase_isolation_uses_separate_files(repo, base_sha):
    write_contract(repo, [criterion("C-01", verify="false")], base=base_sha)
    run(repo, "red")
    run(repo, "verify")
    assert state_path(repo, "sample", "C-01", "red").exists()
    assert state_path(repo, "sample", "C-01", "verify").exists()


def test_phase_isolation_verify_leaves_red_record_unchanged(repo, base_sha):
    write_contract(repo, [criterion("C-01", verify="false")], base=base_sha)
    run(repo, "red")
    red = state_path(repo, "sample", "C-01", "red")
    before = red.read_bytes()
    run(repo, "verify")
    assert red.read_bytes() == before


# --- C-05: status exits zero only when every criterion is PASS ----------------------


def test_status_gate_zero_only_when_all_pass(repo, base_sha):
    cmd = passing_at_head_only(repo)
    write_contract(repo, [criterion("C-01", verify=cmd)], base=base_sha)
    run(repo, "red")
    run(repo, "verify")
    assert run(repo, "status") == 0


def test_status_gate_blocks_on_a_failing_criterion(repo, base_sha):
    cmd = passing_at_head_only(repo)
    write_contract(
        repo,
        [criterion("C-01", verify=cmd), criterion("C-02", verify="false")],
        base=base_sha,
    )
    run(repo, "red")
    run(repo, "verify")
    assert run(repo, "status") != 0


def test_status_gate_blocks_a_criterion_with_no_red_record(repo, base_sha):
    write_contract(repo, [criterion("C-01", verify="true")], base=base_sha)
    run(repo, "verify")  # red deliberately skipped
    assert run(repo, "status") != 0
    assert not state_path(repo, "sample", "C-01", "red").exists()


def test_status_gate_exempts_a_guard_from_the_red_requirement(repo, base_sha):
    write_contract(repo, [criterion("C-01", verify="true", red="guard")], base=base_sha)
    run(repo, "verify")
    assert run(repo, "status") == 0


def test_status_gate_exempts_a_human_criterion_from_the_red_requirement(repo, base_sha):
    crit = {
        "id": "C-01",
        "text": "A judgment a machine cannot make.",
        "verify": "human",
        "kind": "nonfunctional",
    }
    write_contract(repo, [crit], base=base_sha)
    run(repo, "human", "--id", "C-01", "--verdict", "pass", "--author", "tester")
    assert run(repo, "status") == 0


# --- C-06: a check that cannot run at base is NO-BASELINE, not red ------------------


def test_red_base_reports_no_baseline_when_the_command_cannot_run(repo, base_sha):
    write_contract(
        repo,
        [criterion("C-01", verify="definitely-not-an-installed-command")],
        base=base_sha,
    )
    run(repo, "red")
    record = json.loads(state_path(repo, "sample", "C-01", "red").read_text())
    assert record["status"] == "NO-BASELINE"


def test_red_reads_the_report_and_not_the_words_in_the_output(repo):
    """A test whose subject is an exception type prints that name when it fails.

    Matching `SyntaxError` in pytest's output read this ordinary failure as a file that
    does not parse, and a criterion whose red record says NO-BASELINE can never pass the
    status gate — so the criterion became unpassable and the recorded reason was false.
    """
    (repo / "describe.py").write_text(
        'def describe(exc):\n    return "unknown error"\n', encoding="utf-8"
    )
    (repo / "test_describe.py").write_text(
        "from describe import describe\n\n\n"
        "def test_names_a_syntax_error():\n"
        '    assert describe(SyntaxError("bad token")) == "syntax problem: bad token"\n',
        encoding="utf-8",
    )
    git("add", "-A", cwd=repo)
    git("commit", "--quiet", "-m", "describe at base", cwd=repo)
    base = git("rev-parse", "HEAD", cwd=repo).strip()

    cmd = f"{sys.executable} -m pytest test_describe.py -q -p no:cacheprovider"
    write_contract(repo, [criterion("C-01", verify=cmd, runner="pytest")], base=base)
    run(repo, "red")
    record = json.loads(state_path(repo, "sample", "C-01", "red").read_text())
    assert record["status"] == "RED", record


def test_red_records_the_collection_probe_it_executes(repo, base_sha):
    """19 §3 defines commands.jsonl as one object per executed command, and this is one.

    A criterion ruled out at collection gets no other row, so its verdict rested
    entirely on a command the evidence never mentioned.
    """
    cmd = f"{sys.executable} -m pytest tests/test_absent.py -q -p no:cacheprovider"
    write_contract(repo, [criterion("C-01", verify=cmd, runner="pytest")], base=base_sha)
    run(repo, "red")
    rows = [
        json.loads(line)
        for line in (repo / "artifacts" / "sample" / "commands.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    probes = [r for r in rows if r["phase"] == "red-collect" and r["criterion"] == "C-01"]
    assert len(probes) == 1, rows
    assert "--collect-only" in probes[0]["command"]


def test_red_base_finds_tests_when_rootdir_differs_from_the_repo_root(repo, base_sha):
    """A nested pyproject.toml moves pytest's rootdir, and with it the printed paths.

    This repository has exactly that shape (`templates/pyproject.toml`), and it made
    every criterion report NO-TEST until the collection probe pinned its rootdir.
    """
    nested = repo / "pkg"
    (nested / "tests").mkdir(parents=True)
    (nested / "pyproject.toml").write_text(
        '[project]\nname = "nested"\nversion = "0"\n', encoding="utf-8"
    )
    (nested / "tests" / "mod.py").write_text("def v():\n    return 1\n", encoding="utf-8")
    (nested / "tests" / "test_mod.py").write_text(
        "from mod import v\n\n\ndef test_v():\n    assert v() == 1\n", encoding="utf-8"
    )
    git("add", "-A", cwd=repo)
    git("commit", "--quiet", "-m", "nested project", cwd=repo)

    cmd = f"{sys.executable} -m pytest pkg/tests/test_mod.py -q -p no:cacheprovider"
    write_contract(repo, [criterion("C-01", verify=cmd, runner="pytest")], base=base_sha)
    run(repo, "red")
    record = json.loads(state_path(repo, "sample", "C-01", "red").read_text())
    assert record["status"] == "RED", record
    assert record["brought_forward"] == ["pkg/tests/test_mod.py"]


def test_red_base_records_red_when_the_command_fails_at_base(repo, base_sha):
    write_contract(repo, [criterion("C-01", verify="false")], base=base_sha)
    run(repo, "red")
    record = json.loads(state_path(repo, "sample", "C-01", "red").read_text())
    assert record["status"] == "RED"


# --- C-13: a check that passes at base proves nothing -------------------------------


def test_red_passes_at_base_is_not_recorded_as_red(repo, base_sha):
    write_contract(repo, [criterion("C-01", verify="true")], base=base_sha)
    run(repo, "red")
    record = json.loads(state_path(repo, "sample", "C-01", "red").read_text())
    assert record["status"] != "RED"


def test_red_passes_at_base_blocks_status(repo, base_sha):
    write_contract(repo, [criterion("C-01", verify="true")], base=base_sha)
    run(repo, "red")
    run(repo, "verify")
    assert run(repo, "status") != 0
