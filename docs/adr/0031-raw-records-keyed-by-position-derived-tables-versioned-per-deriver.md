# ADR-0031: Raw records are keyed by position, not uuid, and derived tables are versioned per deriver

**Date:** 2026-11-13 · **Status:** accepted, amended by ADR-0039 (§1 migration split, §2 NULL agent key, §9 v1 rows replaced per captured agent) · **Decides:** issue #65 (map #59, v2 audit core)

## Context

v2 captures every transcript record verbatim before any parsing, so that a parser fix re-derives from hindsight's own copy rather than from a disk that retention keeps shrinking (framing brief, `background/ideation/v2-framing.md`). The brief assumed each record could be keyed by its own id and estimated the compressed store at 40–60 MB. Both were measured against the 344 transcripts on disk on 2026-11-13 (94,981 records, 2026-09-24 onward):

- 37% of records carry no `uuid`: the metadata types (`api-request`, `last-prompt`, `custom-title`, `atis-latch` and fourteen more). About 11,000 of them repeat byte for byte within one file, so a content hash would merge records that are distinct. Where a `uuid` exists it is unique across every file.
- 451 MB raw is 129 MB under whole-file zlib and 189 MB under per-record zlib, about 3.7 MB a day. `attachment` records are 193 MB of the raw total.

## Decision

1. **Key: (session id, agent id, byte offset).** The record's position in its transcript; the agent id is NULL for the parent. `uuid` is a non-unique indexed attribute, so a copied record (a fork, should one ever copy) is kept and deduplicated at derivation.
2. **Idempotency: append from a high-water offset.** Capture reads from the stored high-water per transcript, takes complete lines only, and inserts with `INSERT OR IGNORE`. It first checks the hash of the last captured record; a mismatch means the file was rewritten, which is a breakage, never a silent reset.
3. **A raw row holds the key, the verbatim line bytes and `captured_at`, nothing else.** Capture never parses JSON. `type`, `uuid` and `timestamp` come from a first versioned deriver, the records index, so a moved field cannot corrupt capture-time columns.
4. **Each record is zlib-compressed alone**, every row readable on its own. Every record type is captured; size is managed by the raw time limit (issue #67), never by a type filter. *Amended 2026-11-15:* the limit is 90 days from a session's newest record, set by `HINDSIGHT_RAW_DAYS` (`0` = forever). Compaction removes a whole session once every deriver and the what-pass are done, and its rows take a third, frozen provenance, `compacted` (ADR-0034, issue #67).
5. **No stored session date.** Start and end are the earliest and latest record timestamps across the session's parent and subagent transcripts; active days stay days with a usage row, bucketed at read (ADR-0014). A record without a timestamp has no date of its own. *Amended 2026-11-15:* `v1`-provenance sessions keep their stored start day, frozen like their other rows (issue #71). 165 of the 400 have no timestamped `usage` or `tool_events` row (137 of them audited), so the stored day is their only date; where those tables could date a session, the stored day still wins, 13 differing by a day. `sessions.date` holds that day for `v1` rows and NULL for `raw` rows. Every view reads a session's day through one expression: the stored day, else the local day of the earliest records-index timestamp. A `v1` day is never rebucketed after a zone change, and a `v1` session's end is unknown, never inferred. `redate_sessions` and the unread `audit.date` are removed in the v10 migration. *Amended 2026-11-17 (ADR-0039 §1):* v10 is additive only; the drops land in later tickets under later versions — `audit.date` and `redate_sessions` in v11 (#86), `scan_runs` in v12 (#88).
6. **Each derived table has its own deriver version.** A bump truncates and rebuilds that table alone from the raw store; otherwise each deriver works forward from its own high-water key. *Amended 2026-11-15:* a deriver works per session, not from a high-water key (issue #70). A session is due when its newest `raw_records` rowid is above the rowid stored when that deriver last derived it. Then it is re-derived whole, parent and subagents together: its `raw` rows are deleted and its raw records re-scanned, in one transaction per session per deriver. A version bump clears that deriver's stored rowids, so a rebuild runs through the same loop. Derivation is a batch step run by the analysis run and the nightly, never by the capture hook and never on view load, and it needs no live-session guard. State is not carried between runs: the merge rules (last-wins usage, first-wins `tool_use`, late results, the per-session histogram) stay whole-session, as v1's `scan_transcript` has them.
7. **Derived rows carry provenance, `raw` or `v1`.** A rebuild replaces `raw` rows only. `v1` rows, derived before the raw store existed, are frozen: nothing remains to re-derive them from. *Amended 2026-11-14:* the frozen set is most of history, not a remnant. 400 of 486 sessions (82%) have no transcript on disk, holding 366 of 433 audit rows and 41,796 of 51,528 `tool_events`. They are carried across in place, by a schema bump on v1's database rather than a rewrite (issue #66).

## Alternatives rejected

- **Key by `uuid`.** Fails for 37% of records.
- **Key by content hash.** Collapses ~11,000 legitimate repeats.
- **One compressed block per capture batch.** About 30% smaller, but needs an offset index kept in step with the blocks. A preset zlib dictionary is the cheaper later lever if size matters.
- **Drop known-bulky record types.** A maintained list, and unknown types are exactly what the drift guard needs to see.
- **One global schema version (v1's).** A usage-parser fix would rescan every table.

## Consequences

- The framing brief's size estimate is wrong by about 3×; ticket #67 starts from 189 MB for 51 days.
- Claude Code rewriting a transcript in place was not observed and is not handled beyond the breakage in point 2.
- Derived tables are a pure function of the raw store except for `v1` rows, by design.
