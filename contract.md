---
schema_version: 1
feature: split-review-gate
done_level: reviewed

criteria:
  - id: C-01
    text: "THE repository SHALL keep `## Core Rules` as the first body heading of every convention document."
    verify: "for f in conventions/*.md; do [ \"$(grep -m1 '^## ' $f)\" = '## Core Rules' ] || exit 1; done"
    kind: functional
    red: guard

  - id: C-02
    text: "THE repository SHALL contain no tool-call residue and every doc-map link SHALL resolve."
    verify: "! grep -rq '</content>\\|</invoke>' conventions/ templates/ README.md CLAUDE.md && for p in $(grep -oE '\\(conventions/[0-9]{2}-[a-z-]+\\.md\\)' README.md | tr -d '()' | sort -u); do [ -f \"$p\" ] || exit 1; done"
    kind: functional
    red: guard

  - id: C-03
    text: "THE review gate SHALL live in doc 20, and doc 09 SHALL no longer carry the review lane definitions."
    verify: "grep -q 'A lane is defined by its' conventions/20-review-gate.md && ! grep -q 'A lane is defined by its' conventions/09-agentic-workflow.md"
    kind: functional

  - id: C-04
    text: "THE review-gate rules SHALL appear in exactly one document — doc 09 SHALL retain no rule about review lanes, fan-in, or review tooling."
    verify: "! grep -qiE 'fan-in|review lane|cursor-agent|codex' conventions/09-agentic-workflow.md"
    kind: negative

  - id: C-05
    text: "Every reference that pointed at doc 09's review content SHALL point at doc 20 instead."
    verify: "grep -q '20-review-gate' conventions/06-testing-verification.md && grep -q '20-review-gate' conventions/15-doc-tracking.md && grep -q '20-review-gate' conventions/18-work-contract.md && grep -q '20-review-gate' CLAUDE.md"
    kind: functional

  - id: C-06
    text: "THE documents SHALL contain no section cross-reference pointing past their own last section."
    verify: "for f in conventions/09-agentic-workflow.md conventions/20-review-gate.md; do last=$(grep -c '^### ' $f); for n in $(grep -oE '§[0-9]+' $f | tr -d '§' | sort -u); do [ \"$n\" -le \"$last\" ] || exit 1; done; done"
    kind: functional

  - id: C-07
    text: "THE combined length of the convention documents, README, and CLAUDE.md SHALL NOT exceed the 1798-line baseline, and no single convention document SHALL exceed 120 lines."
    verify: "t=$(cat conventions/*.md README.md CLAUDE.md | wc -l); [ \"$t\" -le 1798 ] && ! wc -l conventions/*.md | awk '$1>120 && $2!=\"total\"{f=1} END{exit !f}'"
    kind: nonfunctional

  - id: C-08
    text: "THE change SHALL add exactly one convention document."
    verify: "[ \"$(ls conventions/*.md | wc -l)\" -eq 21 ]"
    kind: negative

  - id: C-09
    text: "THE change SHALL NOT add code or build configuration."
    verify: "! ls pyproject.toml uv.lock .pre-commit-config.yaml 2>/dev/null | grep -q . && [ ! -d templates/scripts ] && [ ! -f .github/workflows/checks.yml ]"
    kind: negative

  - id: C-10
    text: "Each of the two documents SHALL read as a coherent whole rather than as one document cut in half, judged by someone who did not write them."
    verify: human
    kind: nonfunctional

out_of_scope:
  - rebuilding the contract runner
  - generating rule excerpts, and any change to the claude-config repository
  - hooks, agents, skills, plugin packaging
  - evidence visualization and code anchors
  - changing what the review rules say — this moves them, it does not revise them
---

# split-review-gate

## Background

Doc 09 carries six unrelated subjects in 118 lines, and one of them — the review gate — is the
only part that names vendor CLIs and model selection. It decays on a different clock from
everything around it, which is the same argument that separated doc 11 from doc 10.

The split also fixes a cross-reference that broke when doc 09's research-tools section was
removed: §3 still points at "§6" for lightweight iteration, and doc 09 now ends at §5. `C-06`
catches that class of error rather than the single instance.

## What moves

To doc 20: the verification gates section entire — author-versus-verifier, runnable checks,
evidence-based completion, the lane definition table, fan-in, vendor diversity, and both review
tool paths. Six of doc 09's Core Rules move with it.

Doc 09 keeps: instruction files, decomposition and worktree isolation, merge and integration,
model routing, spec gating.

## References to redirect (C-05)

Four point at review content and move to doc 20: `06` (verifier is not the author), `15` (the
code-to-doc check in the review gate), `18` §2 (lane set by done level), and `CLAUDE.md` (fresh
-context review lanes). One splits: `18`'s closing line names decomposition, isolation, review
lanes, and model routing together.

The rest stay — `01` (×3), `12`, `14`, `README` ×2 — because they point at instruction files,
decomposition, or delegation.

## Notes

`C-04` is the criterion that makes this a move rather than a copy. A rule left behind in doc 09
would drift against its twin in doc 20, which is the failure the split is supposed to prevent.

Nothing here revises what the review rules say. Changing them while relocating them would make
the diff unreviewable.
