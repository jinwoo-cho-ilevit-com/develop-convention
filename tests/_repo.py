"""Paths and readers every test module shares. pytest puts `tests/` on `sys.path`."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONVENTIONS = sorted((ROOT / "conventions").glob("*.md"))
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"


def read(path: Path | str) -> str:
    """A `str` is relative to the repository root."""
    return (ROOT / path).read_text(encoding="utf-8")


def load(path: Path) -> dict:
    return json.loads(read(path))
