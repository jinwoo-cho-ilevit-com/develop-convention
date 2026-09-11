export const meta = {
  name: 'dev-harness-build',
  description: 'Lane engine behind /dev-harness:build — not the entry point. Run the command instead; this refuses unless the boundaries were already frozen',
  phases: [
    { title: 'Develop', detail: 'one worktree-isolated agent per lane' },
    { title: 'Review', detail: 'review, fix and recheck — per lane, no barrier' },
  ],
}

// A runaway guard, not an exit: a lane that keeps producing blockers needs a different
// approach, not more rounds (→ conventions/20-review-gate.md).
const ROUND_CAP = 5

// Pinned so freeze checks and lane criteria run one tool version against a boundary's schema
// (→ conventions/06-testing-verification.md).
const SCHEMA_CHECK = 'uvx check-jsonschema@0.38.0'

// The plan records a tier per lane, never a model id (→ conventions/18-work-contract.md).
const TIER_MODEL = { light: 'haiku', mid: 'sonnet', top: 'opus' }
const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']
// How a check was seen failing (→ conventions/06-testing-verification.md §3). A check that
// could not run at the base commit has no red, and no kind here names that state.
const RED_KINDS = ['observed', 'sabotage', 'guard']
const SEVERITY_RANK = { minor: 0, major: 1, blocker: 2 }

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
          criterion: { type: 'string', description: "the brief's id for this criterion (e.g. C-01), or its sentence verbatim when it has none" },
          command: { type: 'string', description: 'empty for a [human] criterion' },
          passed: { type: 'boolean' },
          output: { type: 'string' },
          red: { type: 'string', enum: RED_KINDS, description: 'required when command is non-empty: how you saw this check fail' },
          redOutput: { type: 'string', description: 'required when command is non-empty: the failing output, or for `guard` the exemption reason or its passing output at base' },
        },
      },
    },
  },
}

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['head', 'findings', 'commandsRun', 'tool'],
  additionalProperties: false,
  properties: {
    head: { type: 'string', description: 'the sha `git rev-parse HEAD` printed after your reset' },
    commandsRun: { type: 'integer', description: 'how many commands you actually executed' },
    tool: { type: 'string', description: 'the model family you run on, e.g. Claude' },
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

// Read off git by an agent that did no work in the lane: an actor reporting on its own work
// is not evidence about it. Every later step reads this, never the lane's own report.
const MEASURE_SCHEMA = {
  type: 'object',
  required: ['head', 'branchTip', 'base', 'trackedChanges', 'untracked', 'ownershipDiff', 'causationDiff'],
  additionalProperties: false,
  properties: {
    head: { type: 'string', description: 'the sha printed by git rev-parse HEAD' },
    branchTip: { type: 'string', description: 'the sha printed by git rev-parse of the lane branch' },
    base: { type: 'string', description: 'the sha printed by git rev-parse of the base' },
    trackedChanges: { type: 'array', items: { type: 'string' }, description: 'one entry per line of git status --porcelain --untracked-files=no' },
    untracked: { type: 'array', items: { type: 'string' }, description: 'paths from git ls-files --others --exclude-standard' },
    ownershipDiff: { type: 'array', items: { type: 'string' }, description: 'paths from the diff against the base' },
    causationDiff: { type: 'array', items: { type: 'string' }, description: 'paths from the diff against the previous head' },
  },
}

const FROZEN_SCHEMA = {
  type: 'object',
  required: ['missing', 'head', 'base', 'tool', 'checked'],
  additionalProperties: false,
  properties: {
    missing: {
      type: 'array',
      items: { type: 'string' },
      description: 'only the given paths that do not exist; a path that exists is left out entirely',
    },
    head: { type: 'string', description: 'the sha printed by git rev-parse HEAD after the reset' },
    base: { type: 'string', description: 'the sha printed by git rev-parse of the base' },
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
  required: ['head', 'verdicts'],
  additionalProperties: false,
  properties: {
    head: { type: 'string', description: 'the sha `git rev-parse HEAD` printed after your reset' },
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['key', 'state', 'commandsRun', 'evidence'],
        additionalProperties: false,
        properties: {
          key: { type: 'string', description: 'the finding key exactly as it was given to you' },
          state: { type: 'string', enum: ['confirmed', 'refuted', 'unverified'] },
          commandsRun: { type: 'integer', description: 'how many commands this verdict rests on' },
          evidence: { type: 'string', description: 'what you ran and what it printed' },
        },
      },
    },
  },
}

const RECHECK_SCHEMA = {
  type: 'object',
  required: ['head', 'results', 'brief'],
  additionalProperties: false,
  properties: {
    head: { type: 'string', description: 'the sha `git rev-parse HEAD` printed after your reset' },
    results: {
      type: 'array',
      description: 'exactly one row per command you were given',
      items: {
        type: 'object',
        required: ['criterion', 'exit', 'output'],
        additionalProperties: false,
        properties: {
          criterion: { type: 'string', description: 'the criterion name exactly as it was given to you' },
          exit: { type: 'integer' },
          output: { type: 'string' },
        },
      },
    },
    brief: {
      type: 'array',
      description: "every completion criterion the lane brief lists, copied verbatim",
      items: {
        type: 'object',
        required: ['id', 'sentence', 'command'],
        additionalProperties: false,
        properties: {
          id: { type: 'string', description: 'its id (e.g. C-01), or its sentence verbatim when it has none' },
          sentence: { type: 'string' },
          command: { type: 'string', description: 'the command verbatim, or [human] for a criterion a person decides' },
        },
      },
    },
  },
}

// A lane is defined by its input, not by its attitude — three reviewers told to "be critical"
// over the same input return the same findings three times (→ 20).
const REVIEW_LENSES = [
  { key: 'module', input: 'the diff and the files it changed' },
  { key: 'project', input: 'the diff plus its callers and callees, and the convention docs it must satisfy' },
  { key: 'absence', input: 'the lane brief and the diff — hunt for what the brief requires and the diff omits' },
]

// Added only for a lane the plan declares `security: true` (→ 20 Core Rules). Paths are not
// read for it: a name that looks like a trust boundary is not one, and the reverse is worse.
const SECURITY_LENS = {
  key: 'security',
  input: 'the diff, its trust boundaries, and every point where it accepts input it did not produce',
}

