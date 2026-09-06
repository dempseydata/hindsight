# #9 Lock the extraction contract

state: closed · labels: wayfinder:grilling · opened: 2026-08-01 · closed: 2026-08-01

## Question

Freeze the model-pass contract: combined or separate (per the A/B), finding shape, and the message-index locator contract (extract carries indices; model returns locators; pipeline resolves + stores verbatim spans — model-quoted text never stored as evidence, per the eval's confirmed constraint).

Part of #1



---

**comment · 2026-08-01**

## Resolution: contract frozen — ADR-0002

Grilled 2026-08-01; full contract recorded in [`docs/adr/0002-extraction-contract.md`](../../docs/adr/0002-extraction-contract.md). The decisions:

1. **Two separate passes, frozen flat** — what-pass (audit) + why-pass (setup changes), per the A/B (#3). No revisit trigger: combining saves sub-cent and degrades recall/evidence/count.
2. **Model pinned** to `claude-haiku-4-5-20251001`; the pin moves only via a regression run against the frozen eval set (match-or-beat recall and resolution rate).
3. **Index contract** — extract pieces numbered session-globally across chunk parts; sidecar map piece-index → source jsonl uuid so evidence survives the throwaway extract. Chunk cap 180K chars as measured.
4. **Why-pass shape** — `[{"change", "why", "evidence": [{"msg", "quote"}]}]`, 1–3 locators, quotes 8–40 words as search keys. No category/confidence/severity; categorization revisited when the why-view shows real findings (earliest: why-view greybox).
5. **Resolution ladder** — exact in-message → fuzzy in-message → fuzzy whole-extract (threshold 0.6) → unresolved (finding + locator kept, evidence marked unresolved; model quotes never stored, no exceptions). Resolution rate is a standing health metric.
6. **What-pass frozen as measured** — markdown, no locators, Setup-changes line retained; spot-check remains its integrity check. Ride-along prompt repair: firmer trivial-session SKIP rule.
7. **Overflow** — why-pass: per-part + concatenate (global indices, no dedupe); what-pass: per-part + one merge call to keep one entry per session.

