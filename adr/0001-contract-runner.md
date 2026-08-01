# 0001. The contract runner

Status: accepted (2026-08-01)

## Context

Conventions 18 and 19 fix what a work contract and its evidence must contain, but nothing enforced them. A first runner was built and withdrawn (`a078b30`) after four review lanes found seven blockers, among them a phase that overwrote another's record and a status gate that passed a criterion with no red check behind it. This is the rebuild, and these are the decisions it made that outlive it.

## Decisions

### 1. Refuse what is not implemented, rather than ignore it

`lanes`, `sequential_owner`, `integration`, `checkpoints`, `hermetic: false`, `evidence_todo` and `done_level: bypassed` are all defined by 18 or 19, and all refused with exit `2`, each naming the field.

*Alternatives:* ignore them silently, which is what the first runner did; or implement them, which was out of scope.

*Consequence:* a contract using a documented feature this runner lacks is unusable rather than partly enforced. The failure mode being prevented is an author believing a field is enforced when nothing reads it. `done_level: bypassed` is the sharpest case — 18 and 19 both require a bypass to carry a reason, and a runner that took the level while recording no reason reported a clean gate over the state 18 calls the blocker.

### 2. `verify` is one string, lexed once, and an argument made only of shell punctuation is refused

Refused whether or not the author quoted it. After splitting, someone who wanted a literal `;` and someone who expected a shell have written the same argument.

*Alternatives:* a quote-aware rule that reads the unsplit text as well as the arguments. It was implemented and it failed three separate ways — it split `--format='%h|%s'` at the attached quote and refused a working command, it scored a backslash-escaped `\;` as bare, and on one input its second lexer raised where the real one did not, whereupon the `except ValueError` swallowed the check entirely and an unquoted `&&` reached the program. Two parsers over one string have a degree of freedom that is not worth its expressiveness.

*Consequence:* `find … -exec … ';'` goes in a script. A `verify` list form, taken verbatim with nothing to parse, would remove this whole class and is the recommended follow-up.

### 3. A review lane judging code must execute, and its verdict is weighted by what it ran

Measured on identical text at the same commit: a read-only lane returned PASS with zero findings; an executing lane returned ten, one of them a violation of a Core Rule. Across eleven rounds, 585 runner invocations, every defect that mattered was found by execution and none by reading.

*Consequence:* a judgment about code carries the number of commands the judge actually ran, and a lane that ran none says so instead of returning a verdict.

### 4. When a defect class recurs, characterize the shape instead of enumerating the forms

The same class appeared five times: reading the runner kind from a substring of the command; `SHELL_TOKENS` listing operators and missing the merged `>&`; `hermetic is False` missing `"false"`; the newline check spelling `"\n"` and missing `"\r"`; the report cell escaping `|` and missing the line break. Every fix that enumerated was later breached; every fix that derived the rule from the mechanism held — `LINE_SEPARATORS` from `shlex`'s own whitespace set, a table cell that collapses all whitespace rather than escaping chosen characters.

### 5. Prose describing code is written from the code, and that ordering is a review device

C-10 is a documentation criterion. It found a code defect: a red check that read the word `SyntaxError` out of pytest's output and turned an ordinary failure into a permanently unpassable criterion. The defect had been accepted knowingly in planning; writing the behaviour into a sentence is what exposed that no reason for it survived.

## Consequences and what was not settled

Eleven review rounds did not converge. Findings per round were 5, 6, 3, 3, 1, 3. What changed was their kind: rounds 5–8 found gates opening wrongly or criteria blocked forever; rounds 9–11 found table rendering, error-message formatting and imprecise sentences. The loop was stopped on that observation, not on an empty round — and two thirds of rounds 7 and 8's findings had been introduced by the previous round's fix, so a fix rate is itself a defect source.

Deferred to a follow-up contract, each with a reason recorded here rather than in the deleted contract:

- a list form for `verify`, which removes decision 2's whole class
- `verify_runs[].at` and `review_rounds`, which 19 §4 mandates and this runner omits; `manifest.json` is rewritten whole from a state directory holding only the latest record per criterion and phase, so an accumulating list has no source
- recording a bypass and its reason, which would let decision 1 accept `done_level: bypassed`
- 18's rule restricting `owns` to disjoint directory prefixes, which three independent review lanes found unworkable on a real repository: cross-cutting single files (`README.md`, `.gitignore`, `mkdocs.yml`) cannot be assigned
- the absence of a stopping rule for the pre-execution gate. Three rounds ran; the first two did not converge (9 blockers then 8, with majors rising from 8 to 24) and the third converged only because the blocker definition was narrowed mid-flight, by a rule written nowhere
- config surface, concurrency, resumption, artifact retention, and publishing this ADR directory through the mkdocs build
