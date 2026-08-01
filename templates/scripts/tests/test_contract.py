"""Tests for the contract toolkit.

The load-bearing one is `test_red_refuses_when_no_test_was_written`: an earlier
design judged red by "exit code is non-zero", which meant a contract with no
tests at all passed the check every time. Everything else here guards a rule the
documents make, so that the tool and the documents cannot drift apart silently.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import PYTEST_CMD, crit, git, run_tool, write_contract

FUNCTIONAL = crit("C-01", "true")
NEGATIVE = crit("C-02", "true", "negative")
HUMAN = crit("C-03", "human", "nonfunctional")


# --------------------------------------------------------------------------- #
# Parsing: a broken contract must stop the caller, never fail open
# --------------------------------------------------------------------------- #


def test_missing_contract_raises(tool, tmp_path):
    with pytest.raises(tool.ContractError, match="not found"):
        tool.load_contract(tmp_path / "nope.md")


def test_unparseable_yaml_raises(tool, tmp_path):
    path = tmp_path / "contract.md"
    path.write_text("---\nfeature: [unclosed\n---\n", encoding="utf-8")
    with pytest.raises(tool.ContractError, match="not valid YAML"):
        tool.load_contract(path)


def test_glob_star_in_owns_is_a_yaml_alias_error(tool, tmp_path):
    """`owns: [*.py]` is not a glob to YAML, it is an alias reference."""
    path = tmp_path / "contract.md"
    path.write_text("---\nowns: [*.py]\n---\n", encoding="utf-8")
    with pytest.raises(tool.ContractError, match="not valid YAML"):
        tool.load_contract(path)


def test_missing_front_matter_raises(tool, tmp_path):
    path = tmp_path / "contract.md"
    path.write_text("# just a document\n", encoding="utf-8")
    with pytest.raises(tool.ContractError, match="front matter"):
        tool.load_contract(path)


def test_unsupported_schema_version_raises(tool, tmp_path):
    path = tmp_path / "contract.md"
    path.write_text("---\nschema_version: 99\nfeature: x\n---\n", encoding="utf-8")
    with pytest.raises(tool.ContractError, match="schema_version"):
        tool.load_contract(path)


def test_duplicate_criterion_id_raises(tool, tmp_path):
    path = tmp_path / "contract.md"
    path.write_text(
        "---\nschema_version: 1\nfeature: x\ndone_level: auto\nout_of_scope: [a]\n"
        'criteria:\n  - {id: C-01, text: a, verify: "true"}\n'
        '  - {id: C-01, text: b, verify: "true"}\n---\n',
        encoding="utf-8",
    )
    with pytest.raises(tool.ContractError, match="duplicate"):
        tool.load_contract(path)


def test_parse_error_exits_two_not_zero(repo, capsys):
    (repo / "contract.md").write_text("---\nfeature: [unclosed\n---\n", encoding="utf-8")
    assert run_tool(repo, "lint") == 2
    assert "ERROR" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# lint
# --------------------------------------------------------------------------- #


def test_lint_accepts_a_complete_contract(repo):
    write_contract(repo, FUNCTIONAL + NEGATIVE)
    assert run_tool(repo, "lint") == 0


def test_lint_requires_a_negative_criterion(repo, capsys):
    write_contract(repo, FUNCTIONAL)
    assert run_tool(repo, "lint") == 1
    assert "negative criterion" in capsys.readouterr().out


def test_lint_rejects_glob_in_owns(repo, capsys):
    write_contract(
        repo,
        FUNCTIONAL + NEGATIVE,
        lanes='\n  - id: A\n    owns: ["src/**"]\n    criteria: [C-01]',
    )
    assert run_tool(repo, "lint") == 1
    assert "glob" in capsys.readouterr().out


def test_lint_rejects_bypassed_without_reason(repo, capsys):
    write_contract(repo, FUNCTIONAL + NEGATIVE, done_level="bypassed")
    assert run_tool(repo, "lint") == 1
    assert "revision.reason" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# Ownership
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("a", "b", "conflicts"),
    [
        ("src/loader/", "src/loader/", True),
        ("src/", "src/api/", True),
        ("src/api/", "src/", True),
        ("src/loader/", "src/api/", False),
        ("src/load/", "src/loader/", False),
    ],
)
def test_prefix_conflict(tool, a, b, conflicts):
    assert tool.prefix_conflict(a, b) is conflicts


def test_lanes_detects_nested_ownership(repo, capsys):
    write_contract(
        repo,
        FUNCTIONAL + NEGATIVE,
        lanes='\n  - id: A\n    owns: ["src/"]\n    criteria: [C-01]'
        '\n  - id: B\n    owns: ["src/api/"]\n    criteria: [C-02]',
    )
    assert run_tool(repo, "lanes") == 1
    assert "overlapping" in capsys.readouterr().out


def test_lanes_ignores_abandoned_lanes(repo):
    write_contract(
        repo,
        FUNCTIONAL + NEGATIVE,
        lanes='\n  - id: A\n    owns: ["src/"]\n    criteria: [C-01]'
        '\n  - id: B\n    owns: ["src/api/"]\n    criteria: [C-02]\n    state: abandoned',
    )
    assert run_tool(repo, "lanes") == 0


def test_sequential_owner_may_not_sit_inside_a_lane(repo, capsys):
    write_contract(
        repo,
        FUNCTIONAL + NEGATIVE,
        lanes='\n  - id: A\n    owns: ["src/"]\n    criteria: [C-01]',
        sequential_owner='["src/registry.py"]',
    )
    assert run_tool(repo, "lint") == 1
    assert "single-owner" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# Masking
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "secret",
    [
        "OPENAI_API_KEY=sk-abcdef0123456789abcdef",
        "api_key: 'hunter2-hunter2'",
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9",
        "password=correcthorsebattery",
        "token = ghp_0123456789abcdefghij",
    ],
)
def test_mask_redacts_secret_shapes(tool, secret):
    masked = tool.mask(secret)
    assert tool.MASK in masked
    assert "hunter2-hunter2" not in masked
    assert "correcthorsebattery" not in masked
    assert "eyJhbGciOiJIUzI1NiJ9" not in masked


def test_mask_leaves_ordinary_text_alone(tool):
    text = "uv run pytest tests/test_loader.py -q"
    assert tool.mask(text) == text


def test_verify_masks_the_command_it_records(repo):
    write_contract(
        repo,
        crit("C-01", "echo api_key=supersecretvalue") + NEGATIVE,
    )
    run_tool(repo, "verify")
    records = (repo / "artifacts" / "sample" / "commands.jsonl").read_text(encoding="utf-8")
    assert "supersecretvalue" not in records
    assert "MASKED" in records


# --------------------------------------------------------------------------- #
# verify
# --------------------------------------------------------------------------- #


def test_verify_records_pass_and_fail(repo):
    write_contract(
        repo,
        FUNCTIONAL + crit("C-02", "false", "negative"),
    )
    assert run_tool(repo, "verify") == 1
    statuses = json.loads((repo / "artifacts" / "sample" / "status.json").read_text())
    assert statuses["C-01"]["status"] == "PASS"
    assert statuses["C-02"]["status"] == "FAIL"


def test_verify_writes_report_and_manifest(repo):
    write_contract(repo, FUNCTIONAL + NEGATIVE)
    run_tool(repo, "verify")
    adir = repo / "artifacts" / "sample"
    report = (adir / "REPORT.md").read_text(encoding="utf-8")
    assert "| C-01 | PASS |" in report
    manifest = json.loads((adir / "manifest.json").read_text())
    assert manifest["created_at"]
    assert len(manifest["verify_runs"]) == 2
    assert manifest["review_rounds"] == 0


def test_verify_resume_skips_passing_criteria(repo):
    write_contract(repo, FUNCTIONAL + NEGATIVE)
    run_tool(repo, "verify")
    run_tool(repo, "verify", "--resume")
    manifest = json.loads((repo / "artifacts" / "sample" / "manifest.json").read_text())
    assert len(manifest["verify_runs"]) == 2, "resume re-ran criteria that already passed"


def test_report_status_words_carry_no_symbols(repo):
    write_contract(repo, FUNCTIONAL + NEGATIVE)
    run_tool(repo, "verify")
    report = (repo / "artifacts" / "sample" / "REPORT.md").read_text(encoding="utf-8")
    assert report.isascii(), "status must stay greppable ASCII, not symbols"


# --------------------------------------------------------------------------- #
# human verdicts
# --------------------------------------------------------------------------- #


def test_human_criterion_starts_pending_and_blocks(repo):
    write_contract(repo, FUNCTIONAL + NEGATIVE + HUMAN)
    run_tool(repo, "verify")
    statuses = json.loads((repo / "artifacts" / "sample" / "status.json").read_text())
    assert statuses["C-03"]["status"] == "PENDING-HUMAN"
    assert run_tool(repo, "status") == 1


def test_human_pass_is_recorded_with_author_and_time(repo):
    write_contract(repo, FUNCTIONAL + NEGATIVE + HUMAN)
    run_tool(repo, "verify")
    assert run_tool(repo, "human", "--id", "C-03", "--verdict", "pass", "--author", "jin") == 0
    manifest = json.loads((repo / "artifacts" / "sample" / "manifest.json").read_text())
    verdict = manifest["human_verdicts"][0]
    assert verdict["verdict"] == "pass"
    assert verdict["author"] == "jin"
    assert verdict["at"]


def test_human_reject_becomes_a_failure(repo):
    write_contract(repo, FUNCTIONAL + NEGATIVE + HUMAN)
    run_tool(repo, "verify")
    assert (
        run_tool(repo, "human", "--id", "C-03", "--verdict", "reject", "--note", "wrong shape") == 1
    )
    statuses = json.loads((repo / "artifacts" / "sample" / "status.json").read_text())
    assert statuses["C-03"]["status"] == "FAIL"
    assert "wrong shape" in statuses["C-03"]["note"]


def test_human_rejects_a_non_human_criterion(repo, capsys):
    write_contract(repo, FUNCTIONAL + NEGATIVE)
    assert run_tool(repo, "human", "--id", "C-01", "--verdict", "pass") == 2
    assert "not a `verify: human`" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# red — the check the whole toolkit rests on
# --------------------------------------------------------------------------- #


def _commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").strip()


def test_red_refuses_when_no_test_was_written(repo, capsys):
    """The regression this file exists for.

    No test file exists anywhere. pytest cannot even find the path, so it exits
    non-zero — and a naive "non-zero means red" rule would call that success,
    letting a contract with zero tests clear its own gate.
    """
    base = git(repo, "rev-parse", "HEAD").strip()
    (repo / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    _commit(repo, "change with no test")

    write_contract(
        repo,
        crit("C-01", f"{PYTEST_CMD} tests/test_f.py") + NEGATIVE,
        base=base,
    )
    assert run_tool(repo, "red", "--id", "C-01") == 1
    out = capsys.readouterr().out
    assert "NO-BASELINE" in out
    assert "PASS C-01" not in out


def test_red_passes_when_the_new_test_fails_at_base(repo, capsys):
    """The normal TDD path: the module under test does not exist at base."""
    base = git(repo, "rev-parse", "HEAD").strip()
    (repo / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_f.py").write_text(
        "from mod import f\n\n\ndef test_f():\n    assert f() == 1\n", encoding="utf-8"
    )
    _commit(repo, "add feature with test")

    write_contract(
        repo,
        crit("C-01", f"{PYTEST_CMD} tests/test_f.py") + NEGATIVE,
        base=base,
    )
    assert run_tool(repo, "red", "--id", "C-01") == 0
    assert "PASS C-01" in capsys.readouterr().out


def test_red_fails_when_the_check_already_passes_at_base(repo, capsys):
    base = git(repo, "rev-parse", "HEAD").strip()
    (repo / "note.txt").write_text("x\n", encoding="utf-8")
    _commit(repo, "unrelated change")

    write_contract(
        repo,
        FUNCTIONAL + NEGATIVE,
        base=base,
    )
    assert run_tool(repo, "red", "--id", "C-01") == 1
    assert "passed at base" in capsys.readouterr().out


def test_red_marks_unrunnable_commands_no_baseline(repo, capsys):
    base = git(repo, "rev-parse", "HEAD").strip()
    (repo / "note.txt").write_text("x\n", encoding="utf-8")
    _commit(repo, "unrelated change")

    write_contract(
        repo,
        crit("C-01", "definitely-not-a-command-xyz") + NEGATIVE,
        base=base,
    )
    assert run_tool(repo, "red", "--id", "C-01") == 1
    assert "NO-BASELINE" in capsys.readouterr().out


def test_red_skips_non_hermetic_criteria(repo, capsys):
    base = git(repo, "rev-parse", "HEAD").strip()
    (repo / "note.txt").write_text("x\n", encoding="utf-8")
    _commit(repo, "unrelated change")

    write_contract(
        repo,
        crit("C-01", "true", hermetic="false") + NEGATIVE,
        base=base,
    )
    assert run_tool(repo, "red", "--id", "C-01") == 0
    assert "SKIP C-01" in capsys.readouterr().out


def test_red_without_a_base_is_an_error(repo, capsys):
    write_contract(repo, FUNCTIONAL + NEGATIVE)
    assert run_tool(repo, "red") == 2
    assert "no base commit" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# status
# --------------------------------------------------------------------------- #


def test_status_blocks_without_evidence(repo, capsys):
    write_contract(repo, FUNCTIONAL + NEGATIVE)
    assert run_tool(repo, "status") == 1
    assert "evidence artifacts are missing" in capsys.readouterr().out


def test_status_passes_once_everything_is_green(repo):
    write_contract(repo, FUNCTIONAL + NEGATIVE)
    run_tool(repo, "verify")
    assert run_tool(repo, "status") == 0


def test_status_warns_on_an_unreviewed_checkpoint(repo, capsys):
    write_contract(
        repo,
        FUNCTIONAL + NEGATIVE,
        checkpoints="\n  - after: C-01\n    check: [drift]",
    )
    run_tool(repo, "verify")
    run_tool(repo, "status")
    assert "checkpoint after C-01" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# red: guard criteria
# --------------------------------------------------------------------------- #


def test_red_skips_guard_criteria(repo, capsys):
    """A standing invariant legitimately holds at base and is not a red candidate.

    Found by running the toolkit against its own work: a regression guard such as
    "every document opens with Core Rules" passes at base by design, so without
    this mode any contract containing one could never clear the gate.
    """
    base = git(repo, "rev-parse", "HEAD").strip()
    (repo / "note.txt").write_text("x\n", encoding="utf-8")
    _commit(repo, "unrelated change")

    write_contract(repo, crit("C-01", "true", red="guard") + NEGATIVE, base=base)
    assert run_tool(repo, "red", "--id", "C-01") == 0
    assert "SKIP C-01" in capsys.readouterr().out


def test_status_does_not_require_a_red_result_for_a_guard(repo):
    base = git(repo, "rev-parse", "HEAD").strip()
    write_contract(repo, crit("C-01", "true", red="guard") + NEGATIVE, base=base)
    run_tool(repo, "verify")
    assert run_tool(repo, "status") == 0


def test_lint_rejects_an_unknown_red_mode(repo, capsys):
    write_contract(repo, crit("C-01", "true", red="maybe") + NEGATIVE)
    assert run_tool(repo, "lint") == 1
    assert "red 'maybe'" in capsys.readouterr().out
