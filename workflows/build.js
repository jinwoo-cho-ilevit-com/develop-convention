export const meta = {
  name: 'dev-harness-build',
  description: 'Run each lane in its own worktree, review it the moment it finishes, and loop fix-and-recheck until the blockers are gone',
  phases: [
    { title: 'Develop', detail: 'one worktree-isolated agent per lane' },
    { title: 'Review', detail: 'review, fix and recheck — per lane, no barrier' },
  ],
}

// A lane that keeps producing blockers is not a lane that needs more rounds
// (→ conventions/20-review-gate.md). The cap is a runaway guard, not an exit.
const ROUND_CAP = 5

const DEVELOP_SCHEMA = {
  type: 'object',
  required: ['worktree', 'branch', 'criteria'],
  additionalProperties: false,
  properties: {
    worktree: { type: 'string', description: 'absolute path of the worktree you worked in' },
    branch: { type: 'string' },
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

// Added only when the lane touches auth, secrets, or external input (→ 20 Core Rules).
const SECURITY_LENS = {
  key: 'security',
  input: 'the diff, its trust boundaries, and every point where it accepts input it did not produce',
}
const TRUST_BOUNDARY = /auth|secret|credential|token|login|session|permission|hook|api|webhook|upload/i

// One finding is one defect wherever it was seen, and the same key identifies it across
// rounds — which is what makes repetition measurable without asking a reviewer.
const keyOf = (f) => `${f.file}:${f.line ?? ''}:${f.summary}`

function dedupe(findings) {
  const seen = new Set()
  return findings.filter((f) => (seen.has(keyOf(f)) ? false : (seen.add(keyOf(f)), true)))
}

const planDir = args?.planDir ?? '.plans'
// The conventions travel with the plugin, not with the project the lanes run in, so the
// absolute path has to be handed in — a bare `conventions/…` resolves to nothing there.
const conventionsDir = args?.conventionsDir ?? 'conventions'
const lanes = args?.lanes ?? []
const boundaries = args?.boundaries ?? []

if (!lanes.length) {
  log('No lanes in args. Nothing to build.')
  return { lanes: [], note: 'no lanes supplied' }
}

// Three lanes when the change spans modules or pins an interface, one otherwise, plus a
// security lens when the lane touches a trust boundary (→ 20 §2).
function lensesFor(lane) {
  const spansModules = (lane.owns ?? []).length > 1
  const pinsInterface = boundaries.some((b) => (b.lanes ?? []).includes(lane.name))
  const base = spansModules || pinsInterface ? REVIEW_LENSES : [REVIEW_LENSES[0]]
  // The plan says so explicitly, or the paths say so for a plan that forgot to.
  const touchesTrust =
    lane.security === true || (lane.owns ?? []).some((p) => TRUST_BOUNDARY.test(p))
  return touchesTrust ? [...base, SECURITY_LENS] : base
}

function developPrompt(lane) {
  return [
    `You own lane "${lane.name}". Read ${planDir}/lane-${lane.name}.md and ${planDir}/PLAN.md.`,
    '',
    `Work only inside your owned paths: ${(lane.owns ?? []).join(', ')}.`,
    'Every other path belongs to another lane running right now; touching one collides.',
    'The contract tests for your boundaries already exist and no lane owns them — make them pass, never edit them.',
    '',
    'Create a branch for this lane, commit your work to it, and run every command listed under',
    'the brief\'s completion criteria. Update the AGENTS.md of each directory you own in the same pass',
    `(→ ${conventionsDir}/15-doc-tracking.md).`,
    '',
    'Return the absolute path of the worktree you worked in — later rounds continue in it.',
    'Report each criterion with the command you ran and whether it passed. A [human] criterion has no',
    'command: report it as not passed and leave the command empty.',
  ].join('\n')
}

function reviewPrompt(lane, lens, round, fixSummary) {
  return [
    `Review lane "${lane.name}" through one lens only: ${lens.key}.`,
    `Your input is ${lens.input}.`,
    `cd into ${lane.worktree} before running anything — that is where this lane's work is.`,
    'Running the test command anywhere else tests a tree without the change and reports it as your verdict.',
    '',
    `Read the change with \`git diff ${lane.base}..${lane.branch}\` and \`git show ${lane.branch}:<path>\`.`,
    "Never switch branches in a shared worktree — one checkout erases every other lane's subject.",
    '',
    "You did not write this code and you do not get the author's reasoning. Judge the diff against",
    `${planDir}/lane-${lane.name}.md and the convention docs in ${conventionsDir}/.`,
    '',
    'Run the code. You have the test command and the tool under review; report how many commands you',
    'actually executed. A verdict from a lane that ran none is a reading, not a review.',
    '',
    'Flag correctness and requirement gaps only. Do not manufacture problems in sound code.',
    round > 1
      ? `This is round ${round}. The previous round's fix was:\n${fixSummary}\nFor each finding, set causedByPreviousFix to true only when the defect is in code that fix introduced or changed.`
      : 'This is round 1, so causedByPreviousFix is false for every finding.',
  ].join('\n')
}

function verifyPrompt(lane, blockers) {
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
    '',
    'A finding with no concrete failing scenario is not confirmed. Reviewers asked to find problems',
    'manufacture them in sound code, and an unconfirmed blocker forces a fix that then shows up as',
    'the next round\'s regression signal.',
  ].join('\n')
}

function fixPrompt(lane, blockers) {
  return [
    `You own lane "${lane.name}". Continue in the worktree you already have: ${lane.worktree}.`,
    'Review found these blockers. Fix them and commit to the same lane branch.',
    '',
    blockers.map((b, i) => `${i + 1}. [${b.file}${b.line ? ':' + b.line : ''}] ${b.summary}`).join('\n'),
    '',
    'Fix only these. Anything else you notice goes in your summary, not in the diff — an unrelated',
    'change here forces the whole lane through another review round.',
    'Re-run the criteria commands from your brief before returning.',
    '',
    'Return a short summary of what you changed. The next reviewer reads it to tell which findings',
    'your fix caused.',
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

  const ctx = { ...lane, worktree: dev.worktree, branch: dev.branch, base: args?.base ?? 'main' }
  const lenses = lensesFor(lane)
  const carried = []
  let fixSummary = ''
  let previousKeys = new Set()

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
      return {
        lane: lane.name,
        outcome: 'review-incomplete',
        rounds: round,
        branch: ctx.branch,
        criteria: dev.criteria,
        note: `${lenses.length - reviews.length} of ${lenses.length} review lanes returned nothing. Re-run them rather than merging a short review.`,
      }
    }
    // Any lens, not all of them. Requiring every lens to be silent meant two that ran
    // could carry a third that did not into a clean pass, and the lens that read nothing
    // is exactly the one whose "no findings" means nothing.
    const readings = reviews.filter((r) => !r.commandsRun)
    if (readings.length) {
      return {
        lane: lane.name,
        outcome: 'review-unexecuted',
        rounds: round,
        branch: ctx.branch,
        criteria: dev.criteria,
        note: `${readings.length} of ${reviews.length} review lenses ran zero commands. Those verdicts are readings, not reviews.`,
      }
    }

    // Dedupe across lenses: the same defect seen twice is one defect.
    const seen = new Set()
    const findings = reviews
      .flatMap((r) => r.findings ?? [])
      .filter((f) => {
        if (seen.has(keyOf(f))) return false
        seen.add(keyOf(f))
        return true
      })

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
    const confirmedKeys = new Set(
      (verdicts?.verdicts ?? []).filter((v) => v.confirmed).map((v) => v.key),
    )
    // A verifier that died confirms nothing, and dropping every blocker on its silence
    // would turn its death into a pass.
    const blockers = verdicts ? rawBlockers.filter((f) => confirmedKeys.has(keyOf(f))) : rawBlockers
    const unverified = rawBlockers.filter((f) => !blockers.includes(f))
    if (unverified.length) {
      unverified.forEach((f) => carried.push({ ...f, severity: 'minor', summary: `[unverified] ${f.summary}` }))
      log(`lane ${lane.name} round ${round}: ${unverified.length} blocker(s) did not survive verification`)
    }

    if (!blockers.length) return clean(lane, dev, ctx, round, carried)

    // Two signals that another round will not converge, and the script computes one of
    // them itself. `causedByPreviousFix` is a reviewer's judgment, so a loop that trusts
    // it alone can only detect what a reviewer thought to mark — and a test that sets the
    // flag proves the branch fires, never that the flag is reachable. Repetition is a fact
    // about the findings, so it is derived here from identity across rounds (→ 20 §3).
    const repeated = findings.filter((f) => previousKeys.has(keyOf(f)))
    const fromFix = findings.filter((f) => f.causedByPreviousFix)
    const stuckKeys = new Set([...repeated, ...fromFix].map(keyOf))
    if (round > 1 && stuckKeys.size * 2 > findings.length) {
      return {
        lane: lane.name,
        outcome: 'regression-halt',
        rounds: round,
        branch: ctx.branch,
        blockers,
        carried: dedupe(carried),
        escalation: 'human',
        note: `${stuckKeys.size} of ${findings.length} findings are unchanged from the previous round (${repeated.length}) or introduced by its fix (${fromFix.length}). Change the approach rather than running another round.`,
      }
    }
    previousKeys = new Set(findings.map(keyOf))

    if (round === ROUND_CAP) {
      return {
        lane: lane.name,
        outcome: 'round-cap',
        rounds: round,
        branch: ctx.branch,
        blockers,
        carried: dedupe(carried),
        escalation: 'human',
        note: 'Round cap reached; a person decides what happens next. This is not a completion.',
      }
    }

    // No `isolation` here on purpose: a fresh worktree is the opposite of what the prompt
    // asks for. 20 requires findings to go back "in the tree it already has", and a fix
    // committed anywhere else is a fix the next reviewer never sees and the merge never
    // takes.
    const fix = await agent(fixPrompt(ctx, blockers), {
      label: `fix:${lane.name}#${round}`,
      phase: 'Review',
    })
    if (!fix) return { lane: lane.name, outcome: 'fix-failed', rounds: round, branch: ctx.branch, blockers }
    fixSummary = fix
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
