# ADR-0014: Day buckets are the operator's local day; storage stays UTC

**Date:** 2026-08-29 · **Status:** accepted · **Decides:** issue #74

## Context

Nothing in hindsight converted timezones. Every calendar-day bucket was a raw string slice off a UTC ISO timestamp — `substr(u.at, 1, 10)` at a dozen sites in `build/serve.py`, `[:10]` in `build/how.py` and `build/analyze.py`. `datetime` was imported only to *write* UTC, never to read it back.

Found on 2026-08-29 from the operator's own report: *"activity in hindsight shows up as 8/29 rather than 8/28 — are you using UTC? I am EST."* The session in question ran 20:13–22:52 EDT on 2026-08-28, was stored as `2026-08-29T00:13Z`–`02:52Z`, and every one of its 172 usage rows was filed under 8/29.

Measured on the live db at that moment: **1,937 of 16,848 usage rows (11.5%)** fall in the 00:00–04:00 UTC band and were therefore attributed to the wrong local day. In practice that is every evening session past 20:00 EDT — which is most of them.

## Decision

**Storage stays UTC. Every day bucket is the operator's local day, converted at read time.**

Timestamps are facts about instants and stay exactly as the CLI wrote them: unambiguous, sortable, portable. A *day bucket* is not a fact about an instant, it is an answer to "what did I do yesterday", and yesterday is a local-clock question. For a single-operator observability tool there is no second reading — a chart that files last night's work under tomorrow is simply wrong.

The conversion is expressed exactly twice, so the SQL and Python paths cannot drift:

- `analyze.day_sql(col)` → `substr(datetime(<col>, 'localtime'), 1, 10)`, for the grouped queries.
- `analyze.local_day(ts)`, for the Python-side slices (OTEL attribute timestamps, trail events, run boundaries, rendered dates).

`local_day` passes a bare `YYYY-MM-DD` through untouched. Converting an already-bucketed day would parse it as midnight UTC and walk it a day west, and both kinds of value reach `serve._span`. Anything unparseable keeps the old prefix slice rather than vanishing.

**`sessions.date` moves too, and is the one value that cannot be converted at read time.** It is a *stored* bucket that has already discarded the clock time the conversion needs. Leaving it UTC while the chart went local would have put an evening session's tokens on one day and its ledger row on the next, and the what-view's bar-click filter joins the two — so the incoherence would have been visible, not theoretical. Migration 5 re-derives it by re-reading each transcript's head (`head_scan`, ~0.6 s over 281 sessions). **A session whose transcript has vanished keeps its UTC date**: a guess is not a re-derivation. 14 of 281 sessions re-dated, every one of them by exactly one day.

**The operator's zone is the machine's zone.** No configuration, no stored offset — `localtime` and `astimezone()` read the host clock. This is a local-first single-operator tool; a TZ setting would be a knob with one correct value.

## Consequences

- **11.5% of usage rows re-date.** History is not rewritten — the timestamps are untouched — but it is re-read, and totals move between adjacent days. That is the fix landing.
- **Every stored narrative goes stale for one cycle.** Re-dating shifts run boundaries, so every `status_narrative.ledger_hash` mismatches and the how-view marks every project stale until the next analysis run regenerates it. ADR-0012's stale mechanism working as designed, and haiku-cheap — but it looks alarming once.
- **The frozen eval survives untouched.** `eval/cases.json` is a self-contained fixture set frozen 2026-08-28, not re-derived from the db, so `eval/run.py` and `eval/score.py` are unaffected. What lapses is the *claim* in `test_how.py` that those five fixtures were reproduced byte-for-byte from live data — true of that moment, not of this one. The docstring now says so.
- **Tests pin `TZ=America/New_York`.** Local bucketing makes the fixtures clock-dependent; without a pinned zone the suite asserts whatever the runner's machine believes.
- **Timezone travel re-buckets the display, not the data.** Run hindsight from another zone and the same rows fall on different days. Correct for "what did I do yesterday", asked wherever the operator is standing — and reversible, because the UTC timestamps never moved. `sessions.date` is the exception: re-derived once at migration and not re-derived again, so it holds the zone of the machine that migrated. The next analysis run only sets it for *new* sessions.
- **The backfill import (ticket #20) keeps its archive dates.** `import_backfill.py` inserts the day recorded in the archive inventory, which is UTC-derived and carries no clock time. Migration 5 heals any imported session whose transcript still exists; the rest keep an off-by-up-to-one-day date, which is the honest ceiling on archive metadata.

## Alternatives rejected

- **Stay UTC, state it in the UI.** Cheapest, and defensible for a multi-operator tool. Rejected because it answers a question nobody asked: the operator does not want to know what happened on a UTC day, and a footnote does not make a wrong bucket right.
- **A configured timezone.** Would survive travel and make the choice explicit. Rejected as a knob with exactly one correct value on a single-operator local-first tool — the host clock already holds it.
- **Convert at write time, store local days throughout.** Would make every read a plain slice again. Rejected because it destroys the instant: a stored local day cannot be re-bucketed when the answer needs to change, which is precisely the corner `sessions.date` is stuck in and had to be migrated out of.
