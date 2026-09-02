# 24. Explainer Documents

This document governs deliverables whose product is a person's understanding — reports, guides, tutorials, onboarding pages, published explanations, HTML artifacts. Code-adjacent reference docs (per-directory AGENTS.md, ARCHITECTURE.md, project READMEs, instruction files) are a different genre under opposite pressure — they stay lean per [15-doc-tracking.md](15-doc-tracking.md) and [09-agentic-workflow.md](09-agentic-workflow.md) — and none of this document applies to them.

## Core Rules

- Gloss every technical or domain term at first use: one plain-language phrase the intended reader can act on — "an embedding (a list of numbers representing the text's meaning)". A term the intended reader would not know, used without a gloss, is a violation.
- Never name a methodology or principle without its mechanism. State what it does and why it solves this document's problem — or what breaks without it. "Uses X" alone is a violation: the reader must come away able to re-explain *why X*, not merely repeat *that X*.
- Pair every non-obvious concept with one concrete example — an input→output pair, a before/after, or a scenario. One example per concept; a second belongs in the deep-detail layer.
- Visualize to explain, never to decorate, choosing the form by what is being shown: structure (flow, sequence, hierarchy, topology, comparison of parts) gets a diagram — Mermaid (a text-based diagram language GitHub renders natively) in markdown, inline SVG or Mermaid in HTML; quantities (3+ values compared, a trend, a distribution) get a table plus one sentence stating what the numbers show in markdown, or an inline SVG chart in HTML; a concept text cannot carry (an analogy picture, a spatial layout) may get a drawn graphic in HTML only, always accompanied by the same explanation in text. One or two numbers, or a single fact, stay prose.
- Every visual must be introducible as "this shows X" in one sentence. One that cannot be is decoration and gets cut.
- Size the document by the fresh-reader test, not by word count: long enough that the intended reader can re-explain each mechanism in their own words and act without follow-up questions, and no longer — everything past that point is over-explanation and is cut, the same bar [01-structure-naming.md](01-structure-naming.md) sets for comments and reference docs.
- Layer the structure: a summary stating what this is and why it matters, a body carrying the mechanisms with their examples, deep detail last — so the reader in a hurry and the reader starting from zero both have a path through.
- Ship an HTML explainer as one self-contained file: no external network dependencies, light and dark themes both legible, diagrams inline (Mermaid or SVG), and all text selectable and greppable — never rendered into an image.
- Flow body content as one column of readable line length, sections in reading order — no fixed sidebars or navigation panes; the table of contents goes inline at the top. Two small figures may sit side by side.
- In an HTML explainer, a quantitative claim about the subject (a measurement, rate, count, amount) appears as static text whose element names the field it came from in the file's single embedded data block, and a load-time check compares the text against that field, flagging a mismatch visibly. A hand-typed figure naming no source field is a violation; structural numbers (chapter numerals, "step 2 of 3") and mathematical identities used to explain a formula are exempt.
- Set numeric runs in a monospace face with tabular figures, so digits align vertically across rows; Korean-language labels and table headers stay in the body face.
- Start an HTML explainer from the shipped skeleton ([explainer-skeleton.html](../skills/explainer-docs/explainer-skeleton.html)) — using its design tokens and component classes is the evidence of having started there. The gallery beside it ([explainer-gallery.html](../skills/explainer-docs/explainer-gallery.html)) is a repertoire, not a ceiling: when a bespoke visual shows the mechanism better, invent it under the same caption, theme, and accessibility contract.
- Before an explainer ships, run it through the fresh-reader review lane ([20-review-gate.md](20-review-gate.md) §2): a reviewer with no author context reads the document alone.

## Details

### 1. The genre boundary

The four layers of [15-doc-tracking.md](15-doc-tracking.md) — contracts in code, module logic beside the code, flow at the root, history in commits — serve a reader about to work on the code, who needs the shortest accurate reference. An explainer serves a reader who does not yet hold the model in their head; its product is the transfer of understanding, not the reference. The two pressures are opposite: leanness deletes exactly the scaffolding — glosses, examples, restatements in plain words — that an explainer exists to provide. So the genres are separated by audience, not by file format: a markdown file can be either; which rules it lives under is decided by who it is meant to teach.

### 2. Explaining a mechanism

