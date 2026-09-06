# #29 Live sessions get permanently truncated extracts — analysis of an in-flight transcript is cached forever

state: closed · labels: bug, needs-triage · opened: 2026-08-18 · closed: 2026-08-26

## Found during

The first real end-to-end analysis run (2026-08-17), diagnosing its 21 partial sessions.

## Problem

`analyze.py`'s `extract_session` skips extraction when the session's `map.json` already exists — correct for finished transcripts, wrong for sessions that were live at analysis time. A transcript still being written gets extracted mid-flight; the truncated extract is then cached permanently, and once the session completes processing (`done`), it is never revisited. The audit entry and findings for that session silently cover only the prefix that existed at first extraction. Several of yesterday's partials are exactly this shape (sessions from the same evening, still running when the run reached them).

## Possible directions (operator's call)

- Skip sessions whose transcript mtime is within some window of "now" (a live-session guard) and leave them pending for the next run
- Invalidate the cached extract when the transcript has grown since extraction (compare stored size)
- Accept the prefix semantics and state them in CONTEXT.md ("an entry covers the session as of its analysis run")

## Acceptance criteria

- [ ] A session analysed while live does not end up with a permanently truncated audit entry without that being either prevented or explicitly documented semantics
- [ ] A test covering the transcript-grew-after-extraction case



---

**comment · 2026-08-26**

Fixed in a452d79, all three directions combined:

- **Live-session guard** — transcripts modified within `LIVE_WINDOW_S` (5 min) are skipped by both the substrate scan and the what-pass loop; the session stays pending for the next run.
- **Growth invalidation** — a not-yet-done session whose transcript size differs from the recorded one has its cached extract parts, sidecar map, cached what-pass outputs, and scanned grains dropped and redone that run (covers the extracted→partial→grew straddle).
- **Prefix semantics** — documented in CONTEXT.md: an audit entry covers the session as of its analysis run, so a session resumed after `done` keeps its original entry.

Acceptance criteria: truncation is now prevented pre-done and explicitly documented for the resumed-after-done case; regression tests added at the run_analysis seam (`test_transcript_grown_after_extraction_is_reextracted`, plus guard and grains-rescan tests).

Note beyond the ticket: fill_substrate had the same one-shot shape, freezing tool_events/usage (and adr_count) at the prefix — fixed by the same guard + invalidation. Known residuals: a write landing in the seconds between the guard check and extraction can still slip through (rare race, judged not worth a lock), and pre-fix truncated done entries remain as-is under prefix semantics.

