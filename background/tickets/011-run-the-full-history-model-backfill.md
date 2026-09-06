# #11 Run the full-history model backfill

state: closed · labels: wayfinder:task · opened: 2026-08-01 · closed: 2026-08-01

## Question

One-off: run the frozen extraction over the entire session archive across all projects (~250+ sessions, haiku, batched). Execution override applies. Output: findings + audit entries in local-data/ (and the store once it exists), coverage stated honestly. Feeds the why-view greybox with true multi-month depth.

Part of #1



---

**comment · 2026-08-01**

## Resolution

Backfill complete — the frozen ADR-0002 extraction ran over the full surviving archive. Outputs in `local-data/backfill/` (findings.jsonl, audit.jsonl, coverage.md, plus cached extracts/model outputs); runner committed as `backfill.py` (ac70e34).

**Coverage, stated honestly:**
- Inventory snapshotted before any model call: **210 sessions** across 24 project dirs; **44 prior analysis-run sessions excluded** by prompt signature (ADR-0003 self-exclusion). Sidechain/subagent transcripts not covered (matches the eval corpus). Archive depth as found: **2026-06-26 → 2026-08-01** — Claude Code prunes transcripts, nothing older survives, so "multi-month" in practice means ~5 weeks.
- **207/210 fully processed.** 200 why-findings; 155 audit entries (+55 model-SKIPped trivial sessions).
- **Evidence resolution 354/364 (97%)** — exact=215, fuzzy_msg=87, fuzzy_global=52, unresolved=10. Matches the eval baseline (97%) on production data.

**Two operational facts surfaced for the pipeline spec:**
1. **Limit exhaustion behaved as designed** (ADR-0003): runs 1–2 died mid-run on subscription limits; the cached/resumable design recovered everything on re-run with zero manual repair.
2. **A new why-pass failure mode: transcript capture.** On 4 large extract parts (3 sessions), haiku deterministically answers the transcript's own conversation instead of the analysis prompt — 3 identical failures across 3 runs, `.bad` outputs kept as evidence. Validation catches it (garbage never enters the store). The fix is a prompt repair (restate instructions after the transcript), which must clear the eval regression before landing — deliberately not done here since the why-prompt is frozen. Their what-pass entries are complete; 2 of the 3 have partial why coverage.

The why-view greybox now has true archive-depth data to work with.