// One key per defect across lenses and rounds, which is what makes repetition measurable.
const keyOf = (f) => (f.line != null ? `${f.file}:${f.line}` : `${f.file}:${f.summary}`)

const joinDistinct = (a, b) => (!a ? b : !b || a.split(' | ').includes(b) ? a : `${a} | ${b}`)

// Findings sharing a key are one defect: the highest severity stands and the words of each
// report are kept (→ 20 §3).
function dedupe(findings) {
  const byKey = new Map()
  for (const f of findings) {
    const prev = byKey.get(keyOf(f))
    if (!prev) {
      byKey.set(keyOf(f), { ...f })
      continue
    }
    const top = SEVERITY_RANK[f.severity] > SEVERITY_RANK[prev.severity] ? f : prev
    const { state, ...rest } = top
    byKey.set(keyOf(f), {
      ...rest,
      summary: joinDistinct(prev.summary, f.summary),
      failureScenario: joinDistinct(prev.failureScenario, f.failureScenario),
      causedByPreviousFix: Boolean(prev.causedByPreviousFix || f.causedByPreviousFix),
      // A refutation covers only the finding it was made on, not another at the same line.
      ...(state && prev.state === f.state ? { state } : {}),
    })
  }
  return [...byKey.values()]
}

// Judges the command's form, not what the shell did: an `&&`-only chain, the pinned tool, and
// instance paths that are not the frozen sample and sit under a directory `rm -rf` cleared
// first. Returns null when satisfied, or the failing condition's name.
function producerCheckIssue(c, b) {
  const pinned = `${SCHEMA_CHECK} --schemafile ${b.schema}`
  if (/[;\n\r]|\|\||(^|[^|])\|([^|]|$)/.test(c.command)) return 'chains steps with something other than `&&`, so a failed step does not stop the check'
  const at = c.command.indexOf(pinned)
  const instances = c.command.slice(at + pinned.length).split('&&')[0].trim().split(/\s+/).filter(Boolean).map(normalPath)
  const wiped = [...c.command.slice(0, at).matchAll(/rm -rf\s+(\S+)/g)].map((m) => normalPath(m[1]))
  if (!instances.length) return 'named no file to check'
  if (instances.includes(normalPath(b.sample))) return `checked the frozen sample (${b.sample}) instead of a fresh dump`
  if (!instances.every((p) => wiped.some((d) => p.startsWith(d + '/')))) {
    return 'did not delete the directory it checks first (`rm -rf <dir>` before the check, with the checked file under <dir>)'
  }
  return c.passed ? null : 'was not reported as passing'
}

function normalPath(p) {
  const out = []
  for (const seg of String(p).split('/')) {
    if (seg === '' || seg === '.') continue
    if (seg === '..') out.pop()
    else out.push(seg)
  }
  return (String(p).startsWith('/') ? '/' : '') + out.join('/')
}

function producerCheckFailure(criteria, b) {
  const pinned = `${SCHEMA_CHECK} --schemafile ${b.schema}`
  const candidates = (criteria ?? []).filter((c) => c.command?.includes(pinned))
  if (!candidates.length) return `no criterion ran \`${pinned}\``
  const issues = candidates.map((c) => producerCheckIssue(c, b))
  return issues.includes(null) ? null : issues[0]
}

// Reviewers, fixers and git spell one file as `./src/a.py`, `src/a.py` or an absolute path
// inside the worktree; compared raw, they share nothing and every path rule silently misses.
function repoPath(p, worktree) {
  let out = String(p ?? '').replace(/\\/g, '/')
  if (worktree) {
    const root = String(worktree).replace(/\\/g, '/').replace(/\/+$/, '')
    if (out === root) return ''
    if (out.startsWith(root + '/')) out = out.slice(root.length + 1)
  }
  return out.replace(/^\.\//, '').replace(/^\/+/, '')
}

// An `owns` entry covers itself and everything under it, as a directory prefix.
function covers(own, p) {
  const o = normalPath(own)
  const q = normalPath(p)
  return o === '' || q === o || q.startsWith(o + '/')
}

const isPlainObject = (v) => typeof v === 'object' && v !== null && !Array.isArray(v)
// A lane name keys a brief path and a branch, so it may not carry a separator or traverse.
const LANE_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]*$/
const isText = (v) => typeof v === 'string' && v !== ''
// Both lists this validates decide something by being non-empty, and an empty one reads as
// "no restriction" or "pins nobody", which no plan means.
const isTextList = (v) => Array.isArray(v) && v.length > 0 && v.every(isText)

// The whole argument contract. A key absent from a list is a key nothing reads, so an object
// carrying it is a typo the caller has no other way to see.
const ARG_FIELDS = [
  // `git show <sha>:<planDir>/…` resolves only a path relative to the repository root.
  ['planDir', (v) => isText(v) && !v.startsWith('/') && !v.split('/').includes('..'), 'a repository-relative path'],
  ['base', isText, 'a non-empty string'],
  ['conventionsDir', isText, 'a non-empty string'],
  ['lanes', Array.isArray, 'a list of lane objects'],
  ['boundaries', Array.isArray, 'a list of boundary objects'],
  // Every lane of the plan, for a partial re-run: boundaries may name them and owns may not overlap them.
  ['allLanes', (v) => Array.isArray(v) && v.length > 0, 'a non-empty list of { name, owns } objects'],
  // Type only; whether it is true is policy, refused separately below.
  ['boundariesFrozen', (v) => typeof v === 'boolean', 'a boolean'],
]
const LANE_FIELDS = [
  ['name', (v) => isText(v) && LANE_NAME.test(v), `a name matching ${LANE_NAME.source}`],
  ['owns', isTextList, 'a non-empty list of path strings'],
  ['security', (v) => typeof v === 'boolean', 'a boolean'],
  ['tier', (v) => Object.keys(TIER_MODEL).includes(v), `one of ${Object.keys(TIER_MODEL).join(', ')}`],
  ['effort', (v) => EFFORTS.includes(v), `one of ${EFFORTS.join(', ')}`],
  // A halted lane's existing worktree and branch: develop is skipped and review starts at round 1.
  [
    'resumeFrom',
    (v) => isPlainObject(v) && Object.keys(v).length === 2 && isText(v.worktree) && isText(v.branch),
    'an object { worktree, branch } of non-empty strings',
  ],
  // Why the resumed lane halted, handed to its develop agent.
  ['resumeNote', isText, 'a non-empty string'],
]
const BOUNDARY_FIELDS = [
  ['name', isText, 'a non-empty string'],
  ['contract', isText, 'a path string'],
  ['sample', isText, 'a path string'],
  ['schema', isText, 'a path string'],
  ['producer', isText, 'a lane name string'],
  ['lanes', isTextList, 'a non-empty list of lane names'],
]

