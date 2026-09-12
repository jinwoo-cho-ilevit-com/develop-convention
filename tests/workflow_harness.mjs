// Drives workflows/build.js against scripted review results so the ways the
// review loop can end are each observed, not assumed (→ conventions/20-review-gate.md:
// a gate that passes is not evidence the gate works).
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const source = readFileSync(resolve(here, '..', 'workflows', 'build.js'), 'utf8')

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function loadWorkflow() {
  return new AsyncFunction('args', 'agent', 'parallel', 'pipeline', 'log', 'phase', source.replace('export const meta', 'const meta'))
}

// Minimal stand-ins for the runtime hooks, matching what the workflow-authoring reference
// documents so that no case pins a shape the real runtime cannot produce: pipeline() runs each
// item through every stage independently and drops a throwing item to null; so does parallel().
const parallel = (thunks) => Promise.all(thunks.map((t) => t().catch(() => null)))
const pipeline = (items, ...stages) =>
  Promise.all(
    items.map((item, i) =>
      (async () => {
        let acc = item
        for (const stage of stages) acc = await stage(acc, item, i)
        return acc
      })().catch((err) => {
        // The drop is the runtime's behaviour, but it swallows a typo in a case's `over` hooks
        // just as quietly, leaving it to read as an unanswered lane. Say what was swallowed.
        console.log(`     (pipeline dropped item ${i}: ${err instanceof Error ? err.stack : String(err)})`)
        return null
      }),
    ),
  )

function finding(over = {}) {
  return { file: 'src/a.py', severity: 'blocker', summary: 'boom', causedByPreviousFix: false, ...over }
}

// `rounds` supplies the findings each review round returns, in order. `over` replaces what
// develop returns or makes an agent misbehave, so the paths that end the loop without a
// verdict are reachable too.
const keyOf = (f) => (f.line != null ? `${f.file}:${f.line}` : `${f.file}:${f.summary}`)

// The criterion every lane reports unless a case says otherwise: a command with its red.
const CRIT = { criterion: 'C-01', command: 'uv run pytest tests/a', passed: true, red: 'observed', redOutput: '1 failed' }
const devWith = (criteria) => ({ worktree: '/tmp/wt', branch: 'lane-a', head: 'sha0', criteria })

function makeAgent(rounds, over = {}, seen = { labels: [], isolation: {}, prompts: {}, schemas: {}, opts: {} }) {
  // The round advances on the first verify call of a round, once all its lenses have answered;
  // counting review calls would hand each lens of one round a different entry from `rounds`.
  let round = 0
  let lensInRound = 0
  let measureCalls = 0
  // What each lane's develop reported, and the head last measured for it, so the stubs after
  // it answer about the same criteria and the same commit.
  const devs = {}
  const heads = {}
  let frozenBase = null
  const ranOn = (label, lane) => (over.ranOn ? over.ranOn(label, heads[lane]) : heads[lane])
  const findingsNow = () => rounds[Math.min(round, rounds.length - 1)] ?? []

  return async (prompt, opts = {}) => {
    const label = opts.label ?? ''
    seen.labels.push(label)
    // Where a call runs, what it was told, and on which model are dispatch an outcome cannot see.
    seen.isolation[label] = opts.isolation
    seen.prompts[label] = prompt
    seen.schemas[label] = opts.schema
    seen.opts[label] = opts
    const laneOf = label.split(':')[1]?.split('#')[0]
    if (label === 'freeze-check') {
      if (over.freezeCheckThrows) throw new Error('freeze agent died hard')
      if (over.freezeCheckDies) return null
      // Defaults model a healthy tool and one passing row per boundary that declares a schema.
      const schemaBoundaries = (over.boundaries ?? []).filter((b) => b.schema)
      frozenBase = over.frozenBase ?? over.frozenHead ?? 'f00dbabe'
      return {
        missing: over.missingFrozen ?? [],
        head: over.frozenHead ?? 'f00dbabe',
        base: frozenBase,
        // An answer missing the field outright — schema-invalid, and it must not read as passing.
        ...(over.omitFreezeTool ? {} : { tool: over.freezeTool ?? { exit: 0, output: 'check-jsonschema, version 0.38.0' } }),
        checked: over.freezeChecked ?? schemaBoundaries.map((b) => ({ boundary: b.name, exit: 0, output: 'ok' })),
      }
    }
    if (label.startsWith('develop:')) {
      // eslint-disable-next-line no-throw-literal
      if ('throws' in over) throw over.throws
      if (over.developDies) return null
      const laneName = label.slice('develop:'.length)
      if (over.develop) return (devs[laneName] = over.develop)
      // A producer lane reports a criterion satisfying every producer condition by default;
      // `producerCommand` overrides just the command, `omitProducerCriterion` drops it.
      const produced = (over.boundaries ?? []).filter((b) => b.schema && b.producer === laneName)
      const criteria = [
        CRIT,
        ...(over.omitProducerCriterion
          ? []
          : produced.map((b) => ({
              criterion: `schema check for "${b.name}"`,
              command: over.producerCommand ? over.producerCommand(b) : `rm -rf dump && uvx check-jsonschema@0.38.0 --schemafile ${b.schema} dump/out.json`,
              passed: true,
              red: 'sabotage',
              redOutput: 'dump/out.json: additional property',
            }))),
      ]
      return (devs[laneName] = devWith(criteria))
    }
    if (label.startsWith('fix:')) return over.fixDies ? null : { summary: 'fixed it' }
    // Stands in for the agent that reads git in the lane's worktree, independently of the fix.
    // `#0` measures develop; the fix measurements are indexed from 0 by `fixTouchedSeq`.
    if (label.startsWith('touched:')) {
      const n = measureCalls++
      // `true` kills every measurement; a number kills the call at that index and every one after.
      if (over.touchedDies === true || n >= over.touchedDies) return null
      const causation = n === 0
        ? []
        : over.fixTouchedSeq
          ? (over.fixTouchedSeq[n - 1] ?? over.fixTouchedSeq[over.fixTouchedSeq.length - 1])
          : (over.fixTouched ?? ['src/a.py'])
      const m = { head: `m${n}`, branchTip: `m${n}`, base: frozenBase, trackedChanges: [], untracked: [], ownershipDiff: [], causationDiff: causation }
      const answer = over.measure ? over.measure(label, m) : m
      heads[laneOf] = answer.head
      return answer
    }
    if (label.startsWith('verify:') || label.startsWith('reverify:')) {
      if (over.verifierDies) return null
      // Keys are read from the prompt, so a re-verification answers for exactly what it was sent.
      const keys = [...prompt.matchAll(/^- key: (.*)$/gm)].map((m) => m[1])
      let verdicts = keys.map((key) => ({
        key,
        state: over.refuteBlockers ? 'refuted' : 'confirmed',
        commandsRun: 2,
        evidence: 'stub',
        ...(over.verdict ? over.verdict(label, key) : {}),
      }))
      if (over.emptyVerdicts) verdicts = []
      if (over.dropOneVerdict) verdicts = verdicts.slice(1)
      // Both a confirmed and a refuted row for the same key — schema-valid, self-contradicting.
      if (over.contradictoryVerdicts && keys.length) {
        verdicts = [...verdicts, { key: keys[0], state: 'refuted', commandsRun: 2, evidence: 'stub' }]
      }
      if (label.startsWith('verify:')) {
        round++
        lensInRound = 0
      }
      return { head: ranOn(label, laneOf), verdicts }
    }
    if (label.startsWith('review:')) {
      if (over.reviewerDies) throw new Error('reviewer died')
      // A per-lens sequence, so a round where only one lens stayed silent is expressible.
      const ran = over.commandsRunSeq
        ? (over.commandsRunSeq[lensInRound] ?? 0)
        : (over.commandsRun ?? 3)
      lensInRound++
      return { head: ranOn(label, laneOf), commandsRun: ran, tool: 'Claude', findings: findingsNow() }
    }
    // Re-runs what develop reported and reads the same criteria back as the brief.
    if (label.startsWith('recheck:')) {
      if (over.recheckDies) return null
      // A resumed lane has no develop report; its brief holds the default criterion.
      const criteria = devs[laneOf]?.criteria ?? [CRIT]
      const r = {
        head: ranOn(label, laneOf),
        results: criteria.filter((c) => c.command && c.command !== '[human]').map((c) => ({ criterion: c.criterion, exit: 0, output: 'ok' })),
        brief: criteria.map((c) => ({ id: c.criterion, sentence: `the ${c.criterion} sentence`, command: c.command || '[human]' })),
      }
      return over.recheck ? over.recheck(label, r) : r
    }
    return null
  }
}

async function run(rounds, over = {}) {
  const wf = loadWorkflow()
  const seen = { labels: [], isolation: {}, prompts: {}, schemas: {}, opts: {} }
  // `rawArgs` hands the workflow whatever the case says, object or not — the way arguments
  // reach it when they arrive as text. Everything else builds the normal object.
  const args =
    'rawArgs' in over
      ? over.rawArgs
      : {
          planDir: '.plans',
          base: 'main',
          lanes: [over.lane ?? { name: 'a', owns: ['src/a/'], security: false }],
          boundaries: over.boundaries ?? [],
          // What `/dev-harness:build` declares after writing the contract files. A case can
          // drop it to reach the refusal.
          ...(over.omitFrozen ? {} : { boundariesFrozen: true }),
        }
  const out = await wf(args, makeAgent(rounds, over, seen), parallel, pipeline, () => {}, () => {})
  return { ...out, labels: seen.labels, isolation: seen.isolation, prompts: seen.prompts, schemas: seen.schemas, opts: seen.opts }
}

// How a call was dispatched, checked on both the refusal path and the lane path — a refusal
// is decided by the freeze check, so the case that pins where that check ran never gets to
// the lane results.
function dispatchChecks(expect, out) {
  const why = []
  for (const [label, want] of Object.entries(expect.isolation ?? {})) {
    if (out.isolation[label] !== want) why.push(`isolation[${label}]=${out.isolation[label]}`)
  }
  for (const [label, re] of Object.entries(expect.prompt ?? {})) {
    if (!re.test(out.prompts[label] ?? '')) why.push(`prompt[${label}] does not match ${re}`)
  }
  // A lane on no boundary must be told nothing about one — the absence is the assertion.
  for (const [label, re] of Object.entries(expect.promptExcludes ?? {})) {
    if (re.test(out.prompts[label] ?? '')) why.push(`prompt[${label}] matches ${re}, and must not`)
  }
  // The schema handed to `agent()` is what forces a field to be reported at all.
  // `{ at, fields }` descends through the named array properties to their item schema.
  for (const [label, want] of Object.entries(expect.schemaRequired ?? {})) {
    const { at = [], fields } = Array.isArray(want) ? { fields: want } : want
    const req = at.reduce((sc, k) => sc?.properties?.[k]?.items, out.schemas?.[label])?.required ?? []
    const missing = fields.filter((f) => !req.includes(f))
    if (missing.length) why.push(`schema[${label}].required is missing ${JSON.stringify(missing)}`)
  }
  // Dispatch options such as model and effort, key by key; `undefined` pins an absence.
  for (const [label, want] of Object.entries(expect.opts ?? {})) {
    for (const [k, v] of Object.entries(want)) {
      if (out.opts?.[label]?.[k] !== v) why.push(`opts[${label}].${k}=${out.opts?.[label]?.[k]}`)
    }
  }
  return why
}

