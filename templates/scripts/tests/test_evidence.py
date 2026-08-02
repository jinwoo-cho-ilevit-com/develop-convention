"""C-08 — the four evidence artifacts, and a status that blocks while one is missing.

19 §1 fixes the layout and 19 §2 fixes the table. The withdrawn runner produced all
four and its status blocked on a missing `commands.jsonl`; that defence is restored
here rather than assumed.
"""

import json
import re
import time

import contract
import pytest
from conftest import criterion, write_contract

FOUR = ("REPORT.md", "commands.jsonl", "commands.log", "manifest.json")
# 19 fixes the vocabulary at exactly these four. A fifth word in the status column is
# the finding, not something to add here.
STATUS_WORDS = {"PASS", "FAIL", "PENDING-HUMAN", "NO-BASELINE"}


def art(repo, feature="sample"):
    return repo / "artifacts" / feature


def run(repo, *argv):
    return contract.main([*argv, "--contract", str(repo / "contract.md")])


def simple(repo, base_sha, **over):
    write_contract(
        repo,
        [criterion("C-01", **over), criterion("C-02", kind="negative")],
        base=base_sha,
    )


def test_evidence_verify_writes_all_four_artifacts(repo, base_sha):
    simple(repo, base_sha)
    run(repo, "verify")
    for name in FOUR:
        assert (art(repo) / name).is_file(), name


def test_evidence_red_writes_all_four_artifacts(repo, base_sha):
    simple(repo, base_sha, verify="false")
    run(repo, "red")
    for name in FOUR:
        assert (art(repo) / name).is_file(), name


@pytest.mark.parametrize("missing", FOUR)
def test_evidence_status_blocks_while_an_artifact_is_missing(repo, base_sha, missing):
    simple(repo, base_sha, verify="false")
    run(repo, "red")
    run(repo, "verify")
    (art(repo) / missing).unlink()
    assert run(repo, "status") != 0


def test_evidence_status_writes_nothing(repo, base_sha):
    """Otherwise it could never observe the artifact it creates as missing."""
    simple(repo, base_sha, verify="false")
    run(repo, "red")
    run(repo, "verify")
    before = {p: p.read_bytes() for p in sorted(art(repo).rglob("*")) if p.is_file()}
    run(repo, "status")
    after = {p: p.read_bytes() for p in sorted(art(repo).rglob("*")) if p.is_file()}
    assert after == before


def test_evidence_report_is_one_row_per_criterion(repo, base_sha):
    simple(repo, base_sha)
    run(repo, "verify")
    body = (art(repo) / "REPORT.md").read_text(encoding="utf-8")
    rows = [line for line in body.splitlines() if line.startswith("| C-")]
    assert len(rows) == 2


def test_evidence_status_is_one_of_the_four_words(repo, base_sha):
    """19: status survives grep and diff only if it is one of a fixed, spelled-out set.

    Driven through the states that tempted a fifth word — a criterion blocked by a
    missing red record, and one whose verify never ran.
    """
    simple(repo, base_sha, verify="false")
    run(repo, "verify")
    body = (art(repo) / "REPORT.md").read_text(encoding="utf-8")
    seen = [line.split("|")[2].strip() for line in body.splitlines() if line.startswith("| C-")]
    assert seen, "no criterion rows in the report"
    assert set(seen) <= STATUS_WORDS, seen


def test_evidence_commands_jsonl_is_one_object_per_execution(repo, base_sha):
    simple(repo, base_sha)
    run(repo, "verify")
    lines = (art(repo) / "commands.jsonl").read_text(encoding="utf-8").strip().splitlines()
    records = [json.loads(line) for line in lines]
    assert {r["criterion"] for r in records} == {"C-01", "C-02"}
    assert all(r["phase"] == "verify" for r in records)


def test_evidence_manifest_records_provenance(repo, base_sha):
    simple(repo, base_sha)
    run(repo, "verify")
    manifest = json.loads((art(repo) / "manifest.json").read_text(encoding="utf-8"))
    assert contract.is_iso_utc(manifest["created_at"])
    assert manifest["commit"]
    assert isinstance(manifest["tree_clean"], bool)
    assert manifest["base"] == base_sha


def test_evidence_report_escapes_a_pipe_in_the_command_cell(repo, base_sha):
    """A bare `|` ends the cell early and drops `note`, which carries why it is blocked.

    18 §4 advertises `--format='%h|%s'` as a command this runner runs, so the character
    reaches the report, and every row must still have the four cells its header declares.
    """
    write_contract(
        repo,
        [
            criterion("C-01", verify="git log -1 --format='%h|%s'"),
            criterion("C-02", kind="negative"),
        ],
        base=base_sha,
    )
    contract.main(["verify", "--contract", str(repo / "contract.md")])
    report = (repo / "artifacts" / "sample" / "REPORT.md").read_text(encoding="utf-8")
    row = next(line for line in report.splitlines() if line.startswith("| C-01 "))
    assert r"\|" in row
    assert len(re.findall(r"(?<!\\)\|", row)) == 5, row


