#!/usr/bin/env bash
# Injects the convention routing map once per user prompt. A pointer, not a gate: it judges
# nothing, so the per-edit judgement cost 21 §3 rejects does not arise here, and it carries
# no rule text — the rules stay in conventions/ behind the named skill (→ 15-doc-tracking.md).
#
# Every line is the trigger clause of the skill's own frontmatter description (its first
# "Use ..." sentence), so the map cannot disagree with what the agent selects on, and the
# whole description is not repeated into a context that already holds it. The plugin root is
# derived from this script's own path, which a hook always has.
set -euo pipefail

cat >/dev/null

root=$(cd "$(dirname "$0")/.." && pwd)

echo "<convention-routing>"
echo "Before starting work, load the dev-harness skill that governs it:"
awk '
  function emit() {
    if (name == "" || desc == "") return
    at = index(desc, ". Use ")
    clause = at ? substr(desc, at + 6) : desc
    printf "- %s → %s\n", clause, name
  }
  FNR == 1 { name = ""; desc = ""; inside = ($0 == "---") ; next }
  inside && $0 == "---" { emit(); inside = 0; next }
  inside && /^name: / { name = substr($0, 7) }
  inside && /^description: / { desc = substr($0, 14) }
' "$root"/skills/*/SKILL.md
cat <<'MAP'
A trivial single edit may proceed without one; anything larger reads the routed Core Rules first.
</convention-routing>
MAP
