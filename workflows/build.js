export const meta = {
  name: 'dev-harness-build',
  description: 'Lane engine behind /dev-harness:build — not the entry point. Run the command instead; this refuses unless the boundaries were already frozen',
  phases: [
    { title: 'Develop', detail: 'one worktree-isolated agent per lane' },
    { title: 'Review', detail: 'review, fix and recheck — per lane, no barrier' },
  ],
}

// A lane that keeps producing blockers is not a lane that needs more rounds
// (→ conventions/20-review-gate.md). The cap is a runaway guard, not an exit.
const ROUND_CAP = 5

// Pinned so freeze checks and lane criteria run the same tool version against a
// boundary's schema (→ conventions/06-testing-verification.md).
const SCHEMA_CHECK = 'uvx check-jsonschema@0.38.0'

const DEVELOP_SCHEMA = {
  type: 'object',
  required: ['worktree', 'branch', 'head', 'criteria'],
  additionalProperties: false,
  properties: {
    worktree: { type: 'string', description: 'absolute path of the worktree you worked in' },
    branch: { type: 'string' },
    head: { type: 'string', description: 'the commit sha on your lane branch after your work' },
    criteria: {
      type: 'array',
      items: {
        type: 'object',
        required: ['criterion', 'command', 'passed'],
        additionalProperties: false,
        properties: {
          criterion: { type: 'string' },
          command: { type: 'string', description: 'empty for a [human] criterion' },
          passed: { type: 'boolean' },
          output: { type: 'string' },
        },
      },
    },
  },
}

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['findings', 'commandsRun'],
  additionalProperties: false,
  properties: {
    commandsRun: { type: 'integer', description: 'how many commands you actually executed' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['file', 'severity', 'summary', 'causedByPreviousFix'],
        additionalProperties: false,
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          summary: { type: 'string' },
          failureScenario: { type: 'string' },
          causedByPreviousFix: {
            type: 'boolean',
            description: 'true only if this defect is in code the previous round\'s fix introduced or changed',
          },
        },
      },
    },
  },
}

const FIX_SCHEMA = {
  type: 'object',
  required: ['summary'],
  additionalProperties: false,
  properties: {
    summary: { type: 'string' },
  },
}

// What the fix changed is measured by an agent that did not do the fixing. The fixer is
// never asked, because an actor reporting on its own work is not evidence about it.
const TOUCHED_SCHEMA = {
  type: 'object',
  required: ['files', 'head'],
  additionalProperties: false,
  properties: {
    files: { type: 'array', items: { type: 'string' }, description: 'repository-relative paths, verbatim from the commands' },
    head: { type: 'string', description: 'the sha printed by git rev-parse HEAD' },
  },
}

