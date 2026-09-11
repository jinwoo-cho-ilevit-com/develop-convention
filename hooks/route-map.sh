#!/usr/bin/env bash
# Injects the convention routing map once per user prompt: a pointer carrying no rule text.
# Each line is the trigger clause ("Use ...") of a skill's own frontmatter description, so the
# map cannot disagree with what the agent selects on (→ conventions/15-doc-tracking.md).
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
    printf "- %s → dev-harness:%s\n", clause, name
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
