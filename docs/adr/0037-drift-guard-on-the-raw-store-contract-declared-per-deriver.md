# ADR-0037: The drift guard sits on the raw store: the histogram is a deriver, the contract is declared per deriver, and OTel gets its own histogram

**Date:** 2026-11-16 · **Status:** accepted, amended by ADR-0039 (§1: scan_runs dropped in v12) · **Amends:** ADR-0020 · **Decides:** issue #76 (map #59, v2 audit core)

## Context

The v2 framing brief (lesson 7) requires the drift guard and a field contract to be written before the first reader. ADR-0020's guard was built for v1: a substrate scan that parsed as it captured, three readers sharing one hand-kept `FIELD_CONTRACT`, and a run-level skipped share. v2 changes all three premises:

- Capture never parses (ADR-0031 §3). Derivation is a batch step that re-derives whole sessions (ADR-0031 §6), and raw records are compacted after a limit (ADR-0034).
- v2 has more readers than v1: the records index, usage, tool events, the trail, the extract and the histogram itself.
- OTel now owns tokens, cost, tool decisions, errors and hook timing (ADR-0033). The input-side cross-check covers only input tokens, so a renamed `cost_usd`, `decision` or `query_source` would read as zero or unknown with nothing tripping. A missing `query_source` would also blind the cross-check.

v1 already stores the histogram per session and wipes it on every rescan, which is the shape ADR-0031 §6 gives a deriver. OTel events are stored as flat attribute JSON, versioned by `service.version` under two services (`claude-code`, `claude-code-desktop`), each with its own version series.

## Decision

1. **The field histogram is a versioned deriver over `raw_records`.** It rebuilds a whole session in the same loop as every other deriver, in the batch step, never in the hook. Its rows carry provenance (`raw`, `v1`, `compacted`), and the guard sums across all three, so a compacted or `v1` session still counts as evidence for its version.
2. **The breakage row's *since* day comes from the histogram.** It is the earliest day of any session whose histogram holds the new version. This retires ADR-0020's stated heuristic, which read `sessions.cli_version` and ran late when a session was resumed under a newer CLI.
3. **Each deriver declares the (scope, key) pairs it requires, next to its own code.** The field contract is the union of the declarations. A thinned key's breakage row names the derivers that read it (for example, "usage rows may be thin"). Keys read but not expected present stay outside the declarations, as in ADR-0020 §4. There is no accessor enforcing the declarations: a missed declaration is a review finding.
4. **OTel has its own histogram,** keyed by (`service.name`, `service.version`, event name) over the attribute keys. It is derived per `session.id` from `otel_events`. It never touches the raw store or compaction, and events without a session (metrics) are outside it. It is checked against the keys the OTel-reading derivers declare, under condition 1 only, at tier *problem*. Condition 2 does not apply: an added attribute on a documented interface is noise. The input-side cross-check (ADR-0033 §5) stays a separate condition.
5. **Carried over from ADR-0020 unchanged,** per histogram: the 20-unit floors, the >90% → <50% thinning rule (*problem*), the >50% added-key rule (*informational*, one row per version pair), deduplication against open rows, acknowledge-as-baseline, notification for *problem* rows only, and the CLI version as a log line, never a trigger.
6. **Condition 3 (run-level skipped share) is retired.** In its place is **condition 5**: a stored record that fails to parse as JSON at the records-index deriver writes one *problem* row per session, with no median and no floor. Capture stores complete lines only, so any such row is a breakage. A new record type stays visible in the histogram's type distribution and trips nothing, as before. `scan_runs` is dropped in the v10 migration. Condition 3 rows already written stay in `breakage` as history.

## Alternatives rejected

- **Keep one hand-kept `FIELD_CONTRACT`.** With six or more derivers, it drifts from them silently, and a breakage cannot say which table is thin.
- **Enforce the declarations through an accessor.** This is the refactor ADR-0020 deferred. It wraps every field read in every deriver to catch an omission that a review catches anyway.
- **Rely on the cross-check alone for OTel.** It sees input tokens only. Cost, decisions, errors and `query_source` itself would drift unseen.
- **Condition 2 on OTel.** Additions to a documented interface are expected and harmless, so the condition would only ever produce *informational* noise.
- **Port the skipped share to a per-derivation-batch share.** A batch is whatever sessions happened to be due, no more a sample than a v1 run was. Its main content, unconsumed record types, was never a fault.

## Consequences

- The guard runs after derivation has caught up in the batch step, like the cross-check.
- A compacted session's histogram rows are frozen at the deriver version that wrote them. A histogram deriver version bump rebuilds `raw` sessions only, so comparisons mix versions in the way ADR-0034 already states for every derived table.
- The breakage table now holds conditions 1, 2, 4 and 5 for new rows. Condition 3 survives only in history.
- Not verified: whether OTel attribute keys change between `service.version`s in practice. The guard exists to find out.
