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


# --- verify strings the runner refuses to execute ------------------------------------


@pytest.mark.parametrize("verify", ["a && b", "a | b", "a; b", "a > out", "a `b`", "a $(b)"])
def test_parse_rejects_a_verify_command_that_needs_a_shell(repo, verify):
    """C-02 runs an argument vector, so a shell operator would become a literal argument."""
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

    Only `lint` exists yet. Every later phase is added to this loop as it lands, so
    the property is asserted per entry point rather than once. Asserting an
    unregistered subcommand here would pass on argparse's own exit 2 — the same code
    for a different reason.
    """
    write_raw(repo, "---\nnot: a contract\n---\n")
    for command in ("lint",):
        assert run(repo, command) == 2


def test_parse_a_valid_contract_lints_clean(repo):
    write_contract(repo, [criterion("C-01"), criterion("C-02", kind="negative")])
    assert run(repo, "lint") == 0