// Returns the sentence naming what is wrong, or null. `where` carries the element's index,
// since that is what the caller has to look at.
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

// Two lanes owning one path edit it at once from different worktrees and collide at merge.
function ownsOverlap(lanes) {
  for (let j = 1; j < lanes.length; j++) {
    for (let i = 0; i < j; i++) {
      for (const a of lanes[i].owns) {
        const b = lanes[j].owns.find((o) => covers(a, o) || covers(o, a))
        if (b) return `lane "${lanes[j].name}" owns ${JSON.stringify(b)}, which overlaps lane "${lanes[i].name}"'s ${JSON.stringify(a)}`
      }
    }
  }
  return null
}

// The arguments can reach the script as JSON text rather than as the value that was passed,
// so parse before reading any field; what the text encodes then meets the same guards.
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
// Text carrying no argument is the argument-less invocation, which gets the freeze note.
if (typeof input === 'string' && input.trim() === '') input = undefined

const planDir = input?.planDir ?? '.plans'
// The conventions travel with the plugin, not with the project the lanes run in.
const conventionsDir = input?.conventionsDir ?? 'conventions'
// What every lane resets to and every range starts from; a worktree is cut from
// `origin/main`, so nothing else puts a lane on this commit.
const base = input?.base ?? 'main'
const lanes = input?.lanes ?? []
const boundaries = input?.boundaries ?? []
const allLanes = input?.allLanes
// What owns may not overlap: the lanes run now, and every other lane the plan declares.
const planLanes = () => [...lanes, ...(allLanes ?? []).filter((a) => !lanes.some((l) => l.name === a?.name))]

// Nothing can be read off a value that is not an object, so the freeze check below would
// refuse in the name of a freeze that may well have happened.
if (input !== undefined && !isPlainObject(input)) {
  log('args did not arrive as an object. Nothing can be read from it.')
  return {
    lanes: [],
    note:
      'refused: the arguments did not arrive as an object, so every field including boundariesFrozen read as undefined.' +
      // The parser's words are what tell malformed text from a scalar.
      (parseError ? ` They arrived as text that does not parse as JSON: ${parseError}.` : '') +
      ' Pass { planDir, base, lanes, boundaries, conventionsDir, boundariesFrozen } as an object, or as JSON text encoding one. This is not a reason to hardcode boundariesFrozen.',
  }
}

