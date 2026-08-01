"""C-01 — an unusable contract stops the caller.

The failure this guards is a gate that opens because it could not read its own
rules. Every case here asserts a non-zero exit AND that the runner did not
behave as though the contract were empty.
"""

import contract
import pytest
from conftest import criterion, write_contract


def run(repo, *argv, name="contract.md"):
    return contract.main([*argv, "--contract", str(repo / name)])


def write_raw(repo, text, name="contract.md"):
    path = repo / name
    path.write_text(text, encoding="utf-8")
    return path


# --- the contract cannot be read -----------------------------------------------------


def test_parse_missing_file_exits_two(repo):
    assert run(repo, "lint", name="absent.md") == 2


def test_parse_no_front_matter_exits_two(repo):
    write_raw(repo, "# just a heading\n")
    assert run(repo, "lint") == 2


def test_parse_unclosed_front_matter_exits_two(repo):
    write_raw(repo, "---\nfeature: sample\n")
    assert run(repo, "lint") == 2


def test_parse_invalid_yaml_exits_two(repo):
    write_raw(repo, "---\nfeature: [unclosed\n---\n")
    assert run(repo, "lint") == 2


def test_parse_unknown_schema_version_exits_two(repo):
    write_contract(repo, [criterion("C-01")], schema_version=99)
    assert run(repo, "lint") == 2


def test_parse_missing_required_field_exits_two(repo):
    write_raw(repo, "---\nschema_version: 1\nfeature: sample\n---\n")
    assert run(repo, "lint") == 2


def test_parse_empty_criteria_exits_two(repo):
    write_contract(repo, [])
    assert run(repo, "lint") == 2


def test_parse_duplicate_criterion_id_exits_two(repo):
    write_contract(repo, [criterion("C-01"), criterion("C-01")])
    assert run(repo, "lint") == 2


# --- values that would reach a filesystem path ---------------------------------------


@pytest.mark.parametrize(
    "feature",
    ["../escape", "has/slash", "Has-Upper", "has space", "", "-leading", "trailing-"],
)
def test_parse_rejects_an_unusable_feature_name(repo, feature):
    write_contract(repo, [criterion("C-01")], feature=feature)
    assert run(repo, "lint") == 2


def test_parse_rejects_a_feature_that_is_not_a_string(repo):
    """An unfilled `feature: [short-slug]` placeholder parses as a one-element list."""
    write_contract(repo, [criterion("C-01")], feature=["short-slug"])
    assert run(repo, "lint") == 2


def test_parse_rejects_a_criterion_id_that_is_not_a_plain_slug(repo):
    """Criterion ids become filenames too."""
    write_contract(repo, [criterion("../../evil")])
    assert run(repo, "lint") == 2


def test_parse_refuses_a_bypassed_done_level(repo):
    """18 and 19 both require a bypass to carry a reason, and this runner records none.

    Accepting the level put the reason nowhere and still returned OK from `status` —
    18 calls an unrecorded bypass the blocker, so the runner refuses the contract.
    """
    write_contract(repo, [criterion("C-01")], done_level="bypassed")
    assert run(repo, "lint") == 2


# --- verify strings the runner refuses to execute ------------------------------------


@pytest.mark.parametrize("verify", ["a && b", "a | b", "a; b", "a > out", "a `b`", "a $(b)"])
def test_parse_rejects_a_verify_command_that_needs_a_shell(repo, verify):
    """C-02 runs an argument vector, so a shell operator would become a literal argument."""
    write_contract(repo, [criterion("C-01", verify=verify)])
    assert run(repo, "lint") == 2


@pytest.mark.parametrize("verify", ["a 2>&1", "a &> out", "a >& out", "a <> b", "a |& b"])
def test_parse_rejects_a_redirect_whose_operator_is_two_characters(repo, verify):
    """shlex merges adjacent punctuation, so `>&` is one token and matched no listed operator.

    These loaded cleanly, reached the program as a literal argument, and the criterion
    passed with its redirect having done nothing — the exact outcome the refusal exists
    to prevent. The rule is now the character set shlex splits on, not a list of forms.
    """
    write_contract(repo, [criterion("C-01", verify=verify)])
    assert run(repo, "lint") == 2


def test_parse_rejects_an_empty_verify(repo):
    write_contract(repo, [criterion("C-01", verify="   ")])
    assert run(repo, "lint") == 2


def test_parse_rejects_an_unknown_runner_kind(repo):
    write_contract(repo, [criterion("C-01", runner="make")])
    assert run(repo, "lint") == 2


def test_parse_requires_a_runner_for_a_machine_criterion(repo):
    crit = {"id": "C-01", "text": "t", "verify": "true", "kind": "functional"}
    write_contract(repo, [crit])
    assert run(repo, "lint") == 2


# --- fields this runner does not implement, refused rather than ignored --------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("lanes", [{"id": "A", "owns": ["src/"], "criteria": ["C-01"]}]),
        ("sequential_owner", ["pyproject.toml"]),
        ("integration", {"owner": "A", "criteria": ["C-01"]}),
        ("checkpoints", [{"after": "C-01"}]),
    ],
)
def test_parse_refuses_a_field_this_runner_does_not_implement(repo, field, value):
    """Silently ignoring a field the author believes is enforced is the placeholder defect."""
    write_contract(repo, [criterion("C-01")], **{field: value})
    assert run(repo, "lint") == 2


def test_parse_refuses_hermetic_false(repo):
    """The template documents it as a red exemption; C-05 admits only human and guard."""
    write_contract(repo, [criterion("C-01", hermetic=False)])
    assert run(repo, "lint") == 2


def test_parse_accepts_hermetic_true(repo):
    write_contract(repo, [criterion("C-01", hermetic=True), criterion("C-02", kind="negative")])
    assert run(repo, "lint") == 0


# --- an unreadable contract is not an empty one --------------------------------------


def test_parse_a_broken_contract_never_reports_success(repo):
    """The withdrawn runner's failure mode: a gate that opens because it cannot read.

    Asserted per entry point, because the failure was that one phase stopped and the
    next carried on.
    """
    write_raw(repo, "---\nnot: a contract\n---\n")
    for command in ("lint", "red", "verify", "status"):
        assert run(repo, command) == 2


def test_parse_a_valid_contract_lints_clean(repo):
    write_contract(repo, [criterion("C-01"), criterion("C-02", kind="negative")])
    assert run(repo, "lint") == 0
