# ADR-0012: The how-view status narrative — one model-written fact list, evaluated

**Date:** 2026-08-28 · **Status:** accepted · **Decides:** [issue #64](../../background/tickets/064-greybox-the-how-view-rendering-mechanics-with-real-data.md) (greybox reaction) · **Amends:** ADR-0010

## Context

ADR-0010 made the how-view wholly mechanical: no model narrative, audit titles as the only prose. The greybox (ticket #64) settled the trail as *phase runs* — bands of consecutive same-stage activity, newest first, each summarised by the audit titles of its sessions — and that part holds. What it could not produce mechanically is the thing the operator opens the view for first: a **status** — what has been built so far, what was dropped, what the current focus is. The mechanical ceiling (one line per run, first → last title) duplicates the run bands below it and answers none of those questions; the example the operator reached for ("built the back end, automated ingestion, prototyped and built the UI, removed a page on review, now defining a process view") is selection and synthesis, which is narrative.

## Decision

**The how-view carries exactly one model-written artefact: the status narrative** — a bounded fact list per project at the top of the view, above the runs. Everything else ADR-0010 decided stands: mechanical trail, dumb checker, no verdicts, juxtaposition, graceful degradation.

- **Input** is the run ledger only — stage, date range and audit titles per run, in order — never transcripts. The narrative is a synthesis of already-gated, already-paid-for model prose (ADR-0004's audits), not a fresh read of raw history.
- **Output** is a fact list in three fixed groups — **Built**, **Reversed**, **Now** — each line a claim traceable to one or more ledger entries, dated, in the operator's own stage vocabulary. Not prose: the greybox tried a paragraph and it read as narration rather than status. The grouping is the model's only judgement, which is what the eval scores. It states nothing the ledger does not contain.
- **It is load-bearing, so the Evaluation discipline applies in full** (`my-process.md`): a frozen eval set drawn from real projects' ledgers, a numeric threshold decided before the prompt is written, the cheapest model that holds the judgement, a regression run on any prompt or model change. The eval design is its own ticket, resolved before implementation.
- **Stored and gated like the audit**: generated after a sync when the ledger has changed (keyed on the ledger's content), persisted in the DB, contract-checked at write time as the what-pass output is (#38). Never generated on page load.
- **Degrades like everything else**: no narrative yet, or a refused one, renders the mechanical status (current run + tally) with the absence stated. ~~A project without a declaration gets a narrative over its undivided run — stages are input, not a precondition.~~ *Amended by ticket #67: a project without a declaration has no how-view (#64 addendum), so no narrative is generated for it; the eval set covers declaring projects only.*

*Amended by ticket #68 (the pass):* the narrative is regenerated only when the ledger's content hash, prompt version or model changes, and a regeneration that fails the write-time gate leaves the **last good narrative in place, marked stale** by its `ledger_hash` no longer matching the live ledger — so "refused" collapses to absence only when no narrative was ever stored. The view states staleness rather than hiding a good status behind one bad call. The nightly job therefore makes at most one extra model call per declaring project whose ledger moved.

## Considered options

- **Mechanical status only** (per-run first → last title) — built in the greybox; duplicative of the run bands and not a status. Rejected by the operator on sight.
- **A paragraph** — tried next; too narrative, the facts hid in the sentences. The three-group list kept the facts and lost the prose.
- **Narrative from transcripts** — richer, but a second model read of raw history per project, at audit cost, and unbounded input. The ledger is sufficient and already curated.
- **Narrative on demand, uncached** — simplest, but a model call per page load on a read-only server (ADR-0008) and no stable object to evaluate against.

## Consequences

- ADR-0010's "no model narrative" is narrowed to the trail and checker; the status paragraph is the one exception, and the map's out-of-scope line is amended.
- New tickets on map #58: the eval set and threshold for the status narrative (before implementing), then the narrative pass itself (prompt, storage, gate), then the styled view consuming both.
- CONTEXT.md gains **Run ledger** and **Status narrative**; the how-view and trail entries drop their blanket "no model" wording.
