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

const planDir = args?.planDir ?? '.plans'
// The conventions travel with the plugin, not with the project the lanes run in, so the
// absolute path has to be handed in — a bare `conventions/…` resolves to nothing there.
const conventionsDir = args?.conventionsDir ?? 'conventions'
const lanes = args?.lanes ?? []
const boundaries = args?.boundaries ?? []

// One contract test per boundary, owned by no lane, is written before fan-out — that is what
// holds the interfaces still while every lane edits at once. Invoking this workflow directly
// skips it, so the caller has to declare it happened.
if (args?.boundariesFrozen !== true) {
  log('Boundaries are not frozen. Run /dev-harness:build instead of invoking this workflow.')
  return {
    lanes: [],
    note: 'refused: boundariesFrozen was not true. /dev-harness:build writes one contract test per boundary, owned by no lane, before fanning out; invoking this workflow directly skips that and lets the lanes move the interfaces they are working against.',
  }
}

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
    'Return the absolute path of the worktree you worked in — later rounds continue in it — and the',
    'commit sha on your lane branch after your work, which is the baseline the first round measures from.',
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
      return {
        lane: lane.name,
        outcome: 'verification-incomplete',
        rounds: round,
        branch: ctx.branch,
        criteria: dev.criteria,
        blockers: rawBlockers,
        carried: dedupe(carried),
        escalation: 'human',
        note: !verdicts
          ? 'The verifier returned nothing.'
          : `Verification did not cover the blockers one to one: ${missing.length} missing, ${duplicated.length} duplicated, ${unknown.length} unknown keys.`,
      }
    }
    const refuted = rawBlockers.filter((f) => byKey.get(keyOf(f))[0].confirmed === false)
    const blockers = rawBlockers.filter((f) => byKey.get(keyOf(f))[0].confirmed !== false)
    if (refuted.length) {
      refuted.forEach((f) => carried.push({ ...f, severity: 'minor', summary: `[refuted] ${f.summary}` }))
      log(`lane ${lane.name} round ${round}: ${refuted.length} blocker(s) were refuted on verification`)
    }

    if (!blockers.length) return clean(lane, dev, ctx, round, carried)

    // Two signals that another round will not converge, and the script computes one of
    // them itself. `causedByPreviousFix` is a reviewer's judgment, so a loop that trusts
    // it alone can only detect what a reviewer thought to mark — and a test that sets the
    // flag proves the branch fires, never that the flag is reachable. Repetition is a fact
    // about the findings, so it is derived here from identity across rounds (→ 20 §3).
    // Blockers only, on both sides of the ratio. Counting every finding let two majors
    // that are carried round after round — by design, since only blockers get fixed —
    // form the majority and halt a lane whose actual blocker had changed and was fixable.
    // The loop this exit governs is the blocker loop; its denominator has to be the same.
    // The causation claim is checked, not taken. Confirming a blocker establishes that the
    // defect is real; it says nothing about who introduced it, and those are different
    // claims. A real pre-existing blocker in untouched code, mislabelled as fix-induced,
    // would halt the loop by itself and never be fixed. A fix that never touched the file
    // cannot have caused a defect in it, so the flag only counts where the previous fix
    // actually reached. Where it reached comes from a separate agent that read git in the
    // lane's worktree — the fixer is not asked about its own diff, since an actor grading
    // itself can hide a regression by omission or halt a fixable lane by overclaiming.
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
      return {
        lane: lane.name,
        outcome: 'regression-halt',
        rounds: round,
        branch: ctx.branch,
        blockers,
        carried: dedupe(carried),
        escalation: 'human',
        note: `${stuckKeys.size} of ${blockers.length} confirmed blockers are unchanged from the previous round (${repeated.length}) or introduced by its fix (${fromFix.length}). Change the approach rather than running another round.`,
      }
    }
    previousKeys = new Set(blockers.map(keyOf))

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
      schema: FIX_SCHEMA,
    })
    if (!fix) return { lane: lane.name, outcome: 'fix-failed', rounds: round, branch: ctx.branch, blockers }
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
