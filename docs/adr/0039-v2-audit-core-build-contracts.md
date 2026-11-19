# ADR-0039: v2 audit core — build contracts fixed before the unattended build

**Date:** 2026-11-17 · **Status:** accepted · **Decides:** the decision sitting before the night-shift build of [#82](https://github.com/dempseydata/hindsight/issues/82) (tickets #84–#94) · **Amends:** ADR-0031 (migration split, NULL agent key, §7 v1-row replacement), ADR-0037 (migration split)

## Context

ADR-0031 to ADR-0038 settle the v2 design but leave contracts open that several tickets share: tables one ticket migrates and later tickets read, bytes one ticket stores and another hashes, and one place where the ADRs and the tickets disagree about which migration does what. A prescan found eight; the operator settled each before the build, so no implementer invents one alone.

## Decision

1. **Migration split follows the tickets.** v10 is additive only and carries *every* new table and column the spec needs, including the breakage columns below. v11 (#86) drops `audit.date` and `redate_sessions`; v12 (#88) drops `scan_runs`. ADR-0031 §5 and ADR-0037 §6, which put the drops in v10, are amended accordingly.
2. **NULL agent key stays NULL.** The parent's raw records keep `agent` NULL (ADR-0031). Idempotency comes from a unique index on `(session, ifnull(agent, ''), offset)`; `raw_records` stays a rowid table, since deriver state reads the rowid.
3. **Stored bytes and the hash.** A raw record stores the exact line bytes *including* its trailing `\n`, so the records in offset order rebuild the file prefix. The registry's hash is sha256 of the last stored line's bytes, and the registry stores that line's length, so verification is one seek.
4. **The capture key comes from the path.** Session id and agent id are taken from the transcript path (`<session>.jsonl`, `subagents/agent-<id>.jsonl`) by the hook and the sweep alike — v1's `subagent_transcripts` rule — never from the hook payload's ids.
5. **Health row.** Columns beyond the spec's last success / last error / error text: `failing_since` (set on the first error after a success, cleared on success) and `detail` (JSON; the analysis row carries the active raw limit and the count of sessions held past it). Every timestamp, `captured_at` included, is ISO UTC with a trailing `Z`. Sessions held past the raw limit are a designed skip and stay silent at SessionStart.
6. **Breakage columns.** v10 adds nullable `source`, `session_id`, `day` and `derivers` to `breakage`, and relaxes `old_share` / `new_share` to nullable, so per-day (#89), per-session (#86), per-deriver (#88) and OTel rows share one table.
7. **Re-audit share unit.** #91's "captured record bytes" is the registry's high-water offset — file-byte units, the same unit as v1's `audited_size` — so existing audits do not mass-trip a re-audit.
8. **Names.** New tables: `transcripts` (the registry), `deriver_state`, `records_index`, `health`; new column `provenance`. Fixed in #84's migration.
9. **v1 rows are replaced per captured agent** (settled mid-shift, #87; amends ADR-0031 §7). When a deriver derives a session from the raw store, it deletes that session's `v1` rows only for the agents (parent `''`, or a subagent id) the raw store holds, and writes them as `raw`, in one transaction. `v1` rows for an agent whose transcript was never captured stay frozen; `field_histogram` `v1` rows stay unless every v1 agent of the session is captured. This avoids double counting without deleting anything the raw store cannot rebuild.

Shift conduct, also settled at the sitting: #84 is built assuming `"async": true` fires on `Stop` and `SubagentStop` and left open for a live check; #94 builds the resolution code and drafts hindsight's `local-process.md` (every stage restated, `cli/` for `build/`, `eval/` added), left open for review and the master's frontmatter edit.

## Consequences

- Version numbers never collide whatever order #88 and #89 land in, because no ticket after #84 adds a column.
- A change to the stored bytes or the hash after the first real capture would raise a false breakage for every transcript; treat §3 as frozen.
- A resume or fork that reuses a payload id under a different file path is captured under the path's key — one copy per file, never two per record.
