# ADR-0034: Raw records are compacted per session after a configurable limit, holding back anything not yet derived

**Date:** 2026-11-15 · **Status:** accepted, amended by ADR-0038 (§8: compaction runs in the analysis run, on demand too) · **Amends:** ADR-0031 · **Decides:** issue #67 (map #59, v2 audit core)

## Context

The raw store exists so that a parser fix re-derives from hindsight's own copy (ADR-0031). It also holds whatever was pasted into a session, secrets included, verbatim. ADR-0031 §4 made a time limit the store's only size control. Measured on 2026-11-13: per-record zlib holds 51 days in 189 MB, about 3.7 MB a day.

Claude Code's documented transcript retention defaults to 30 days, and this machine sets no `cleanupPeriodDays`. Even so, transcripts up to about 50 days old were still on disk on 2026-11-15. The limit is therefore measured against an observed horizon, not one Claude Code guarantees.

The secrets case is narrower than the ticket put it. The database is local, owned by the same user and backed up like `~/.claude`. Failed-call error text in derived rows is already kept verbatim and uncapped (ADR-0027), and no limit on raw records reaches it.

## Decision

1. **The limit defaults to 90 days, counted from a session's newest record** across its parent and subagent transcripts. About 330 MB at today's rate, and a parser fix can rebuild a quarter of history.
2. **It is set by `HINDSIGHT_RAW_DAYS`**, the same environment-variable pattern as `HINDSIGHT_TZ` and the `~/.hindsight/` override. `0` means never compact. There is no floor. A negative or non-numeric value is a configuration error: the nightly records it in health and compacts nothing that night, never falling back to the default. A bad value stops deletion; it never triggers it.
3. **Compaction is per session, never per record.** Derivers rebuild a session whole (ADR-0031 §6), so a session with some of its records deleted would re-derive into wrong rows rather than missing ones.
4. **Held until done.** A session is not compacted while any current deriver has yet to derive it, or while the what-pass has it `pending` or `partial`, unless it is trivial. This is ADR-0015's lesson: a queue must never hold a session past the point of deletion. Health reports sessions held past the limit.
5. **Everything derived survives.** That includes the records index, which `raw` sessions are dated from (ADR-0031 §5), and each transcript's high-water and last-record hash, so the sweep never captures a compacted session again.
6. **A compacted session's rows take a third provenance, `compacted`.** Like `v1`, they are frozen: a deriver version bump skips them, and views count them, never hide them.
7. **No scrubbing.** Raw records stay verbatim. The limit is the only control on secrets held there.
8. **Compaction runs in the nightly, after derivation.** It logs how many sessions it compacted, and health states the active limit. Lowering the limit takes effect at the next nightly, without confirmation, and cannot be undone. The v10 migration sets `auto_vacuum = INCREMENTAL` (one full `VACUUM`), so deleted pages go back to the disk.

## Alternatives rejected

- **Match Claude Code's retention (30 days).** Re-derivation would cover barely more than the disk already does.
- **Keep forever by default.** About 1.35 GB a year, and secrets held forever. It remains available as `0`.
- **A constant in code.** Rejected by the operator in favour of a setting.
- **Keep `raw` provenance and record the deriver version per session.** A table would then hold rows from mixed versions, a new kind of unknown, where frozen is one the views already state.
- **A redaction pass.** It breaks the verbatim rule re-derivation rests on, and a pattern scrubber implies coverage it cannot give.
- **A floor on the limit.** The holds already prevent the one real loss: a session compacted before it is derived.

## Consequences

- After a deriver version bump, the rebuilt table mixes `raw` rows at the new version with `compacted` and `v1` rows at older ones. The views say so.
- The what-pass extract is derived output, so it survives. A changed what-pass prompt cannot re-run on a compacted session, because its conversation text is gone.
- Error text in derived rows outlives the limit (ADR-0027).
- Not verified: why transcripts here outlive Claude Code's documented 30-day default. The decision does not depend on it.
