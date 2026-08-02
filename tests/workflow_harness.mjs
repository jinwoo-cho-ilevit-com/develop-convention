// Drives workflows/build.js against scripted review results so the three ways the
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

// Minimal stand-ins for the runtime hooks. pipeline() runs each item through every
// stage independently, which is the property the script relies on.
const parallel = (thunks) => Promise.all(thunks.map((t) => t().catch(() => null)))
const pipeline = (items, ...stages) =>
  Promise.all(
    items.map(async (item, i) => {
      let acc = item
      for (const stage of stages) acc = await stage(acc, item, i)
      return acc
    }),
  )

function finding(over = {}) {
  return { file: 'src/a.py', severity: 'blocker', summary: 'boom', causedByPreviousFix: false, ...over }
}

// `rounds` supplies the findings each review round returns, in order. `over` replaces what
// develop returns or makes the reviewers misbehave, so the paths that end the loop without
// a verdict are reachable too.
const keyOf = (f) => `${f.file}:${f.line ?? ''}:${f.summary}`

function makeAgent(rounds, over = {}, seen = { labels: [] }) {
  // The round advances on the verify call, which happens once after a round's lenses have
  // all answered. Counting review calls instead would hand each lens of one round a
  // different entry from `rounds`, so a multi-lens case would stop modelling a round.
  let round = 0
  let lensInRound = 0
  // The measurement is one call per fix, so its own counter is what indexes a per-round
  // file set. `round` cannot: it advances on verify, before the fix this measures.
  let touchedCalls = 0
  const findingsNow = () => rounds[Math.min(round, rounds.length - 1)] ?? []

  return async (_prompt, opts = {}) => {
    const label = opts.label ?? ''
    seen.labels.push(label)
    if (label.startsWith('develop:')) {
      // eslint-disable-next-line no-throw-literal
      if ('throws' in over) throw over.throws
      return over.develop ?? { worktree: '/tmp/wt', branch: 'lane-a', head: 'sha0', criteria: [] }
    }
    if (label.startsWith('fix:')) return { summary: 'fixed it' }
    // Stands in for the agent that reads git in the lane's worktree. It answers
    // independently of what the fix stub returned, which is the separation under test.
    if (label.startsWith('touched:')) {
      // `true` kills every measurement; a number kills the call at that index and every one
      // after, which is how a round that measured is followed by a round that did not.
      if (over.touchedDies === true || touchedCalls >= over.touchedDies) return null
      const files = over.fixTouchedSeq
        ? (over.fixTouchedSeq[touchedCalls] ?? over.fixTouchedSeq[over.fixTouchedSeq.length - 1])
        : (over.fixTouched ?? ['src/a.py'])
      touchedCalls++
      return { files, head: `sha${touchedCalls}` }
    }
    if (label.startsWith('verify:')) {
      if (over.verifierDies) return null
      // Confirms whatever it was handed unless the case says otherwise, so the loop under
      // test is the review loop and not this stub.
      const blockers = findingsNow().filter((f) => f.severity === 'blocker')
      let verdicts = blockers.map((f) => ({ key: keyOf(f), confirmed: !over.refuteBlockers, evidence: 'stub' }))
      if (over.emptyVerdicts) verdicts = []
      if (over.dropOneVerdict) verdicts = verdicts.slice(1)
      // Both a true and a false row for the same key — schema-valid, self-contradicting.
      if (over.contradictoryVerdicts && blockers.length) {
        verdicts = [...verdicts, { key: keyOf(blockers[0]), confirmed: false, evidence: 'stub' }]
      }
      round++
      lensInRound = 0
      return { verdicts }
    }
    if (label.startsWith('review:')) {
      if (over.reviewerDies) throw new Error('reviewer died')
      // A per-lens sequence, so a round where only one lens stayed silent is expressible.
      const ran = over.commandsRunSeq
        ? (over.commandsRunSeq[lensInRound] ?? 0)
        : (over.commandsRun ?? 3)
      lensInRound++
      return { commandsRun: ran, findings: findingsNow() }
    }
    return null
  }
}

