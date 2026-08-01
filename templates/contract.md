---
# Work contract. Front matter is machine-readable; the body below is for humans.
# Full rules: <CONVENTION_PATH>/conventions/18-work-contract.md
#
# YAML notes that bite in practice:
#   - Bracketed placeholders below are quoted on purpose: a bare `[short-slug]` parses as a
#     one-element list, not a string, and silently becomes the literal `['short-slug']`.
#   - Quote anything starting with `*` or `&`. `owns` takes directory prefixes, not globs:
#     `owns: ["src/loader/"]` — a glob such as `src/**` is rejected.
#   - Quote any command containing `:` or `#`: verify: "pytest -k 'a: b'"
#   - Use a block scalar for multi-line commands:
#       verify: |
#         uv run python -m tool --flag
#   - A bare `---` in the body ends the front matter. Use `***` for a horizontal rule.

schema_version: 1
feature: "[short-slug]"

# auto      = criteria pass only (docs, formatting, behaviour-preserving refactor)
# reviewed  = + zero confirmed blockers from a non-authoring review   <- default
# proven    = + integration smoke + one run on real data
# bypassed  = a gate was skipped; requires the `bypass` block below, and is refused
#             without it — an unrecorded bypass is the blocker, not the bypass
# Choose by size x reversibility, not size alone.
done_level: reviewed

# Commit the work starts from. Required when adding tests (red check runs against it).
base: "[git-sha]"

criteria:
  - id: C-01
    # EARS: WHEN <trigger> THE <system> SHALL <response>
    # or Given-When-Then. Judgment test: could two agents disagree? Then rewrite.
    text: "WHEN [trigger], THE [system] SHALL [observable response]."
    verify: "[executable command]"
                              # A string is split into arguments, and one made only of
                              # shell punctuation is refused. Write a list instead when an
                              # argument has to be a literal `;` or `|`:
                              #   verify: [find, ., -exec, echo, "{}", ";"]
                              # A list is the argument vector, taken verbatim.
    runner: pytest            # pytest | command -- declared, never guessed from the command
                              # text. Required unless `verify: human`.
    kind: functional          # functional | nonfunctional | negative
    hermetic: true            # the only value scripts/contract.py accepts; it refuses any
                              # other, because it implements no exemption behind it.
                              # For an invariant that holds at base, use `red: guard`
    red: required             # required = must fail at base
                              # guard    = standing invariant that legitimately holds at base

  - id: C-02
    text: "THE [system] SHALL NOT [thing that must not happen]."
    verify: "[executable command]"
    runner: command
    kind: negative            # at least one negative criterion; it is what stops over-building
    hermetic: true

  - id: C-03
    text: "[judgment a machine cannot make]"
    verify: human             # blocks completion until a verdict is recorded
    kind: nonfunctional

# Only with done_level: bypassed. Reaches manifest.json, so the decision has a record.
# bypass:
#   reason: "[why the gate was skipped]"
#   author: "[who decided]"

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