A methodology named without its mechanism forces the reader to either trust it blindly or leave the document to research it — both are failures of the document, not of the reader. The test: could the intended reader re-explain *why this approach* after reading, not just repeat that it is used?

Violation:

> Deduplication uses cosine similarity with a 0.9 threshold.

Compliant:

> Deduplication uses cosine similarity — each sentence is turned into a vector of numbers, and the measure scores how closely two vectors point in the same direction. Sentences that mean the same thing produce similar directions even when their wording differs, so this catches paraphrased duplicates that exact string comparison misses. The 0.9 threshold keeps only near-certain pairs.

The compliant version costs three sentences and removes the reader's need to trust or leave. This is what the fresh-reader lane (§4) checks: a mechanism the reviewer cannot re-explain from the document alone is a finding.

### 3. Examples and visualization

An example is the cheapest comprehension check the author can run on themselves: a concept that resists a concrete input→output, before/after, or scenario is usually not yet understood by its author either.

Visuals are chosen by what is being shown; each kind has its own trigger and medium:

| Showing | Trigger | In markdown | In HTML |
|---|---|---|---|
| Structure | flow, sequence, hierarchy, topology, comparison of parts | Mermaid | inline SVG or Mermaid |
| Quantities | 3+ values compared, a trend, a distribution | table + one sentence stating what the numbers show | inline SVG chart |
| A concept text cannot carry | analogy picture, spatial layout | stay in prose | inline SVG, with the same explanation in text |

The medium split follows from what each medium can carry: markdown has no reliable inline charting, and a table is text — it renders everywhere and diffs cleanly — while an HTML file can embed the chart itself.

The gate against decoration is the caption test from the Core Rules: a visual that cannot be introduced as "this shows X" in one sentence is cut — the same spirit as recording status in words rather than emoji ([01-structure-naming.md](01-structure-naming.md)).

### 4. The fresh-reader test

"Appropriate length" is not a word count. The document is long enough when the intended reader can re-explain each mechanism in their own words and act without follow-up questions; everything past that point is cut.

The test is run, not imagined: the fresh-reader lane of [20-review-gate.md](20-review-gate.md) §2 gives the document — and nothing else — to a reviewer carrying no author context, and asks for the re-explanations plus a list of terms used without a gloss. The shape is the same as 15's blind rebuild: block out the surrounding context and see what the artifact supports on its own. Handing that lane the code or the author's notes defeats it, because the lane would fill gaps from material the real reader will not have.

### 5. HTML artifacts

An HTML explainer is the same genre in a rendering that must survive being handed around — opened from mail and chat, offline, in either theme:

- **Self-contained single file.** No external network dependencies — CDN scripts, remote fonts, hotlinked images. Anything remote is a part of the document that silently disappears.
- **Both themes legible.** Check light and dark rendering; a page that inherits the viewer's theme but styles only one has an invisible half.
- **Diagrams inline.** Mermaid or SVG in the file itself, chosen by the same triggers as §3.
- **Text stays text.** Selectable and greppable, never rendered into an image — an image defeats search, copy, diff, and screen readers at once.
- **Single reading column.** An explainer is read in order, each section standing on the one before it; a two-column flow splits that path into two tracks the reader must reconcile, and forces exception CSS wherever a section outgrows its column. A readable measure at 16px Korean body text is roughly 780–860px, about 45 characters per line — wide enough to use the viewport without spreading text past a comfortable line length.

### 6. The explainer skeleton

The plugin ships two HTML files beside the explainer-docs skill: [explainer-skeleton.html](../skills/explainer-docs/explainer-skeleton.html), the file a new explainer is copied from, and [explainer-gallery.html](../skills/explainer-docs/explainer-gallery.html), a browsable catalog of visualization recipes. The decisions they embody — fonts, tokens, components, the number-verification wire contract — are commented inside the files themselves, which travel with every copy; this section does not restate them.

One decision is anchored here because it interprets §5: body figures are static text checked against the embedded data block, not rendered by script. A figure that exists only after JavaScript runs is invisible to grep, copy, and script-blocked viewers — the failures "text stays text" exists to prevent — while a load-time check that only flags divergence, never rewriting the text, preserves those guarantees and still ties every figure to its source field. Interactive charts are the one runtime exception; a filterable table keeps its rows static and lets script toggle visibility only.
