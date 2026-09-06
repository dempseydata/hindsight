# #44 Server skeleton and shared header chrome

state: closed · labels: wayfinder:task · opened: 2026-08-20 · closed: 2026-08-25

Part of #40

## Question

Build the on-demand foreground server (stdlib `http.server`, started to look / stopped when done, strictly read-only over SQLite, `tokens.css` inlined at render time) and the shared header chrome both views mount:

- project chips — filter, never switch; compose with time filters;
- stacked per-day chart between chips and content — calendar-continuous, scrollable, newest at right;
- click-a-bar time filtering (day → range → deselect → clear);
- window presets 7/14/28/90/all, default 14, anchored to last-synced day; a chart click overrides;
- "Hide cache reads" toggle.

Judge here against real data and record: chip policy (the ≥1%-of-tokens threshold, scratch-dir names making unreadable chips). The server never grows a run button.


---

**comment · 2026-08-25**

**Resolved.** Commit c6f2af9 — `build/serve.py` + `build/test_serve.py` (7 tests, full suite green; interactions verified in a live browser against the real DB).

**Server** — stdlib `http.server` on `127.0.0.1:8321`, foreground (`python3 build/serve.py`, Ctrl-C to stop), strictly read-only: the SQLite connection is opened `file:…?mode=ro` so a write is a hard error, not a convention. `tokens.css` is read and inlined per request — a token edit shows on the next reload, and ⌘R is the whole refresh story (ADR-0008). No run button, and none possible: the handler only implements GET. `/` redirects to `/what`; `/what` and `/where` render the chrome with stub bodies until #45/#48.

**Chrome, as specified** — chips filter (never switch) and compose with time filters; stacked per-day token chart (four segments: in / out / cache-create / cache-read on `--o-ink-1..4`), calendar-continuous 2026-07-11 → last-synced, gaps rendered as absent bars (never zero-height), newest at right with auto-scroll; click-a-bar day → range → deselect, clear resets, any chart click overrides the preset; presets 7/14/28/90/all, default 14, anchored to `MAX(sessions.date)`; hide-cache-reads toggle drops the fourth segment and re-peaks the chart. Selection renders as a faint `--o-compare` wash plus a 2px underline. Coverage line states synced-through date, session count, and the gaps-vs-unknown honesty rule.

**Chip policy — the judgement this ticket owed, made on real data:**

The bare ≥1%-of-tokens threshold fails the what-view: only 3 projects clear it (the largest project 88%, hindsight 6.4%, the next 4.7%), and it permanently strands ledger-heavy projects whose transcripts were pruned — `my-os-my-logs` has 36 sessions and *unknown* (not zero) tokens, so no token threshold can ever reach it. The scratch-dir problem is orthogonal: unreadable chips all share one mechanical marker (project names that are encoded filesystem paths, leading `-`).

**Policy adopted:** a chip requires (a) a non-path project name — leading `-` means scratchpad/probe/system dir, excluded outright regardless of volume — and (b) ≥1% of all-time tokens **or** ≥1% of all-time sessions. The session leg is what keeps pruned-transcript projects reachable; all-time (not per-window) keeps the chip row stable while filtering. On today's DB: 8 chips (career-ops, hindsight, content, thisisme, my-os-my-logs, career-ops-CLI, my-os, my-logs), 17 chipless tail projects, stated in a note under the chips ("data still counted; chips filter, never switch").

**Mount seam for the view tickets** — page JS exposes `window.hs`: `S` (active chips, tFrom/tTo, hideCR, preset), `inWin(d)` / `inProj(p)` predicates, `fmt`, and `hs.onFilter(fn)` — a view registers a callback and re-renders its own content when any filter changes. `DATA` carries the per-(day, project) token grain.

**Riders:** the pre-commit review swept the whole recent diff and found nothing in this ticket's files; all residue from #41–#43 (two confirmed scan crash paths, the migration wipe window, CONTEXT.md's stale `runs` entry, unamended ADR-0002, handoff drift, smaller quality items) is filed as #50, needs-triage — off this map's route per the #38/#29 precedent.


