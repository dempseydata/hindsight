# #38 Backfill stored model-refusal text as audit entries (29 rows, skip=0)

state: closed · labels: bug, needs-triage · opened: 2026-08-19 · closed: 2026-08-26

Found by the design delta pass ([#31](031-delta-pass-greyboxes-re-judged-on-the-real-backend.md)): 29 of the 183 non-skip audit rows contain model refusal text instead of an audit entry — e.g. "I'm ready to generate audit-log entries, but I don't see a session transcript to analyze…" — stored verbatim in `audit.markdown` with `skip=0`.

Detection:

```sql
SELECT COUNT(*) FROM audit
WHERE skip=0 AND markdown IS NOT NULL AND markdown NOT LIKE '###%';
-- 29 as of 2026-08-18
```

The what-pass contract (ADR-0004) expects strict four-section markdown opening with `### title`; these rows are what-pass calls that never received/parsed a transcript, imported by the backfill as if they were entries. They should be SKIP rows (or reprocessed), not rendered entries — the what-view currently has to quarantine them at render time.

Also spotted in the same pass, likely the same family of ingest laxness: at least one `tool_events.name` holds a shell command string (`ls output/…`) rather than a tool name — the substrate scan accepted a malformed record.

A separate concern from #29 (truncated live-session extracts), but both are ingest-honesty defects.



---

**comment · 2026-08-26**

Fixed in 08c3c17. Write-time contract gate (`valid_entry`): a what/merge output must open `###` or be a SKIP verdict; anything else (refusal prose) is a failed call — uncached, retried next run, never stored. `call_cached` also rejects a poisoned cached file, so pre-gate refusals re-run instead of being served stale, and the backfill import applies the same gate (refusal-cached sessions import as pending).

A user_version-2 migration deleted the 29 stored skip=0 refusal rows (28 what-v1, 1 what-v2) and set their sessions back to pending — already applied to the live db; they reprocess on the next analysis run. Detection query now returns 0.

The `tool_events.name` half was already fixed at scan time by the #50 sweep (whitespace/non-string names counted as skipped); the live db holds zero such rows.

