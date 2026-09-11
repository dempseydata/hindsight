# ADR-0010: The how-view — mechanical process trail, operator-declared stages, no verdicts

**Date:** 2026-08-26 · **Status:** accepted, amended by ADR-0012 (status narrative) · **Decides:** [issue #54](../../background/tickets/054-ideate-process-view-actual-process-followed-vs-the-project-s.md)

## Context

The dropped why-view (ADR-0006) never mapped the process actually followed nor compared it to a stated one — the operator's stated reason for letting it go. Ticket #54 asked whether that gap deserves a view, feasibility first, with hindsight itself as the test case.

The feasibility probe settled two facts. First, the arc is reconstructible: skill invocations, phase-folder writes and audit titles already in the DB reproduce the project's real chronology (framing Jul 30 → grilling burst + first ADRs Aug 1 → prototype Aug 3 → build Aug 16+ → design Aug 18–20 → review cycles Aug 25) — including truths the operator misremembered. Second, tool events alone are blind to the deliberate-process signal: a user-typed slash command injects its skill into the user message with no Skill tool call, so this folder's transcripts hold 196 `/wayfinder` invocations while `tool_events` holds zero. The `<command-name>` marker sits verbatim in the JSONL — capturing it is plain parsing, a new grain type.

## Decision

**A third view, `how`** — the process actually followed, per workspace folder ("how did I get here with this project"), joining `what` and `where` post-v1.

- **Mechanical assembly, no model narrative.** The trail is command grains + skill invocations + phase-folder writes in date order; audit titles (already model-written, gated and paid for) supply the prose. A narrative-writing model pass would make model output load-bearing and drag in the full Evaluation discipline for one document per project.
- **`my-process.md` gains machine-readable frontmatter** — the process declaration: an ordered stage list, each stage mapping to observable markers. Branching (the two design routes: hero-led marketing flow vs prototype-first greybox) is resolved at authoring time — each project declares only its own route; the branching logic stays in house-pipeline prose. Prose below the frontmatter remains the authority on meaning.
- **The checker is deliberately dumb:** presence ("design: nothing observed"), first/last-seen per stage, off-script list (events mapping to no stage — also the declaration's rot detector when upstream renames a skill). Explicitly **no order rules and no conformance verdicts**: the stages interleave by design, the prose is full of conditionals a checker would false-positive on, and deviation is informative rather than bad. Comparison is juxtaposition — stated process rendered beside the trail, judgement stays with the operator.
- **Graceful degradation, nothing hides.** The trail exists for every project; a project without a declaration (or without the file) shows the raw ungrouped trail, and the stated-process panel is simply absent. The ticket's "hide the view if unconfigured?" question dissolves.
- **Output is stage-anchored:** trail events bucketed under the operator's own stage names, so back-and-forth iteration between stages is the visible texture of the timeline. Rendering mechanics (lanes, granularity) are prototype-territory, deferred to greybox with real data.

## Considered options

- **Model-written narrative / model comparison** — reads nicer, but load-bearing model output means frozen eval set, thresholds and regression runs per the project's Evaluation discipline; declined for a mechanically derivable document.
- **Condition-language schema** (`when: has-visual-surface`) — one declaration could express the whole house pipeline, but the checker must evaluate conditions and the schema slides toward a workflow engine with compliance verdicts — the eval burden in a YAML hat.
- **Hide the view when unconfigured** — unnecessary once comparison degrades gracefully.

## Consequences

- The substrate scan grows a command grain (parse `<command-name>` from user messages).
- The frontmatter convention lands in three projects' `my-process.md` plus the template.
- The build is its own effort with its own wayfinder map, not an addition to map #40.
- DB coverage completeness needs a look before the view ships: the probe found 70 hindsight sessions in the DB against 853 JSONL files on disk (subagent sidecars and a pending run explain some, not all) — the feasibility evidence came from transcripts directly.

## Amendment (ADR-0012, 2026-08-28)

"No model narrative" is narrowed: the trail and checker stay mechanical, but the view opens with one model-written **status narrative** synthesised from the run ledger, under the full Evaluation discipline. The greybox (ticket #64) also settled the trail's shape as **phase runs** — bands of consecutive same-stage activity, newest first — rather than a stage-bucketed chronology.

## Amendment (ticket #64 resolution, 2026-08-28) — the view applies only to declaring projects

"Graceful degradation, nothing hides" is narrowed. A project with **no** `.claude/my-process.md` declaration is not shown in the how-view at all — the view is about a stated process, and without one there is nothing to juxtapose; the raw ungrouped trail rendered for such a project in the greybox answered nothing. The project selector lists declaring projects only. The **invalid** state is unchanged: a fence that fails to parse still renders the trail with the line-numbered error, so a declaration written wrong is never mistaken for one never written. "Hide the view when unconfigured" — rejected above — is therefore adopted for the *absent* case only.

## Amendment (issue #17, 2026-09-11) — off-script events form runs

The off-script list was the end of the road for an unclaimed event: `run_ledger` banded staged events only, so days spent wholly outside the declared stages never reached the ledger or the narrative. The trigger was the content project, 2026-09-08 → 09-10: 25 off-script events, 23 of them writes under `.claude/` (skills, agents, `my-process.md`), all in the aside's list and none in a run, so the narrative's *Now* could not see three days of work. The six on-process events of those days were bands of one and folded back by the minimum-run rule — correct, and the same days went dark twice over.

- **Off-script events band exactly as staged events do**, under the one label `off-script`: consecutive unclaimed events form a run, `MIN_RUN` and the fold-into-preceding rule unchanged, majority titling unchanged. The label never appears in the stated-process panel or the declaration; the run wears the existing off hue and lists its used names, so a run of skill edits reads as what it is.
- **One lane, one term.** Considered and rejected: a separate *upkeep* or *other* lane (two names for one property — "matched no declared stage" — and a judgement the checker swore off), and declaring upkeep as a stage per project (meta-work in the ordered pipeline, repeated in every declaration). An off-script run is the rot detector made visible; whether it means upkeep or an undeclared step stays with the operator, per the juxtaposition rule.
- **`/compact` joins the session boundaries** (`SESSION_BOUNDARIES`, ADR-0011 #70): it opens a session as `/clear` does, and once off-script forms runs a compaction would otherwise become a step in one. Boundaries are set aside from runs as they are from the list — stated in the boundary total, never a run event.
- **Narrative.** The ledger is the narrative's sole input, so off-script runs reach the prompt as any run does. The prompt is unchanged and `STATUS_VERSION` stays `status-v1`: its *Now* form (`<Stage>, since <Mon D>: what the titles are about`) already states an off-script run as work done under its label, and the write-time gate's M5 needs only that label in the line. The standing eval set holds no off-script run, so a prompt edit could not have been measured against it; the regression run recorded in the closing comment is a variance run of the unchanged prompt. Every stored narrative regenerates once at the next analysis run because run boundaries — and so ledger hashes — move under the new banding.
