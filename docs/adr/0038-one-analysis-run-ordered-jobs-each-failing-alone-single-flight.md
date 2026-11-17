# ADR-0038: The nightly is the analysis run on a timer: one ordered job list, each job failing alone, single-flight

**Date:** 2026-11-16 · **Status:** accepted · **Amends:** ADR-0034 · **Decides:** issue #78 (map #59, v2 audit core)

## Context

Five v2 decisions each placed a job in "the nightly": the capture sweep (ADR-0033 §1), derivation (ADR-0031 §6), the input-side cross-check (ADR-0033 §5), the drift guard (ADR-0037) and compaction (ADR-0034 §8). The what-pass, the how-view narrative, the backstop and the sunk-cost scan carry over from v1.

In v1, the nightly is a launchd invocation of `analyze.py`, the same command run on demand (ADR-0001, amended 2026-08-24). Its steps run in fixed order. Only the drift guard and the narrative pass are wrapped so that a failure cannot stop the run (ticket 077: never trade mechanical fact for a nicety). Any other exception aborts the run. There is no lock, so a run started by hand can overlap the nightly.

## Decision

1. **There is one job list.** With capture moved to the hook, nothing is left that only the nightly can do. The sweep is a catch-up, and compaction is gated per session (ADR-0034 §4). The on-demand analysis run therefore runs every job, compaction included. The nightly is its scheduled invocation. *Amends ADR-0034 §8:* compaction runs in the analysis run, so lowering `HINDSIGHT_RAW_DAYS` takes effect at the next run, whether scheduled or on demand.
2. **The jobs run in this order:**
   1. migration
   2. sweep
   3. project bookkeeping: identity fill, presence, canonicalisation
   4. derivation: every deriver
   5. drift guard and cross-check
   6. what-pass
   7. how narrative
   8. backstop and sunk-cost scan
   9. compaction
   10. health write

   Project bookkeeping comes before anything that reads `sessions.project`. Compaction comes after the what-pass, so it sees this run's results rather than the previous run's.
3. **Each job fails alone.** Every job runs in its own try block. A later job skips only when one of its own prerequisites failed:
   - **Migration fails:** nothing runs, because every job assumes the current schema.
   - **Sweep fails:** derivation still runs, over whatever has been captured.
   - **Derivation** fails per session, in one transaction per session per deriver. A failed session stays due, and the other sessions proceed.
   - **Guard and cross-check** run only when derivation has left no session due. Otherwise they skip, because a half-derived day would trip the cross-check falsely.
   - **What-pass:** a limit pause skips the narrative, as in v1. A pause is not a failure.
   - **Compaction** runs regardless, because its per-session holds are the gate.
   - **Backstop and sunk-cost scan** always run.
4. **The analysis run writes one health row** (ADR-0033 §6). The run is errored if any job raised an error, and the error text names each failing job with its message. A designed skip is not an error: a limit pause, sessions held from compaction, or guard and cross-check skipped because derivation is behind. A bad `HINDSIGHT_RAW_DAYS` is an error (ADR-0034 §2). A session that fails a deriver every night keeps the run errored every night. The health check's "failing for N days" then counts from when the failure began.
5. **Single-flight.** A lock in Hindsight home lets only one analysis run proceed at a time. A second invocation exits at once with one log line, exit code 0 and no health write. It is neither an error nor a stale source, because the running invocation writes the row. The lock is held by the process (an OS advisory lock), so a crashed run never leaves it held.

## Alternatives rejected

- **The on-demand run never compacts.** That adds a mode to guard a deletion already gated per session. It only changes when an operator's lowered limit takes effect: on demand rather than at 03:00, which is the same irreversible act a few hours sooner.
- **One health row per job.** That would mean up to ten sources for a health check designed to show one line (ADR-0036 §6). The job names in the error text carry the same information.
- **Guard and cross-check over a partly derived store.** A day whose transcript-side tokens are missing would read as a gap above 5%, which is a false breakage.
- **No lock.** Overlapping runs mean duplicated model calls and two writers on one session's derivation.

## Consequences

- The **Analysis run** entry in CONTEXT.md lists the v2 jobs. "The nightly" is not a separate term.
- A poison session cannot hide: it errors the run until a parser fix or a deriver version bump clears it.
- Guard and cross-check results can lag by a run while derivation is behind. That lag is stated as a skip, never as a pass.
