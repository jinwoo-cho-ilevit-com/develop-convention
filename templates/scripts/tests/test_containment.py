"""C-12 — a rejected feature name, and every write confined to the artifacts directory.

Withdrawal blocker 6 was `root / cfg["artifacts_dir"] / contract.feature` with nothing
validated, so `feature: ../../tmp/x` wrote outside the repository. Both halves are
enforced here: the name at parse time, the paths at the one place that opens a file.
"""

import contract
import pytest
from conftest import criterion, write_contract


def tree(root):
    """Every path in the repository except git internals and the artifacts directory."""
    return {
        p.relative_to(root)
        for p in root.rglob("*")
        if ".git" not in p.parts and "artifacts" not in p.parts
    }


# --- the name half -------------------------------------------------------------------


@pytest.mark.parametrize("feature", ["../escape", "..", "a/b", "/abs", "Upper", "with space"])
def test_containment_rejects_a_feature_name_that_is_not_a_plain_slug(repo, feature):
    write_contract(repo, [criterion("C-01")], feature=feature)
    assert contract.main(["lint", "--contract", str(repo / "contract.md")]) == 2


def test_containment_creates_no_directory_for_a_rejected_feature(repo):
    write_contract(repo, [criterion("C-01")], feature="../escape")
    contract.main(["verify", "--contract", str(repo / "contract.md")])
    assert not (repo.parent / "escape").exists()


# --- the write half ------------------------------------------------------------------


def writer(tmp_path):
    root = tmp_path / "artifacts" / "sample"
    root.mkdir(parents=True)
    return contract.ArtifactWriter(root)


@pytest.mark.parametrize("rel", ["../escape.txt", "../../escape.txt", "/etc/passwd", ".."])
def test_containment_refuses_a_write_outside_the_artifacts_directory(tmp_path, rel):
    with pytest.raises(contract.ContractError):
        writer(tmp_path).write_text(rel, "x")


@pytest.mark.parametrize("rel", ["../escape.txt", "/etc/passwd"])
def test_containment_refuses_an_append_outside_the_artifacts_directory(tmp_path, rel):
    with pytest.raises(contract.ContractError):
        writer(tmp_path).append_line(rel, "x")


def test_containment_refuses_a_reserved_path_outside_the_artifacts_directory(tmp_path):
    with pytest.raises(contract.ContractError):
        writer(tmp_path).reserve("../escape.xml")


def test_containment_refuses_a_symlink_that_points_outside(tmp_path):
    w = writer(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (w.root / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(contract.ContractError):
        w.write_text("link/escape.txt", "x")


def test_containment_allows_a_nested_relative_path(tmp_path):
    path = writer(tmp_path).write_text("state/C-01.red.json", "{}")
    assert path.read_text(encoding="utf-8") == "{}"


# --- the whole run leaves the tree alone ---------------------------------------------


def test_containment_a_full_run_writes_nothing_outside_artifacts(repo, base_sha):
    write_contract(
        repo,
        [criterion("C-01", verify="true"), criterion("C-02", kind="negative")],
        base=base_sha,
    )
    before = tree(repo)
    contract.main(["verify", "--contract", str(repo / "contract.md")])
    assert tree(repo) == before