// One row per refusal `checkShape` can produce: name, the path the note must name, the value
// landing there, and the words naming the cause. The path also decides what the row overrides
// and the first half of the expected note, so no row passes on a message about another field.
const LANE = { name: 'a', owns: ['src/a/'], security: false }
// A lane picked up where it halted: it already has a worktree, so it gets no fresh one.
const RESUMED = { ...LANE, resumeFrom: { worktree: '/tmp/wt2', branch: 'lane-a' }, resumeNote: 'criteria-failed: C-01' }
const BOUNDARY = { name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }
const SCHEMA_BOUNDARY = { ...BOUNDARY, schema: '.plans/contracts/api.schema.json', producer: 'a' }
const SHAPE_ROWS = [
  ['a misspelled top-level key is refused rather than defaulted', 'args', { lanes: [LANE], conventionDir: '/abs/conventions', boundariesFrozen: true }, /unknown key "conventionDir"/],
  ['arguments carrying no lanes at all are refused by name', 'args', { boundariesFrozen: true }, /declares no lanes/],
  ['lanes arriving as text of its own is refused rather than thrown out of', 'args.lanes', { lanes: JSON.stringify([LANE]), boundaries: [], boundariesFrozen: true }, /must be a list of lane objects/],
  ['boundaries arriving as text of its own is refused rather than thrown out of', 'args.boundaries', { lanes: [LANE], boundaries: JSON.stringify([BOUNDARY]), boundariesFrozen: true }, /must be a list of boundary objects/],
  ['a base that is not a string is refused', 'args.base', { lanes: [LANE], base: {}, boundariesFrozen: true }, /is \{\}, and must be a non-empty string/],
  ['a base present but empty is refused', 'args.base', { lanes: [LANE], base: '', boundariesFrozen: true }, /is "", and must be a non-empty string/],
  ['a lane that is a name rather than an object is refused', 'args.lanes[0]', 'auth', /is "auth", not an object/],
  ['a lane object with no name is refused', 'args.lanes[0]', { owns: ['src/a/'], security: false }, /declares no name/],
  ['a lane that owns nothing is refused', 'args.lanes[0]', { name: 'a', security: false }, /declares no owns/],
  ['a lane that declares no security is refused', 'args.lanes[0]', { name: 'a', owns: ['src/a/'] }, /declares no security/],
  ['a lane whose security is not a boolean is refused', 'args.lanes[0].security', { name: 'a', owns: ['src/a/'], security: 'true' }, /must be a boolean/],
  ['a misspelled lane key is refused rather than defaulted', 'args.lanes[0]', { name: 'a', owns: ['src/a/'], security: false, onws: ['src/typo/'] }, /unknown key "onws"/],
  ['a lane name that traverses out of the plan directory is refused', 'args.lanes[0].name', { name: '../escape', owns: ['src/a/'], security: false }, /must be a name matching/],
  ['owns arriving as text of its own is refused', 'args.lanes[0].owns', { name: 'a', owns: '["src/a/"]', security: false }, /must be a non-empty list of path strings/],
  ['an owns entry that is not a path string is refused', 'args.lanes[0].owns', { name: 'a', owns: ['src/a/', 42], security: false }, /must be a non-empty list of path strings/],
  ['a boundary that is a name rather than an object is refused', 'args.boundaries[0]', 'api', /is "api", not an object/],
  ['a boundary that pins no lane is refused', 'args.boundaries[0]', { name: 'api', contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }, /declares no lanes/],
  // `test` is not a known boundary field — a stale PLAN.md carrying it is refused loudly
  // rather than silently accepted as a boundary with no contract path.
  ['a boundary using a `test` key is refused as an unknown key', 'args.boundaries[0]', { name: 'api', lanes: ['a'], test: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }, /unknown key "test"/],
  ['a boundary with a contract but no sample is refused', 'args.boundaries[0]', { name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md' }, /declares no sample/],
  // Both paths are required, so a boundary missing either is refused here — before the freeze
  // check could skip it and leave every lane told its contract file exists unmeasured.
  ['a boundary with a sample but no contract is refused', 'args.boundaries[0]', { name: 'api', lanes: ['a'], sample: 'tests/fixtures/api.sample.json' }, /declares no contract/],
  // Sabotage: drop 'name' from the boundary required list.
  ['a boundary with no name is refused', 'args.boundaries[0]', { lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }, /declares no name/],
  // Sabotage: accept any string as a tier.
  ['a lane tier outside light, mid, top is refused', 'args.lanes[0].tier', { name: 'a', owns: ['src/a/'], security: false, tier: 'opus' }, /must be one of light, mid, top/],
  // Sabotage: accept any string as `planDir`.
  ['an absolute planDir is refused', 'args.planDir', { lanes: [LANE], planDir: '/abs/.plans', boundariesFrozen: true }, /is "\/abs\/\.plans", and must be a repository-relative path/],
  ['a planDir climbing out of the repository is refused', 'args.planDir', { lanes: [LANE], planDir: '../.plans', boundariesFrozen: true }, /must be a repository-relative path/],
  // Sabotage: skip the shape check on `allLanes` entries.
  ['an allLanes entry that is a bare name is refused', 'args.allLanes[0]', { lanes: [LANE], allLanes: ['a'], boundariesFrozen: true }, /is "a", not an object/],
  // Sabotage: drop the resumeNote-without-resumeFrom check.
  ['a resumeNote with no resumeFrom is refused', 'args.lanes[0]', { ...LANE, resumeNote: 'why' }, /has a resumeNote but no resumeFrom/],
  // Sabotage: accept any object as `resumeFrom`.
  ['a resumeFrom without a branch is refused', 'args.lanes[0].resumeFrom', { name: 'a', owns: ['src/a/'], security: false, resumeFrom: { worktree: '/tmp/wt' } }, /must be an object \{ worktree, branch \}/],
  ['a lane effort outside the effort values is refused', 'args.lanes[0].effort', { name: 'a', owns: ['src/a/'], security: false, effort: 'extreme' }, /must be one of low, medium/],
]

const escapeRe = (t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// A path naming an element overrides just that element; anything above one is the whole
// argument, and it goes in as text — the form a nested field can be mis-encoded in.
function shapeCase([name, where, value, cause]) {
  const over = where.startsWith('args.lanes[')
    ? { lane: value }
    : where.startsWith('args.boundaries[')
      ? { boundaries: [value] }
      : { rawArgs: JSON.stringify(value) }
  return { name, rounds: [[]], over, expect: { refused: new RegExp(`${escapeRe(where)} [^]*?${cause.source}`) } }
}

const cases = [
  {
    name: 'no blockers ends the loop',
    rounds: [[finding({ severity: 'minor' })]],
    expect: { outcome: 'passed', rounds: 1 },
  },
  {
    name: 'findings caused by the previous fix halt the loop',
    rounds: [
      [finding()],
      [finding({ causedByPreviousFix: true }), finding({ summary: 'b', causedByPreviousFix: true }), finding({ summary: 'c' })],
    ],
    expect: { outcome: 'regression-halt', rounds: 2, escalation: 'human' },
  },
  {
    // The reviewer flag is never set here, so the halt has to come from the loop noticing the
    // finding is unchanged. A loop that only believed `causedByPreviousFix` would grind to the cap.
    name: 'the same finding returning unchanged halts without any reviewer flag',
    rounds: [[finding()]],
    expect: { outcome: 'regression-halt', rounds: 2, escalation: 'human' },
  },
  {
    name: 'blockers that change every round hit the cap and call a person',
    rounds: [
      [finding({ summary: 'r1' })],
      [finding({ summary: 'r2' })],
      [finding({ summary: 'r3' })],
      [finding({ summary: 'r4' })],
      [finding({ summary: 'r5' })],
    ],
    expect: { outcome: 'round-cap', rounds: 5, escalation: 'human' },
  },
  {
    name: 'a blocker the verifier refutes never reaches the fix agent',
    rounds: [[finding()]],
    over: { refuteBlockers: true },
    expect: { outcome: 'passed', rounds: 1, noLabel: 'fix:', carriedState: [['boom', 'refuted']] },
  },
  {
    // A verifier that answers with nothing cleared nothing: an empty verdict list must not read
    // as refuting every blocker.
    name: 'a verifier returning no verdicts leaves the blocker standing',
    rounds: [[finding()]],
    over: { emptyVerdicts: true },
    expect: { outcome: 'verification-incomplete', rounds: 1, escalation: 'human', noLabel: 'fix:' },
  },
  {
    name: 'a develop agent that returns nothing is a failed lane',
    rounds: [[]],
    over: { developDies: true },
    expect: { outcome: 'develop-failed', noLabel: 'review:' },
  },
  {
    name: 'a fix agent that returns nothing halts the lane with its blockers',
    rounds: [[finding()]],
    over: { fixDies: true },
    expect: { outcome: 'fix-failed', rounds: 1, noLabel: 'touched:a#1' },
  },
  {
    name: 'a verifier that returns nothing at all stops the round',
    rounds: [[finding()]],
    over: { verifierDies: true },
    expect: { outcome: 'verification-incomplete', rounds: 1, escalation: 'human', noLabel: 'fix:' },
  },
  {
    // Schema-valid and self-contradicting: a true and a false row for the same key. Letting
    // either row win would drop a real blocker into a clean pass, so neither decides.
    name: 'a verifier contradicting itself decides nothing',
    rounds: [[finding()]],
    over: { contradictoryVerdicts: true },
    expect: { outcome: 'verification-incomplete', rounds: 1, escalation: 'human', noLabel: 'fix:' },
  },
  {
    name: 'a verdict missing for one of two blockers stops the round',
    rounds: [[finding({ summary: 'b1' }), finding({ summary: 'b2' })]],
    over: { dropOneVerdict: true },
    expect: { outcome: 'verification-incomplete', rounds: 1, escalation: 'human', noLabel: 'fix:' },
  },
  {
    // Confirming a blocker establishes the defect is real; it says nothing about who caused it.
    // A pre-existing blocker in a file the fix never touched, mislabelled as fix-induced, must
    // not halt the loop on that label alone — halting there leaves the blocker unfixed.
    name: 'a fix-causation claim about an untouched file does not halt the loop',
    rounds: [
      [finding({ file: 'src/a.py', summary: 'A' })],
      [finding({ file: 'src/untouched.py', summary: 'B', causedByPreviousFix: true })],
      [],
    ],
    over: { fixTouched: ['src/a.py'] },
    expect: { outcome: 'passed', rounds: 3, hasLabel: 'fix:a#2' },
  },
  {
    // Majors are carried by design and never fixed, so counting them let two of them
    // outvote a blocker that had actually changed and was still fixable.
    name: 'carried majors do not halt a lane whose blocker is still changing',
    rounds: [
      [finding({ severity: 'major', summary: 'm1' }), finding({ severity: 'major', summary: 'm2' }), finding({ summary: 'b1' })],
      [finding({ severity: 'major', summary: 'm1' }), finding({ severity: 'major', summary: 'm2' }), finding({ summary: 'b2' })],
      [],
    ],
    expect: { outcome: 'passed', rounds: 3, carried: ['m1', 'm2'] },
  },
  {
    // The reviewer and the fixer spell the same file differently, which is ordinary. A
    // plain string compare found nothing in common and quietly switched causation off.
    name: 'causation still counts when the two sides spell the path differently',
    rounds: [
      [finding({ file: './src/a.py', summary: 'A' })],
      [finding({ file: '/tmp/wt/src/a.py', summary: 'B', causedByPreviousFix: true })],
    ],
    over: { fixTouched: ['src/a.py'] },
    expect: { outcome: 'regression-halt', rounds: 2, escalation: 'human' },
  },
  {
    // Each measurement diffs from the head the previous one reported, so a round sees its
    // own fix only. An accumulated set would still hold src/a.py from round 1 and halt on
    // round 3's claim about it.
    name: 'each round measures only its own fix',
    rounds: [
      [finding({ file: 'src/a.py', summary: 'A' })],
      [finding({ file: 'src/b.py', summary: 'B' })],
      [finding({ file: 'src/a.py', summary: 'C', causedByPreviousFix: true })],
      [],
    ],
    over: { fixTouchedSeq: [['src/a.py'], ['src/b.py'], ['src/b.py']] },
    expect: { outcome: 'passed', rounds: 4, notOutcome: 'regression-halt' },
  },
  {
    // A stage that throws drops its lane to null, so the lane list the workflow reports is
    // shorter than the lane list it was given. That gap is reported as `unanswered` rather
    // than read as a pass — sabotage: drop the `filter(Boolean)` before the outcome split.
    name: 'a lane whose stage throws is counted unanswered, not passed',
    rounds: [[]],
    over: { throws: null },
    expect: { unanswered: 1, passedCount: 0 },
  },
  {
    name: 'a lane the plan declared security gets a security lens',
    rounds: [[]],
    over: { lane: { name: 'a', owns: ['src/a/'], security: true } },
    expect: { outcome: 'passed', hasLabel: 'review:a:security#1' },
  },
  {
    // A path that looks like a trust boundary is not a declaration; only `security: true` is,
    // and a lens nobody asked for reads as coverage of a boundary nobody assessed.
    name: 'a lane owning an auth path but declaring security false gets no security lens',
    rounds: [[]],
    over: { lane: { name: 'a', owns: ['src/api/auth/'], security: false } },
    expect: { outcome: 'passed', noLabel: 'review:a:security' },
  },
  {
    name: 'a lane whose own criteria failed never reaches review',
    rounds: [[]],
    over: { develop: { worktree: '/tmp/wt', branch: 'lane-a', head: 'sha0', criteria: [{ criterion: 'parser drops empties', command: 'pytest x', passed: false }] } },
    expect: { outcome: 'criteria-failed' },
  },
  {
    name: 'reviewers that all died do not count as a pass',
    rounds: [[]],
    over: { reviewerDies: true },
    expect: { outcome: 'review-incomplete', rounds: 1 },
  },
  {
    name: 'reviewers that ran no commands do not count as a pass',
    rounds: [[]],
    over: { commandsRun: 0 },
    expect: { outcome: 'review-unexecuted', rounds: 1 },
  },
  {
    // Two lenses that ran must not carry a third that did not into a clean pass: the silent
    // lens is precisely the one whose "no findings" carries no information.
    name: 'one silent lens among three still stops the pass',
    rounds: [[]],
    over: { lane: { name: 'a', owns: ['src/a/', 'src/b/'], security: false }, commandsRunSeq: [0, 2, 2] },
    expect: { outcome: 'review-unexecuted', rounds: 1 },
  },
  {
    // A single owned path means spansModules is false, so pinsInterface alone has to be
    // what still puts the lane through all three lenses (→ 20 §2).
    name: 'a lane pinned by a boundary gets three lenses even with one owned path',
    rounds: [[]],
    over: {
      lane: { name: 'a', owns: ['src/a/'], security: false },
      boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }],
    },
    expect: {
      outcome: 'passed',
      hasLabel: ['review:a:module#1', 'review:a:project#1', 'review:a:absence#1'],
    },
  },
  {
    // A lane is told its boundary's exact paths, not a directory to go browse for them.
    name: "a pinned lane's develop and review prompts name its boundary's exact contract and sample paths",
    rounds: [[]],
    over: {
      lane: { name: 'a', owns: ['src/a/'], security: false },
      boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }],
    },
    expect: {
      outcome: 'passed',
      prompt: {
        'develop:a': /- api: contract \.plans\/contracts\/api\.md, sample tests\/fixtures\/api\.sample\.json/,
        'review:a:module#1': /- api: contract \.plans\/contracts\/api\.md, sample tests\/fixtures\/api\.sample\.json/,
      },
    },
  },
  {
    // A lane on no boundary has nothing to be told about one — the block is omitted entirely
    // rather than rendered empty, and the pinned lane's own prompt still names its path.
    name: 'a lane on no boundary gets no contract or sample path, unlike a lane pinned by one',
    rounds: [[]],
    over: {
      rawArgs: JSON.stringify({
        lanes: [
          { name: 'a', owns: ['src/a/'], security: false },
          { name: 'b', owns: ['src/b/'], security: false },
        ],
        boundaries: [{ name: 'api', lanes: ['b'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }],
        boundariesFrozen: true,
      }),
    },
    expect: {
      outcome: 'passed',
      promptExcludes: { 'develop:a': /contract \.plans\/contracts\/api\.md/ },
      prompt: { 'develop:b': /- api: contract \.plans\/contracts\/api\.md, sample tests\/fixtures\/api\.sample\.json/ },
    },
  },
  {
    name: 'a lane awaiting a human verdict is held out of passed',
    rounds: [[]],
    over: { develop: { worktree: '/tmp/wt', branch: 'lane-a', head: 'sha0', criteria: [{ criterion: 'the warning reads well', command: '', passed: false }] } },
    expect: { outcome: 'pending-human', escalation: 'human' },
  },
  {
    name: 'non-blocker findings from an earlier round are carried out',
    rounds: [[finding(), finding({ summary: 'keep me', severity: 'major' })], []],
    expect: { outcome: 'passed', rounds: 2, carried: ['keep me'] },
  },
  {
    // Installed, the workflow is invokable as a skill beside the command. That path skips the
    // contract files that freeze the boundaries, so the lanes would fan out onto interfaces
    // nothing holds still — no agent may be dispatched at all.
    name: 'a caller that did not freeze the boundaries never reaches an agent',
    rounds: [[]],
    over: { omitFrozen: true },
    expect: { refused: /boundariesFrozen was not true/ },
  },
  {
    // The arguments can reach the script as JSON text rather than as the object that was
    // passed. Refusing that over the shape sends a caller who did nothing wrong to fix the
    // call, and the only fix it leaves them is to hardcode the flag.
    name: 'args arriving as JSON text encoding an object is parsed and runs',
    rounds: [[]],
    over: { rawArgs: JSON.stringify({ lanes: [{ name: 'a', owns: ['src/a/'], security: false }], boundariesFrozen: true }) },
    expect: { outcome: 'passed', rounds: 1 },
  },
  {
    // Parsing the text must not become a way past the freeze. What the text encodes is the
    // declaration, and text that omits it declares nothing.
    name: 'JSON text that omits the freeze is still refused over the freeze',
    rounds: [[]],
    over: { rawArgs: JSON.stringify({ lanes: [{ name: 'a', owns: ['src/a/'], security: false }] }) },
    expect: { refused: /boundariesFrozen was not true/ },
  },
  {
    // Parsing invents no fields: `42` parses to a number, which still has none. A caller who
    // really did send a scalar is the case that needs the call fixed rather than accommodated.
    name: 'a value that parses to something other than an object is refused for its shape',
    rounds: [[]],
    over: { rawArgs: '42' },
    expect: { refused: /did not arrive as an object/ },
  },
  {
    // Text that is not JSON at all reaches the same refusal — the parse attempt must not throw
    // out of the workflow on its way there.
    name: 'a value that is not JSON is refused rather than thrown out of',
    rounds: [[]],
    over: { rawArgs: 'not json' },
    expect: { refused: /did not arrive as an object/ },
  },
  {
    // Malformed text and a genuine scalar reach the same guard, and only the parser's words
    // tell them apart. Without them the note instructs its caller to do what they just did.
    name: 'text that is nearly JSON is refused in the parser own words',
    rounds: [[]],
    over: { rawArgs: '{"lanes":[{"name":"a"}],"boundariesFrozen":tru' },
    expect: { refused: /does not parse as JSON: .+/ },
  },
  {
    // `typeof [] === 'object'`, so without the array clause this reaches the freeze check and
    // a caller whose payload is the wrong shape is sent off to fix their declaration.
    name: 'JSON text encoding an array is refused for its shape, not the freeze',
    rounds: [[]],
    over: { rawArgs: JSON.stringify([{ name: 'a', owns: ['src/a/'], security: false }]) },
    expect: { refused: /did not arrive as an object/ },
  },
  {
    // Pins the `input === null` clause: `typeof null` is also 'object', so dropping it sends
    // null to the freeze refusal and no case notices.
    name: 'a null argument is refused for its shape, not the freeze',
    rounds: [[]],
    over: { rawArgs: null },
    expect: { refused: /did not arrive as an object/ },
  },
  ...SHAPE_ROWS.map(shapeCase),
  {
    // The arguments reaching the script as JSON text go through a parse the object path skips, and
    // every refusal after it has to hold on both paths. Sabotage: guard the missing-path refusal
    // with `&& typeof args !== 'string'` — the object cases all stay green.
    name: 'a missing contract file is refused by name when the arguments arrive as text',
    rounds: [[]],
    over: {
      rawArgs: JSON.stringify({ lanes: [LANE], boundaries: [BOUNDARY], boundariesFrozen: true }),
      missingFrozen: ['.plans/contracts/api.md'],
    },
    expect: { refused: /do not exist: \.plans\/contracts\/api\.md/ },
  },
  {
    // Declaring the freeze is not doing it: the lanes are told the contract files exist on the
    // strength of that declaration alone. The note names each absent path and the sha it was
    // absent at — without the sha a reader finds the file in their own tree and disbelieves it.
    name: 'a missing frozen path is refused by name, at the commit the lanes start from',
    rounds: [[]],
    over: {
      boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }],
      missingFrozen: ['.plans/contracts/api.md'],
      frozenHead: 'deadbee',
    },
    expect: {
      refused: /declared frozen but these contract, schema, sample or plan files do not exist: \.plans\/contracts\/api\.md — not at deadbee, the commit the lanes start from/,
    },
  },
  {
    // A freeze check reading the orchestrator's tree answers about a tree no lane works in,
    // and passes while every lane starts on a commit holding none of the contracts. It has to
    // be isolated and reset the way a lane is, and only the dispatch shows whether it was.
    name: 'the freeze check measures from a lane-shaped worktree reset to base',
    rounds: [[]],
    over: { boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }] },
    expect: {
      outcome: 'passed',
      rounds: 1,
      isolation: { 'freeze-check': 'worktree' },
      prompt: { 'freeze-check': /git reset --hard main/ },
    },
  },
  {
    // The stub answers `missingFrozen` whatever it was asked, so only the prompt shows that
    // both of a boundary's paths are sent to be measured.
    name: 'the freeze check is asked about both the contract and the sample path',
    rounds: [[]],
    over: { boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }] },
    expect: {
      outcome: 'passed',
      rounds: 1,
      prompt: { 'freeze-check': /- \.plans\/contracts\/api\.md\n- tests\/fixtures\/api\.sample\.json/ },
    },
  },
  {
    // A worktree is cut from origin/main, which may hold neither the frozen contracts nor the
    // briefs. Nothing but this instruction puts the lane on `base`, and no outcome shows it.
    name: 'a lane is told to reset to base before it reads anything',
    rounds: [[]],
    expect: {
      outcome: 'passed',
      rounds: 1,
      isolation: { 'develop:a': 'worktree' },
      prompt: { 'develop:a': /^Before anything else, run `git reset --hard f00dbabe`/ },
    },
  },
  {
    // Fail closed: a check that answered nothing measured nothing, and reading its silence as
    // "none missing" would put the declaration back in charge of itself.
    name: 'a freeze check that answers nothing refuses rather than assuming',
    rounds: [[]],
    over: { boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }], freezeCheckDies: true },
    expect: { refused: /unmeasured declaration is that same declaration/ },
  },
  {
    // The same evidentiary state reached by dying rather than by answering nothing. This is
    // the one agent call outside the pipeline, so the runtime does not turn its throw into a
    // null — uncaught, it left as a stack trace and the caller got no note to dispatch on.
    name: 'a freeze check that dies refuses in the same words, naming the death',
    rounds: [[]],
    over: { boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }], freezeCheckThrows: true },
    expect: { refused: /died \(freeze agent died hard\).*unmeasured declaration is that same declaration/ },
  },
  {
    // Sabotage: drop the brief and PLAN.md paths from `frozenPaths`.
    name: 'a plan with no boundaries still has its plan and briefs checked at base',
    rounds: [[]],
    expect: { outcome: 'passed', rounds: 1, prompt: { 'freeze-check': /- \.plans\/PLAN\.md\n- \.plans\/lane-a\.md/ } },
  },
  {
    // Both lanes read one brief, take one branch and answer to one label, so the second is
    // indistinguishable from the first in the results.
    name: 'two lanes of the same name are refused',
    rounds: [[]],
    over: {
      rawArgs: JSON.stringify({
        lanes: [{ name: 'a', owns: ['src/a/'], security: false }, { name: 'a', owns: ['src/b/'], security: false }],
        boundariesFrozen: true,
      }),
    },
    expect: { refused: /declares the same name twice/ },
  },
  {
    // An argument-less call and text carrying no argument are the same call. Answering one
    // with "your arguments were the wrong shape" sends it looking for a payload it never had.
    name: 'text carrying no argument is answered like an argument-less call',
    rounds: [[]],
    over: { rawArgs: '   ' },
    expect: { refused: /boundariesFrozen was not true/ },
  },
  {
    // A pinned lane gets three lenses instead of one (→ 20 §2). A boundary naming a lane that
    // does not exist pins nothing, so the lane is reviewed once and no outcome shows why.
    name: 'a boundary pinning a lane that does not exist is refused',
    rounds: [[]],
    over: { boundaries: [{ name: 'api', lanes: ['nonexistent'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }] },
    expect: { refused: /args\.boundaries\[0\]\.lanes\[0\] is "nonexistent", which no lane declares/ },
  },
  {
    // The accept-list's positive case: every key `commands/build.md` and `commands/spec.md`
    // mandate, which has to build — a key dropped from the list refuses every real plan.
    name: 'the payload the docs mandate is accepted and fans out',
    rounds: [[]],
    over: {
      rawArgs: JSON.stringify({
        planDir: '.plans',
        base: 'main',
        conventionsDir: '/abs/plugin/conventions',
        lanes: [{ name: 'a', owns: ['src/a/', 'src/shared/config.py'], security: true, tier: 'mid', effort: 'medium' }],
        boundaries: [
          { name: 'parser-validator', lanes: ['a'], contract: '.plans/contracts/parser-validator.md', sample: 'tests/fixtures/parser_out.sample.json' },
        ],
        boundariesFrozen: true,
      }),
    },
    expect: {
      outcome: 'passed',
      rounds: 1,
      hasLabel: 'review:a:security#1',
      prompt: { 'develop:a': /Work only inside your owned paths: src\/a\/, src\/shared\/config\.py\./ },
    },
  },
  {
    // Sabotage: remove the `failedChecks.length` refusal block — this then fans out
    // (or refuses with different wording) instead of naming the failing boundary.
    name: 'a sample that fails its schema check is refused naming the boundary and output',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      freezeChecked: [{ boundary: 'api', exit: 1, output: 'additional properties not allowed' }],
    },
    expect: { refused: /api \(exit 1: additional properties not allowed\)/ },
  },
  {
    // Sabotage: drop the `frozen.tool?.exit !== 0` refusal block entirely — this then falls
    // through to the schema-check-failed wording instead, or passes outright.
    name: 'a schema tool that cannot run is refused with wording distinct from a failing sample',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      freezeTool: { exit: 127, output: 'uvx: command not found' },
    },
    expect: { refused: /schema tool could not run/ },
  },
  {
    // Sabotage: remove the `uncheckedNames.length` arm of the one-to-one refusal.
    name: 'a schema boundary with no checked row is refused as unmeasured',
    rounds: [[]],
    over: { boundaries: [SCHEMA_BOUNDARY], freezeChecked: [] },
    expect: { refused: /unmeasured/ },
  },
  {
    // Sabotage: remove the `duplicatedNames.length` arm of the one-to-one refusal.
    name: 'a duplicate checked row for the same boundary is refused as unmeasured',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      freezeChecked: [
        { boundary: 'api', exit: 0, output: 'ok' },
        { boundary: 'api', exit: 0, output: 'ok' },
      ],
    },
    expect: { refused: /unmeasured/ },
  },
  {
    // Sabotage: remove the `unknownNames.length` arm of the one-to-one refusal.
    name: 'an unknown checked row naming no schema boundary is refused as unmeasured',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      freezeChecked: [
        { boundary: 'api', exit: 0, output: 'ok' },
        { boundary: 'ghost', exit: 0, output: 'ok' },
      ],
    },
    expect: { refused: /unmeasured/ },
  },
  {
    // Sabotage: build `detail` from `schemaBoundaries` instead of `failedChecks` — the
    // passing boundary then shows up in the note too.
    name: 'two schema boundaries with one failing names only the failing one',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY, { name: 'db', lanes: ['a'], contract: '.plans/contracts/db.md', sample: 'tests/fixtures/db.sample.json', schema: 'tests/fixtures/db.schema.json', producer: 'a' }],
      freezeChecked: [
        { boundary: 'api', exit: 0, output: 'ok' },
        { boundary: 'db', exit: 1, output: 'boom' },
      ],
    },
    expect: { refused: /^(?!.*api \(exit).*db \(exit 1: boom\).*$/ },
  },
  {
    // Sabotage: move the missing-path check after the schema checks — this then fails on the
    // schema-check-failed wording instead of the missing-path wording.
    name: 'missing path refusal wins even when the schema check would fail',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      missingFrozen: ['tests/fixtures/api.sample.json'],
      freezeChecked: [{ boundary: 'api', exit: 1, output: 'boom' }],
    },
    expect: { refused: /declared frozen but these contract, schema, sample or plan files do not exist/ },
  },
  {
    // Sabotage: always include `--schemafile` regardless of `b.schema` — this then matches
    // where it must not.
    name: 'a boundary without a schema gets no --schemafile line and needs no checked row',
    rounds: [[]],
    over: { boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }] },
    expect: { outcome: 'passed', rounds: 1, promptExcludes: { 'freeze-check': /--schemafile/ } },
  },
  {
    // Sabotage: drop `SCHEMA_CHECK`/`--version`/the per-boundary command line from the freeze
    // prompt — each is otherwise unobserved by any other case.
    name: "the freeze prompt names the schema tool, --version, and each schema boundary's exact paths",
    rounds: [[]],
    over: { boundaries: [SCHEMA_BOUNDARY] },
    expect: {
      outcome: 'passed',
      rounds: 1,
      prompt: {
        'freeze-check': /(?=[\s\S]*uvx check-jsonschema@0\.38\.0 --version)(?=[\s\S]*uvx check-jsonschema@0\.38\.0 --schemafile \.plans\/contracts\/api\.schema\.json tests\/fixtures\/api\.sample\.json)/,
      },
    },
  },
  {
    // Sabotage: drop the schema path from `boundaryContracts`'s per-boundary line.
    name: "a pinned lane's prompts include its boundary's schema path",
    rounds: [[]],
    over: { boundaries: [SCHEMA_BOUNDARY] },
    expect: {
      outcome: 'passed',
      prompt: {
        'develop:a': /- api: contract \.plans\/contracts\/api\.md, schema \.plans\/contracts\/api\.schema\.json, sample tests\/fixtures\/api\.sample\.json/,
      },
    },
  },
  {
    // Sabotage: remove the boundary-name duplicate check from the `complaint` chain.
    name: 'two boundaries of the same name are refused',
    rounds: [[]],
    over: {
      boundaries: [
        { name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' },
        { name: 'api', lanes: ['a'], contract: '.plans/contracts/api2.md', sample: 'tests/fixtures/api2.sample.json' },
      ],
    },
    expect: { refused: /args\.boundaries\[1\] repeats the name "api"/ },
  },
  {
    // Sabotage: drop the `schemaBoundaries.length` guard around the tool.exit check — a
    // plan with no schema boundary then refuses over a tool it never needed.
    name: 'a plan with no schema boundary fans out even if the schema tool is unavailable',
    rounds: [[]],
    over: {
      boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }],
      freezeTool: { exit: 127, output: 'uvx: command not found' },
    },
    expect: { outcome: 'passed', rounds: 1 },
  },
  {
    // Sabotage: change `frozen.tool?.exit !== 0` to `frozen.tool && frozen.tool.exit !== 0` —
    // an absent `tool` then reads as nothing to check instead of unmeasured.
    name: 'a schema boundary whose freeze result carries no tool field is refused',
    rounds: [[]],
    over: { boundaries: [SCHEMA_BOUNDARY], omitFreezeTool: true },
    expect: { refused: /schema tool could not run/ },
  },
  {
    // Sabotage: only list the first schema boundary's command in the freeze prompt.
    name: 'the freeze prompt contains both schema boundaries\' exact --schemafile commands',
    rounds: [[]],
    over: {
      boundaries: [
        SCHEMA_BOUNDARY,
        { name: 'db', lanes: ['a'], contract: '.plans/contracts/db.md', sample: 'tests/fixtures/db.sample.json', schema: 'tests/fixtures/db.schema.json', producer: 'a' },
      ],
    },
    expect: {
      outcome: 'passed',
      rounds: 1,
      prompt: {
        'freeze-check': /(?=[\s\S]*uvx check-jsonschema@0\.38\.0 --schemafile \.plans\/contracts\/api\.schema\.json tests\/fixtures\/api\.sample\.json)(?=[\s\S]*uvx check-jsonschema@0\.38\.0 --schemafile tests\/fixtures\/db\.schema\.json tests\/fixtures\/db\.sample\.json)/,
      },
    },
  },
  {
    // Sabotage: drop the `b.producer === lane.name` branch in `boundaryContracts` (always
    // emit the consumer sentence) — the producer's prompt then loses its own instruction.
    name: "a producer lane's prompt carries the fresh-dump instruction; a consumer's does not",
    rounds: [[]],
    over: {
      // `rawArgs` is what the workflow reads; `boundaries` here is only so the freeze-check
      // stub can derive its own default `checked` rows for the same boundary.
      boundaries: [{ name: 'api', lanes: ['a', 'b'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json', schema: '.plans/contracts/api.schema.json', producer: 'a' }],
      rawArgs: JSON.stringify({
        lanes: [
          { name: 'a', owns: ['src/a/'], security: false },
          { name: 'b', owns: ['src/b/'], security: false },
        ],
        boundaries: [{ name: 'api', lanes: ['a', 'b'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json', schema: '.plans/contracts/api.schema.json', producer: 'a' }],
        boundariesFrozen: true,
      }),
    },
    expect: {
      outcome: 'passed',
      prompt: {
        'develop:a': /You produce boundary "api"'s payload:.*deletes its dump directory, re-runs/,
      },
      promptExcludes: {
        'develop:b': /deletes its dump directory/,
      },
    },
  },
  {
    // Second half of the case above — sabotage: force the producer branch for every
    // boundary in `boundaryContracts` — the consumer's own sentence then says it produces.
    name: "a consumer lane's prompt says it consumes the boundary, not that it produces it",
    rounds: [[]],
    over: {
      boundaries: [{ name: 'api', lanes: ['a', 'b'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json', schema: '.plans/contracts/api.schema.json', producer: 'a' }],
      rawArgs: JSON.stringify({
        lanes: [
          { name: 'a', owns: ['src/a/'], security: false },
          { name: 'b', owns: ['src/b/'], security: false },
        ],
        boundaries: [{ name: 'api', lanes: ['a', 'b'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json', schema: '.plans/contracts/api.schema.json', producer: 'a' }],
        boundariesFrozen: true,
      }),
    },
    expect: {
      outcome: 'passed',
      prompt: {
        'develop:b': /You consume boundary "api"'s payload; its producer \("a"\) carries the schema check/,
      },
    },
  },
  {
    // Sabotage: drop the producer's name, or the trailing "is a finding" clause, from
    // `schemaFindingNotes`'s sentence.
    name: "the review prompt names the producer lane in the schema-check finding",
    rounds: [[]],
    over: { boundaries: [SCHEMA_BOUNDARY] },
    expect: {
      outcome: 'passed',
      prompt: {
        'review:a:module#1': /Lane "a" carries the schema check for boundary "api"; a brief or report missing it is a finding\./,
      },
    },
  },
  {
    // Sabotage: remove the `b?.schema && !b?.producer` clause from the `complaint` chain.
    name: 'a boundary with a schema but no producer is refused',
    rounds: [[]],
    over: { boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json', schema: '.plans/contracts/api.schema.json' }] },
    expect: { refused: /args\.boundaries\[0\] has a schema but names no producer/ },
  },
  {
    // Sabotage: remove the `!(b.lanes ?? []).includes(b.producer)` clause.
    name: "a producer that is not one of the boundary's lanes is refused",
    rounds: [[]],
    over: { boundaries: [{ name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json', schema: '.plans/contracts/api.schema.json', producer: 'ghost' }] },
    expect: { refused: /args\.boundaries\[0\]\.producer is "ghost", which is not one of this boundary's lanes/ },
  },
  {
    // Sabotage: remove the shared-sample/different-schema clause from the `complaint` chain.
    name: 'two boundaries sharing a sample but naming different schemas are refused',
    rounds: [[]],
    over: {
      boundaries: [
        { name: 'api', lanes: ['a'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/shared.sample.json', schema: '.plans/contracts/api.schema.json', producer: 'a' },
        { name: 'api2', lanes: ['a'], contract: '.plans/contracts/api2.md', sample: 'tests/fixtures/shared.sample.json', schema: '.plans/contracts/api2.schema.json', producer: 'a' },
      ],
    },
    expect: { refused: /args\.boundaries\[1\] shares a sample with another boundary but names a different schema/ },
  },
  {
    // Sabotage: remove the producer-criterion injection block at the top of `reviewLoop`.
    name: 'a producer lane that reports no --schemafile criterion fails like any other missed criterion',
    rounds: [[]],
    over: { boundaries: [SCHEMA_BOUNDARY], omitProducerCriterion: true },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // A consumer lane carries no `produced` boundary, so the injection never applies to it —
    // sabotage: drop the `b.producer === lane.name` filter (match any boundary with a schema).
    name: 'a consumer lane is not required to report the producer\'s schema-check criterion',
    rounds: [[]],
    over: {
      boundaries: [{ name: 'api', lanes: ['a', 'b'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json', schema: '.plans/contracts/api.schema.json', producer: 'a' }],
      rawArgs: JSON.stringify({
        lanes: [
          { name: 'a', owns: ['src/a/'], security: false },
          { name: 'b', owns: ['src/b/'], security: false },
        ],
        boundaries: [{ name: 'api', lanes: ['a', 'b'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json', schema: '.plans/contracts/api.schema.json', producer: 'a' }],
        boundariesFrozen: true,
      }),
    },
    expect: { outcome: 'passed', passedCount: 2 },
  },
  {
    // Sabotage: drop `...(b.schema ? [b.schema] : [])` from `frozenPaths` — the schema path
    // would then be absent from the freeze prompt's own missing-paths bullet list.
    name: "the freeze prompt's missing-paths list includes the schema path",
    rounds: [[]],
    over: { boundaries: [SCHEMA_BOUNDARY] },
    expect: {
      outcome: 'passed',
      rounds: 1,
      prompt: { 'freeze-check': /- \.plans\/contracts\/api\.schema\.json/ },
    },
  },
  {
    // Sabotage: drop the wiped-directory condition from `producerCheckIssue`.
    name: 'a producer criterion missing `rm -rf` does not satisfy the schema check',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      producerCommand: (b) => `uvx check-jsonschema@0.38.0 --schemafile ${b.schema} dump/out.json`,
    },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // Sabotage: match on the bare substring `check-jsonschema` instead of the pinned
    // `${SCHEMA_CHECK} --schemafile <schema>` prefix in `producerCheckFailure`.
    name: 'a producer criterion using an unpinned check-jsonschema call does not satisfy the schema check',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      producerCommand: (b) => `rm -rf dump && check-jsonschema --schemafile ${b.schema} dump/out.json`,
    },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // Sabotage: drop the `instances.includes(b.sample)` condition from `producerCheckIssue`.
    name: 'a producer criterion that checks the frozen sample instead of a fresh dump does not satisfy the schema check',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      producerCommand: (b) => `rm -rf dump && uvx check-jsonschema@0.38.0 --schemafile ${b.schema} ${b.sample}`,
    },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // Sabotage: accept any `rm -rf` in the command instead of one clearing the checked file's directory.
    name: 'a producer criterion that wipes some other directory does not satisfy the schema check',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      producerCommand: (b) => `rm -rf /tmp/scratch && uvx check-jsonschema@0.38.0 --schemafile ${b.schema} runs/old/out.json`,
    },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // Sabotage: drop the `&&`-only chain condition from `producerCheckIssue`.
    name: 'a producer criterion chained with `;` does not satisfy the schema check',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      producerCommand: (b) => `false && rm -rf dump ; uvx check-jsonschema@0.38.0 --schemafile ${b.schema} dump/out.json`,
    },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // Sabotage: compare the instance to the sample without `normalPath`.
    name: 'a producer criterion reaching the sample through `./` does not satisfy the schema check',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      producerCommand: (b) => `rm -rf tests && uvx check-jsonschema@0.38.0 --schemafile ${b.schema} ${b.sample.replace('/', '/./')}`,
    },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // Sabotage: drop newlines from the separator check in `producerCheckIssue`.
    name: 'a producer criterion split across lines does not satisfy the schema check',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      producerCommand: (b) => `false && rm -rf dump\nuvx check-jsonschema@0.38.0 --schemafile ${b.schema} dump/out.json`,
    },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // Sabotage: let `normalPath` drop the leading slash, equating /tmp/dump with tmp/dump.
    name: 'a producer criterion wiping an absolute directory but checking a relative one does not satisfy the schema check',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      producerCommand: (b) => `rm -rf /tmp/dump && uvx check-jsonschema@0.38.0 --schemafile ${b.schema} tmp/dump/out.json`,
    },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // The correct form, reading the sample as the stage's input — sabotage: reject any command
    // naming the sample anywhere, as a whole-command substring match would.
    name: 'a producer criterion with rm -rf, the pinned tool, and a fresh dump satisfies the schema check',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      producerCommand: (b) => `rm -rf dump && uv run python -m stage --input ${b.sample} --dump dump && uvx check-jsonschema@0.38.0 --schemafile ${b.schema} dump/out.json`,
    },
    expect: { outcome: 'passed' },
  },
  {
    // Sabotage: drop `&& v.commandsRun > 0` from `stateOf` — a read-only confirmation then reaches the fix.
    name: 'a confirmation that ran nothing is unverified, re-verified once, and halts unfixed',
    rounds: [[finding()]],
    over: { verdict: () => ({ state: 'confirmed', commandsRun: 0 }) },
    expect: {
      outcome: 'unverified-blocker',
      rounds: 1,
      escalation: 'human',
      noLabel: 'fix:',
      hasLabel: ['reverify:a#1', 'recheck:a#1'],
      prompt: { 'reverify:a#1': /Reproduce each one/ },
    },
  },
  {
    // Sabotage: require commands for `confirmed` only — a read-only refutation then clears the blocker.
    name: 'a refutation that ran nothing does not clear the blocker',
    rounds: [[finding()]],
    over: { verdict: () => ({ state: 'refuted', commandsRun: 0 }) },
    expect: { outcome: 'unverified-blocker', rounds: 1, escalation: 'human', noLabel: 'fix:' },
  },
  {
    // Sabotage: skip merging the re-verification's states — the reproduced blocker then halts unfixed.
    name: 'a blocker reproduced on re-verification goes to the fix',
    rounds: [[finding()], []],
    over: { verdict: (label) => (label.startsWith('verify:') ? { state: 'unverified', commandsRun: 0 } : {}) },
    expect: { outcome: 'passed', rounds: 2, hasLabel: 'fix:a#1' },
  },
  {
    // Sabotage: take `passed` from develop's report instead of the recheck's exit code.
    name: 'a criterion the fix broke fails the recheck after the last fix',
    rounds: [[finding()], []],
    over: { recheck: (label, r) => (label === 'recheck:a#2' ? { ...r, results: r.results.map((x) => ({ ...x, exit: 1 })) } : r) },
    expect: { outcome: 'criteria-failed', rounds: 2, hasLabel: 'fix:a#1' },
  },
  {
    // Sabotage: return `clean(...)` directly when round 1 has no blocker, skipping `finish`.
    name: 'a lane clean in round 1 still has its criteria re-run',
    rounds: [[]],
    over: { recheck: (label, r) => ({ ...r, results: r.results.map((x) => ({ ...x, exit: 1 })) }) },
    expect: { outcome: 'criteria-failed', rounds: 1, hasLabel: 'recheck:a#1' },
  },
  {
    // Sabotage: re-apply the producer check with the reported criteria instead of the rechecked ones.
    name: 'a producer check failing on the recheck fails the lane',
    rounds: [[]],
    over: {
      boundaries: [SCHEMA_BOUNDARY],
      recheck: (label, r) => ({ ...r, results: r.results.map((x) => (x.criterion.startsWith('schema check') ? { ...x, exit: 1 } : x)) }),
    },
    expect: { outcome: 'criteria-failed', rounds: 1, note: /producer check for boundary "api"/ },
  },
  {
    // Sabotage: remove the empty-criteria check at the top of `reviewLoop`.
    name: 'a lane reporting no criteria fails without review',
    rounds: [[]],
    over: { develop: devWith([]) },
    expect: { outcome: 'criteria-failed', noLabel: 'review:' },
  },
  {
    // Sabotage: remove `ownsOverlap(lanes)` from the `complaint` chain.
    name: 'two lanes whose owns overlap are refused',
    rounds: [[]],
    over: { rawArgs: JSON.stringify({ lanes: [{ name: 'a', owns: ['src/a'], security: false }, { name: 'b', owns: ['src/a/b/'], security: false }], boundariesFrozen: true }) },
    expect: { refused: /lane "b" owns "src\/a\/b\/", which overlaps lane "a"'s "src\/a"/ },
  },
  {
    // Sabotage: compare owns with a bare `startsWith`, without the `/` — sibling prefixes then overlap.
    name: 'lanes owning sibling paths that share a prefix are not an overlap',
    rounds: [[]],
    over: { rawArgs: JSON.stringify({ lanes: [{ name: 'a', owns: ['src/a/'], security: false }, { name: 'b', owns: ['src/ab/'], security: false }], boundariesFrozen: true }) },
    expect: { outcome: 'passed', passedCount: 2 },
  },
  {
    // Sabotage: remove the frozen-file ownership entry from the `complaint` chain.
    name: "a lane whose owns covers a boundary's frozen file is refused",
    rounds: [[]],
    over: { lane: { name: 'a', owns: ['src/a/', '.plans/contracts/'], security: false }, boundaries: [BOUNDARY] },
    expect: { refused: /owns entry "\.plans\/contracts\/" covers boundary "api"'s frozen file \.plans\/contracts\/api\.md/ },
  },
  {
    // Sabotage: drop the `outside` check from `measure`.
    name: 'a develop diff outside owns halts before review',
    rounds: [[]],
    over: { measure: (label, m) => ({ ...m, ownershipDiff: ['src/a/x.py', 'src/other.py'] }) },
    expect: { outcome: 'ownership-violated', rounds: 0, noLabel: 'review:', note: /src\/other\.py/ },
  },
  {
    // Sabotage: drop `trackedChanges` from the dirty list in `measure`.
    name: 'an uncommitted tracked change halts as a dirty worktree',
    rounds: [[]],
    over: { measure: (label, m) => ({ ...m, trackedChanges: [' M src/a/x.py'] }) },
    expect: { outcome: 'dirty-worktree', rounds: 0, noLabel: 'review:' },
  },
  {
    // Sabotage: drop `untracked` from the dirty list in `measure`.
    name: 'an untracked file under owns halts as a dirty worktree',
    rounds: [[]],
    over: { measure: (label, m) => ({ ...m, untracked: ['src/a/new.py'] }) },
    expect: { outcome: 'dirty-worktree', rounds: 0 },
  },
  {
    // Sabotage: drop the `owned` filter on `untracked` — the dump then reads as dirty.
    name: 'an untracked dump outside owns is not dirty',
    rounds: [[]],
    over: { measure: (label, m) => ({ ...m, untracked: ['runs/sample/out.json'] }) },
    expect: { outcome: 'passed', rounds: 1, prompt: { 'touched:a#0': /git ls-files --others --exclude-standard -- src\/a\// } },
  },
  {
    // Sabotage: let `measure` return `{ m }` when the agent answered nothing.
    name: 'a measurement that returns nothing after develop halts before review',
    rounds: [[]],
    over: { touchedDies: true },
    expect: { outcome: 'measurement-failed', rounds: 0, noLabel: 'review:' },
  },
  {
    // Sabotage: drop the `missing.length` arm of the recheck one-to-one check.
    name: 'a recheck missing a criterion row is incomplete',
    rounds: [[]],
    over: { recheck: (label, r) => ({ ...r, results: [] }) },
    expect: { outcome: 'recheck-incomplete', rounds: 1 },
  },
  {
    // Sabotage: drop the `duplicated.length` arm of the recheck one-to-one check.
    name: 'a recheck answering one criterion twice is incomplete',
    rounds: [[]],
    over: { recheck: (label, r) => ({ ...r, results: [...r.results, { ...r.results[0], exit: 1 }] }) },
    expect: { outcome: 'recheck-incomplete', rounds: 1 },
  },
  {
    // Sabotage: drop the `!re` arm — a dead recheck then throws or passes.
    name: 'a recheck that returns nothing is incomplete',
    rounds: [[]],
    over: { recheckDies: true },
    expect: { outcome: 'recheck-incomplete', rounds: 1 },
  },
  {
    // Sabotage: drop the `!re.brief?.length` arm — the drift comparison then passes on nothing.
    name: 'a recheck that read no brief criteria is incomplete',
    rounds: [[]],
    over: { recheck: (label, r) => ({ ...r, brief: [] }) },
    expect: { outcome: 'recheck-incomplete', rounds: 1, note: /read no criteria from the lane brief/ },
  },
  {
    // Sabotage: drop the missing-id arm of `criteriaDrift`.
    name: 'a brief criterion the lane never reported is drift',
    rounds: [[]],
    over: { recheck: (label, r) => ({ ...r, brief: [...r.brief, { id: 'C-02', sentence: 'empties are dropped', command: 'uv run pytest tests/b' }] }) },
    expect: { outcome: 'criteria-drift', rounds: 1, note: /C-02 is missing/ },
  },
  {
    // Sabotage: drop the command comparison from `criteriaDrift`.
    name: 'a criterion whose command was weakened from the brief is drift',
    rounds: [[]],
    over: { recheck: (label, r) => ({ ...r, brief: r.brief.map((b) => ({ ...b, command: 'uv run pytest tests/a tests/a_edge' })) }) },
    expect: { outcome: 'criteria-drift', rounds: 1 },
  },
  {
    // Sabotage: drop the kind arm of `criteriaDrift`.
    name: 'a [human] criterion turned into a command is drift',
    rounds: [[]],
    over: { recheck: (label, r) => ({ ...r, brief: r.brief.map((b) => ({ ...b, command: '[human]' })) }) },
    expect: { outcome: 'criteria-drift', rounds: 1, note: /is a command criterion, and the brief makes it a human one/ },
  },
  {
    // Sabotage: drop `normalId` from `criteriaDrift` — the brief's `[human]` marker then reads as a different id.
    name: 'a [human] marker on the brief id alone is not drift',
    rounds: [[]],
    over: {
      develop: devWith([CRIT, { criterion: 'the warning reads well', command: '', passed: false }]),
      recheck: (label, r) => ({ ...r, brief: r.brief.map((b) => (b.command === '[human]' ? { ...b, id: '[human] the warning reads well' } : b)) }),
    },
    expect: { outcome: 'pending-human', rounds: 1, escalation: 'human' },
  },
  {
    // Sabotage: compare commands without `.trim()`.
    name: 'a command differing from the brief only in surrounding whitespace is not drift',
    rounds: [[]],
    over: { recheck: (label, r) => ({ ...r, brief: r.brief.map((b) => ({ ...b, command: ` ${b.command}\t` })) }) },
    expect: { outcome: 'passed', rounds: 1 },
  },
  {
    // Sabotage: pass `{ red: false }` to the develop-time `withInjected`.
    name: 'a command criterion reported without red fails',
    rounds: [[]],
    over: { develop: devWith([{ criterion: 'C-01', command: 'uv run pytest tests/a', passed: true }]) },
    expect: { outcome: 'criteria-failed', noLabel: 'review:', note: /red for "C-01" was not recorded/ },
  },
  {
    // Sabotage: accept any non-empty `red` instead of `RED_KINDS` — a no-baseline record then passes.
    name: 'a no-baseline record is not a red',
    rounds: [[]],
    over: { develop: devWith([{ ...CRIT, red: 'no-baseline', redOutput: 'command not found at base' }]) },
    expect: { outcome: 'criteria-failed', noLabel: 'review:' },
  },
  {
    // Sabotage: drop `isText(c.redOutput)` from the red check.
    name: 'a red with no failing output fails',
    rounds: [[]],
    over: { develop: devWith([{ ...CRIT, redOutput: '' }]) },
    expect: { outcome: 'criteria-failed' },
  },
  {
    // Sabotage: drop the no-baseline instruction from `developPrompt`.
    name: 'the develop prompt says a check with no baseline needs a sabotage red',
    rounds: [[]],
    expect: { outcome: 'passed', prompt: { 'develop:a': /no baseline, which is not a red: after implementing,\s+sabotage the code it checks/ } },
  },
  {
    // Sabotage: drop the red list from the module lens prompt.
    name: 'the module lens is handed each criterion red to check',
    rounds: [[]],
    expect: { outcome: 'passed', prompt: { 'review:a:module#1': /- C-01 \(observed\): `uv run pytest tests\/a` — recorded: 1 failed/ } },
  },
  {
    // Sabotage: drop `carried` from the base fields of `result` — halts then lose earlier majors.
    name: 'a fix that dies still carries the non-blockers already found',
    rounds: [[finding(), finding({ severity: 'major', summary: 'keep me' })]],
    over: { fixDies: true },
    expect: { outcome: 'fix-failed', rounds: 1, carried: ['keep me'] },
  },
  {
    // Same sabotage, on a halt raised by the measurement rather than the loop.
    name: 'a dirty worktree after a fix still carries the non-blockers already found',
    rounds: [[finding(), finding({ severity: 'major', summary: 'keep me' })]],
    over: { measure: (label, m) => (label === 'touched:a#1' ? { ...m, trackedChanges: [' M src/a/x.py'] } : m) },
    expect: { outcome: 'dirty-worktree', rounds: 1, carried: ['keep me'] },
  },
  {
    // Sabotage: keep the first finding per key in `dedupe` — the minor then hides the blocker.
    // Sabotage: key on `f.line ?` truthiness — line 0 then keys by summary and the key changes.
    name: 'a minor and a blocker on one line merge to the blocker with both summaries',
    rounds: [[finding({ line: 0, severity: 'minor', summary: 'x' }), finding({ line: 0, summary: 'y' })], []],
    expect: { outcome: 'passed', rounds: 2, hasLabel: 'fix:a#1', prompt: { 'verify:a#1': /- key: src\/a\.py:0\n  claim: x \| y/ } },
  },
  {
    // Sabotage: build `lastFixTouched` from `ownershipDiff` — the cumulative diff then blames the fix.
    name: 'causation reads the diff since the previous head, not the diff since base',
    rounds: [
      [finding({ file: 'src/a/x.py', summary: 'A' })],
      [finding({ file: 'src/a/x.py', summary: 'B', causedByPreviousFix: true })],
      [],
    ],
    over: { measure: (label, m) => (label === 'touched:a#0' ? m : { ...m, ownershipDiff: ['src/a/x.py'], causationDiff: ['src/a/y.py'] }) },
    expect: { outcome: 'passed', rounds: 3, notOutcome: 'regression-halt', prompt: { 'touched:a#1': /diff --no-renames --name-only m0\.\.HEAD/ } },
  },
  {
    // Sabotage: drop `isolation: 'worktree'` from the review, verify or recheck dispatch.
    name: 'review, verify and recheck run isolated and reset to the measured head',
    rounds: [[finding()], []],
    expect: {
      outcome: 'passed',
      rounds: 2,
      isolation: { 'review:a:module#1': 'worktree', 'verify:a#1': 'worktree', 'recheck:a#2': 'worktree', 'fix:a#1': undefined },
      prompt: {
        'review:a:module#1': /git reset --hard m0`[^]*git diff f00dbabe\.\.m0/,
        'verify:a#1': /git reset --hard m0`/,
        'review:a:module#2': /git reset --hard m1`[^]*git diff f00dbabe\.\.m1/,
        'recheck:a#2': /git reset --hard m1`/,
      },
      promptExcludes: { 'review:a:module#1': /cd into/ },
    },
  },
  {
    // Sabotage: drop `...tierOpts(lane)` from the fix dispatch.
    name: "a lane's tier and effort set its develop and fix model, and the review keeps the session's",
    rounds: [[finding()], []],
    over: { lane: { name: 'a', owns: ['src/a/'], security: false, tier: 'top', effort: 'high' } },
    expect: {
      outcome: 'passed',
      opts: {
        'develop:a': { model: 'opus', effort: 'high' },
        'fix:a#1': { model: 'opus', effort: 'high' },
        'review:a:module#1': { model: undefined, effort: undefined },
      },
    },
  },
  {
    // Sabotage: drop `head`, `worktree`, `tool` or the `commandsRun` sum from `result`.
    name: 'the lane result names its lenses, their commands, the model family and the measured head',
    rounds: [[finding()], []],
    expect: { outcome: 'passed', rounds: 2, result: { lenses: ['module'], commandsRun: { module: 6 }, tool: 'Claude', head: 'm1', worktree: '/tmp/wt' } },
  },
  {
    // Sabotage: drop a field from `RECHECK_SCHEMA.required` or from `FROZEN_SCHEMA.required`.
    // Whatever the freeze check is not forced to report is a field the workflow then reads as
    // absent rather than as unmeasured.
    name: 'the recheck and freeze schemas require the sha they ran on and what they measured',
    rounds: [[]],
    expect: {
      outcome: 'passed',
      schemaRequired: {
        'recheck:a#1': ['head', 'results', 'brief'],
        'freeze-check': ['head', 'base', 'tool', 'checked'],
      },
    },
  },
  {
    // Sabotage: drop a field from the `required` list of the named schema.
    name: 'the verdict, measurement, recheck and findings schemas require their new fields',
    rounds: [[finding()], []],
    over: { verdict: (label) => (label.startsWith('verify:') ? { state: 'unverified', commandsRun: 0 } : {}) },
    expect: {
      outcome: 'passed',
      schemaRequired: {
        'verify:a#1': ['head', 'verdicts'],
        'reverify:a#1': { at: ['verdicts'], fields: ['key', 'state', 'commandsRun', 'evidence'] },
        'touched:a#1': ['head', 'branchTip', 'base', 'trackedChanges', 'untracked', 'ownershipDiff', 'causationDiff'],
        'recheck:a#2': { at: ['brief'], fields: ['id', 'sentence', 'command'] },
        'review:a:module#1': ['head', 'findings', 'commandsRun', 'tool'],
      },
    },
  },
  {
    // Sabotage: filter `awaiting` to human criteria not reported passed.
    name: 'a human criterion the lane reported as passed still awaits a verdict',
    rounds: [[]],
    over: { develop: devWith([CRIT, { criterion: 'C-02', command: '', passed: true }]) },
    expect: { outcome: 'pending-human', rounds: 1, escalation: 'human', result: { awaiting: ['C-02'] } },
  },
  {
    // Sabotage: let `failing` treat any non-empty command as a command.
    name: 'a criterion whose command is the literal [human] is a human criterion',
    rounds: [[]],
    over: { develop: devWith([CRIT, { criterion: 'C-02', command: '[human]', passed: false }]) },
    expect: { outcome: 'pending-human', rounds: 1, escalation: 'human', promptExcludes: { 'recheck:a#1': /C-02: `\[human\]`/ } },
  },
  {
    // Sabotage: collapse internal whitespace before comparing commands.
    name: 'a command whose quoted whitespace differs from the brief is drift',
    rounds: [[]],
    over: {
      develop: devWith([{ ...CRIT, command: "test 'a  b' = 'a b'" }]),
      recheck: (label, r) => ({ ...r, brief: [{ id: 'C-01', sentence: 's', command: "test 'a b' = 'a b'" }] }),
    },
    expect: { outcome: 'criteria-drift', rounds: 1 },
  },
  {
    // Sabotage: have the recheck read the brief from its own tree instead of `git show <base>:`.
    name: 'the brief is read at base, so a lane that weakened its own brief drifts',
    rounds: [[]],
    over: {
      develop: devWith([{ ...CRIT, command: 'uv run pytest tests/a -k smoke' }]),
      recheck: (label, r) => ({ ...r, brief: [{ id: 'C-01', sentence: 's', command: CRIT.command }] }),
    },
    expect: { outcome: 'criteria-drift', rounds: 1, prompt: { 'recheck:a#1': /git show f00dbabe:\.plans\/lane-a\.md/ } },
  },
  {
    // Sabotage: drop `guard` from `RED_KINDS`, or its exemption wording from the develop prompt.
    name: 'a guard red recorded with its exemption reason is accepted',
    rounds: [[]],
    over: { develop: devWith([{ ...CRIT, red: 'guard', redOutput: 'standing invariant; passes at base: 3 passed' }]) },
    expect: { outcome: 'passed', prompt: { 'develop:a': /`guard` for a standing\s+invariant, with the reason it is exempt or its passing output at the base commit/ } },
  },
  {
    // Sabotage: drop `--no-renames` from the ownership diff.
    name: 'a file moved into owns from outside is an ownership violation',
    rounds: [[]],
    over: { measure: (label, m) => ({ ...m, ownershipDiff: ['lib/moved.py', 'src/a/moved.py'] }) },
    expect: { outcome: 'ownership-violated', rounds: 0, note: /lib\/moved\.py/, prompt: { 'touched:a#0': /diff --no-renames --name-only f00dbabe\.\.HEAD → ownershipDiff/ } },
  },
  {
    // Sabotage: count any answer in `onHead`, whatever sha it ran on.
    name: 'a review that ran on another commit counts as no review',
    rounds: [[]],
    over: { ranOn: (label, h) => (label.startsWith('review:') ? 'elsewhere' : h) },
    expect: { outcome: 'review-incomplete', rounds: 1 },
  },
  {
    // Sabotage: drop `answer.head !== ctx.head` from `verifyRound`.
    name: 'a verification that ran on another commit decides nothing',
    rounds: [[finding()]],
    over: { ranOn: (label, h) => (label.startsWith('verify:') ? 'elsewhere' : h) },
    expect: { outcome: 'verification-incomplete', rounds: 1, escalation: 'human', noLabel: 'fix:', note: /ran on elsewhere/ },
  },
  {
    // Sabotage: drop the `re.head !== head` check from `finish`.
    name: 'a recheck that ran on another commit is incomplete',
    rounds: [[]],
    over: { ranOn: (label, h) => (label.startsWith('recheck:') ? 'elsewhere' : h) },
    expect: { outcome: 'recheck-incomplete', rounds: 1, note: /ran on elsewhere/ },
  },
  {
    // Sabotage: drop the `frozen.head !== frozen.base` refusal.
    name: 'a freeze check that did not land on base refuses',
    rounds: [[]],
    over: { frozenBase: 'b4se' },
    expect: { refused: /ran on f00dbabe, not on base b4se/, prompt: { 'freeze-check': /git rev-parse main` prints as `base`/ } },
  },
  {
    // Sabotage: drop the `branchTip` check from `measure`.
    name: 'a branch tip other than the worktree HEAD is a dirty worktree',
    rounds: [[]],
    over: { measure: (label, m) => ({ ...m, branchTip: 'ahead' }) },
    expect: { outcome: 'dirty-worktree', rounds: 0, note: /is not the worktree HEAD/, prompt: { 'touched:a#0': /git rev-parse lane-a → branchTip/ } },
  },
  {
    // Sabotage: give a resumed lane's develop agent a fresh isolated worktree and the reset prompt.
    name: 'a resumed lane continues in its worktree with a continue prompt, then takes the normal path',
    rounds: [[]],
    over: { lane: { name: 'a', owns: ['src/a/'], security: false, resumeFrom: { worktree: '/tmp/wt2', branch: 'lane-a' }, resumeNote: 'criteria-failed: C-01' } },
    expect: {
      outcome: 'passed',
      rounds: 1,
      hasLabel: ['develop:a', 'touched:a#0', 'recheck:a#1'],
      isolation: { 'develop:a': undefined },
      prompt: {
        'develop:a': /which halted: criteria-failed: C-01\.\nContinue in its existing worktree \/tmp\/wt2 on branch lane-a — do not reset it[^]*git show f00dbabe:\.plans\/lane-a\.md/,
        'touched:a#0': /Measure the worktree \/tmp\/wt2/,
      },
      promptExcludes: { 'develop:a': /git reset --hard/ },
      result: { worktree: '/tmp/wt2', branch: 'lane-a' },
    },
  },
  // A resumed lane is held to every check a fresh one is. Each check is a separate case because
  // a run reaches exactly one terminal outcome, so a case triggering all four would leave a
  // bypass of the three it never reaches invisible. Sabotage for each: guard that one check with
  // `&& !lane.resumeFrom`. Breaking the check outright is caught by the non-resumed cases and
  // proves nothing about the resume path.
  {
    name: 'a resumed lane must report red again, and fails without it',
    rounds: [[]],
    over: {
      lane: RESUMED,
      develop: devWith([{ criterion: 'C-01', command: 'uv run pytest tests/a', passed: true }]),
    },
    expect: { outcome: 'criteria-failed', rounds: 0, noLabel: 'review:', note: /red for "C-01" was not recorded/ },
  },
  {
    name: 'a resumed lane is compared against its brief at base like any other',
    rounds: [[]],
    over: {
      lane: RESUMED,
      recheck: (label, r) => ({ ...r, brief: [...r.brief, { id: 'C-02', sentence: 's', command: 'uv run pytest tests/b' }] }),
    },
    expect: { outcome: 'criteria-drift', rounds: 1, note: /C-02 is missing/ },
  },
  {
    name: 'a resumed lane whose diff reaches outside owns is an ownership violation',
    rounds: [[]],
    over: { lane: RESUMED, measure: (label, m) => ({ ...m, ownershipDiff: ['src/other.py'] }) },
    expect: { outcome: 'ownership-violated', rounds: 0, note: /src\/other\.py/, result: { worktree: '/tmp/wt2' } },
  },
  {
    name: 'a resumed lane with uncommitted work halts as a dirty worktree',
    rounds: [[]],
    over: { lane: RESUMED, measure: (label, m) => ({ ...m, trackedChanges: [' M src/a/x.py'] }) },
    expect: { outcome: 'dirty-worktree', rounds: 0, noLabel: 'review:', note: /uncommitted work/ },
  },
  {
    // Sabotage: validate boundary lanes against `lanes` only, ignoring `allLanes`.
    name: 'a partial re-run may pin a boundary to a lane named only in allLanes',
    rounds: [[]],
    over: {
      rawArgs: JSON.stringify({
        lanes: [{ name: 'a', owns: ['src/a/'], security: false }],
        allLanes: [{ name: 'a', owns: ['src/a/'] }, { name: 'b', owns: ['src/b/'] }],
        boundaries: [{ name: 'api', lanes: ['a', 'b'], contract: '.plans/contracts/api.md', sample: 'tests/fixtures/api.sample.json' }],
        boundariesFrozen: true,
      }),
    },
    expect: { outcome: 'passed', rounds: 1, hasLabel: 'review:a:absence#1' },
  },
  {
    // Sabotage: drop the lanes-in-allLanes check.
    name: 'a lane missing from allLanes is refused',
    rounds: [[]],
    over: { rawArgs: JSON.stringify({ lanes: [{ name: 'a', owns: ['src/a/'], security: false }], allLanes: [{ name: 'b', owns: ['src/b/'] }], boundariesFrozen: true }) },
    expect: { refused: /args\.lanes\[0\] is "a", which args\.allLanes omits/ },
  },
  {
    // Sabotage: carry `[refuted]` in the summary, or keep `state` on a merge whose sides disagree.
    name: 'a refutation stays on its own finding and does not mark another at the same line',
    rounds: [[finding({ line: 3, summary: 'r' }), finding({ file: 'src/b.py', summary: 'go' })], [finding({ line: 3, severity: 'minor', summary: 'm' })]],
    over: { verdict: (label, key) => (key === 'src/a.py:3' ? { state: 'refuted' } : {}) },
    expect: { outcome: 'passed', rounds: 2, carriedState: [['r | m', undefined]] },
  },
  {
    // Sabotage: drop the repeated-id arm of `criteriaDrift`.
    name: 'a criterion id reported twice is drift',
    rounds: [[]],
    over: { develop: devWith([CRIT, { ...CRIT, command: 'uv run pytest tests/b' }]) },
    expect: { outcome: 'criteria-drift', rounds: 1, note: /C-01 is reported more than once/ },
  },
  {
    // Sabotage: skip the `unverified.size` arm in `clean`.
    name: 'a blocker left unverified beside a fixed one still halts after the fix',
    rounds: [[finding({ summary: 'c' }), finding({ summary: 'u' })], []],
    over: { verdict: (label, key) => (key === 'src/a.py:u' ? { state: 'unverified', commandsRun: 0 } : {}) },
    expect: { outcome: 'unverified-blocker', rounds: 2, escalation: 'human', hasLabel: 'fix:a#1' },
  },
  // The measurement after a fix is held to the same checks as the one after develop. Separate
  // cases for the same reason the resume ones are separate. Sabotage for each: narrow that check
  // to the develop measurement with `&& label.endsWith('#0')`.
  {
    name: 'a fix that reaches outside owns is an ownership violation',
    rounds: [[finding()]],
    over: { measure: (label, m) => (label === 'touched:a#1' ? { ...m, ownershipDiff: ['src/other.py'] } : m) },
    expect: { outcome: 'ownership-violated', rounds: 1, note: /src\/other\.py/ },
  },
  {
    name: 'a measurement that returns nothing after a fix halts the lane',
    rounds: [[finding()], []],
    over: { touchedDies: 1 },
    expect: { outcome: 'measurement-failed', rounds: 1, noLabel: 'review:a:module#2' },
  },
  {
    // Sabotage: drop the `m.base !== baseSha` check from `measure`.
    name: 'a measurement resolving base to another sha than the freeze check halts',
    rounds: [[]],
    over: { measure: (label, m) => ({ ...m, base: 'elsewhere' }) },
    expect: { outcome: 'measurement-failed', rounds: 0, note: /resolved base to elsewhere, not the pinned f00dbabe/ },
  },
  {
    // Sabotage: check owns overlap among the run lanes only, not `allLanes`.
    name: 'a lane whose owns overlaps a lane not being run is refused',
    rounds: [[]],
    over: {
      rawArgs: JSON.stringify({
        lanes: [{ name: 'a', owns: ['src/a/'], security: false }],
        allLanes: [{ name: 'a', owns: ['src/a/'] }, { name: 'b', owns: ['src/a/x/'] }],
        boundariesFrozen: true,
      }),
    },
    expect: { refused: /lane "b" owns "src\/a\/x\/", which overlaps lane "a"'s "src\/a\/"/ },
  },
  {
    // Sabotage: keep `state` when any merged member has it, rather than every one.
    name: 'a minor merged with a later refutation at the same line is not refuted',
    rounds: [[finding({ line: 3, severity: 'minor', summary: 'm' }), finding({ file: 'src/b.py', summary: 'go' })], [finding({ line: 3, summary: 'r' })]],
    over: { verdict: (label, key) => (key === 'src/a.py:3' ? { state: 'refuted' } : {}) },
    expect: { outcome: 'passed', rounds: 2, carriedState: [['m | r', undefined]] },
  },
]

let failed = 0
for (const c of cases) {
  // A throw is this case's failure, not the run's: an escaping throw aborts the loop and one
  // broken case then hides every case after it.
  let out
  try {
    out = await run(c.rounds, c.over)
  } catch (err) {
    // JavaScript lets anything be thrown, and `err.message` on a thrown null throws again,
    // so the message is rendered defensively.
    failed++
    console.log(`FAIL ${c.name} -> threw: ${err instanceof Error ? err.message : String(err)}`)
    continue
  }
  // A refusal returns before the pipeline, so there is no lane result to read. What it has to
  // show is that nothing ran: an early return that still dispatched agents refused nothing.
  if (c.expect.refused) {
    const why = []
    if (out.passed !== undefined) why.push('the workflow ran the lanes')
    // A refusal dispatched no lane. `freeze-check` decides whether to refuse, so it is allowed;
    // these prefixes are every label lane work produces.
    const laneWork = out.labels.filter((l) => /^(develop|touched|review|verify|reverify|fix|recheck):/.test(l))
    if (laneWork.length) why.push(`lane agents were dispatched: ${JSON.stringify(laneWork)}`)
    // Each case pins the words naming its own cause: a refusal for the wrong reason sends the
    // caller to fix the wrong thing, and one shared pattern could not tell them apart.
    if (!c.expect.refused.test(out.note ?? '')) why.push(`note=${out.note}`)
    why.push(...dispatchChecks(c.expect, out))
    if (why.length) failed++
    console.log(`${why.length ? 'FAIL' : 'OK  '} ${c.name}${why.length ? ' -> ' + why.join(', ') : ''}`)
    continue
  }

  // A refusal on a case that expects a lane outcome has no `passed` to read; reading it anyway
  // throws out of the loop, which is the guard above extended to where the assertions run.
  if (out.passed === undefined) {
    failed++
    console.log(`FAIL ${c.name} -> refused unexpectedly: ${out.note}`)
    continue
  }

  const got = (out.passed[0] ?? out.halted[0]) ?? {}
  const why = []
  const check = (cond, msg) => {
    if (!cond) why.push(msg)
  }

  check(got.outcome === c.expect.outcome, `outcome=${got.outcome}`)
  // Stated separately from the expected outcome because the point of some cases is the exit
  // they must not take, and an equality check alone does not say which one was at stake.
  if (c.expect.notOutcome) check(got.outcome !== c.expect.notOutcome, `outcome=${got.outcome}`)
  if (c.expect.rounds !== undefined) check(got.rounds === c.expect.rounds, `rounds=${got.rounds}`)
  if (c.expect.carried) {
    check(
      c.expect.carried.every((s) => (got.carried ?? []).some((f) => f.summary.includes(s))),
      `carried=${JSON.stringify((got.carried ?? []).map((f) => f.summary))}`,
    )
  }
  // An exit that says "a person decides" is only true if something a caller can act on
  // fires. Asserting the outcome string alone let the escalation stay a note nobody reads.
  if (c.expect.escalation) {
    check(got.escalation === c.expect.escalation, `escalation=${got.escalation}`)
    check(out.escalations.filter((e) => e.lane === got.lane).length === 1, `escalations=${out.escalations.length}`)
  } else {
    check((out.escalations ?? []).length === 0, `escalations fired on a clean lane`)
  }
  if (c.expect.hasLabel) {
    const wanted = [].concat(c.expect.hasLabel)
    check(wanted.every((l) => out.labels.includes(l)), `labels=${JSON.stringify(out.labels)}`)
  }
  if (c.expect.noLabel) {
    check(!out.labels.some((l) => l.startsWith(c.expect.noLabel)), `labels=${JSON.stringify(out.labels)}`)
  }
  // Fields of the lane result itself, compared as JSON.
  for (const [k, v] of Object.entries(c.expect.result ?? {})) {
    check(JSON.stringify(got[k]) === JSON.stringify(v), `${k}=${JSON.stringify(got[k])}`)
  }
  // [summary, state] pairs: the carried finding with that summary must carry exactly that state.
  for (const [summary, state] of c.expect.carriedState ?? []) {
    const f = (got.carried ?? []).find((x) => x.summary === summary)
    check(f && f.state === state, `carried ${JSON.stringify(summary)}=${JSON.stringify(f)}`)
  }
  if (c.expect.note) check(c.expect.note.test(got.note ?? ''), `note=${got.note}`)
  // `got` reads only one lane; a multi-lane case pins the others by count.
  if (c.expect.passedCount !== undefined) check(out.passed.length === c.expect.passedCount, `passed.length=${out.passed.length}`)
  // Lanes the pipeline dropped. Read from the workflow's own count, not from `got`, which is
  // empty for a dropped lane and would make every absence read as agreement.
  if (c.expect.unanswered !== undefined) check(out.unanswered === c.expect.unanswered, `unanswered=${out.unanswered}`)
  why.push(...dispatchChecks(c.expect, out))

  if (why.length) failed++
  console.log(`${why.length ? 'FAIL' : 'OK  '} ${c.name}${why.length ? ' -> ' + why.join(', ') : ''}`)
}

process.exit(failed ? 1 : 0)
