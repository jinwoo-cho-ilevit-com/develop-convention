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

// A lane is defined by its input, not by its attitude — three reviewers told to
// "be critical" over the same input return the same findings three times (→ 20).
const REVIEW_LENSES = [
  { key: 'module', input: 'the diff and the files it changed' },
  { key: 'project', input: 'the diff plus its callers and callees, and the convention docs it must satisfy' },
  { key: 'absence', input: 'the lane brief and the diff — hunt for what the brief requires and the diff omits' },
]

const planDir = args?.planDir ?? '.plans'
const lanes = args?.lanes ?? []
const boundaries = args?.boundaries ?? []

if (!lanes.length) {
  log('No lanes in args. Nothing to build.')
  return { lanes: [], note: 'no lanes supplied' }
}

// Three lanes when the change spans modules or pins an interface, one otherwise (→ 20 §2).
function lensesFor(lane) {
  const spansModules = (lane.owns ?? []).length > 1
  const pinsInterface = boundaries.some((b) => b.lanes?.includes(lane.name))
  return spansModules || pinsInterface ? REVIEW_LENSES : [REVIEW_LENSES[0]]
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
    '(→ conventions/15-doc-tracking.md).',
    '',
    'Return the absolute path of the worktree you worked in — later rounds continue in it.',
    'Report each criterion with the command you ran and whether it passed. A [human] criterion has no',
    'command: report it as not passed and leave the command empty.',
  ].join('\n')
}

function reviewPrompt(lane, lens, round, fixSummary) {
  return [
    `Review lane "${lane.name}" through one lens only: ${lens.key}.`,
    `Your input is ${lens.input}. Work in ${lane.worktree ?? 'the lane worktree'} on branch ${lane.branch ?? ''}.`,
    '',
    'Read the change with `git diff <base>..<branch>` and `git show <ref>:<path>`. Never switch branches',
    'in a shared worktree — one checkout erases every other lane\'s subject.',
    '',
    'You did not write this code and you do not get the author\'s reasoning. Judge the diff against',
    `${planDir}/lane-${lane.name}.md and the convention docs.`,
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

// Review, fix, recheck — for one lane, independent of every other lane.
async function reviewLoop(dev, lane) {
  if (!dev) return { lane: lane.name, outcome: 'develop-failed' }

  const ctx = { ...lane, worktree: dev.worktree, branch: dev.branch }
  const lenses = lensesFor(lane)
  const carried = []
  let fixSummary = ''

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

    // A lane that finished is not a lane that answered (→ 20 Core Rules).
    if (reviews.length < lenses.length) {
      log(`lane ${lane.name} round ${round}: ${lenses.length - reviews.length} review lane(s) returned nothing`)
    }
    const readOnly = reviews.filter((r) => !r.commandsRun).length
    if (readOnly) log(`lane ${lane.name} round ${round}: ${readOnly} lane(s) ran no commands — those verdicts are readings`)

    // Dedupe across lenses: the same defect seen twice is one defect.
    const seen = new Set()
    const findings = reviews
      .flatMap((r) => r.findings ?? [])
      .filter((f) => {
        const key = `${f.file}:${f.line ?? ''}:${f.summary}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })

    const blockers = findings.filter((f) => f.severity === 'blocker')

    if (!blockers.length) {
      carried.push(...findings)
      return { lane: lane.name, outcome: 'passed', rounds: round, branch: ctx.branch, criteria: dev.criteria, carried }
    }

    // The fix has become the defect source. More rounds will not converge (→ 18 §2).
    const fromFix = findings.filter((f) => f.causedByPreviousFix).length
    if (round > 1 && fromFix * 2 > findings.length) {
      return {
        lane: lane.name,
        outcome: 'regression-halt',
        rounds: round,
        branch: ctx.branch,
        blockers,
        note: `${fromFix} of ${findings.length} findings came from the previous fix. Change the approach rather than running another round.`,
      }
    }

    if (round === ROUND_CAP) {
      return { lane: lane.name, outcome: 'round-cap', rounds: round, branch: ctx.branch, blockers, note: 'Round cap reached; a person decides what happens next.' }
    }

    const fix = await agent(fixPrompt(ctx, blockers), {
      label: `fix:${lane.name}#${round}`,
      phase: 'Review',
      isolation: 'worktree',
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
  humanCriteria: passed.flatMap((r) =>
    (r.criteria ?? []).filter((c) => !c.command).map((c) => ({ lane: r.lane, criterion: c.criterion })),
  ),
}
