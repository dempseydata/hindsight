# #22 Where-view substrate: tool events, usage, mechanical ADR counts

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-17

## Parent

#15

## What to build

The JSONL-derived measurement substrate: `tool_events` (session, tool-use id, name, timestamp, file path where applicable) and `usage` (per-assistant-record token counts by model) filled during sync, and the mechanical ADR count computed onto audit rows at assemble time — distinct files under the project's `docs/adr/` written or edited in the session, semantics "ADRs touched", never model-derived (ADR-0004). Token totals become queryable per session, day, and project regardless of OTEL coverage.

## Acceptance criteria

- [ ] Fixture sync fills tool_events with tool_use/tool_result pairing by id and usage with all four token fields
- [ ] A fixture session touching two ADR files (one created, one amended) gets adr_count=2; an unrelated-edit session gets 0
- [ ] Tokens per session/day/project answerable with plain SQL against the store
- [ ] Unknown JSONL record types are counted-and-skipped, not fatal
- [ ] Version-gated fields (tool_use_id absent on older CLIs) degrade gracefully

## Blocked by

- #17

