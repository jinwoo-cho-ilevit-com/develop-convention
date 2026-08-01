---
schema_version: 1
feature: doc-consistency-and-density
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
    text: "WHEN a document or comment is edited, THE conventions SHALL state that accumulated edits are replaced by a rewrite past a size threshold, and SHALL forbid narrating change history in body text."
    verify: "sed -n '/^## Core Rules/,/^## Details/p' conventions/01-structure-naming.md | grep -qi 'rewrite'"
    kind: functional

  - id: C-04
    text: "THE conventions SHALL define three test layers including a project-level end-to-end smoke, with stated conditions for what counts as end-to-end."
    verify: "grep -qi 'end-to-end' conventions/06-testing-verification.md && grep -qi 'entry point' conventions/06-testing-verification.md"
    kind: functional

  - id: C-05
    text: "THE planning method SHALL be expressed as answerable questions and start signals, and no planning-depth dial SHALL remain."
    verify: "! grep -rq 'plan_depth' conventions/ README.md templates/ && grep -q 'start signal' conventions/18-work-contract.md"
    kind: functional

  - id: C-06
    text: "THE review-lane rules SHALL forbid switching branches in a shared worktree and SHALL require naming the tool version a finding was tested against."
    verify: "grep -qi 'worktree' conventions/09-agentic-workflow.md && grep -qi 'version you tested' conventions/09-agentic-workflow.md"
    kind: functional

  - id: C-07
    text: "THE seven unresolved documentation findings listed in the body SHALL each be resolved."
    verify: "! grep -q 'Using Research Tools' conventions/09-agentic-workflow.md && ! grep -q 'toolkit version' conventions/19-evidence.md && ! grep -q 'llm-api-research' conventions/10-llm-api-inference.md"
    kind: functional

  - id: C-08
    text: "THE combined length of the convention documents, README, and CLAUDE.md SHALL NOT exceed the 1798-line baseline, and no single convention document SHALL exceed 120 lines."
    verify: "t=$(cat conventions/*.md README.md CLAUDE.md | wc -l); [ \"$t\" -le 1798 ] && ! wc -l conventions/*.md | grep -qE '^ *(1[2-9][0-9]|[2-9][0-9]{2})[0-9]* conventions'"
    kind: nonfunctional

  - id: C-09
    text: "THE change SHALL NOT add a new convention document."
    verify: "[ \"$(ls conventions/*.md | wc -l)\" -eq 20 ]"
    kind: negative

  - id: C-10
    text: "THE change SHALL NOT add code or build configuration."
    verify: "! ls pyproject.toml uv.lock .pre-commit-config.yaml 2>/dev/null | grep -q . && [ ! -d templates/scripts ] && [ ! -f .github/workflows/checks.yml ]"
    kind: negative

  - id: C-11
    text: "The rewritten documents SHALL read more clearly than what they replace, judged by someone who did not write them."
    verify: human
    kind: nonfunctional

out_of_scope:
  - splitting doc 09 into a separate review-gate document
  - rebuilding the contract runner
  - generating rule excerpts, and any change to the claude-config repository
  - hooks, agents, skills, plugin packaging
  - evidence visualization and code anchors
---

# doc-consistency-and-density

## Background

Three rules are missing and one is broken. Comments and documents accumulate because the
conventions say how to write them but not how to edit them. Testing rules cover modules but
never the assembled project. The planning method rests on a self-reported dial that cannot be
checked and whose two extremes are written identically.

Alongside those, a review of the previous change left seven documentation findings unresolved
and eleven prunings identified in the existing conventions. All of it is document editing, and
the items overlap enough that doing them separately means editing the same sections three times.

This work is also the first application of the rule it introduces: sections that have grown by
accretion get rewritten rather than extended. `C-08` is what makes that real — three rule sets
are being added and the total must not grow.

## The seven unresolved findings (C-07)

1. Doc 19 specifies `duration`, a masked flag, working-tree cleanliness, GPU presence, and a
   toolkit version, none of which anything produces. Narrow the spec to what is actually required.
2. Doc 19 says to scan the artifacts directory before committing it; conv-init says to gitignore
   it. Decide once.
3. Doc 18 says a contract is archived on completion without saying where or how.
4. Doc 18's Core Rules state "write before development and freeze" unconditionally; the
   reconciliation with doc 09 §6 (lightweight iteration for small work) exists only in Details,
   so the excerpted rules still read as a conflict.
5. Docs 06 and 19 both carry the NO-BASELINE distinction in their Core Rules.
6. Doc 09's decomposition table and doc 18's `lanes[]` are two registers of the same information
   with no stated primary.
7. `templates/pyproject.toml` declares a pre-commit dependency, but templates carry neither a
   pre-commit config nor a CI workflow, so a bootstrapped project cannot satisfy doc 03's
   two-stage check.

## Overlap to avoid

Doc 01 already forbids narrating write history in comments (`01:58`). The new editing rule extends
that to documents and adds the size threshold; restating the comment half would violate the rule
it introduces.

## The eleven prunings

Doc 09 §4 (restates 00/12/16) · doc 01's PEP 8 enumeration · doc 13 §3 (ten lines saying no code
change is needed) · doc 15's fitness-test pilot · doc 02's run-naming rule (move to Details) ·
doc 00 Core Rule 7 (merge into 2) · doc 14's compaction walkthrough (vendor manual, keep one
line) · doc 10's in-house incident anecdote (replace with a public source) · doc 15 §6 (competition
analysis asserting a negative without enumeration) · docs 03 and 07's RunPod-specific wording ·
the README rule summary, which has already drifted from the documents it summarizes.

Doc 15 §6 cannot move to `docs/adr/` — that path is gitignored. Keep it in `conventions/` or drop it.

## Notes

`C-08`'s 120-line ceiling forces docs 09 (122) and 18 (134) to be rewritten rather than extended.
That is the intent: both grew by accretion, and 18 in particular now exceeds the document it was
split out to avoid bloating.

`C-11` is a human judgment and blocks completion until answered. Nobody can settle whether prose
reads better by running a command.
