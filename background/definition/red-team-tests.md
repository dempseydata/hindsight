# Red-team tests: results (2026-07-31)

Tests run same-day against `red-team.md`'s kill-assumptions, using the harness in `../ideation/eval-why-extractability/`.

## Test 3 — evidence-span resolution: RESOLVED, contract refined

Fuzzy resolver (`resolve.py`, word-window SequenceMatcher) over all 19 evidence quotes from the s380 run: **17/19 (89%) resolved above the 0.6 confidence threshold; 19/19 located the correct source region** (both sub-threshold misses were stitched multi-sentence quotes that still landed on the right neighbourhood).

Per the frozen kill criterion (<90%): the design adopts the contract change — **the extract carries message indices; the model returns index locators; resolution is exact.** Fuzzy matching survives as the repair path when an index is wrong. The constraint is implementable; assumption closed.

## Test 2 — generalisation beyond process-writing sessions: PASS

Same prompt, same extractor, second corpus from other projects:

| Session | Character | Result |
| --- | --- | --- |
| career-ops 07-23 (day of a known config commit) | Ordinary working day, config evolved mid-task | **4 real setup/process changes detected with correct drivers** — one hard-verified on disk (a numeric threshold in that project's config file, file mtime = session day). Evidence integrity 62% strict — same paraphrase pattern, handled by the index contract |
| career-ops 07-28 | Ordinary work | `[]` — clean |
| ccwhere 07-20 (19KB of product discussion) | Ordinary work | `[]` — clean |

Notable: the vendored v1.22.0 auto-update commit itself went **unreported** — a silent mechanical change with no conversation. Confirms the standing constraint: mechanical file/config diffing must backstop the model; the model only sees changes that were talked about.

Not yet run from this test's scope: the combined-vs-separate prompt A/B for the "one pass, two outputs" coupling. Flagged for the pre-implementation eval set.

## Test 1 — will the audit trail be reviewed: ARTIFACT GENERATED, clock started

`dogfood-hindsight-audit.md` generated: 18 entries over 20 sessions (2 self-identified trivial), one file, newest first, ~2 minutes of haiku in batches of 4. **The two-week review test starts now.** Kill criterion revised 2026-07-31 on operator correction — the what-view is a pseudo audit log; review, not action, is the job. Demote only if (a) both weekly reviews get skipped or (b) spot-checks find materially wrong entries (>1 in 10 unfaithful). Acted-upon items remain a bonus signal.

First-read observations, themselves evidence of value:

- The log resurfaced **buried project history**: hindsight v1 was a capture-pipeline/memory product (stages 0–4 built 07-14, ccwhy spun out of it 07-15/21, then decommissioned) — context the current framing didn't carry.
- Session 727e934e (07-21) records a prior decision directly relevant to the current definition: a fourth **"how"** observability dimension was pressure-tested and ruled a separate tool from ccwhere because it needs LLM content-interpretation with different trust/cost models. The current what/why views are, in effect, that tool — worth acknowledging in the definition's provenance.
- Format miss: one entry echoed a raw `FLUSH_OK` instead of `SKIP` — prompt needs a firmer trivial-session rule.

## Test 4 — launch-batch economics: PARTIAL, incidental numbers

Not formally run, but the dogfood pass gives bounds: 20 sessions ≈ 2 minutes at concurrency 4 (~6s/session amortised). A typical single day's new sessions (1–5) lands well under the 60s bar. Full-history backfill is minutes-scale and must be async regardless. Formal benchmark deferred to the pre-implementation eval set.

## Test 5 — build order: standing decision

No test; carried into `to-tickets`: what/why pipeline first, where-view rebuild last.
