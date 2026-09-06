# ADR-0015: A pruned, never-extracted session is `lost` — a terminal status decided by condition, not budget

**Date:** 2026-08-29 · **Status:** accepted · **Decides:** [issue #78](../../background/tickets/078-28-sessions-retry-forever-partial-has-no-terminal-state-for.md)

## Context

28 sessions sat at `partial` from July onward. Every run selected them (`status IN ('pending','partial')`), every run failed them at extraction, nothing changed. Their transcripts had passed Claude Code's retention: 27 had no cached extract and could never be analysed; the 28th had a poisoned cached output and is a separate defect.

`partial` encodes *retryable, next run*. There was no state meaning *unknowable*. The queue had no exit, "27 outstanding" was reported forever, and the ledger's LEFT JOIN rendered every one as *synced, not yet analyzed — run an analysis*: a false instruction, since the server could not tell *not yet* from *never*.

Origin of the backlog: 22 entered via the backfill import with transcripts already pruned. 6 were on disk at substrate-scan time and were lost because extraction lived inside the per-session model loop, behind the limit-exhaustion pause — they aged past retention waiting for a model call.

## Decision

**A new terminal status, `lost`: the transcript no longer exists *and* no cached extract (`<sid>.map.json`) exists.** Never selected by the run queue. Decided at analysis time by an explicit existence test (`is_lost`), not inferred from `ExtractionFailed`, which also covers unreadable or malformed files that remain retryable.

**Extraction is greedy.** `classify_and_extract` runs before the model loop: every quiet `pending`/`partial` session is either marked `lost` or has its extract cached, with no model call. Once an extract is on disk, pruning the transcript loses nothing, so the race that created the backlog cannot recur. `ExtractionFailed` there is swallowed; the session stays retryable.

**An entry always outranks the status.** A `done` session queued for re-audit (ADR-0013) whose transcript is then pruned has nothing to read but a standing audit entry; it is restored to `done`, prefix-semantic, never `lost`. The view applies the same rule: a session with an audit row renders its entry whatever `status` says.

**Natural drain, no migration.** The run loop classifies the backlog on first contact. `sessions.status` is otherwise untouched.

**The ledger says so.** A `lost` session renders as a dim one-liner — *transcript pruned before analysis — unrecoverable* — sibling of the trivial and pending rows. The summary line gains `· N unrecoverable`; *awaiting analysis* counts only sessions the next run can actually reach. This is the first time `sessions.status` is a view input, deliberately: without it "not yet" and "never" are indistinguishable at render.

**Substrate untouched.** `usage`/`tool_events`/`command_grains` of a `lost` session are kept; sessions never scanned stay NULL — unknown, never zero. Nothing about `lost` re-shapes history (ADR-0009's rule, applied to the queue).

## Alternatives rejected

- **Retry count or age bound on `partial`.** A policy dressed as a fact: a session is not unrecoverable because it has failed N times or is M days old, it is unrecoverable because there is nothing to read. A bound would also mark sessions `lost` that a later run could have extracted, and would leave a genuinely unreadable transcript retrying under the same label as a vanished one.
- **Naming it `pruned`.** Done-and-pruned sessions exist and are not lost — their audit rows stand. `lost` names the outcome, not the cause. *Unknowable* is kept for prose.
- **Silence.** Omitting `lost` rows from the ledger would break the LEFT JOIN rule (the ledger never omits a session the coverage line counts) and hide a month-wide gap.

## Consequences

- First run after this lands: `partial` 28 → 1, `lost` 27, `done`/`empty` unchanged, no substrate row deleted.
- The 22 imported-without-extract sessions were dead on arrival; `import_backfill.classify` is unchanged and such sessions still enter `pending`, draining to `lost` at the first run.
- The remaining `partial` session (`296cf33f`) and any retry bound on model-call failures are out of scope — own issue.
