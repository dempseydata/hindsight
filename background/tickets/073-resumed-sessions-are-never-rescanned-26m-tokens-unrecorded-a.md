# #73 Resumed sessions are never rescanned: 26M tokens unrecorded across 17 done sessions

state: closed · labels: bug, needs-triage · opened: 2026-08-29 · closed: 2026-08-29

Found while checking live data on 2026-08-29 (operator report: "no token usage for `content`, I was using quite a bit last night").

## Symptom

`content`'s session `23fbbb32-8e51-4d96-b81d-31c58ab77453` is `done` in the DB at 951,241 bytes dated 2026-08-27. On disk it is **1,649,894 bytes, modified 2026-08-29 07:33** — the session was resumed. None of the new work is in the DB, and none of it ever will be.

## Root cause

`invalidate_grown` in `build/analyze.py` only considers unfinished sessions:

```python
rows = conn.execute("SELECT id, transcript_path, size FROM sessions"
                    " WHERE status != 'done'").fetchall()
```

Its docstring states the intent plainly: *"Done sessions are never revisited: an audit entry covers the session as of its analysis run (prefix semantics, CONTEXT.md)."* So a `done` session that grows is never re-scanned — not late, never.

This is a deliberate decision, not an oversight. The premise it rests on — that a completed analysis run means a completed session — no longer holds now that resuming a session is routine.

## Measured blast radius (2026-08-29)

17 `done` sessions have grown on disk; **23.1 MB unscanned, 26,215,021 tokens unrecorded**:

| project | sessions | unrecorded tokens | usage rows |
|---|---|---|---|
| `content` | 2 | 18,211,701 | 71 |
| `hindsight` | 1 | 4,771,642 | 34 |
| `career-ops` | 3 | 3,231,678 | 12 |

The loss compounds: every future resume adds to it silently. `tool_events` and `command_grains` are missing for the same tails, so the how-view trail and the what-view ledger are also short.

## The decision this ticket has to make

**Proposed split — separate the substrate from the audit.** Prefix semantics are a sound argument about the *audit*: a model-written summary is legitimately "as of" its run. They have no bearing on *usage rows*, which are mechanical facts carrying their own timestamps. Conflating the two is why the tokens vanished.

So: always top up `usage` / `tool_events` / `command_grains` when a transcript grows, whatever the session's status; leave the audit prefix-semantic.

**Open question for the operator (HITL, not for an agent to settle):** does a resumed session get re-audited?

- Leave the old audit → the ledger entry understates what the session did.
- Re-audit → model calls, and it rewrites a ledger entry that may already have been read.

## Notes

- `invalidate_grown` already deletes substrate rows per session before rescan, so extending it must not double-count — reuse that path rather than adding a second one.
- Related but distinct: #66 (extract.py's own skip gap), and `skipped_records` doubling as the scanned marker in `fill_substrate`.
- Expect `content` and `career-ops` totals to jump when this lands. That is the fix working.



---

**comment · 2026-08-29**

## Resolution

Fixed in 7ac8f6d. ADR-0013 records the decision; CONTEXT.md's prefix-semantics entry was factually wrong and is corrected.

### The split

Prefix semantics only ever applied to the **audit**, never to the substrate. `usage`/`tool_events`/`command_grains` are mechanical facts carrying their own timestamps — nothing about them is "as of" anything. They are now **always** topped up when a transcript grows, whatever the session's status. Conflating them with the audit is what made the tokens vanish.

The audit entry stays prefix-semantic, but not unconditionally: it is rewritten once **`REAUDIT_SHARE = 0.25`** of the current transcript is unseen by it.

### The threshold, decided on the data

Chosen against the 17 sessions found, not in the abstract — and fixed before any re-audit ran, in the spirit of the Evaluation discipline. Nine cross it:

