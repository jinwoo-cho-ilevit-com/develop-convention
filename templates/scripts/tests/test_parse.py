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


@pytest.mark.parametrize("verify", ["a && b", "a | b", "a; b", "a > out", "a $(b)"])
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


@pytest.mark.parametrize(
    "verify",
    [
        "git log -1 --format='%h|%s'",
        "awk '{print}' f",
        "pytest -k 'a; b'",
        "ruff check --select='E,F'",
        "awk '{print $(NF)}' f",
        "grep -c '```' README.md",
    ],
)
def test_parse_accepts_an_argument_that_merely_contains_punctuation(repo, verify):
    """Only an argument made *only* of operator punctuation is refused.

    A second lex over the quoted text split `--format='%h|%s'` at the attached quote
    and scored the `|` as bare, refusing a command that runs correctly. One lex, read
    once, cannot disagree with itself that way.
    """
    write_contract(repo, [criterion("C-01", verify=verify), criterion("C-02", kind="negative")])
    assert run(repo, "lint") == 0


@pytest.mark.parametrize(
    "verify",
    [
        "echo --ignore='a(b)' && echo PWNED",
        "rm -rf tmpdir ; echo a'|'b",
        "find . -exec echo {} ';'",
        r"find . -exec echo {} \;",
        "echo 'cost $(1) usd' && true",
    ],
)
def test_parse_refuses_an_operator_argument_however_it_was_written(repo, verify):
    """Quoting does not buy an exemption, and the first two show why it cannot.

    Reading the quoted form to grant one needed a second lex, and on the first input
    that lex raised where the real one did not. The `except ValueError: return []` then
    skipped the check entirely and an unquoted `&&` reached the program as an argument.
    """
    write_contract(repo, [criterion("C-01", verify=verify), criterion("C-02", kind="negative")])
    assert run(repo, "lint") == 2


def test_parse_accepts_a_backtick_as_an_ordinary_argument(repo):
    """There is no shell to substitute anything, and refusing it cost real commands.

    The rule that refused a backtick also refused ``grep -c '```' README.md`` — a
    criterion this repository would write — and appeared in no document.
    """
    write_contract(
        repo,
        [criterion("C-01", verify="grep -c '```' README.md"), criterion("C-02", kind="negative")],
    )
    assert run(repo, "lint") == 0


@pytest.mark.parametrize(
    "verify",
    [
        "/bin/echo a\n/bin/echo b",
        "/bin/echo a\n\n/bin/echo b",
        "/bin/echo a\r/bin/echo b",
        "/bin/echo a\r\n/bin/echo b",
    ],
)
def test_parse_refuses_a_verify_that_spans_more_than_one_line(repo, verify):
    """POSIX counts a newline among the control operators; shlex counts it as whitespace.

    A YAML block scalar holding two commands was fused into one argv and the criterion
    passed on a command the contract never states — the same failure the operator check
    exists to prevent, arriving through a character the check never looked at. Checking
    for `\\n` alone then let `\\r` through the same way, which is why the rule is now
    derived from shlex's whitespace set rather than written out.
    """
    write_contract(repo, [criterion("C-01", verify=verify), criterion("C-02", kind="negative")])
    assert run(repo, "lint") == 2


def test_parse_passes_an_unquoted_hash_through_as_an_argument(repo):
    """shlex drops an unquoted `#` and the rest of the line unless commenters is cleared.

    The criterion then passed on a shorter command than the contract states, and the
    evidence attributed the truncated form to it.
    """
    write_contract(
        repo,
        [criterion("C-01", verify="echo keepme #tail"), criterion("C-02", kind="negative")],
    )
    assert run(repo, "lint") == 0
    loaded = contract.load_contract(repo / "contract.md")
    assert contract.display_command(loaded.criteria[0].check).endswith("keepme '#tail'")


@pytest.mark.parametrize("hermetic", ["false", 0, "no", "banana", None])
def test_parse_refuses_a_hermetic_value_that_is_not_true(repo, hermetic):
    """`is False` let every near-miss through, and each one reads as an exemption."""
    write_contract(repo, [criterion("C-01", hermetic=hermetic)])
    assert run(repo, "lint") == 2


def test_parse_refuses_a_bare_runner_key_on_a_human_criterion(repo):
    """A `runner:` line left behind parses as null, which `is not None` did not catch."""
    write_contract(repo, [{"id": "C-01", "text": "x", "verify": "human", "runner": None}])
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


@pytest.mark.parametrize("key", ["on", "no", "2024", "yes"])
def test_parse_names_an_unknown_field_whose_key_yaml_did_not_leave_a_string(repo, key):
    """YAML 1.1 resolves `on`/`no`/`yes` to booleans and a bare year to an int.

    Joining the unknown names raised, so the runner exited 3 — "the runner broke" —
    where it owed the author 2 and the name of the field.
    """
    write_raw(
        repo,
        "---\nschema_version: 1\nfeature: sample\ndone_level: reviewed\n"
        f"{key}: something\ncriteria:\n  - id: C-01\n    text: x\n    verify: 'true'\n"
        "    runner: command\n    kind: negative\nout_of_scope: [x]\n---\n",
    )
    assert run(repo, "lint") == 2


def test_parse_accepts_a_verify_folded_across_lines(repo):
    """A folded scalar has no line break left in it: YAML made it one line, as asked."""
    write_raw(
        repo,
        "---\nschema_version: 1\nfeature: sample\ndone_level: reviewed\n"
        "criteria:\n  - id: C-01\n    text: x\n    verify: >-\n      echo one\n      two\n"
        "    runner: command\n    kind: negative\nout_of_scope: [x]\n---\n",
    )
    assert run(repo, "lint") == 0
    loaded = contract.load_contract(repo / "contract.md")
    assert contract.display_command(loaded.criteria[0].check) == "echo one two"