// One pass, before any field reaches a prompt, a path or a git command. Parsing recovers only
// the top level, so every level below is checked here rather than where it is used.
const complaint =
  // An argument-less call has no shape to be wrong; the freeze gate below answers it.
  (input === undefined ? null : checkShape(input, 'args', ARG_FIELDS, ['lanes'])) ??
  lanes.map((l, i) => checkShape(l, `args.lanes[${i}]`, LANE_FIELDS, ['name', 'owns', 'security'])).find(Boolean) ??
  boundaries.map((b, i) => checkShape(b, `args.boundaries[${i}]`, BOUNDARY_FIELDS, ['name', 'lanes', 'contract', 'sample'])).find(Boolean) ??
  // Two lanes of one name share a brief, a branch and every label.
  (new Set(lanes.map((l) => l?.name)).size !== lanes.length ? 'args.lanes declares the same name twice' : null) ??
  // A `checked` row keys a schema result by boundary name.
  boundaries
    .map((b, i) => (boundaries.findIndex((x) => x?.name === b?.name) !== i ? `args.boundaries[${i}] repeats the name ${JSON.stringify(b?.name)}` : null))
    .find(Boolean) ??
  // A schema with no named producer leaves no lane to carry its dump-recheck criterion.
  boundaries.map((b, i) => (b?.schema && !b?.producer ? `args.boundaries[${i}] has a schema but names no producer` : null)).find(Boolean) ??
  // A producer outside the boundary's lanes is never told to report its criterion.
  boundaries
    .map((b, i) => (b?.producer && !(b.lanes ?? []).includes(b.producer) ? `args.boundaries[${i}].producer is ${JSON.stringify(b.producer)}, which is not one of this boundary's lanes` : null))
    .find(Boolean) ??
  // One shared sample is one payload, and a payload has exactly one schema.
  boundaries
    .map((b, i) => {
      const conflict = boundaries.find((x, j) => j < i && x?.sample === b?.sample && (x?.schema ?? null) !== (b?.schema ?? null))
      return conflict ? `args.boundaries[${i}] shares a sample with another boundary but names a different schema` : null
    })
    .find(Boolean) ??
  // A pinned lane gets three lenses instead of one; a name matching no lane buys the shallower
  // review and says nothing.
  (allLanes ?? []).map((l, i) => checkShape(l, `args.allLanes[${i}]`, LANE_FIELDS.slice(0, 2), ['name', 'owns'])).find(Boolean) ??
  lanes.map((l, i) => (allLanes && !allLanes.some((a) => a.name === l.name) ? `args.lanes[${i}] is ${JSON.stringify(l.name)}, which args.allLanes omits` : null)).find(Boolean) ??
  lanes.map((l, i) => (l.resumeNote && !l.resumeFrom ? `args.lanes[${i}] has a resumeNote but no resumeFrom` : null)).find(Boolean) ??
  boundaries
    .flatMap((b, i) =>
      (b.lanes ?? []).map((n, j) =>
        planLanes().some((l) => l.name === n) ? null : `args.boundaries[${i}].lanes[${j}] is ${JSON.stringify(n)}, which no lane declares`,
      ),
    )
    .find(Boolean) ??
  ownsOverlap(planLanes()) ??
  // The frozen files belong to no lane; a lane owning one may move the interface it works against.
  lanes
    .flatMap((l, i) =>
      l.owns.flatMap((o) =>
        boundaries.flatMap((b) =>
          [b.contract, b.sample, b.schema]
            .filter((p) => p && covers(o, p))
            .map((p) => `args.lanes[${i}].owns entry ${JSON.stringify(o)} covers boundary "${b.name}"'s frozen file ${p}`),
        ),
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

log(`base ${base}, plans in ${planDir}, conventions in ${conventionsDir}, ${lanes.length} lane(s), ${boundaries.length} boundary(ies)`)

// Invoking this workflow directly skips the freeze that holds the interfaces still while every
// lane edits at once, so the caller has to declare it happened.
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

// Three lenses when the change spans modules or pins an interface, one otherwise, plus a
// security lens for a lane the plan declared `security: true` (→ 20 §2).
function lensesFor(lane) {
  const spansModules = (lane.owns ?? []).length > 1
  const pinsInterface = boundaries.some((b) => (b.lanes ?? []).includes(lane.name))
  const base = spansModules || pinsInterface ? REVIEW_LENSES : [REVIEW_LENSES[0]]
  return lane.security === true ? [...base, SECURITY_LENS] : base
}

const tierOpts = (lane) => ({
  ...(lane.tier ? { model: TIER_MODEL[lane.tier] } : {}),
  ...(lane.effort ? { effort: lane.effort } : {}),
})

const owned = (lane, p) => lane.owns.some((o) => covers(o, p))

// A lane pointed at a directory reads the wrong file, or treats a contract as something to
// run, so every lane-scoped agent gets its own boundaries' exact paths. Empty off-boundary.
function boundaryContracts(lane) {
  const mine = boundaries.filter((b) => (b.lanes ?? []).includes(lane.name))
  if (!mine.length) return ''
  return [
    "Your boundaries' contracts are files, not tests — owned by no lane, never edit them or their samples:",
    ...mine.map((b) => `- ${b.name}: contract ${b.contract}${b.schema ? `, schema ${b.schema}` : ''}, sample ${b.sample}`),
    "The consumer side runs its sample run on the sample. The producer's own output is checkable",
    "against the schema; only the other side's code is absent, and the whole boundary is exercised",
    'after the merge.',
    ...mine
      .filter((b) => b.schema)
      .map((b) =>
        b.producer === lane.name
          ? `You produce boundary "${b.name}"'s payload: carry and report a criterion that deletes its dump directory, re-runs your sample run, and checks the fresh dump with \`${SCHEMA_CHECK} --schemafile ${b.schema} <dump>\`.`
          : `You consume boundary "${b.name}"'s payload; its producer ("${b.producer}") carries the schema check, not you.`,
      ),
  ].join('\n')
}

// Names who carries a boundary's schema check, so a finding faults a specific brief or report.
function schemaFindingNotes(lane) {
  return boundaries
    .filter((b) => b.schema && (b.lanes ?? []).includes(lane.name))
    .map((b) => `Lane "${b.producer}" carries the schema check for boundary "${b.name}"; a brief or report missing it is a finding.`)
}

const resetTo = (sha) => [
  `Before anything else, run \`git reset --hard ${sha}\` in your worktree, then report what \`git rev-parse HEAD\``,
  'prints as `head`. That sha is the lane\'s work as measured; an answer from any other tree is not counted.',
]

function developPrompt(lane) {
  const contracts = boundaryContracts(lane)
  const r = lane.resumeFrom
  return [
    ...(r
      ? [
          `You own lane "${lane.name}", which halted${lane.resumeNote ? `: ${lane.resumeNote}` : ''}.`,
          `Continue in its existing worktree ${r.worktree} on branch ${r.branch} — do not reset it and do not start`,
          'another branch. Fix what halted it and commit on that branch.',
          `Read the brief as base holds it, \`git show ${baseSha}:${planDir}/lane-${lane.name}.md\`, and ${planDir}/PLAN.md.`,
        ]
      : [
          `Before anything else, run \`git reset --hard ${baseSha}\` in your worktree, then \`git log --oneline -1\``,
          'and confirm you are on that commit.',
          `Your worktree is cut from origin/main, which may be behind ${baseSha} and may carry neither the frozen`,
          `boundary files nor the lane briefs under ${planDir}.`,
          '',
          `You own lane "${lane.name}". Read ${planDir}/lane-${lane.name}.md and ${planDir}/PLAN.md.`,
          'Create a branch for this lane and commit your work to it.',
        ]),
    '',
    `Work only inside your owned paths: ${lane.owns.join(', ')}.`,
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
    "Run every command listed under the brief's completion criteria. Update the AGENTS.md of each",
    'directory you own in the same pass',
    `(→ ${conventionsDir}/15-doc-tracking.md). Leave nothing uncommitted: no changed tracked file and no`,
    'untracked file under your owned paths. Report every criterion below afresh, red included — nothing',
    'carries over from an earlier run.',
    '',
    'Return the absolute path of the worktree you worked in — later rounds continue in it — and the',
    'commit sha on your lane branch after your work.',
    "Report every criterion the brief lists, under the brief's id for it (or its sentence verbatim when it",
    'has none), with the exact command the brief gives and whether it passed. A [human] criterion has no',
    'command: report it as not passed and leave the command empty.',
    '',
    `For every criterion with a command, report \`red\` and \`redOutput\` (→ ${conventionsDir}/06-testing-verification.md §3):`,
    '`observed` when it failed at the base commit before your change, `sabotage` when you broke the code it',
    'checks after the change and saw it fail — with that failing output — or `guard` for a standing',
    'invariant, with the reason it is exempt or its passing output at the base commit.',
    'A check that could not run at the base commit has no baseline, which is not a red: after implementing,',
    'sabotage the code it checks, record that failure as `sabotage`, and restore the code.',
  ].join('\n')
}

function reviewPrompt(lane, lens, round, fixSummary) {
  const contracts = boundaryContracts(lane)
  const commandCriteria = lane.criteria.filter(isCommand)
  return [
    `Review lane "${lane.name}" through one lens only: ${lens.key}.`,
    `Your input is ${lens.input}.`,
    ...resetTo(lane.head),
    '',
    `Read the change with \`git diff ${baseSha}..${lane.head}\`, and its commit messages with`,
    `\`git log ${baseSha}..${lane.head}\` — a bug fix's reproduction lives in its ## Result.`,
    '',
    "You did not write this code and you do not get the author's reasoning. Judge the diff against",
    `${planDir}/lane-${lane.name}.md and the convention docs in ${conventionsDir}/.`,
    '',
    'Run the code. You have the test command and the tool under review; report how many commands you',
    'actually executed, and the model family you run on as `tool`. A verdict from a lane that ran none is a',
    'reading, not a review.',
    ...(lens.key === 'module' && commandCriteria.length
      ? [
          '',
          'Each command criterion carries a red its author reported. Check that each holds: the recorded',
          'output must be what the command prints when the behaviour it checks is broken — re-create a',
          'sabotage red where you doubt one. A red that does not hold is a finding.',
          ...commandCriteria.map((c) => `- ${c.criterion} (${c.red}): \`${c.command}\` — recorded: ${c.redOutput}`),
        ]
      : []),
    ...(contracts
      ? [
          contracts,
          "Compare this lane's side against each contract file listed — names, signatures, call",
          'direction. Where a boundary has a schema, that schema decides its fields, types and',
          'values; where it does not, compare the value set the contract file names. A mismatch is a',
          "finding; the other side's absence is not.",
          ...schemaFindingNotes(lane),
        ]
      : []),
    '',
    'Flag correctness and requirement gaps only. Do not manufacture problems in sound code.',
    round > 1
      ? `This is round ${round}. The previous round's fix was:\n${fixSummary}\nFor each finding, set causedByPreviousFix to true only when the defect is in code that fix introduced or changed.`
      : 'This is round 1, so causedByPreviousFix is false for every finding.',
  ].join('\n')
}

function verifyPrompt(lane, blockers, again) {
  const contracts = boundaryContracts(lane)
  return [
    `Check each claimed blocker in lane "${lane.name}" against the actual code. You are not`,
    'reviewing the change and you are not looking for new problems — you are deciding whether',
    'each of these is real.',
    ...resetTo(lane.head),
    '',
    blockers.map((b) => `- key: ${keyOf(b)}\n  claim: ${b.summary}\n  scenario: ${b.failureScenario ?? '(none given)'}`).join('\n'),
    '',
    'Decide each by running something: reproduce it and the state is `confirmed`; run what shows it',
    'cannot happen and the state is `refuted`. Report how many commands each verdict rests on. A verdict',
    'reached by reading alone is `unverified` — reading decides nothing here.',
    ...(again
      ? ['A first pass left these unverified. Reproduce each one: write and run the smallest input that triggers it.']
      : []),
    'Return one verdict per key, with the key copied exactly, and say what you ran and what it printed.',
    ...(contracts ? [contracts] : []),
    '',
    'A finding with no concrete failing scenario is not confirmed: a fix sent after a defect nobody showed',
    'changes sound code, and that change is the next round\'s regression signal.',
  ].join('\n')
}

function fixPrompt(lane, blockers) {
  const contracts = boundaryContracts(lane)
  return [
    `You own lane "${lane.name}". Continue in the worktree you already have: ${lane.worktree}.`,
    'Review found these blockers. Fix them and commit to the same lane branch.',
    '',
    blockers.map((b, i) => `${i + 1}. [${b.file}${b.line != null ? ':' + b.line : ''}] ${b.summary}`).join('\n'),
    '',
    'Fix only these, inside your owned paths. Anything else you notice goes in your summary, not in the',
    'diff — an unrelated change here forces the whole lane through another review round.',
    'Re-run the criteria commands from your brief before returning, and leave nothing uncommitted.',
    ...(contracts ? [contracts] : []),
    '',
    'Return a short summary of what you changed.',
  ].join('\n')
}

// Runs in the lane's own worktree, since that is where the evidence is, and changes nothing.
function measurePrompt(lane, since) {
  return [
    `Measure the worktree ${lane.worktree}. Work there and nowhere else; change nothing and judge nothing.`,
    '',
    'Run exactly these commands and copy their output into the field named after each:',
    '1. git rev-parse HEAD → head',
    `2. git rev-parse ${lane.branch} → branchTip`,
    `3. git rev-parse ${baseSha} → base`,
    '4. git status --porcelain --untracked-files=no → trackedChanges, one entry per output line',
    `5. git ls-files --others --exclude-standard -- ${lane.owns.join(' ')} → untracked`,
    `6. git --no-pager diff --no-renames --name-only ${baseSha}..HEAD → ownershipDiff`,
    `7. git --no-pager diff --no-renames --name-only ${since}..HEAD → causationDiff`,
    '',
    'Report every line exactly as printed, without filtering to what looks relevant; an empty output is [].',
  ].join('\n')
}

function recheckPrompt(lane, commandCriteria) {
  const brief = `git show ${baseSha}:${normalPath(`${planDir}/lane-${lane.name}.md`)}`
  return [
    `Re-run lane "${lane.name}"'s completion criteria on its measured commit. You did not write this code.`,
    ...resetTo(lane.head),
    '',
    `Read the lane brief as the base commit holds it, with \`${brief}\` — not the copy in your tree, which`,
    'the lane may have changed. Report every completion criterion it lists as `brief`: its id (or its sentence',
    'verbatim when it has none), its sentence, and its command verbatim — `[human]` for a criterion a person decides.',
    '',
    'Run each of these commands exactly as written and report one `results` row per criterion: its',
    'name exactly as given, the exit code, and the output verbatim. Copy the brief; do not reconcile it with this list.',
    ...(commandCriteria.length ? commandCriteria.map((c) => `- ${c.criterion}: \`${c.command}\``) : ['(none — report `results` as [])']),
  ].join('\n')
}

const kindOf = (command) => (!command || command.trim() === '[human]' ? 'human' : 'command')
const isCommand = (c) => kindOf(c.command) === 'command'
// The kind travels in the command, so a `[human]` marker in an id is not part of the name.
const normalId = (id) => String(id).replace(/^\s*\[human\]\s*/, '').trim()

// Every criterion the brief sets must reach the report unweakened: same id, same kind, same
// command (→ conventions/18-work-contract.md). Criteria the lane added beyond the brief are allowed.
function criteriaDrift(brief, criteria) {
  const ids = criteria.map((c) => normalId(c.criterion))
  const byId = new Map(criteria.map((c) => [normalId(c.criterion), c]))
  const repeated = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))].map((id) => `${id} is reported more than once`)
  return repeated.concat(brief
    .map((b) => {
      const c = byId.get(normalId(b.id))
      if (!c) return `${b.id} is missing`
      if (kindOf(b.command) !== kindOf(c.command)) return `${b.id} is a ${kindOf(c.command)} criterion, and the brief makes it a ${kindOf(b.command)} one`
      if (kindOf(b.command) === 'command' && b.command.trim() !== c.command.trim()) {
        return `${b.id} ran \`${c.command}\` instead of the brief's \`${b.command}\``
      }
      return null
    })
    .filter(Boolean))
}