async function run(rounds, over = {}) {
  const wf = loadWorkflow()
  const seen = { labels: [] }
  const args = {
    planDir: '.plans',
    base: 'main',
    lanes: [over.lane ?? { name: 'a', owns: ['src/a/'] }],
    boundaries: over.boundaries ?? [],
    // What `/dev-harness:build` declares after writing the contract tests. A case can drop it
    // to reach the refusal.
    ...(over.omitFrozen ? {} : { boundariesFrozen: true }),
  }
  const out = await wf(args, makeAgent(rounds, over, seen), parallel, pipeline, () => {}, () => {})
  return { ...out, labels: seen.labels }
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
    // The reviewer flag is never set here. If the loop only believed `causedByPreviousFix`
    // it would grind to the cap, which is what it used to do — the old case set the flag
    // itself and so proved the branch fires, never that anything can reach it.
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
    expect: { outcome: 'passed', rounds: 1, noLabel: 'fix:' },
  },
  {
    // A verifier that answers with nothing is not a verifier that cleared anything. Keying
    // off `confirmed` made an empty list read as refuting every blocker, so one real
    // blocker reached `passed` with no fix and no escalation.
    // It goes to the fix agent and then halts on repetition, which is the designed path.
    // What matters is that it is not `passed`: an unanswered verdict used to clear it.
    name: 'a verifier returning no verdicts leaves the blocker standing',
    rounds: [[finding()]],
    over: { emptyVerdicts: true },
    expect: { outcome: 'verification-incomplete', rounds: 1, escalation: 'human', noLabel: 'fix:' },
  },
  {
    // Schema-valid and self-contradicting: a true and a false row for the same key. The
    // refutation used to win, dropping a real blocker into a clean pass.
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
    // Confirming a blocker establishes the defect is real; it says nothing about who caused
    // it. A real pre-existing blocker in a file the fix never touched, mislabelled as
    // fix-induced, used to halt the loop by itself and was then never fixed.
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
    // The fix agent is no longer asked which files it touched, so the only thing that can
    // supply the file list is the separate measurement — the halt here is proof it ran and
    // was read, and the label assertion pins which agent produced it.
    name: 'the causation check reads a measurement, not the fixer\'s word',
    rounds: [
      [finding({ file: 'src/measured.py', summary: 'A' })],
      [finding({ file: 'src/measured.py', summary: 'B', causedByPreviousFix: true })],
    ],
    over: { fixTouched: ['src/measured.py'] },
    expect: { outcome: 'regression-halt', rounds: 2, escalation: 'human', hasLabel: 'touched:a#1' },
  },
  {
    // Round 1 measures, round 2's measurement dies. The next round's causation claim then
    // has nothing to match against and must not halt: an empty set is the fail-safe side,
    // and carrying round 1's list forward would blame a fix nobody measured.
    name: 'a failed measurement disables causation without ending the loop',
    rounds: [
      [finding({ file: 'src/a.py', summary: 'A' })],
      [finding({ file: 'src/b.py', summary: 'B' })],
      [finding({ file: 'src/a.py', summary: 'C', causedByPreviousFix: true })],
      [],
    ],
    over: { touchedDies: 1 },
    expect: { outcome: 'passed', rounds: 4, notOutcome: 'regression-halt' },
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
    // JavaScript lets anything be thrown, and reading `.message` off a thrown null threw
    // again — so the guard against one case hiding the rest hid the rest.
    name: 'a case throwing a non-Error is reported, not fatal',
    rounds: [[]],
    over: { throws: null },
    expect: { threw: true },
  },
  {
    name: 'the case after a thrown non-Error still runs',
    rounds: [[]],
    expect: { outcome: 'passed', rounds: 1 },
  },
  {
    name: 'a lane touching a trust boundary gets a security lens',
    rounds: [[]],
    over: { lane: { name: 'a', owns: ['src/auth/'] } },
    expect: { outcome: 'passed', hasLabel: 'review:a:security#1' },
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
    // Two lenses that ran used to carry a third that did not into a clean pass, and the
    // silent lens is precisely the one whose "no findings" carries no information.
    name: 'one silent lens among three still stops the pass',
    rounds: [[]],
    over: { lane: { name: 'a', owns: ['src/a/', 'src/b/'] }, commandsRunSeq: [0, 2, 2] },
    expect: { outcome: 'review-unexecuted', rounds: 1 },
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
    // contract tests that freeze the boundaries, so the lanes would fan out onto interfaces
    // nothing holds still — no agent may be dispatched at all.
    name: 'a caller that did not freeze the boundaries never reaches an agent',
    rounds: [[]],
    over: { omitFrozen: true },
    expect: { refused: true },
  },
]

let failed = 0
for (const c of cases) {
  // A throw is this case's failure, not the run's. Letting it escape aborted the loop, so
  // one broken case hid every case after it — the same shape as every other defect this
  // harness exists to catch.
  let out
  try {
    out = await run(c.rounds, c.over)
  } catch (err) {
    // `err.message` on a thrown null is itself a throw, so the guard against one case
    // hiding the rest hid the rest. JavaScript lets anything be thrown; render defensively.
    const shown = err instanceof Error ? err.message : String(err)
    if (c.expect.threw) {
      console.log(`OK   ${c.name} (threw ${shown}, run continues)`)
    } else {
      failed++
      console.log(`FAIL ${c.name} -> threw: ${shown}`)
    }
    continue
  }
  // A refusal returns before the pipeline, so there is no lane result to read. What it has to
  // show is that nothing ran: an early return that still dispatched agents refused nothing.
  if (c.expect.refused) {
    const why = []
    if (out.passed !== undefined) why.push('the workflow ran the lanes')
    if (out.labels.length) why.push(`agents were dispatched: ${JSON.stringify(out.labels)}`)
    if (!/boundariesFrozen/.test(out.note ?? '')) why.push(`note=${out.note}`)
    if (why.length) failed++
    console.log(`${why.length ? 'FAIL' : 'OK  '} ${c.name}${why.length ? ' -> ' + why.join(', ') : ''}`)
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
  if (c.expect.hasLabel) check(out.labels.includes(c.expect.hasLabel), `labels=${JSON.stringify(out.labels)}`)
  if (c.expect.noLabel) {
    check(!out.labels.some((l) => l.startsWith(c.expect.noLabel)), `labels=${JSON.stringify(out.labels)}`)
  }

  if (why.length) failed++
  console.log(`${why.length ? 'FAIL' : 'OK  '} ${c.name}${why.length ? ' -> ' + why.join(', ') : ''}`)
}

process.exit(failed ? 1 : 0)
