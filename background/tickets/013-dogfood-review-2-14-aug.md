# #13 Dogfood review #2 (~14 Aug)

state: closed · labels: wayfinder:task · opened: 2026-08-01 · closed: 2026-08-16

## Question

Second weekly review; closes the two-week test. Same recording as review #1. Outcome feeds "Lock the audit format".

Part of #1



---

**comment · 2026-08-16**

**Agent prep (2026-08-16) — recording done + objective spot-check ahead of the human review.** The memory-vs-entries verdict is the dev's; this comment covers only what can be verified against records.

**Recording (same as review #1):** frozen ADR-0002 what/why passes, pinned haiku via `claude -p`, over the 12 hindsight sessions dated 2026-08-01 → 2026-08-16 (597 analysis-run sessions self-excluded by prompt signature; the in-flight review session itself excluded). Result: **11 substantive entries + 1 model-SKIPped trivial session**, log at `local-data/dogfood-week2/dogfood-hindsight-audit-week2.md`; evidence resolution 5/5. One transient why-pass failure (5740b136 p1) retried clean — *not* the backfill's transcript-capture mode. The trivial session was correctly SKIPped this time (review #1's FLUSH_OK-echo miss did not recur, unprompted).

**Verified against git/issues:**
- Commit hashes named in entries exist and match: `0c7b475` (ADR-0002 freeze), `1ea0041` (ADR-0003 amendment).
- Backfill entry's stats match `coverage.md` exactly (207/210, 200 findings, 155 entries, 97% resolution, 44 self-excluded).
- `507/507` tool_use_id pairing is verbatim from `definition/ingest-schema-verification.md`.
- All three greybox entries match the resolutions on #5, #6, #12 (ledger variant, day-ledger variant C + noise policy, panel dashboard + presets + sunk-cost drill + ccwhere dedup fix).
- The 16 Aug entry matches #7's resolution as recorded today.

**Findings for the dev to judge:**
1. **Backfill entry (05e0f0ca), Decided line: "Run from cloud via `claude -p` from repo root" — wrong.** The backfill ran locally on subscription (ADR-0003); the phrase is self-contradictory and "from cloud" is fabricated. One distorted clause in an otherwise accurate entry.
2. Backend-stack entry says ADR-0003 was "amended twice"; git shows one amendment commit changing two lines (two clarifications, one commit). Charitable read is faithful.
3. Process-conformance entry's rationale ("existing backfill already captures required signal") is a loose paraphrase — the recorded rationale was raw-JSONL survival + config snapshots, not the backfill.

**Threshold arithmetic:** 11 substantive entries; >1-in-10 materially-wrong means **≥2 bad entries** kills. Timing: targeted ~14 Aug, run 16 Aug — late by 2 days, not skipped; with review #1 also done, kill criterion (a) cannot trigger.



---

**comment · 2026-08-16**

**Resolution (2026-08-16).**

- **Review done:** yes, 2026-08-16 — two days past the ~14 Aug target. Late, not skipped; with review #1 also done, kill criterion (a) — both reviews skipped — is definitively not triggered.
- **Accuracy vs memory:** dev verdict — "the information is good." No materially wrong entries. The one agent finding stands (the backfill entry's fabricated "Run from cloud" clause): one distorted clause of 11 substantive entries, well under the ≥2-of-11 (>1-in-10) threshold. Kill criterion (b) not triggered.
- **Actions arising:** none reported — per the review #1 calibration note, not a failure signal for a quiet window (work concentrated on 1 and 3 Aug, quiet 4–15 Aug).
- **Bonus signal:** the trivial session was correctly model-SKIPped this run with no prompt change — review #1's FLUSH_OK-echo miss did not recur.

**Verdict: the two-week test is closed and assumption 1 survives both reviews.** The what-view stands as a review-worthy pseudo audit log. Inputs for "Lock the audit format" (#14): review #1's missing-culling-rationale finding, this review's fabricated-clause finding ("from cloud"), and the observed loose-paraphrase tendency in Decided lines.