// A missing red record and a failing producer check are injected as failed criteria, so they
// halt through the same `criteria-failed` exit as any other (→ conventions/06-testing-verification.md §3, §7).
function withInjected(lane, criteria, { red }) {
  const noRed = red ? criteria.filter((c) => isCommand(c) && !(RED_KINDS.includes(c.red) && isText(c.redOutput))) : []
  const producer = boundaries
    .filter((b) => b.schema && b.producer === lane.name)
    .map((b) => ({ b, issue: producerCheckFailure(criteria, b) }))
    .filter((x) => x.issue)
  return [
    ...criteria,
    ...noRed.map((c) => ({
      criterion: `red for "${c.criterion}" was not recorded as one of ${RED_KINDS.join(', ')} with its output`,
      command: c.command,
      passed: false,
    })),
    ...producer.map(({ b, issue }) => ({
      criterion: `producer check for boundary "${b.name}" (--schemafile ${b.schema}) failed: ${issue}`,
      command: `${SCHEMA_CHECK} --schemafile ${b.schema} <dump>`,
      passed: false,
    })),
  ]
}

const failing = (criteria) => criteria.filter((c) => isCommand(c) && !c.passed)

// Review, fix and recheck for one lane, independent of every other lane.
async function reviewLoop(dev, lane) {
  const lenses = lensesFor(lane)
  const carried = []
  const commandsRun = {}
  const tools = new Set()
  // Blockers no verifier could decide by running anything, keyed; a later verdict removes one.
  const unverified = new Map()
  let head = null
  // A resumed lane stays in the worktree and branch it was resumed from, whatever develop reports.
  const worktree = lane.resumeFrom?.worktree ?? dev?.worktree
  const branch = lane.resumeFrom?.branch ?? dev?.branch
  // Every exit names the same fields, so a review points row can be filled from any of them.
  const result = (outcome, round, extra) => ({
    lane: lane.name,
    outcome,
    rounds: round,
    branch,
    worktree,
    head,
    lenses: lenses.map((l) => l.key),
    commandsRun,
    tool: [...tools].join(' + '),
    carried: dedupe(carried),
    ...(unverified.size ? { unverified: [...unverified.values()] } : {}),
    ...extra,
  })
  if (!dev) return result('develop-failed', 0)
  if (!dev.criteria?.length) {
    return result('criteria-failed', 0, { criteria: [], note: 'develop reported no completion criteria, so nothing says the lane is done.' })
  }
  // A lane whose own criteria failed is not done, and is not reviewed (→ conventions/18-work-contract.md).
  const criteria = withInjected(lane, dev.criteria, { red: true })
  const failedAtDevelop = failing(criteria)
  if (failedAtDevelop.length) {
    return result('criteria-failed', 0, {
      criteria,
      note: `${failedAtDevelop.length} criteria with a command did not pass: ${failedAtDevelop.map((c) => c.criterion).join('; ')}`,
    })
  }

  const ctx = { ...lane, worktree, branch, criteria, head: null }

  // Returns the measurement, or the outcome that halts on it.
  const measure = async (label, since) => {
    const m = await agent(measurePrompt(ctx, since), { label, phase: 'Review', schema: MEASURE_SCHEMA })
    if (!isText(m?.head)) return { outcome: 'measurement-failed', note: `${label} returned no head sha, so which commit to review is unknown.` }
    if (m.base !== baseSha) return { outcome: 'measurement-failed', note: `${label} resolved base to ${m.base}, not the pinned ${baseSha}.` }
    if (m.branchTip !== m.head) {
      return { outcome: 'dirty-worktree', note: `the tip of ${ctx.branch} (${m.branchTip}) is not the worktree HEAD (${m.head}), so the commit reviewed would not be the one merged.` }
    }
    const dirty = [...(m.trackedChanges ?? []), ...(m.untracked ?? []).filter((p) => owned(lane, repoPath(p, ctx.worktree)))]
    if (dirty.length) {
      return { outcome: 'dirty-worktree', note: `${label} found uncommitted work, which no reviewer at ${m.head} would see: ${dirty.join(', ')}` }
    }
    const outside = (m.ownershipDiff ?? []).map((p) => repoPath(p, ctx.worktree)).filter((p) => !owned(lane, p))
    if (outside.length) {
      return { outcome: 'ownership-violated', note: `the diff from ${m.base} touches paths outside owns (${lane.owns.join(', ')}): ${outside.join(', ')}` }
    }
    return { m }
  }

  const developed = await measure(`touched:${lane.name}#0`, baseSha)
  if (!developed.m) return result(developed.outcome, 0, { criteria, note: developed.note })
  ctx.head = head = developed.m.head

  // Decides each blocker by the verifier's run, one to one; a verdict that ran nothing is unverified.
  const verifyRound = async (blockers, round, again) => {
    const answer = await agent(verifyPrompt(ctx, blockers, again), {
      label: `${again ? 'reverify' : 'verify'}:${lane.name}#${round}`,
      phase: 'Review',
      schema: VERDICT_SCHEMA,
      isolation: 'worktree',
    })
    const submitted = blockers.map(keyOf)
    const byKey = new Map()
    ;(answer?.verdicts ?? []).forEach((v) => byKey.set(v.key, (byKey.get(v.key) ?? []).concat(v)))
    const missing = submitted.filter((k) => !byKey.has(k))
    const duplicated = submitted.filter((k) => (byKey.get(k) ?? []).length > 1)
    const unknown = [...byKey.keys()].filter((k) => !submitted.includes(k))
    if (!answer || answer.head !== ctx.head || missing.length || duplicated.length || unknown.length) {
      return {
        incomplete: !answer
          ? 'The verifier returned nothing.'
          : answer.head !== ctx.head
            ? `The verifier ran on ${answer.head}, not on the measured ${ctx.head}.`
            : `Verification did not cover the blockers one to one: ${missing.length} missing, ${duplicated.length} duplicated, ${unknown.length} unknown keys.`,
      }
    }
    const stateOf = (v) => (['confirmed', 'refuted'].includes(v.state) && v.commandsRun > 0 ? v.state : 'unverified')
    return { states: new Map(submitted.map((k) => [k, stateOf(byKey.get(k)[0])])) }
  }

  // Every clean exit re-runs the criteria on the measured head first, by an agent that is not the fixer.
  const finish = async (round) => {
    const re = await agent(recheckPrompt(ctx, criteria.filter(isCommand)), {
      label: `recheck:${lane.name}#${round}`,
      phase: 'Review',
      schema: RECHECK_SCHEMA,
      isolation: 'worktree',
    })
    const incomplete = (note) => result('recheck-incomplete', round, { criteria, note })
    if (!re) return incomplete('The recheck returned nothing.')
    if (re.head !== head) return incomplete(`The recheck ran on ${re.head}, not on the measured ${head}.`)
    if (!re.brief?.length) return incomplete('The recheck read no criteria from the lane brief, so nothing was compared against it.')
    const drift = criteriaDrift(re.brief, dev.criteria)
    if (drift.length) return result('criteria-drift', round, { criteria, note: `the reported criteria differ from the brief: ${drift.join('; ')}` })
    const byName = new Map()
    ;(re.results ?? []).forEach((r) => byName.set(r.criterion, (byName.get(r.criterion) ?? []).concat(r)))
    const names = criteria.filter(isCommand).map((c) => c.criterion)
    const missing = names.filter((n) => !byName.has(n))
    const duplicated = names.filter((n) => (byName.get(n) ?? []).length > 1)
    const unknown = [...byName.keys()].filter((n) => !names.includes(n))
    if (missing.length || duplicated.length || unknown.length) {
      return incomplete(`The recheck did not cover the criteria one to one: ${missing.length} missing, ${duplicated.length} duplicated, ${unknown.length} unknown.`)
    }

    const rechecked = withInjected(
      lane,
      criteria.map((c) => (isCommand(c) ? { ...c, passed: byName.get(c.criterion)[0].exit === 0, output: byName.get(c.criterion)[0].output } : c)),
      { red: false },
    )
    const failed = failing(rechecked)
    if (failed.length) {
      return result('criteria-failed', round, {
        criteria: rechecked,
        note: `${failed.length} criteria failed on the recheck at ${head}: ${failed.map((c) => c.criterion).join('; ')}`,
      })
    }
    return clean(round, rechecked)
  }

  // A `[human]` criterion or an undecided blocker holds the lane out of `passed`: once merged,
  // a rejection can no longer act (→ conventions/19-evidence.md).
  const clean = (round, rechecked) => {
    // Every human criterion awaits its verdict, whatever the lane reported about it.
    const awaiting = rechecked.filter((c) => !isCommand(c)).map((c) => c.criterion)
    if (unverified.size) {
      return result('unverified-blocker', round, {
        criteria: rechecked,
        escalation: 'human',
        ...(awaiting.length ? { awaiting } : {}),
        note: `${unverified.size} blocker(s) were neither reproduced nor refuted by a run; a person confirms or dismisses each before this lane can merge.`,
      })
    }
    if (awaiting.length) {
      return result('pending-human', round, {
        criteria: rechecked,
        escalation: 'human',
        awaiting,
        note: `${awaiting.length} criteria need a human verdict before this lane can merge.`,
      })
    }
    return result('passed', round, { criteria: rechecked })
  }

  let fixSummary = ''
  let previousKeys = new Set()
  // What the last fix changed; round 1 has no previous fix, so nothing is attributed to one.
  let lastFixTouched = new Set()

  for (let round = 1; round <= ROUND_CAP; round++) {
    const answers = await parallel(
      lenses.map((lens) => () =>
        agent(reviewPrompt(ctx, lens, round, fixSummary), {
          label: `review:${lane.name}:${lens.key}#${round}`,
          phase: 'Review',
          schema: FINDINGS_SCHEMA,
          isolation: 'worktree',
        }),
      ),
    )
    // An answer from another commit reviewed other code, so it counts as no answer.
    const onHead = (r) => r?.head === head
    answers.forEach((r, i) => {
      if (!onHead(r)) return
      commandsRun[lenses[i].key] = (commandsRun[lenses[i].key] ?? 0) + (r.commandsRun ?? 0)
      if (isText(r.tool)) tools.add(r.tool)
    })
    const reviews = answers.filter(onHead)

    // A lens that did not answer, or answered without running anything, is not a review (→ 20 Core Rules).
    if (reviews.length < lenses.length) {
      return result('review-incomplete', round, {
        criteria,
        note: `${lenses.length - reviews.length} of ${lenses.length} review lanes returned nothing or ran on a commit other than ${head}. Re-run them rather than merging a short review.`,
      })
    }
    const readings = reviews.filter((r) => !r.commandsRun)
    if (readings.length) {
      return result('review-unexecuted', round, {
        criteria,
        note: `${readings.length} of ${reviews.length} review lenses ran zero commands. Those verdicts are readings, not reviews.`,
      })
    }

    const findings = dedupe(reviews.flatMap((r) => r.findings ?? []))
    const rawBlockers = findings.filter((f) => f.severity === 'blocker')
    // Non-blockers leave every round: the merge may downgrade a finding but never drops one (20 §3).
    carried.push(...findings.filter((f) => f.severity !== 'blocker'))

    if (!rawBlockers.length) return finish(round)

    // 20 §3: check each blocker against the code before acting on it, and let only a run decide.
    const first = await verifyRound(rawBlockers, round, false)
    if (first.incomplete) return result('verification-incomplete', round, { criteria, blockers: rawBlockers, escalation: 'human', note: first.incomplete })
    const states = first.states
    const pending = rawBlockers.filter((f) => states.get(keyOf(f)) === 'unverified')
    if (pending.length) {
      const again = await verifyRound(pending, round, true)
      if (again.incomplete) return result('verification-incomplete', round, { criteria, blockers: pending, escalation: 'human', note: again.incomplete })
      again.states.forEach((s, k) => states.set(k, s))
    }
    for (const f of rawBlockers) {
      const s = states.get(keyOf(f))
      if (s === 'unverified') unverified.set(keyOf(f), f)
      else unverified.delete(keyOf(f))
      if (s === 'refuted') carried.push({ ...f, severity: 'minor', state: 'refuted' })
    }
    const blockers = rawBlockers.filter((f) => states.get(keyOf(f)) === 'confirmed')
    if (!blockers.length) return finish(round)

    // Two signals that another round will not converge (→ 20 §3): a blocker repeating by key,
    // or one the reviewer blames on the last fix in a file that fix measurably changed.
    const repeated = blockers.filter((f) => previousKeys.has(keyOf(f)))
    const touched = new Set([...lastFixTouched].map((p) => repoPath(p, ctx.worktree)))
    const claimsFix = (f) => f.causedByPreviousFix && touched.has(repoPath(f.file, ctx.worktree))
    const fromFix = blockers.filter(claimsFix)
    const misattributed = blockers.filter((f) => f.causedByPreviousFix && !claimsFix(f))
    if (misattributed.length) {
      log(`lane ${lane.name} round ${round}: ${misattributed.length} finding(s) claimed the previous fix caused them in files it never touched`)
    }
    const stuckKeys = new Set([...repeated, ...fromFix].map(keyOf))
    if (round > 1 && stuckKeys.size * 2 > blockers.length) {
      return result('regression-halt', round, {
        criteria,
        blockers,
        escalation: 'human',
        note: `${stuckKeys.size} of ${blockers.length} confirmed blockers are unchanged from the previous round (${repeated.length}) or introduced by its fix (${fromFix.length}). Change the approach rather than running another round.`,
      })
    }
    previousKeys = new Set(blockers.map(keyOf))

    if (round === ROUND_CAP) {
      return result('round-cap', round, {
        criteria,
        blockers,
        escalation: 'human',
        note: 'Round cap reached; a person decides what happens next. This is not a completion.',
      })
    }

    // No `isolation`: 20 sends findings back to the tree the lane already has, and a fix
    // committed anywhere else is one the merge never takes.
    const fix = await agent(fixPrompt(ctx, blockers), {
      label: `fix:${lane.name}#${round}`,
      phase: 'Review',
      schema: FIX_SCHEMA,
      ...tierOpts(lane),
    })
    if (!fix) return result('fix-failed', round, { criteria, blockers })
    fixSummary = fix.summary

    const fixed = await measure(`touched:${lane.name}#${round}`, head)
    if (!fixed.m) return result(fixed.outcome, round, { criteria, blockers, note: fixed.note })
    lastFixTouched = new Set(fixed.m.causationDiff ?? [])
    ctx.head = head = fixed.m.head
  }
}

