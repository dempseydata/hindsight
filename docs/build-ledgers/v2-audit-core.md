# Build ledger: #82 v2 audit core — branch night-shift/v2-audit-core

Authority: push + tracker yes · End state: branch only · Baseline: 255 tests (1 skipped), 30 s

Order: #84 → #85 → #86 → #87 → #88 → #89 → #90 → #91 → #92 → #93 → #94. Human (skipped): #95, #96.
Human-verified (built, left open): #84 (async on Stop/SubagentStop), #91 (real-data equivalence run), #93 (live install, launchd), #94 (local-process.md review, master frontmatter).
Contracts: ADR-0039.

| Ticket | Status | Commit | Rounds | Suite | Notes |
| --- | --- | --- | --- | --- | --- |
| #84 | built, open for human check | (this commit) | 1 | 261 tests, 31 s | `async` on Stop/SubagentStop needs a live session |

## Owed

## Decisions
- #84: raw store columns are `session_id`, `agent_id`, `byte_offset`, `high_water`, `last_hash`, `last_size`; each new table gets a unique index on `ifnull(agent_id,'')` — ADR? yes (permanent once v10 ships; fold into ADR-0039 §8)
- #84: folder identity stored as `transcripts.folder_identity` on the parent registry row; first recorded wins — ADR? no
- #84: a rewritten prefix is breakage condition 6, `source='capture'`, one open row per session; `BREAKAGE_COLS` gains `session_id` — ADR? yes (amends ADR-0033/0037's condition list)
- #84: `provenance` defaults to `'v1'` until #87 — ADR? no
- #84: `otel_histogram` table created in v10 (ADR-0039 §1) — ADR? no
- #84: the capture hook calls `init_db`, so it runs the migration itself — ADR? no
- #84: a payload naming no transcript, or a path not ending `.jsonl`, writes nothing; a missing cwd records no identity; events other than SessionStart/Stop/SubagentStop exit before opening the store — ADR? no

## Blocked

## Nits
- #84: acknowledging a condition-6 row does not stick; the next firing reopens it. The banner's "acknowledge … to close" overpromises until a reset path exists.
- #84: the condition-6 banner keeps the heading "transcript shape changed" (`cli/serve.py:150`).
- #84: `_migrate_v10` commits `user_version=10` before `VACUUM`; if that VACUUM fails, `auto_vacuum` is never retried.
- #84: a refused rewrite still records capture health as a success.
- #84: `docs/` (flows, architecture, cron, permissions, variables) still describes `hook.py` — re-run `/document-app` after the shift.
