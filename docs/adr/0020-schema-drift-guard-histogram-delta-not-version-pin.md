# ADR-0020: The schema-drift guard is a histogram delta between record versions, not a version pin — and acknowledge is decoupled from rescan

**Date:** 2026-09-11 · **Status:** accepted · **Decides:** issue #15 (spec #11, ingest fidelity)

## Context

Ingest joins on JSONL fields Anthropic documents as internal: `type`, `message.content`, `message.usage`, block types and their keys. A CLI release can thin the rows without failing the run — the scan counts an unknown record into `skipped_records` and carries on, and a missing `usage` key is a silent zero in every where-view total. Nothing compared one run's shape with the last.

The obvious guard — pin `claude --version` and alert on a bump — was checked against the corpus before this was cut: seven distinct record versions across 326 sessions in three months (nine, after the subagent transcripts landed). A pin would fire most weeks and train the operator to re-pin blind. The version is a fact worth logging; it is not a signal.

## Decision

1. **The signal is the shape, per record version.** The substrate scan counts, as it parses, every key one level deep — the record-type distribution, each type's top-level keys, `message`, `message.usage`, the content block types and each block type's keys — into a **field histogram** keyed by the record's own `version`. Never per run (a run only scans what grew that night) and never per session (one transcript can hold records from two CLIs). Stored per session so that the per-session wipe every rescan path already runs keeps it exact; summed per version at check time.
2. **The comparison is the newest version with at least 20 records against the nearest earlier one with as many** — and a scope (a record type, or a block type within one) is compared only where both sides have 20 units. A new CLI with one short session waits for evidence instead of tripping on a sample of three.
3. **Three trip conditions, two tiers.** A **field-contract** key present in >90% of a scope's units before and <50% after is *problem*: the rows since may be thin. A top-level key absent before and present in >50% after is *informational*: upstream added something, the rows cannot be wrong. This run's skipped share exceeding 3× the median of the last seven runs is *problem*, the one per-run condition, because a parse failure is a run-time event; a run under 1,000 records neither trips nor enters the median's window.
4. **The field contract lives beside the readers.** `FIELD_CONTRACT` at the top of `build/substrate.py` lists every (scope, key) the scan, the extract and the head scan depend on being present, enumerated from the code. The guard walks that list; the histogram counts a superset of it, so an added key is visible without the contract naming it. The three readers were not refactored into one module for this — the list is the seam, not a rewrite.
5. **A trip is a breakage row, and ingest never halts.** One row per trip, deduplicated against the open rows: run timestamp, tier, condition, the two versions, the key, the two shares, and the first session day under the new version. Session rows are never marked — the row carries the date range, so there is nothing to un-mark. The run completes as normal.
6. **Surfacing: every tier on every view, notification for the thin-rows tiers only.** A banner on what, where and how, tier-coloured through the semantic roles (problem red, informational blue — Few), naming the condition, the key, the versions and the date since. A macOS notification for conditions 1 and 3 only, behind a flag the command line sets and no test does: a notification always means a decision is needed.
7. **Acknowledge is decoupled from rescan.** `acknowledge-breakage <id>` closes the row, and that row's new version becomes the comparison baseline: versions below it are never the comparison again, so the same delta is quiet from then and the next version is judged against the acknowledged one. It is a judgement about the alert and nothing else. A parser fix ships as a code change plus a schema-version bump, which rescans the affected sessions through the existing migration mechanism. Two operator actions, each with one meaning; neither is ever automatic.
8. **The CLI's own version is a log line.** `claude --version` is printed once per run. It fires nothing.

## Alternatives rejected

- **Pin `claude --version` and alert on change.** Seven versions in three months: noise that trains blindness. Kept as the log line only.
- **Per-run or per-session histograms.** A run's shape is whatever happened to grow that night; a session's is one CLI's — until it is resumed under the next one. The record's own `version` is the only grain at which "this CLI writes this shape" is true.
- **One histogram row per (version, key), incremented in place.** Simpler to read, but the growth top-up and the schema-bump rescan both wipe and refill a session — the increment would double-count every resumed session. Per-session rows join the existing wipe list and the sum is a query.
- **Mark the affected sessions.** The date range is on the breakage row already; a session mark would need un-marking on acknowledge and would conflate a run-level observation with a session's lifecycle (`pending → done | empty | lost`).
- **Acknowledge triggers a rescan.** A rescan without a parser change reproduces the same rows; a rescan with one is the schema-bump path that already exists. Coupling the two gives one command two meanings.
- **Refactor the three readers into one module so the contract is enforced by construction.** Right in principle, larger than this ticket; the contract list beside the readers, walked by the guard, is the smallest thing that stops the two drifting, and the refactor stays available.

## Consequences

- The first run after this lands rescans every scanned session whose transcript survives (migration 8) so the baseline covers the corrected corpus — 4 s on this machine, no model calls. Every contract key reads 100% under every version and nothing trips.
- A CLI that drops the `version` key itself is the one drift this cannot see: its records fall into the versionless bucket, which sorts oldest. `sessions.cli_version` going NULL on new sessions is the tell; stated, not guarded.
- Two stated heuristics: the breakage row's *since* day reads `sessions.cli_version`, the head-scan version, so a session opened under the old CLI and resumed under the new one is missed and the day can run late; and a spiked run enters condition 3's window like any other, so a new normal stops tripping after about four runs — the open row stays until acknowledged, so the alarm is never silently lost.
- A new record *type* is visible in the histogram's type distribution but trips nothing — condition 2 is about top-level keys of a known type. Widen if a type ever carries the tokens.
