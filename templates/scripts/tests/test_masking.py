"""C-15 — secrets are masked in the command line, the environment and the output.

19 requires masking at every sink, so the tests here plant a real credential and then
assert its absence from every artifact on disk rather than unit-testing the matcher.
The first two tests are about the pattern file itself: a shape with no working sample
is a shape nobody has proven catches anything.
"""

import json

import contract
import pytest
from conftest import criterion, write_contract

SHAPES = contract.secret_shapes()


def artifacts(repo, feature="sample"):
    return repo / "artifacts" / feature


def all_artifact_text(repo, feature="sample"):
    root = artifacts(repo, feature)
    return "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(root.rglob("*"))
        if p.is_file()
    )


# --- the pattern file is trustworthy -------------------------------------------------


def test_masking_ships_at_least_one_shape():
    assert SHAPES


@pytest.mark.parametrize("shape", SHAPES, ids=lambda s: s.name)
def test_masking_every_shape_matches_its_own_sample(shape):
    """A pattern added without a sample it matches fails here, not silently later."""
    assert shape.sample.strip()
    assert contract.re.search(shape.pattern, shape.sample)


@pytest.mark.parametrize("shape", SHAPES, ids=lambda s: s.name)
def test_masking_no_sample_sits_whole_in_the_pattern_file(shape):
    """A sample is a credential in the format scanners look for.

    Written whole it makes this file a secret: GitHub's push protection rejected a push
    over the Slack sample, and a project that copied the toolkit inherited the block.
    Fragments are joined in memory, so the split has to survive review — this is what
    refuses one that was reassembled into a single fragment.
    """
    body = contract.SECRETS_PATH.read_text(encoding="utf-8")
    assert shape.sample not in body


@pytest.mark.parametrize("shape", SHAPES, ids=lambda s: s.name)
def test_masking_redacts_the_sample_of_every_shape(shape):
    masked = contract.Masker.from_env({}).mask(f"prefix {shape.sample} suffix")
    assert shape.sample not in masked
    assert contract.MASK in masked


def test_masking_leaves_ordinary_text_alone():
    text = "uv run --group dev pytest templates/scripts/tests -q"
    assert contract.Masker.from_env({}).mask(text) == text


# --- environment values, which match no shape ----------------------------------------


def test_masking_redacts_the_value_of_a_secret_bearing_variable():
    secret = "wholly-unremarkable-string-0192837465"
    masked = contract.Masker.from_env({"MYAPP_TOKEN": secret}).mask(f"got {secret} back")
    assert secret not in masked


def test_masking_ignores_a_variable_that_is_not_secret_bearing():
    value = "ordinary-value-0192837465"
    assert value in contract.Masker.from_env({"MYAPP_REGION": value}).mask(f"x {value} y")


def test_masking_ignores_a_short_secret_value():
    """A variable set to `1` would otherwise shred every artifact."""
    masked = contract.Masker.from_env({"MYAPP_TOKEN": "1"}).mask("exit code 1 seen")
    assert masked == "exit code 1 seen"


# --- end to end: nothing unmasked reaches disk ---------------------------------------


@pytest.mark.parametrize("shape", SHAPES, ids=lambda s: s.name)
def test_masking_keeps_a_planted_credential_out_of_every_artifact(repo, base_sha, shape):
    """The credential is in the command line and in the command's output."""
    write_contract(
        repo,
        [
            criterion("C-01", verify=f"echo {shape.sample}"),
            criterion("C-02", kind="negative"),
        ],
        base=base_sha,
    )
    contract.main(["verify", "--contract", str(repo / "contract.md")])
    text = all_artifact_text(repo)
    assert text, "no artifacts were written"
    assert shape.sample not in text


def test_masking_manifest_names_only_what_was_actually_redacted(repo, base_sha, monkeypatch):
    """A manifest that named a variable it did not mask is a false assurance.

    Both names match the secret-bearing globs; only the long value is redacted, so
    only the long one may be listed. Listing the short one would tell a reviewer the
    value was hidden while the log still carries it.
    """
    monkeypatch.setenv("LONG_TOKEN", "zq7wlongsecretvalue")
    monkeypatch.setenv("SHORT_TOKEN", "abc")
    write_contract(
        repo,
        [
            criterion("C-01", verify="printenv SHORT_TOKEN"),
            criterion("C-02", kind="negative"),
        ],
        base=base_sha,
    )
    contract.main(["verify", "--contract", str(repo / "contract.md")])
    manifest = json.loads((artifacts(repo) / "manifest.json").read_text(encoding="utf-8"))
    assert "LONG_TOKEN" in manifest["masked_env_names"]
    assert "SHORT_TOKEN" not in manifest["masked_env_names"]
    assert "abc" in all_artifact_text(repo), "the short value really is in the clear"


def test_masking_keeps_an_environment_secret_out_of_every_artifact(repo, base_sha, monkeypatch):
    secret = "env-only-credential-5647382910"
    monkeypatch.setenv("MYAPP_TOKEN", secret)
    write_contract(
        repo,
        [
            criterion("C-01", verify="printenv MYAPP_TOKEN"),
            criterion("C-02", kind="negative"),
        ],
        base=base_sha,
    )
    contract.main(["verify", "--contract", str(repo / "contract.md")])
    assert secret not in all_artifact_text(repo)
