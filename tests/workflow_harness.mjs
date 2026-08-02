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
function makeAgent(rounds, over = {}) {
  let reviewRound = 0
  return async (_prompt, opts = {}) => {
    const label = opts.label ?? ''
    if (label.startsWith('develop:')) {
      return over.develop ?? { worktree: '/tmp/wt', branch: 'lane-a', criteria: [] }
    }
    if (label.startsWith('fix:')) return 'fixed the thing'
    if (label.startsWith('review:')) {
      if (over.reviewerDies) throw new Error('reviewer died')
      const findings = rounds[Math.min(reviewRound++, rounds.length - 1)]
      return { commandsRun: over.commandsRun ?? 3, findings }
    }
    return null
  }
}

async function run(rounds, over = {}) {
  const wf = loadWorkflow()
  const args = { planDir: '.plans', base: 'main', lanes: [{ name: 'a', owns: ['src/a/'] }], boundaries: [] }
  return wf(args, makeAgent(rounds, over), parallel, pipeline, () => {}, () => {})
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
    expect: { outcome: 'regression-halt', rounds: 2 },
  },
  {
    name: 'persistent unrelated blockers hit the cap and call a person',
    rounds: [[finding()]],
    expect: { outcome: 'round-cap', rounds: 5 },
  },
  {
    name: 'a lane whose own criteria failed never reaches review',
    rounds: [[]],
    over: { develop: { worktree: '/tmp/wt', branch: 'lane-a', criteria: [{ criterion: 'parser drops empties', command: 'pytest x', passed: false }] } },
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
    name: 'non-blocker findings from an earlier round are carried out',
    rounds: [[finding(), finding({ summary: 'keep me', severity: 'major' })], []],
    expect: { outcome: 'passed', rounds: 2, carried: ['keep me'] },
  },
]

let failed = 0
for (const c of cases) {
  const out = await run(c.rounds, c.over)
  const got = (out.passed[0] ?? out.halted[0]) ?? {}
  let ok = got.outcome === c.expect.outcome
  if (ok && c.expect.rounds !== undefined) ok = got.rounds === c.expect.rounds
  if (ok && c.expect.carried) {
    ok = c.expect.carried.every((s) => (got.carried ?? []).some((f) => f.summary === s))
  }
  if (!ok) failed++
  const detail = c.expect.carried ? ` carried=${JSON.stringify((got.carried ?? []).map((f) => f.summary))}` : ''
  console.log(`${ok ? 'OK  ' : 'FAIL'} ${c.name} -> outcome=${got.outcome} rounds=${got.rounds}${detail}`)
}

process.exit(failed ? 1 : 0)