const FROZEN_SCHEMA = {
  type: 'object',
  required: ['missing', 'head', 'tool', 'checked'],
  additionalProperties: false,
  properties: {
    missing: {
      type: 'array',
      items: { type: 'string' },
      description: 'only the given paths that do not exist; a path that exists is left out entirely',
    },
    head: { type: 'string', description: 'the sha printed by git rev-parse HEAD after the reset' },
    tool: {
      type: 'object',
      required: ['exit', 'output'],
      additionalProperties: false,
      description: 'exit code and verbatim output of `SCHEMA_CHECK --version`',
      properties: {
        exit: { type: 'integer' },
        output: { type: 'string' },
      },
    },
    checked: {
      type: 'array',
      description: 'exactly one row per boundary that declares a schema; [] if none does',
      items: {
        type: 'object',
        required: ['boundary', 'exit', 'output'],
        additionalProperties: false,
        properties: {
          boundary: { type: 'string' },
          exit: { type: 'integer' },
          output: { type: 'string' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['verdicts'],
  additionalProperties: false,
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['key', 'confirmed', 'evidence'],
        additionalProperties: false,
        properties: {
          key: { type: 'string', description: 'the finding key exactly as it was given to you' },
          confirmed: { type: 'boolean' },
          evidence: { type: 'string', description: 'what you ran or read that decided it' },
        },
      },
    },
  },
}

// A lane is defined by its input, not by its attitude — three reviewers told to
// "be critical" over the same input return the same findings three times (→ 20).
const REVIEW_LENSES = [
  { key: 'module', input: 'the diff and the files it changed' },
  { key: 'project', input: 'the diff plus its callers and callees, and the convention docs it must satisfy' },
  { key: 'absence', input: 'the lane brief and the diff — hunt for what the brief requires and the diff omits' },
]

// Added only for a lane the plan declares `security: true` — one that touches auth, secrets
// or external input (→ 20 Core Rules). The declaration is the only source; paths are not read
// for it, because a name that looks like a trust boundary is not one and the reverse is worse.
const SECURITY_LENS = {
  key: 'security',
  input: 'the diff, its trust boundaries, and every point where it accepts input it did not produce',
}

// One finding is one defect wherever it was seen, and the same key identifies it across
// rounds — which is what makes repetition measurable without asking a reviewer.
const keyOf = (f) => `${f.file}:${f.line ?? ''}:${f.summary}`

// A reviewer writes `./src/a.py` where the fixer writes `src/a.py` or an absolute path
// inside the worktree, and a plain string compare then finds nothing in common. That fails
// safe — an unmatched claim never halts — but it disables the causation rule entirely and
// says nothing while doing it.
function repoPath(p, worktree) {
  let out = String(p ?? '').replace(/\\/g, '/')
  if (worktree) {
    const root = String(worktree).replace(/\\/g, '/').replace(/\/+$/, '')
    if (out === root) return ''
    if (out.startsWith(root + '/')) out = out.slice(root.length + 1)
  }
  return out.replace(/^\.\//, '').replace(/^\/+/, '')
}

function dedupe(findings) {
  const seen = new Set()
  return findings.filter((f) => (seen.has(keyOf(f)) ? false : (seen.add(keyOf(f)), true)))
}

const isPlainObject = (v) => typeof v === 'object' && v !== null && !Array.isArray(v)
// A lane name keys a brief path and a branch, so it may not carry a separator or traverse.
const LANE_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]*$/
const isText = (v) => typeof v === 'string' && v !== ''
// Both lists this validates decide something by being non-empty — which paths a lane may
// touch, and which lanes a boundary pins. An empty one reads as "no restriction" and as
// "pins nobody", neither of which any plan means to say.
const isTextList = (v) => Array.isArray(v) && v.length > 0 && v.every(isText)

// The whole argument contract, in one place. A key absent from a list is a key nothing reads,
// so an object carrying it is a typo the caller has no other way to see. Guarding field by
// field as each one surfaced left the next one down unchecked every time.
const ARG_FIELDS = [
  ['planDir', isText, 'a non-empty string'],
  ['base', isText, 'a non-empty string'],
  ['conventionsDir', isText, 'a non-empty string'],
  ['lanes', Array.isArray, 'a list of lane objects'],
  ['boundaries', Array.isArray, 'a list of boundary objects'],
  // Type only. Whether it is true is policy, refused separately below in its own words.
  ['boundariesFrozen', (v) => typeof v === 'boolean', 'a boolean'],
]
const LANE_FIELDS = [
  ['name', (v) => isText(v) && LANE_NAME.test(v), `a name matching ${LANE_NAME.source}`],
  ['owns', isTextList, 'a non-empty list of path strings'],
  ['security', (v) => typeof v === 'boolean', 'a boolean'],
]
const BOUNDARY_FIELDS = [
  ['name', isText, 'a non-empty string'],
  ['contract', isText, 'a path string'],
  ['sample', isText, 'a path string'],
  ['schema', isText, 'a path string'],
  ['lanes', isTextList, 'a non-empty list of lane names'],
]

// Returns the sentence naming what is wrong, or null. `where` is what the caller has to look
// at, so it carries the index of the element rather than just the field.
function checkShape(value, where, fields, required = []) {
  if (!isPlainObject(value)) {
    return `${where} is ${JSON.stringify(value) ?? String(value)}, not an object`
  }
  const known = fields.map(([k]) => k)
  for (const key of Object.keys(value)) {
    if (!known.includes(key)) {
      return `${where} carries an unknown key ${JSON.stringify(key)} — nothing reads it, so it is a typo for one of: ${known.join(', ')}`
    }
  }
  for (const [key, ok, expectation] of fields) {
    if (key in value && !ok(value[key])) {
      return `${where}.${key} is ${JSON.stringify(value[key])}, and must be ${expectation}`
    }
  }
  for (const key of required) {
    if (!(key in value)) return `${where} declares no ${key}`
  }
  return null
}

// The arguments can reach the script as JSON text rather than as the value that was passed,
// so parse before reading any field. Whatever the text turns out to encode is then judged by
// the same guards below as a value that arrived without the encoding.
let input = args
let parseError = null
if (typeof input === 'string') {
  try {
    input = JSON.parse(input)
    log('args arrived as JSON text and were parsed before use.')
  } catch (err) {
    parseError = err instanceof Error ? err.message : String(err)
  }
}
// Text carrying no argument is the argument-less invocation, and needs its instruction, not a
// complaint about shape.
if (typeof input === 'string' && input.trim() === '') input = undefined

const planDir = input?.planDir ?? '.plans'
// The conventions travel with the plugin, not with the project the lanes run in, so the
// absolute path has to be handed in — a bare `conventions/…` resolves to nothing there.
const conventionsDir = input?.conventionsDir ?? 'conventions'
// The commit the reviewers diff against and every lane is told to reset to. A worktree is
// cut from `origin/main`, so nothing else puts a lane on this commit.
const base = input?.base ?? 'main'
const lanes = input?.lanes ?? []
const boundaries = input?.boundaries ?? []

// Nothing can be read off a value that is not an object, so the frozen check below would
// refuse in the name of a freeze that may well have happened.
if (input !== undefined && !isPlainObject(input)) {
  log('args did not arrive as an object. Nothing can be read from it.')
  return {
    lanes: [],
    note:
      'refused: the arguments did not arrive as an object, so every field including boundariesFrozen read as undefined.' +
      // Without the parser's own words, text that is merely malformed is indistinguishable
      // from a scalar, and the note tells its caller to do what they already did.
      (parseError ? ` They arrived as text that does not parse as JSON: ${parseError}.` : '') +
      ' Pass { planDir, base, lanes, boundaries, conventionsDir, boundariesFrozen } as an object, or as JSON text encoding one. This is not a reason to hardcode boundariesFrozen.',
  }
}

// One pass, before anything reads a field into a prompt, a path or a git command. Parsing
// recovers only the top level, so a field that arrived as text of its own is still text and
// every level below the top is checked here rather than where it is used.
const complaint =
  // An argument-less call has no shape to be wrong. It belongs to the freeze gate below,
  // whose note is the one that names the command to run instead.
  (input === undefined ? null : checkShape(input, 'args', ARG_FIELDS, ['lanes'])) ??
  lanes.map((l, i) => checkShape(l, `args.lanes[${i}]`, LANE_FIELDS, ['name', 'owns', 'security'])).find(Boolean) ??
  boundaries.map((b, i) => checkShape(b, `args.boundaries[${i}]`, BOUNDARY_FIELDS, ['lanes', 'contract', 'sample'])).find(Boolean) ??
  // Two lanes of one name share a brief, a branch and every label, and the second silently
  // becomes indistinguishable from the first in the results.
  (new Set(lanes.map((l) => l?.name)).size !== lanes.length ? 'args.lanes declares the same name twice' : null) ??
  // A `checked` row below keys a schema result by boundary name, so two boundaries of the
  // same name could not be told apart in it.
  boundaries
    .map((b, i) => (boundaries.findIndex((x) => x?.name === b?.name) !== i ? `args.boundaries[${i}] repeats the name ${JSON.stringify(b?.name)}` : null))
    .find(Boolean) ??
  // A boundary names the lanes it pins, and a pinned lane is reviewed through three lenses
  // instead of one. A name matching no lane buys the shallower review and says nothing.
  boundaries
    .flatMap((b, i) =>
      (b.lanes ?? []).map((n, j) =>
        lanes.some((l) => l.name === n) ? null : `args.boundaries[${i}].lanes[${j}] is ${JSON.stringify(n)}, which no lane declares`,
      ),
    )
    .find(Boolean)

if (complaint) {
  log(`${complaint}.`)
  return {
    lanes: [],
    note: `refused: ${complaint}. Every lane brief, review prompt and git command is built from these fields, so one that is not what it claims reaches an agent rather than this message.`,
  }
}

// What every prompt below is built from, once, so a run can be reconstructed from its log
// rather than from the arguments nobody kept.
log(`base ${base}, plans in ${planDir}, conventions in ${conventionsDir}, ${lanes.length} lane(s), ${boundaries.length} boundary(ies)`)

// One contract file and sample per boundary, owned by no lane, is written before fan-out —
// that is what holds the interfaces still while every lane edits at once. Invoking this
// workflow directly skips it, so the caller has to declare it happened.
if (input?.boundariesFrozen !== true) {
  log('Boundaries are not frozen. Run /dev-harness:build instead of invoking this workflow.')
  return {
    lanes: [],
    note: 'refused: boundariesFrozen was not true. /dev-harness:build writes one contract file and sample per boundary, owned by no lane, before fanning out; invoking this workflow directly skips that and lets the lanes move the interfaces they are working against.',
  }
}

if (!lanes.length) {
  log('No lanes in args. Nothing to build.')
  return { lanes: [], note: 'no lanes supplied' }
}

// Three lanes when the change spans modules or pins an interface, one otherwise, plus a
// security lens for a lane the plan declared `security: true` (→ 20 §2).
function lensesFor(lane) {
  const spansModules = (lane.owns ?? []).length > 1
  const pinsInterface = boundaries.some((b) => (b.lanes ?? []).includes(lane.name))
  const base = spansModules || pinsInterface ? REVIEW_LENSES : [REVIEW_LENSES[0]]
  return lane.security === true ? [...base, SECURITY_LENS] : base
}

// Every lane-scoped agent needs its own boundaries' exact paths, not a directory to go browse —
// a lane pointed at a directory reads the wrong file, or treats a contract as something to run.
// Empty for a lane on no boundary, since it has nothing to be told.
function boundaryContracts(lane) {
  const mine = boundaries.filter((b) => (b.lanes ?? []).includes(lane.name))
  if (!mine.length) return ''
  const withSchema = mine.filter((b) => b.schema)
  return [
    "Your boundaries' contracts are files, not tests — owned by no lane, never edit them or their samples:",
    ...mine.map((b) => `- ${b.name}: contract ${b.contract}${b.schema ? `, schema ${b.schema}` : ''}, sample ${b.sample}`),
    "The consumer side runs its sample run on the sample. The producer's own output is checkable",
    "against the schema; only the other side's code is absent, and the whole boundary is exercised",
    'after the merge.',
    ...(withSchema.length
      ? [
          'Where a boundary above has a schema, the lane producing its payload carries a criterion',
          'that deletes its dump directory, re-runs its sample run, and checks the fresh dump with',
          `\`${SCHEMA_CHECK} --schemafile <schema> <dump>\`, using that boundary's schema path.`,
        ]
      : []),
  ].join('\n')
}

function developPrompt(lane) {
  const contracts = boundaryContracts(lane)
  return [
    `Before anything else, run \`git reset --hard ${base}\` in your worktree, then \`git log --oneline -1\``,
    'and confirm you are on that commit.',
    `Your worktree is cut from origin/main, which may be behind ${base} and may carry neither the frozen`,
    `boundary files nor the lane briefs under ${planDir}.`,
    '',
    `You own lane "${lane.name}". Read ${planDir}/lane-${lane.name}.md and ${planDir}/PLAN.md.`,
    '',
    `Work only inside your owned paths: ${(lane.owns ?? []).join(', ')}.`,
    'Every other path belongs to another lane running right now; touching one collides.',
    ...(contracts
      ? [
          contracts,
          'Build your side to match the contract file: the names and signatures the caller uses, and',
          'the call direction. Where a boundary above has a schema, that schema decides its fields,',
          'types and values — match it exactly. Where it does not, emit or accept exactly the value',
          'set the contract file names.',
        ]
      : []),
    "Your own checks are the brief's completion criteria; where your stage reads a frozen sample, read it and never write it.",
    '',
    'Create a branch for this lane, commit your work to it, and run every command listed under',
    'the brief\'s completion criteria. Update the AGENTS.md of each directory you own in the same pass',
    `(→ ${conventionsDir}/15-doc-tracking.md).`,
    '',
    'Return the absolute path of the worktree you worked in — later rounds continue in it — and the',
    'commit sha on your lane branch after your work, which is the baseline the first round measures from.',
    'Report each criterion with the command you ran and whether it passed. A [human] criterion has no',
    'command: report it as not passed and leave the command empty.',
  ].join('\n')
}

function reviewPrompt(lane, lens, round, fixSummary) {
  const contracts = boundaryContracts(lane)
  return [
    `Review lane "${lane.name}" through one lens only: ${lens.key}.`,
    `Your input is ${lens.input}.`,
    `cd into ${lane.worktree} before running anything — that is where this lane's work is.`,
    'Running the test command anywhere else tests a tree without the change and reports it as your verdict.',
    '',
    `Read the change with \`git diff ${lane.base}..${lane.branch}\` and \`git show ${lane.branch}:<path>\`,`,
    `and its commit messages with \`git log ${lane.base}..${lane.branch}\` — a bug fix's reproduction lives in its ## Result.`,
    "Never switch branches in a shared worktree — one checkout erases every other lane's subject.",
    '',
    "You did not write this code and you do not get the author's reasoning. Judge the diff against",
    `${planDir}/lane-${lane.name}.md and the convention docs in ${conventionsDir}/.`,
    '',
    'Run the code. You have the test command and the tool under review; report how many commands you',
    'actually executed. A verdict from a lane that ran none is a reading, not a review.',
    ...(contracts
      ? [
          contracts,
          "Compare this lane's side against each contract file listed — names, signatures, call",
          'direction. Where a boundary has a schema, that schema decides its fields, types and',
          'values; where it does not, compare the value set the contract file names. A mismatch is a',
          "finding; the other side's absence is not. A producing lane on a boundary with a schema",
          'whose brief or report lacks the schema check is a finding.',
        ]
      : []),
    '',
    'Flag correctness and requirement gaps only. Do not manufacture problems in sound code.',
    round > 1
      ? `This is round ${round}. The previous round's fix was:\n${fixSummary}\nFor each finding, set causedByPreviousFix to true only when the defect is in code that fix introduced or changed.`
      : 'This is round 1, so causedByPreviousFix is false for every finding.',
  ].join('\n')
}

function verifyPrompt(lane, blockers) {
  const contracts = boundaryContracts(lane)
  return [
    `Check each claimed blocker in lane "${lane.name}" against the actual code. You are not`,
    'reviewing the change and you are not looking for new problems — you are deciding whether',
    'each of these is real.',
    `Work in ${lane.worktree} on branch ${lane.branch}.`,
    '',
    blockers.map((b) => `- key: ${keyOf(b)}\n  claim: ${b.summary}\n  scenario: ${b.failureScenario ?? '(none given)'}`).join('\n'),
    '',
    'Reproduce it, or read the code path and show it cannot happen. Return one verdict per key,',
    'with the key copied exactly, and say what you ran or read.',
    ...(contracts ? [contracts] : []),
    '',
    'A finding with no concrete failing scenario is not confirmed. Reviewers asked to find problems',
    'manufacture them in sound code, and an unconfirmed blocker forces a fix that then shows up as',
    'the next round\'s regression signal.',
  ].join('\n')
}

function fixPrompt(lane, blockers) {
  const contracts = boundaryContracts(lane)
  return [
    `You own lane "${lane.name}". Continue in the worktree you already have: ${lane.worktree}.`,
    'Review found these blockers. Fix them and commit to the same lane branch.',
    '',
    blockers.map((b, i) => `${i + 1}. [${b.file}${b.line ? ':' + b.line : ''}] ${b.summary}`).join('\n'),
    '',
    'Fix only these. Anything else you notice goes in your summary, not in the diff — an unrelated',
    'change here forces the whole lane through another review round.',
    'Re-run the criteria commands from your brief before returning.',
    ...(contracts ? [contracts] : []),
    '',
    'Return a short summary of what you changed.',
  ].join('\n')
}

// The measurement the causation rule runs on. Its whole job is to read git and copy the
// answer out, so it is dispatched separately from the fix — a fixer reporting which files
// it touched is the actor grading itself, and under- or over-reporting either hides a real
// regression or halts a lane over a pre-existing blocker.
function touchedPrompt(ctx, since) {
  return [
    `Report which files changed in the worktree ${ctx.worktree}. Work there and nowhere else.`,
    '',
    'Run exactly these three commands:',
    `1. git --no-pager diff --name-only ${since}`,
    '2. git ls-files --others --exclude-standard',
    '3. git rev-parse HEAD',
    '',
    'Return the union of the first two as `files` and the output of the third as `head`.',
    'The diff is taken against the working tree on purpose, so a fix that was never committed',
    'still counts.',
    '',
    'Change nothing and judge nothing. Report every path exactly as the commands printed it,',
    'without filtering to what looks relevant — the next round decides whether a defect is',
    'fix-induced by matching against this list.',
  ].join('\n')
}

// The one place a lane leaves the loop without a blocker, so the human-verdict check
// cannot be added to one exit and missed on the other — which is how a lane awaiting a
// verdict reached `passed` from the early return while the late one held it back.
function clean(lane, dev, ctx, round, carried) {
  // A `[human]` criterion has no command and is reported not-passed by construction.
  // Putting the lane in `passed` makes the caller merge it and ask for the verdict
  // afterwards, which is the order 19 forbids: PENDING-HUMAN blocks completion, and a
  // merged lane is past the point where a rejection can act.
  const awaiting = (dev.criteria ?? []).filter((c) => !c.command && !c.passed)
  return {
    lane: lane.name,
    outcome: awaiting.length ? 'pending-human' : 'passed',
    rounds: round,
    branch: ctx.branch,
    criteria: dev.criteria,
    carried: dedupe(carried),
    ...(awaiting.length
      ? {
          escalation: 'human',
          awaiting: awaiting.map((c) => c.criterion),
          note: `${awaiting.length} criteria need a human verdict before this lane can merge.`,
        }
      : {}),
  }
}

// Review, fix, recheck — for one lane, independent of every other lane.
async function reviewLoop(dev, lane) {
  // Every exit the loop takes with a blocker standing names the same four fields.
  const halt = (outcome, round, extra) => ({ lane: lane.name, outcome, rounds: round, branch: dev.branch, ...extra })
  if (!dev) return { lane: lane.name, outcome: 'develop-failed' }

  // A lane whose own criteria failed is not a lane to review and merge; the brief says
  // what done means and it is not done (→ conventions/18-work-contract.md).
  const failed = (dev.criteria ?? []).filter((c) => c.command && !c.passed)
  if (failed.length) {
    return {
      lane: lane.name,
      outcome: 'criteria-failed',
      branch: dev.branch,
      criteria: dev.criteria,
      note: `${failed.length} criteria with a command did not pass: ${failed.map((c) => c.criterion).join('; ')}`,
    }
  }

  const ctx = { ...lane, worktree: dev.worktree, branch: dev.branch, base }
  const lenses = lensesFor(lane)
  const carried = []
  let fixSummary = ''
  let previousKeys = new Set()
  // Round 1 has no previous fix, so nothing can be attributed to one.
  let lastFixTouched = new Set()
  // What each round's measurement diffs against: develop's head first, then the head the
  // previous measurement read, so a round sees its own fix and not the ones before it.
  let sinceSha = dev.head

  for (let round = 1; round <= ROUND_CAP; round++) {
    const reviews = (
      await parallel(
        lenses.map((lens) => () =>
          agent(reviewPrompt(ctx, lens, round, fixSummary), {
            label: `review:${lane.name}:${lens.key}#${round}`,
            phase: 'Review',
            schema: FINDINGS_SCHEMA,
          }),
        ),
      )
    ).filter(Boolean)

    // A lane that finished is not a lane that answered, and a verdict from a lane that
    // ran nothing is a reading (→ 20 Core Rules). Both are detected here and both stop
    // the loop — detecting them and passing anyway is how a short review gets merged.
    if (reviews.length < lenses.length) {
      return halt('review-incomplete', round, {
        criteria: dev.criteria,
        note: `${lenses.length - reviews.length} of ${lenses.length} review lanes returned nothing. Re-run them rather than merging a short review.`,
      })
    }
    // Any lens, not all of them. Requiring every lens to be silent meant two that ran
    // could carry a third that did not into a clean pass, and the lens that read nothing
    // is exactly the one whose "no findings" means nothing.
    const readings = reviews.filter((r) => !r.commandsRun)
    if (readings.length) {
      return halt('review-unexecuted', round, {
        criteria: dev.criteria,
        note: `${readings.length} of ${reviews.length} review lenses ran zero commands. Those verdicts are readings, not reviews.`,
      })
    }

    // The same defect seen by two lenses is one defect.
    const findings = dedupe(reviews.flatMap((r) => r.findings ?? []))

    const rawBlockers = findings.filter((f) => f.severity === 'blocker')
    // Non-blockers are carried out of every round, not only the last. 20 §3: the merge may
    // downgrade a finding but never silently drops one.
    carried.push(...findings.filter((f) => f.severity !== 'blocker'))

    if (!rawBlockers.length) return clean(lane, dev, ctx, round, carried)

    // 20 §3 step 3, the one it calls the most important: check each finding against the
    // code before acting on it. Skipping it lets one reviewer's invention force a fix, and
    // that fix then shows up as the next round's regression signal.
    const verdicts = await agent(verifyPrompt(ctx, rawBlockers), {
      label: `verify:${lane.name}#${round}`,
      phase: 'Review',
      schema: VERDICT_SCHEMA,
    })
    // Exactly one verdict per submitted blocker, and nothing else. Filtering for refutations
    // instead let a schema-valid answer carrying both a true and a false row for the same
    // key drop that blocker and reach `passed`; missing rows were merely logged. Missing,
    // duplicated, unknown or self-contradicting output is a verification that did not
    // happen, and a verification that did not happen decides nothing.
    const submitted = rawBlockers.map(keyOf)
    const rows = verdicts?.verdicts ?? []
    const byKey = new Map()
    rows.forEach((v) => byKey.set(v.key, (byKey.get(v.key) ?? []).concat(v)))
    const missing = submitted.filter((k) => !byKey.has(k))
    const duplicated = submitted.filter((k) => (byKey.get(k) ?? []).length > 1)
    const unknown = [...byKey.keys()].filter((k) => !submitted.includes(k))
    if (!verdicts || missing.length || duplicated.length || unknown.length) {
      return halt('verification-incomplete', round, {
        criteria: dev.criteria,
        blockers: rawBlockers,
        carried: dedupe(carried),
        escalation: 'human',
        note: !verdicts
          ? 'The verifier returned nothing.'
          : `Verification did not cover the blockers one to one: ${missing.length} missing, ${duplicated.length} duplicated, ${unknown.length} unknown keys.`,
      })
    }
    const refuted = rawBlockers.filter((f) => byKey.get(keyOf(f))[0].confirmed === false)
    const blockers = rawBlockers.filter((f) => byKey.get(keyOf(f))[0].confirmed !== false)
    if (refuted.length) {
      refuted.forEach((f) => carried.push({ ...f, severity: 'minor', summary: `[refuted] ${f.summary}` }))
      log(`lane ${lane.name} round ${round}: ${refuted.length} blocker(s) were refuted on verification`)
    }

    if (!blockers.length) return clean(lane, dev, ctx, round, carried)

    // Two signals that another round will not converge (→ 20 §3). Repetition is derived
    // from finding identity across rounds, blockers only on both sides of the ratio. The
    // reviewer's `causedByPreviousFix` counts only in files the measured fix reached.
    const repeated = blockers.filter((f) => previousKeys.has(keyOf(f)))
    const touched = new Set([...lastFixTouched].map((p) => repoPath(p, ctx.worktree)))
    const claimsFix = (f) => f.causedByPreviousFix && touched.has(repoPath(f.file, ctx.worktree))
    const fromFix = blockers.filter(claimsFix)
    const misattributed = blockers.filter((f) => f.causedByPreviousFix && !claimsFix(f))
    if (misattributed.length) {
      log(
        `lane ${lane.name} round ${round}: ${misattributed.length} finding(s) claimed the previous fix caused them in files it never touched`,
      )
    }
    const stuckKeys = new Set([...repeated, ...fromFix].map(keyOf))
    if (round > 1 && stuckKeys.size * 2 > blockers.length) {
      return halt('regression-halt', round, {
        blockers,
        carried: dedupe(carried),
        escalation: 'human',
        note: `${stuckKeys.size} of ${blockers.length} confirmed blockers are unchanged from the previous round (${repeated.length}) or introduced by its fix (${fromFix.length}). Change the approach rather than running another round.`,
      })
    }
    previousKeys = new Set(blockers.map(keyOf))

    if (round === ROUND_CAP) {
      return halt('round-cap', round, {
        blockers,
        carried: dedupe(carried),
        escalation: 'human',
        note: 'Round cap reached; a person decides what happens next. This is not a completion.',
      })
    }

    // No `isolation` here on purpose: a fresh worktree is the opposite of what the prompt
    // asks for. 20 requires findings to go back "in the tree it already has", and a fix
    // committed anywhere else is a fix the next reviewer never sees and the merge never
    // takes.
    const fix = await agent(fixPrompt(ctx, blockers), {
      label: `fix:${lane.name}#${round}`,
      phase: 'Review',
      schema: FIX_SCHEMA,
    })
    if (!fix) return halt('fix-failed', round, { blockers })
    fixSummary = fix.summary

    // Measured by an agent that did no work in this lane, without `isolation` for the same
    // reason the fix call has none: the evidence is in the worktree the lane already has.
    const measured = await agent(touchedPrompt(ctx, sinceSha), {
      label: `touched:${lane.name}#${round}`,
      phase: 'Review',
      schema: TOUCHED_SCHEMA,
    })
    // An empty set is the fail-safe direction, since an unmatched claim never halts. Carrying
    // the previous round's set forward would attribute this round's findings to a fix that
    // was not measured.
    if (!measured) {
      log(
        `lane ${lane.name} round ${round}: the touched-file measurement returned nothing, so the causation check is off for the next round; repetition still applies`,
      )
    }
    lastFixTouched = new Set(measured?.files ?? [])
    sinceSha = measured?.head ?? sinceSha
  }
}

// Every lane is told its contract and sample files already exist, on the strength of the
// declaration alone. Measuring it costs one agent that only stats files, skipped only for a
// plan that declares no boundaries — which has nothing to freeze.
const schemaBoundaries = boundaries.filter((b) => b.schema)
const frozenPaths = boundaries.flatMap((b) => [b.contract, b.sample, ...(b.schema ? [b.schema] : [])])
if (frozenPaths.length) {
  // Isolated and reset exactly as a lane is, because the question is what a lane sees. Read
  // from the orchestrator's tree the check answers about a different tree than the one the
  // work happens in, and passes while every lane starts on a commit holding none of it.
  let freezeError = null
  const frozen = await agent(
    [
      `Run \`git reset --hard ${base}\` in your worktree before looking at anything. Your worktree is`,
      `cut from origin/main, which may be behind ${base}, and this check is about what a lane sees`,
      'after the same reset — not about what the orchestrator has in its tree.',
      '',
      'Then, from the repository root, run exactly these checks and report their results — nothing else.',
      '',
      'Report which of these paths do not exist as files, as `missing`:',
      ...frozenPaths.map((p) => `- ${p}`),
      '',
      `Run \`${SCHEMA_CHECK} --version\` and report its exit code and output verbatim as \`tool\`.`,
      '',
      ...(schemaBoundaries.length
        ? [
            "For each of these boundaries, run the command shown and report exactly one `checked` row",
            "with that boundary's name, the exit code, and the output verbatim:",
            ...schemaBoundaries.map((b) => `- ${b.name}: \`${SCHEMA_CHECK} --schemafile ${b.schema} ${b.sample}\``),
          ]
        : ['No boundary declares a schema, so run no schema check and report `checked` as [].']),
      '',
      'Check existence and run the commands above only. Create nothing and judge nothing else — not',
      'whether a file is the right contract or sample, not whether a schema check should have passed.',
      'Report the paths exactly as they are given here, and report the sha `git rev-parse HEAD` prints',
      'after the reset as `head`.',
    ].join('\n'),
    { label: 'freeze-check', phase: 'Develop', schema: FROZEN_SCHEMA, isolation: 'worktree' },
  ).catch((err) => {
    // A check that died measured no more than a check that answered nothing, so it belongs to
    // the same refusal. This call is the one outside the pipeline, and the runtime turns a
    // throw into null only inside one — uncaught here, it left as a stack trace with no note.
    freezeError = err instanceof Error ? err.message : String(err)
    return null
  })
  if (!frozen) {
    log(`The freeze check ${freezeError ? `died: ${freezeError}` : 'returned nothing'}, so nothing about the contract or sample files was measured.`)
    return {
      lanes: [],
      note: `refused: the freeze check ${freezeError ? `died (${freezeError})` : 'returned nothing'}, so whether the contract or sample files exist is unmeasured, and with them the commit every lane starts on. This check exists because the declaration cannot be trusted, and an unmeasured declaration is that same declaration again — a guard that cannot decide must not be the one that says yes.`,
    }
  }
  if (frozen.missing?.length) {
    log(`${frozen.missing.length} of ${frozenPaths.length} contract or sample file paths do not exist at ${frozen.head}.`)
    return {
      lanes: [],
      note: `refused: the boundaries were declared frozen but these contract or sample files do not exist: ${frozen.missing.join(', ')} — not at ${frozen.head}, the commit the lanes start from. If they were written they are not in that commit, so commit and push the freeze; otherwise every lane starts where nothing holds the interfaces still and writes its own copy.`,
    }
  }

  // Existence wins outright — reading a schema result after that refusal would judge output
  // for a command run against paths the promised commit never held.
  if (frozen.tool?.exit !== 0) {
    log(`the schema tool exited ${frozen.tool?.exit} instead of 0, so no schema result can be trusted.`)
    return {
      lanes: [],
      note: `refused: \`${SCHEMA_CHECK} --version\` exited ${frozen.tool?.exit} instead of 0 (${frozen.tool?.output}), so the schema tool could not run and nothing below it was checked.`,
    }
  }
  // Every schema boundary needs exactly one row — anything else is a check that did not
  // measure that boundary, not a check that passed it.
  const checked = frozen.checked ?? []
  const byBoundary = new Map()
  checked.forEach((c) => byBoundary.set(c.boundary, (byBoundary.get(c.boundary) ?? []).concat(c)))
  const schemaNames = schemaBoundaries.map((b) => b.name)
  const uncheckedNames = schemaNames.filter((n) => !byBoundary.has(n))
  const duplicatedNames = schemaNames.filter((n) => (byBoundary.get(n) ?? []).length > 1)
  const unknownNames = [...byBoundary.keys()].filter((n) => !schemaNames.includes(n))
  if (uncheckedNames.length || duplicatedNames.length || unknownNames.length) {
    log(`the schema check did not cover the schema boundaries one to one: ${uncheckedNames.length} missing, ${duplicatedNames.length} duplicated, ${unknownNames.length} unknown.`)
    return {
      lanes: [],
      note: `refused: the schema check did not cover the boundaries with a schema one to one — ${uncheckedNames.length} missing, ${duplicatedNames.length} duplicated, ${unknownNames.length} unknown boundary name(s) in \`checked\`. This is unmeasured, not passing.`,
    }
  }
  const failedChecks = schemaBoundaries.filter((b) => byBoundary.get(b.name)[0].exit !== 0)
  if (failedChecks.length) {
    const detail = failedChecks.map((b) => `${b.name} (exit ${byBoundary.get(b.name)[0].exit}: ${byBoundary.get(b.name)[0].output})`).join('; ')
    log(`${failedChecks.length} boundary sample(s) failed their schema check: ${detail}`)
    return {
      lanes: [],
      note: `refused: the sample for ${detail} did not pass its schema check. Fix the sample or the schema before lanes fan out against it.`,
    }
  }
}

phase('Develop')

const results = await pipeline(
  lanes,
  (lane) =>
    agent(developPrompt(lane), {
      label: `develop:${lane.name}`,
      phase: 'Develop',
      schema: DEVELOP_SCHEMA,
      isolation: 'worktree',
    }),
  reviewLoop,
)

const settled = results.filter(Boolean)
const passed = settled.filter((r) => r.outcome === 'passed')
const halted = settled.filter((r) => r.outcome !== 'passed')

log(`${passed.length}/${lanes.length} lanes passed review`)
for (const h of halted) log(`lane ${h.lane}: ${h.outcome}${h.note ? ' — ' + h.note : ''}`)

return {
  passed,
  halted,
  unanswered: lanes.length - settled.length,
  // 20 requires a lane on a different vendor's family, or a record that only one was
  // reachable. This script dispatches every lens on the session's model, so the record is
  // the honest half — a report that stays silent reads as if the rule were satisfied.
  vendorDiversity: 'not implemented: every review lens ran on the session model family',
  escalations: halted
    .filter((r) => r.escalation === 'human')
    .map((r) => ({ lane: r.lane, outcome: r.outcome, note: r.note, awaiting: r.awaiting })),
}