def test_evidence_report_keeps_every_row_when_a_note_holds_a_blank_line(repo, base_sha):
    """A blank line closes the table, and every criterion below it stops being a row.

    `--note` carries whatever an author typed, so this arrives through the sanctioned
    way of attaching a reason to a verdict.
    """
    write_contract(
        repo,
        [
            {"id": "C-01", "text": "a judgement", "verify": "human", "kind": "functional"},
            criterion("C-02", kind="negative"),
        ],
        base=base_sha,
    )
    args = ["human", "--contract", str(repo / "contract.md"), "--id", "C-01"]
    contract.main([*args, "--verdict", "reject", "--author", "me", "--note", "blocked\n\nsee"])
    report = (repo / "artifacts" / "sample" / "REPORT.md").read_text(encoding="utf-8")
    rows = [line for line in report.splitlines() if line.startswith("| C-")]
    assert len(rows) == 2, report
    assert all(len(re.findall(r"(?<!\\)\|", row)) == 5 for row in rows), rows


def test_verify_runs_accumulate_across_runs(repo, base_sha):
    """19 §4 names this as a field without which lead time cannot be derived at all.

    It has to accumulate, and a per-criterion record holds only the latest — so the phase
    appends to a run log inside the state directory and the manifest is rendered from it,
    which keeps the manifest derived rather than merged into.
    """
    simple(repo, base_sha)
    run(repo, "verify")
    run(repo, "verify")
    manifest = json.loads((art(repo) / "manifest.json").read_text(encoding="utf-8"))
    runs = manifest["verify_runs"]
    assert len(runs) == 2, runs
    assert all(contract.is_iso_utc(entry["at"]) for entry in runs)


def test_bypass_reason_reaches_the_manifest(repo, base_sha):
    """18 calls an unrecorded bypass the blocker; the record is what makes it a decision."""
    write_contract(
        repo,
        [criterion("C-01"), criterion("C-02", kind="negative")],
        base=base_sha,
        done_level="bypassed",
        bypass={"reason": "the deploy window closed", "author": "someone"},
    )
    run(repo, "verify")
    manifest = json.loads((art(repo) / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["done_level"] == "bypassed"
    assert manifest["bypass"]["reason"] == "the deploy window closed"


def test_created_at_does_not_move_between_renders(repo, base_sha):
    """19 §4 derives lead time per contract from this field, and a value that moves
    derives nothing. It used to be `now_iso()` at every render — the time of the last
    write rather than the first.
    """
    simple(repo, base_sha)
    run(repo, "verify")
    first = json.loads((art(repo) / "manifest.json").read_text(encoding="utf-8"))["created_at"]
    time.sleep(1.1)
    run(repo, "verify")
    second = json.loads((art(repo) / "manifest.json").read_text(encoding="utf-8"))["created_at"]
    assert first == second
    runs = json.loads((art(repo) / "manifest.json").read_text(encoding="utf-8"))["verify_runs"]
    assert runs[-1]["at"] != first, "the run log must still advance while created_at holds"


def test_another_feature_awaiting_a_verdict_is_reported(repo, base_sha, capsys):
    """A contract awaiting verdicts can be replaced by the next one with nothing noticing.

    It happened three times in the session that added this. The runner cannot refuse —
    collecting verdicts at the end means several contracts are pending on purpose — so
    it reports what it sees.
    """
    other = art(repo, "earlier") / "state"
    other.mkdir(parents=True)
    (other / "C-01.human.json").write_text(
        json.dumps({"criterion": "C-01", "phase": "human", "status": "PENDING-HUMAN"}),
        encoding="utf-8",
    )
    simple(repo, base_sha)
    run(repo, "lint")
    assert "earlier still awaits a human verdict" in capsys.readouterr().out


def test_the_current_feature_is_not_reported_as_pending(repo, base_sha, capsys):
    write_contract(
        repo,
        [
            {"id": "C-01", "text": "a judgement", "verify": "human", "kind": "functional"},
            criterion("C-02", kind="negative"),
        ],
        base=base_sha,
    )
    run(repo, "verify")
    capsys.readouterr()
    run(repo, "status")
    assert "still awaits a human verdict" not in capsys.readouterr().out