// Every lane is told its plan, brief, contract, schema and sample files exist on the strength
// of the declaration alone, so one agent measures that from a lane's starting commit.
const schemaBoundaries = boundaries.filter((b) => b.schema)
const frozenPaths = [
  ...boundaries.flatMap((b) => [b.contract, b.sample, ...(b.schema ? [b.schema] : [])]),
  `${planDir}/PLAN.md`,
  ...lanes.map((l) => `${planDir}/lane-${l.name}.md`),
]
// Isolated and reset exactly as a lane is, because the question is what a lane sees, not
// what the orchestrator has in its tree.
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
    ...(schemaBoundaries.length
      ? [
          `Run \`${SCHEMA_CHECK} --version\` and report its exit code and output verbatim as \`tool\`.`,
          '',
          "For each of these boundaries, run the command shown and report exactly one `checked` row",
          "with that boundary's name, the exit code, and the output verbatim:",
          ...schemaBoundaries.map((b) => `- ${b.name}: \`${SCHEMA_CHECK} --schemafile ${b.schema} ${b.sample}\``),
        ]
      : ['No boundary declares a schema, so report `tool` as { exit: 0, output: \'\' } and `checked` as [].']),
    '',
    'Check existence and run the commands above only. Create nothing and judge nothing else — not',
    'whether a file is the right contract or sample, not whether a schema check should have passed.',
    'Report the paths exactly as they are given here, the sha `git rev-parse HEAD` prints after the reset',
    `as \`head\`, and the sha \`git rev-parse ${base}\` prints as \`base\`.`,
  ].join('\n'),
  { label: 'freeze-check', phase: 'Develop', schema: FROZEN_SCHEMA, isolation: 'worktree' },
).catch((err) => {
  // Outside the pipeline a throw is not turned into null, and a check that died measured
  // no more than one that answered nothing.
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
if (frozen.head !== frozen.base) {
  log(`The freeze check ran on ${frozen.head}, not on base ${frozen.base}.`)
  return {
    lanes: [],
    note: `refused: the freeze check ran on ${frozen.head}, not on base ${frozen.base}, so what it measured is not what the lanes start from.`,
  }
}
if (frozen.missing?.length) {
  log(`${frozen.missing.length} of ${frozenPaths.length} plan, brief, contract, schema or sample file paths do not exist at ${frozen.head}.`)
  return {
    lanes: [],
    note: `refused: the boundaries were declared frozen but these contract, schema, sample or plan files do not exist: ${frozen.missing.join(', ')} — not at ${frozen.head}, the commit the lanes start from. If they were written they are not in that commit, so commit them and merge them into base locally; otherwise every lane starts where nothing holds the interfaces still and writes its own copy.`,
  }
}

// A plan with no schema boundary needs no schema tool, and existence was decided above first.
if (schemaBoundaries.length) {
  if (frozen.tool?.exit !== 0) {
    log(`the schema tool exited ${frozen.tool?.exit} instead of 0, so no schema result can be trusted.`)
    return {
      lanes: [],
      note: `refused: \`${SCHEMA_CHECK} --version\` exited ${frozen.tool?.exit} instead of 0 (${frozen.tool?.output}), so the schema tool could not run and nothing below it was checked.`,
    }
  }
  // Exactly one row per schema boundary; anything else did not measure that boundary.
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

// The one base every later prompt and range uses, so a ref that moves mid-run moves nothing.
const baseSha = frozen.base

phase('Develop')

const results = await pipeline(
  lanes,
  (lane) =>
    // A resumed lane continues in the worktree it already has, so it gets no fresh one.
    agent(developPrompt(lane), {
      label: `develop:${lane.name}`,
      phase: 'Develop',
      schema: DEVELOP_SCHEMA,
      ...(lane.resumeFrom ? {} : { isolation: 'worktree' }),
      ...tierOpts(lane),
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
  vendorDiversity:
    "a lane's review lenses run on the session model and may share one family, named in each lane's `tool`; the vendor diversity the review gate requires is paid at the plan and merged-whole review points (→ conventions/20-review-gate.md)",
  escalations: halted
    .filter((r) => r.escalation === 'human')
    .map((r) => ({ lane: r.lane, outcome: r.outcome, note: r.note, awaiting: r.awaiting, unverified: r.unverified })),
}
