#!/usr/bin/env bash
# Injects the convention routing map once per user prompt. A pointer, not a gate: it judges
# nothing, so the per-edit judgement cost 21 §3 rejects does not arise here, and it carries
# no rule text — the rules stay in conventions/ behind the named skill (→ 15-doc-tracking.md).
#
# Every line is read out of the skill's own frontmatter, so the map and the description an
# agent selects on cannot say different things. The plugin root is derived from this script's
# own path, which a hook always has, rather than from an environment variable it may not.
set -euo pipefail

cat >/dev/null

root=$(cd "$(dirname "$0")/.." && pwd)

echo "<convention-routing>"
echo "Before starting work, load the dev-harness skill that governs it:"
for skill in "$root"/skills/*/SKILL.md; do
  awk '
    NR == 1 && $0 != "---" { exit }
    NR > 1 && $0 == "---" { exit }
    /^name: / { name = substr($0, 7) }
    /^description: / { description = substr($0, 14) }
    END { if (name != "" && description != "") printf "- %s → %s\n", description, name }
  ' "$skill"
done
cat <<'MAP'
A trivial single edit may proceed without one; anything larger reads the routed Core Rules first.
</convention-routing>
MAP
