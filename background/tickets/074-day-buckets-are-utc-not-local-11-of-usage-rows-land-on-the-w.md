# #74 Day buckets are UTC, not local: 11% of usage rows land on the wrong day

state: closed · labels: bug, needs-triage · opened: 2026-08-29 · closed: 2026-08-29

Found while checking live data on 2026-08-29 (operator report: "activity in hindsight shows up as 8/29 rather than 8/28 — are you using UTC? I am EST").

## Symptom

Yes, it is UTC. Last night's session ran **20:13–22:52 EDT on 2026-08-28**, stored as `2026-08-29T00:13Z`–`02:52Z`, and all 172 usage rows are filed under **8/29**.

## Root cause

Nothing in the codebase converts timezones. Every day bucket is a raw string slice off a UTC ISO timestamp:

- `build/serve.py` — `substr(u.at, 1, 10)` / `[:10]` at ~12 sites (header chart, ledger, league, sunk cost, coverage range, hooks)
- `build/analyze.py:370` — `date = e["timestamp"][:10]`, which sets `sessions.date`
- `build/how.py:276-277` — run start/end dates

`datetime` is imported only to *write* UTC (`analyze.py:821`, `:1248`), never to read it back locally.

## Scale

**1,870 of 16,590 usage rows (11.3%)** fall between 00:00–04:00 UTC and are therefore attributed to the wrong local day. In practice: every evening session after 20:00 EDT. Distinct day count moves from 46 (UTC) to 45 (local).

## The decision

Bucket by local day, or stay UTC? For a personal observability tool answering "what did I do yesterday", local is the only reading that matches the question. But it silently re-dates 11% of all history, so it wants recording as an ADR rather than a quiet patch.

Storage stays UTC either way — this is a read-time bucketing change only.

`substr(datetime(at,'localtime'), 1, 10)` handles the stored format correctly (verified against `2026-08-29T00:13:55.057Z` → `2026-08-28`). The `[:10]` sites in Python need the equivalent.

## Known consequences — checked, not speculative

- **The frozen eval survives.** `eval/cases.json` is a self-contained fixture set (frozen 2026-08-28), not re-derived from the DB, so `eval/run.py` and `eval/score.py` are unaffected.
- **Every stored narrative goes stale.** Re-dating shifts run boundaries, so every `status_narrative.ledger_hash` will mismatch and the how-view will mark every project stale until the next analysis run regenerates it. That is ADR-0012's stale mechanism working as designed, and it is haiku-cheap — but it will look alarming for one cycle.
- **One docstring becomes false.** `build/test_how.py:230` records that the five frozen eval fixtures were reproduced byte-for-byte from live data. After this change they will not be. The claim needs updating (it is a note, not an assertion — no test fails).
- Decide whether `sessions.date` moves too, or only the display buckets. `MAX(date)` drives "synced through".

## Sequencing

Land after #73 (the resume gap), so this re-dates a complete data set rather than a partial one. No hard dependency.



---

**comment · 2026-08-29**

Landed in 671c305, recorded as [ADR-0014](../../docs/adr/0014-local-day-buckets.md).

**Local, not UTC.** Storage is untouched — every day bucket converts at read time, via exactly two expressions in `analyze.py` so the SQL and Python paths cannot drift: `day_sql(col)` for the grouped queries, `local_day(ts)` for the slices. `local_day` passes a bare `YYYY-MM-DD` through, since both kinds of value reach `serve._span` and converting an already-bucketed day would walk it a day west.

**`sessions.date` moved too** — the question in the ticket. It is the one *stored* bucket and has already discarded the clock time a conversion needs, so migration 5 re-derives it from each transcript head (~0.6 s over 281 sessions). A vanished transcript keeps its UTC date; a guess is not a re-derivation. Leaving it UTC would have put an evening session's tokens on one day and its ledger row on the next, and the what-view's bar-click filter joins the two.

**Measured on the live db:** 1,937 of 16,848 usage rows (11.5%) re-date. 14 of 281 sessions re-date, every one by exactly one day.

The three known consequences held as written: the frozen eval is untouched, every narrative goes stale for one cycle, and `test_how.py`'s byte-for-byte claim now says it was true of that moment only. Tests pin `TZ=America/New_York` — local bucketing makes the fixtures clock-dependent. 126 tests pass.

One extra, from the review: `run_ledger` now skips an undated trail event rather than emitting an empty run boundary. The old `[:10]` crashed on `None`; `local_day` made it silently empty, which is worse in this project's grammar. The event stays in the trail, the aggregates and the off-script list — only the band skips it.

The backfill import keeps writing the archive inventory's UTC day (migration 5 heals any imported session whose transcript survives). Documented as the ceiling on archive metadata, in the ADR and a `ponytail:` comment at the site.

Review also surfaced two pre-existing bugs on committed work, filed separately: #76 (#73's `invalidate_grown` wipes a live session's substrate) and #77 (a null narrative group takes down the analysis run).

