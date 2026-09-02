# ADR-0013: Resumed sessions — substrate is topped up, the audit is prefix-semantic past a threshold

**Date:** 2026-08-29 · **Status:** accepted · **Decides:** issue #73

## Context

`invalidate_grown` re-extracted and rescanned any session whose transcript had grown since sync, but only `WHERE status != 'done'`. Its docstring stated the rule plainly: *"Done sessions are never revisited: an audit entry covers the session as of its analysis run (prefix semantics, CONTEXT.md)."*

That rule rests on a premise that no longer holds. It reads a completed analysis run as a completed *session*, but resuming a session is now routine — the operator continues yesterday's work in the same transcript rather than starting a new one. Once a session is marked `done`, everything appended to it afterwards is invisible to hindsight for good. Not late: never.

Found on 2026-08-29 from the operator's own report ("no token usage for `content`"). Measured at that moment: **17 `done` sessions had grown on disk, 23.1 MB unscanned, 26,215,021 tokens unrecorded** — `content` 18.2M, `hindsight` 4.8M, `career-ops` 3.2M. `tool_events` and `command_grains` were short by the same tails, so the how-view trail and what-view ledger understated the work too. The loss compounds silently with every resume.

## Decision

**Split the substrate from the audit. Prefix semantics only ever applied to one of them.**

`usage`, `tool_events` and `command_grains` are mechanical facts carrying their own timestamps. Nothing about them is "as of" anything, and no interpretation is involved. They are **always** topped up when a transcript grows, whatever the session's status. Conflating them with the audit is what made the tokens vanish.

The audit entry is a model-written summary and is legitimately "as of" its run, so it stays prefix-semantic — but not unconditionally. It is rewritten once **`REAUDIT_SHARE` (0.25) of the current transcript is unseen by it**. Below that line the entry still fairly describes the session and the model call is waste; above it, the entry is reporting a prefix as the whole.

The threshold was chosen against the 17 sessions found on the day, not in the abstract. Nine cross it. The extremes make the case in both directions: one `career-ops` session had grown from 61 KB to 6.8 MB — its entry *(verbatim quote redacted at publication — it summarised private-project content)* described 0.9% of the session and was simply false — while five others had grown by a few hundred bytes, where a re-audit would buy nothing.

**The share is measured against `audited_size`, a new watermark on `sessions`, not against `size`.** Topping up substrate moves `size` to match the disk, so measuring against `size` would reset the gap on every run and a session resumed in small increments would drift indefinitely without ever tripping the threshold — the same silent-loss failure mode in slow motion.

`audited_size` is stamped in `process_session`, not in `insert_results`. The backfill import (ticket #20) shares `insert_results` and supplies a `size` that is archive metadata rather than a measurement of the transcript. An imported session therefore keeps a **NULL** watermark and is never re-audited on size grounds: nothing records what its audit actually saw, and a guess is not grounds to spend a model call. Migration v4 stamps `audited_size = size` for sessions that already carry an audit — the only evidence available of what those entries covered.

**"Always" means *once the transcript is quiet*.** Amended for issue #76: the wipe is only half a top-up, and `fill_substrate` skips a live session (ticket #29), so wiping a live one ends the run with zero substrate rows for it — worse than the stale prefix it replaced. Pre-#73 the `status != 'done'` filter hid this; opening the path to every done session exposed it. Live sessions are therefore skipped outright, and top up on the first run that catches them quiet. Deferral, not exception: the tail is still on disk.

**A transcript that shrank is left alone.** The previous code compared with `==` and so rescanned a shrunk file; it now skips one. Pruning means *unknown*, never *less* — rescanning would overwrite what we still hold with a smaller truth, which is the honesty grammar inverted.

## Consequences

- Re-auditing rewrites ledger entries the operator may already have read. This is accepted: an entry describing 0.9% of its session is worse than one that changes.
- The first run after this lands re-audits 9 sessions, at **one what-pass call each**. Transcript bytes and extract size are only loosely related: `extract.py` caps every message at `PER_MSG_CAP` (1500 chars), so even the 12.5 MB `career-ops` transcript renders as a single sub-`CHUNK_CAP` part. Size gates the *decision* to re-audit; it does not predict the *cost* of one. The model is haiku; the run is bounded and one-off.
- Project totals jump on that run — `content` 225.2M → 243.4M tokens. That is the fix landing, not a new defect.
- The re-audit gate is a **number decided in advance**, in the spirit of the Evaluation discipline: 0.25, fixed before the first re-audit ran, rather than tuned afterwards to fit the result.

## Alternatives rejected

- **Substrate only, never re-audit.** Cheapest, and preserves prefix semantics strictly. Rejected because it knowingly leaves the 10,996%-growth entry standing as a false description of its session.
- **Always re-audit on any growth.** Most correct in principle, but burns calls on the five sessions that grew by ~0% and rewrites entries that were already accurate. The threshold gets the same correctness for a fraction of the spend.
- **A second audit row per continuation.** Would preserve the original entry honestly, but `audit` is keyed one row per session; a revision concept is a schema and UI change far beyond the defect being fixed.