| unseen | project | date | growth |
|---|---|---|---|
| 99.1% | career-ops | 08-17 | +6.78 MB |
| 86.0% | career-ops | 08-25 | +10.76 MB |
| 59.1% | hindsight | 08-27 | +3.47 MB |
| 42.9% | thisisme | 08-17 | +0.13 MB |
| 42.6% | hindsight | 08-01 | +0.21 MB |
| 42.4% | content | 08-27 | +0.70 MB |
| 29.3% / 28.8% / 25.8% | hindsight | | |
| *below the line* | 8 sessions | | 16.9% → 0.0% |

The extremes make the case both ways: the 99.1% entry *(quote redacted at publication — private-project content)* describes 0.9% of its session — not understated, false. Five others grew by a few hundred bytes, where a re-audit buys nothing.

**Correction to the estimate given when this was scoped:** I said 3–4 sessions would re-audit. The honest number is **9** — that figure came from eyeballing percentage *growth* rather than the fraction of the transcript left unseen, which is what the gate actually measures.

### The watermark, and why `size` could not be it

The share is measured against a new `sessions.audited_size`, not `size`. Topping up substrate moves `size` to match the disk, so measuring against `size` would reset the gap on every run — a session resumed in small increments would drift indefinitely and never trip the threshold. The same silent-loss failure mode, in slow motion.

Stamped in `process_session`, **not** `insert_results`: the backfill import (#20) shares that function and supplies a `size` that is archive metadata, not a measurement of the transcript. An imported session therefore keeps a NULL watermark and never re-audits on size grounds — nothing records what its audit saw, and a guess is not grounds to spend a model call. This surfaced as a real test failure (`test_imported_session_substrate_fills_on_next_run`), not as foresight.

Migration **v4** backfills `audited_size = size` for already-audited sessions — the only evidence available of what those entries covered.

### Also fixed

A **shrunk** transcript is now skipped rather than rescanned. The old comparison was `== size`, so a truncated file was treated as changed and refilled from less than we already held. Pruning means *unknown*, never *less* — the honesty grammar, inverted.

### Verification

Dry run of migration + `invalidate_grown` + `fill_substrate` against a copy of the live db, no model calls:

```
usage rows   16,590 ->  16,707      (+117)
tokens    5,332,789,710 -> 5,359,004,731  (+26,215,021)
queued for re-audit: 9
content   225,236,529 -> 243,448,230
```

Two new tests cover both sides of the gate — a small resume tops up substrate with `StubRunner([])`, so a spurious model call fails the test; a material resume rewrites the entry. 123 tests pass.

### Not done here

The next scheduled analysis run picks this up automatically and will make the 9 re-audit calls (haiku). The two `career-ops` sessions at 12.5 MB and 6.8 MB dominate that cost, since extraction splits them into several parts and each part is a what-pass call. **I have not run it against the live db** — that spends money and rewrites ledger entries, so it is the operator's call whether to run it now or let the nightly job take it.

Sequencing note: #74 (UTC day buckets) should land after the next run, so it re-dates a complete data set.



---

**comment · 2026-08-29**

**Correction to the resolution's cost estimate** (ADR-0013 amended in e4e2f88).

The resolution said the two large `career-ops` sessions would dominate the re-audit cost because extraction splits them into several parts. That is wrong. Measured against the live queue, **all nine re-audits extract to a single part — one what-pass call each**:

```
hindsight    +  0.21 MB  -> 1 part      career-ops   +  6.78 MB  -> 1 part
hindsight    +  0.45 MB  -> 1 part      career-ops   + 10.76 MB  -> 1 part
hindsight    +  0.24 MB  -> 1 part      thisisme     +  0.13 MB  -> 1 part
hindsight    +  0.15 MB  -> 1 part      content      +  0.70 MB  -> 1 part
hindsight    +  3.47 MB  -> 1 part
```

`extract.py` caps every message at `PER_MSG_CAP` (1500 chars), so a 12.5 MB transcript still renders well under `CHUNK_CAP` (180,000). Transcript size gates the *decision* to re-audit; it does not predict the *cost* of one — I conflated the two.

Full first-run queue, for the record: 9 re-audits + 8 genuinely new transcripts to sync, plus the status-narrative pass for the two declaring projects. The 28 `partial` sessions all have pruned transcripts, so extraction fails and none of them costs a call.

