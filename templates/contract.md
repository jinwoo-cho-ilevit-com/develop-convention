---
# Work contract. Front matter is machine-readable; the body below is for humans.
# Full rules: <CONVENTION_PATH>/conventions/18-work-contract.md
#
# YAML notes that bite in practice:
#   - Quote anything starting with `*` or `&`: `owns: ["src/loader/**"]`, not `[*.py]`
#   - Quote any command containing `:` or `#`: verify: "pytest -k 'a: b'"
#   - Use a block scalar for multi-line commands:
#       verify: |
#         uv run python -m tool --flag
#   - A bare `---` in the body ends the front matter. Use `***` for a horizontal rule.

schema_version: 1
feature: [short-slug]

# auto      = criteria pass only (docs, formatting, behaviour-preserving refactor)
# reviewed  = + zero confirmed blockers from a non-authoring review   <- default
# proven    = + integration smoke + one run on real data
# bypassed  = a gate was skipped; `revision.reason` is then required
# Choose by size x reversibility, not size alone.
done_level: reviewed

# Commit the work starts from. Required when adding tests (red check runs against it).
base: [git-sha]

criteria:
  - id: C-01
    # EARS: WHEN <trigger> THE <system> SHALL <response>
    # or Given-When-Then. Judgment test: could two agents disagree? Then rewrite.
    text: "WHEN [trigger], THE [system] SHALL [observable response]."
    verify: "[executable command]"
    kind: functional          # functional | nonfunctional | negative
    hermetic: true            # false = touches network/db/ports; excluded from red check

  - id: C-02
    text: "THE [system] SHALL NOT [thing that must not happen]."
    verify: "[executable command]"
    kind: negative            # at least one negative criterion; it is what stops over-building
    hermetic: true

  - id: C-03
    text: "[judgment a machine cannot make]"
    verify: human             # blocks completion until a verdict is recorded
    kind: nonfunctional

out_of_scope:
  - [what this work deliberately does not do]

# ---- Fields below are optional. Fill only what the work triggers. ----

# Two or more parallel lanes only. `owns` must be disjoint directory prefixes.
# lanes:
#   - id: A
#     owns: ["src/loader/"]
#     criteria: [C-01, C-02]
#     model_tier: mid          # light | mid | top -- tier only, never a model id
#     state: active            # active | abandoned (abandoned needs a reason in the body)

# Single-owner resources. Never assigned to a lane.
# sequential_owner: ["pyproject.toml", "uv.lock", "migrations/"]

# integration:
#   owner: A
#   order: [A, B]
#   criteria: [C-04]

# When a plan-versus-diff review should fire.
# checkpoints:
#   - after: C-02
#     check: [drift]

# Evidence wanted but whose format is not specified yet. Records intent, defers form.
# evidence_todo: [distribution-before-after]

# Set when the frozen contract changes.
# revision:
#   kind: additive             # additive | narrowing | breaking
#   reason: "[why]"
---

# [feature]

## Background

[What problem this solves, and what happens if it is not done.]

## Approach

[How, in a few lines. Reference criteria by id; do not restate their text here —
a contract that repeats itself drifts inside one file.]

## Notes

[Assumptions being made, anything deliberately left open, why a lane was abandoned.]
