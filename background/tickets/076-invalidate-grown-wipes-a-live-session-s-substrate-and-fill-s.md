# #76 invalidate_grown wipes a live session's substrate and fill_substrate then skips it — the rows are gone for that run

state: closed · labels: bug · opened: 2026-08-29 · closed: 2026-08-29

Found by `/code-review` while landing #74. A regression introduced by **#73**, not by #74.

## Symptom

`invalidate_grown` (`build/analyze.py:724`) deletes every `usage`, `tool_events` and `command_grains` row for any session whose transcript has grown, then clears `skipped_records` so the next `fill_substrate` refills them.

#73 correctly removed its old `WHERE status != 'done'` filter — the substrate must be topped up whatever the status (ADR-0013). But it never gained the live-session guard that `fill_substrate` has. So for a session that is **`done` and currently live** (modified within `LIVE_WINDOW_S`):

1. `invalidate_grown` deletes all its substrate rows.
2. `fill_substrate` sees the live transcript and skips it (ticket #29's mid-flight guard).
3. The session ends the run with **zero** usage/tool/grain rows.

Reproduced: 1 usage row in, 0 out.

## Why it matters more now

Pre-#73 the `status != 'done'` filter meant done sessions were never touched, so this path could not reach historical data. #73 opened it to every done session — which is the bulk of the corpus. Any analysis run that starts while a resumed session is still being worked loses that session's substrate until the next run catches it not-live.

## Likely fix

The live check `fill_substrate` performs already exists. `invalidate_grown` should skip a live transcript rather than wipe-then-fail-to-refill — one guard, before the DELETE. Worth checking whether the wipe and refill should share a transaction while there.



---

**comment · 2026-08-29**

Fixed in 1dfff4a. `invalidate_grown` now skips a live transcript before the DELETE — the guard `fill_substrate` already had. Regression test `test_live_resumed_session_keeps_its_substrate` fails at 0 rows without it. ADR-0013 amended: "always topped up" means once the transcript is quiet; deferral, not exception.

On the transaction question — not needed. The wipe sets `skipped_records=NULL`, which is the scanned marker, so a crash between `invalidate_grown` and `fill_substrate` leaves the session refillable on the next run. The defect was the guard, not the commit boundary.

