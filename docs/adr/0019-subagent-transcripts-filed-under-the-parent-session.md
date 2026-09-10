# ADR-0019: A subagent transcript is filed under its parent session — never a session of its own

**Date:** 2026-09-10 · **Status:** accepted · **Decides:** issue #13 (spec #11, ingest fidelity)

## Context

Claude Code writes each spawned subagent its own JSONL at `<project>/<session>/subagents/agent-<id>.jsonl`. `sync_sessions` globbed `*/*.jsonl` — two levels — and never saw them. On this machine 345 such transcripts sit under 64 of 673 sessions; one session spawned 98. Every record in one carries `sessionId` (the parent's id), `agentId`, `isSidechain: true` and the same `type` / `message` / `usage` shape as a parent record, and a subagent transcript holds its **own** `usage` records — the parent's transcript does not repeat them.

OTEL sized the hole: since 2026-08-01, `claude_code.token.usage` with `query_source=subagent` is ~481M cache-read and ~33M cache-creation tokens against main's ~2,546M and ~48M. Every where-view total, league entry and how-view trail was short by that spend and those events.

## Decision

1. **A session is the operator's session including everything it spawned.** A subagent transcript is not a `sessions` row. Its `usage`, `tool_events` and `command_grains` rows are filed under the **parent session id**, with `agent_id` kept on each row (NULL for the parent's own) so a per-agent breakdown is a query, never a second session. The vocabulary is *subagent transcript* / *parent session* / *agent id* — never "child".
2. **Growth is detected per transcript.** `subagent_transcripts` records each transcript's path and size against the parent, as `sessions.size` does for the parent's own. A session with a subagent transcript unseen or grown since its scan is a session that grew and rides the existing top-up path (ADR-0013). That path is also the backfill: sessions synced before this decision have no recorded subagent transcripts, so their first run after it tops them up — no migration.
3. **The live-session guard covers the parent when any subagent transcript is fresh.** Scanning a session while one of its agents is still writing would cache a truncated agent.
4. **Self-exclusion is inherited.** A subagent transcript has no prompt signature of its own; it is reached only through its parent's `sessions` row, so an excluded parent's subagents write nothing.
5. **The audit is blind to subagents, by design.** The extract, the what-pass and the re-audit threshold (`audited_size`, the quarter-unseen rule) read the parent transcript alone. A subagent's internal turns are not the operator's conversation, and its returned result already sits in the parent as a tool result, which the extract excludes on purpose. A subagent transcript appearing or growing never rewrites an audit entry; the what-pass eval set stays valid.
6. **Rendering: two numbers, no list.** The what ledger row carries a mechanical *N subagents* note so a large total has a visible cause. The where view carries the subagent count and their share of the tokens in view as a tile — at window grain, because the where view has no per-session detail; `WHERE.sess` feeds only the session lens and the sessions tile. The count is attributed to the session's first day, as the sessions tile beside it is; the token share is computed at (day, project) grain, the same base as the token tiles, so it is a true ratio in any window. No per-agent rows, no grouping by agent type, no new league row type: a consumer appearing in both parent and subagent is the same session and the session lens charges it once.

## Alternatives rejected

- **A subagent transcript is its own session.** The ledger, the league and the how-view all want the operator's session as the unit; a 98-agent session would become 99 ledger rows. The OTEL feed already attributes subagent tokens to the parent session id, so agreement across sources needs the same key.
- **Fold subagent rows in without an agent id.** Cheapest, but the per-agent question ("which agent type spends") would then need a rescan to answer; one nullable column keeps it a query.
- **Include subagent turns in the extract.** Would put the agents' internal chatter in front of the what-pass, poisoning entries the eval set was built against, and grow extracts many-fold for text the parent already summarises as tool results.
- **Storing the subagent transcripts' mtime.** Nothing reads it — liveness reads the disk, growth reads the size. Left out.

## Consequences

- The first run after this lands wipes and refills the substrate of every session with a subagent transcript on disk (64 today). Project totals rise on that run; that is the undercount closing, not a new defect. Re-audits are untouched — the share is measured on the parent alone.
- `sessions.skipped_records` counts the subagent transcripts' skipped records too — one marker per session, as before.
- Issue #15's field-histogram baseline is computed after this lands, over the corrected corpus.
