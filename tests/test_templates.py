"""`templates/` is the only thing this repository hands to another project.

Every defect here is one a next user meets, and each of the ones checked below arrived
the same way: something changed and the file that distributes it did not learn. The
runner gained five subcommands while conv-init went on saying there is no runner; the
root pinned ruff while the template it ships kept the instruction and dropped the pin.
"""

import re
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
CONV_INIT = TEMPLATES / "skills" / "conv-init" / "SKILL.md"

sys.path.insert(0, str(TEMPLATES / "scripts"))
import contract as runner  # noqa: E402


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def template_front_matter() -> dict:
    body = read(TEMPLATES / "contract.md")
    return yaml.safe_load(runner.split_front_matter(body))


# --- conv-init ships what the repository ships -------------------------------------------


def test_conv_init_installs_the_runner():
    """One file said both "copies the contract runner" and "there is no runner yet"."""
    body = read(CONV_INIT)
    assert "no runner yet" not in body
    assert "templates/scripts" in body or "scripts/" in body


def test_conv_init_copies_only_paths_that_exist():
    """A bootstrap should fail here, not in the project being bootstrapped."""
    named = set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:md|toml|yaml|py))`", read(CONV_INIT)))

    # Written relative to templates/, relative to the repository, or as a bare filename
    # somewhere beneath templates/ — the skill uses all three forms.
    def resolves(name: str) -> bool:
        if (TEMPLATES / name).exists() or (ROOT / name).exists():
            return True
        return any(TEMPLATES.rglob(Path(name).name))

    missing = sorted(name for name in named if not resolves(name))
    assert not missing, f"conv-init names paths that do not exist: {missing}"


# --- the template's own instruction about ruff --------------------------------------------


def hook_rev(config_path: Path, repo_fragment: str) -> str:
    config = yaml.safe_load(read(config_path))
    for entry in config["repos"]:
        if repo_fragment in entry["repo"]:
            return entry["rev"].lstrip("v")
    raise AssertionError(f"{config_path} has no {repo_fragment} hook")


def pinned_version(pyproject: Path, package: str) -> str | None:
    declared = tomllib.loads(read(pyproject))
    for entry in declared.get("dependency-groups", {}).get("dev", []):
        if entry.startswith(package):
            match = re.search(r"==\s*([0-9][0-9.]*)", entry)
            return match.group(1) if match else None
    return None


def test_ruff_pin_matches_the_hook_rev_in_the_template():
    """The template's own comment: keep `rev` in step with the pin — and there was none.

    pre-commit installs its own copy, so two versions format differently and the hook
    rewrites what the local check just called clean.
    """
    pinned = pinned_version(TEMPLATES / "pyproject.toml", "ruff")
    assert pinned, "templates/pyproject.toml does not pin ruff"
    assert pinned == hook_rev(TEMPLATES / ".pre-commit-config.yaml", "ruff-pre-commit")


def test_ruff_pin_matches_between_the_repository_and_the_template():
    """`templates/pyproject.toml` is the ruff config for files under templates/."""
    assert pinned_version(ROOT / "pyproject.toml", "ruff") == pinned_version(
        TEMPLATES / "pyproject.toml", "ruff"
    )


def test_template_declares_runner_dependencies():
    """`uv run --script` resolves the PEP 723 block; `uv run python scripts/…` does not."""
    source = read(TEMPLATES / "scripts" / "contract.py")
    inline = re.search(r"dependencies = \[([^\]]*)\]", source)
    assert inline, "the runner no longer declares inline script dependencies"
    needed = {
        entry.strip(" \"'").split(">")[0].split("=")[0] for entry in inline.group(1).split(",")
    }
    declared = tomllib.loads(read(TEMPLATES / "pyproject.toml"))
    dev = " ".join(declared["dependency-groups"]["dev"])
    missing = sorted(name for name in needed if name and name not in dev)
    assert not missing, f"templates/pyproject.toml omits {missing}, which the runner imports"


# --- the contract template describes the shipped runner -------------------------------------


def test_template_matches_the_runner_field_set():
    """A field the template offers and the runner refuses is a contract that will not load."""
    document = template_front_matter()
    unknown = sorted(set(document) - runner.KNOWN_FIELDS - set(runner.UNSUPPORTED_FIELDS))
    assert not unknown, f"the template offers top-level fields the runner refuses: {unknown}"
    for criterion in document["criteria"]:
        extra = sorted(set(criterion) - runner.KNOWN_CRITERION_FIELDS)
        assert not extra, f"{criterion.get('id')} offers fields the runner refuses: {extra}"


def test_template_matches_the_runner_on_hermetic():
    """The runner accepts `hermetic` only as literal true; anything else is exit 2.

    The template documented `false` as the way to exclude a criterion from the red check,
    which is a red exemption the runner does not implement — `red: guard` is the one it does.
    """
    body = read(TEMPLATES / "contract.md")
    assert "excluded from red check" not in body
    for criterion in template_front_matter()["criteria"]:
        assert criterion.get("hermetic", True) is True


def test_template_matches_the_runner_on_done_level():
    document = template_front_matter()
    assert document["done_level"] in runner.DONE_LEVELS


# --- one answer for an agent with no local clone ---------------------------------------------


SITE = "jinwoo-cho-ilevit-com.github.io/develop-convention"


def test_sandbox_guidance_is_the_same_in_both_places():
    """README offered a submodule and never named the site; the template did the reverse.

    An agent reaches whichever it happens to read, so the two have to say the same thing.
    """
    readme = read(ROOT / "README.md")
    agents = read(TEMPLATES / "AGENTS.md")
    assert SITE in readme, "README's cloud-sandbox note never mentions the published site"
    assert SITE in agents
    assert "submodule" in readme
    assert "submodule" in agents, "templates/AGENTS.md omits the submodule option README offers"


# --- the negative criterion --------------------------------------------------------------------


def test_no_runner_change_and_no_new_runtime_dependency():
    """The template is what is out of step, not the tool."""
    declared = tomllib.loads(read(ROOT / "pyproject.toml"))
    assert declared["project"]["dependencies"] == []
    assert runner.KNOWN_FIELDS == frozenset(
        {"schema_version", "feature", "done_level", "base", "criteria", "out_of_scope", "revision"}
    )
    assert runner.DONE_LEVELS == ("auto", "reviewed", "proven")


@pytest.mark.parametrize("name", ["contract.py", "secrets.toml"])
def test_no_runner_change_leaves_the_toolkit_present(name):
    assert (TEMPLATES / "scripts" / name).is_file()


# --- a project bootstrapped from templates/ can actually run a contract ---------------------


def test_bootstrap_runs_a_contract_end_to_end(tmp_path):
    """The claim `templates/` makes, executed rather than read.

    Every check above reads a file. This one performs conv-init's copy steps into an
    empty repository and drives the copied runner through all five phases, which is the
    only way to find out whether what leaves this repository works where it lands.
    """
    import json
    import subprocess

    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    (tmp_path / "scripts").mkdir()
    for name in ("contract.py", "secrets.toml"):
        (tmp_path / "scripts" / name).write_bytes((TEMPLATES / "scripts" / name).read_bytes())
    (tmp_path / "pyproject.toml").write_bytes((TEMPLATES / "pyproject.toml").read_bytes())

    git("init", "--quiet")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    git("config", "core.hooksPath", str(tmp_path / "nohooks"))
    git("config", "commit.gpgsign", "false")
    (tmp_path / "marker").write_text("base\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "--quiet", "-m", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout.strip()

    # A criterion that fails at base and passes at head, the shape a red check exists for.
    (tmp_path / "feature").write_text("done\n", encoding="utf-8")
    (tmp_path / "contract.md").write_text(
        "---\n"
        + yaml.safe_dump(
            {
                "schema_version": 1,
                "feature": "bootstrap",
                "done_level": "auto",
                "base": base,
                "criteria": [
                    {
                        "id": "C-01",
                        "text": "THE feature file SHALL exist.",
                        "verify": "test -f feature",
                        "runner": "command",
                        "kind": "functional",
                    },
                    {
                        "id": "C-02",
                        "text": "THE build SHALL NOT leave a stray file.",
                        "verify": "test -f marker",
                        "runner": "command",
                        "kind": "negative",
                        "red": "guard",
                    },
                ],
                "out_of_scope": ["everything else"],
            },
            sort_keys=False,
        )
        + "---\n\n# bootstrap\n",
        encoding="utf-8",
    )

    def phase(name):
        return subprocess.run(
            [sys.executable, "scripts/contract.py", name, "--contract", "contract.md"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

    assert phase("lint").returncode == 0
    assert phase("red").returncode == 0, phase("red").stderr
    assert phase("verify").returncode == 0
    assert phase("status").returncode == 0

    evidence = tmp_path / "artifacts" / "bootstrap"
    for name in ("REPORT.md", "commands.jsonl", "commands.log", "manifest.json"):
        assert (evidence / name).is_file(), name
    assert json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))["base"] == base
