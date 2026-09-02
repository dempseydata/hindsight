# ADR-0002: The extraction contract — two pinned passes, index locators, verbatim-only evidence

**Date:** 2026-08-01 · **Status:** accepted · **Decides:** Lock the extraction contract, on the evidence of the combined-vs-separate A/B and red-team test 3 (`definition/red-team-tests.md`)

## Context

The what/why pipeline hangs on model extraction over session-transcript extracts. Three things had to be frozen before `to-spec` could own the pipeline: whether the two extraction jobs share one model call, what a finding looks like, and how evidence points back at the transcript. The eval work supplied the constraints: combining the passes degrades recall (12/13 vs 13/13), evidence integrity (48% vs 68%), and finding count (−33%); and model-quoted "evidence" paraphrases too often to be stored (test 3: index locators resolve exactly, fuzzy matching repairs).

## Decision

**Passes.** Two separate calls per session extract — the **what-pass** (audit entry) and the **why-pass** (setup/process changes) — over the same extract. Frozen flat, no revisit trigger: combining saves sub-cent per session and measurably degrades output.

**Model.** Pinned to `claude-haiku-4-5-20251001`. The pin moves only through a regression run against the frozen eval set: a candidate must match-or-beat baseline recall and resolution rate. Transport (`claude -p` vs API) is implementation detail.

**Extract & index.** Each role-prefixed extract piece is numbered (`[17] USER: …`), sequentially per session, continuous across chunk parts. The extractor keeps a sidecar map piece-index → source jsonl message (uuid), so stored evidence references the real transcript, not the throwaway extract. Chunk cap stays 180K chars as measured.

**Why-pass finding shape.** `[{"change", "why", "evidence": [{"msg", "quote"}]}]` — 1–3 locators per finding, quotes 8–40 words. Session id, date, and resolved spans are attached by the pipeline, never asked of the model. Fenced JSON is tolerated and stripped. No category, confidence, or severity fields; categorization is revisited when the why-view shows real findings (earliest: the why-view greybox).

**Locator resolution.** The model's quote is a search key, **never stored as evidence** — no exceptions, including the failure path. Ladder: exact substring within the indexed message → fuzzy within that message → fuzzy over the whole extract (threshold 0.6, the tested value) → **unresolved**: finding kept, locator kept, evidence stored as unresolved and rendered "evidence not located". Resolution rate is a standing per-run health metric compared against the eval baseline.

**What-pass.** Frozen as measured: strict markdown (title / **Did** / **Decided** / **Setup changes**), no locators — its integrity check is the standing weekly spot-check, with the transcript as source of truth. The Setup-changes line is retained despite overlapping the why-pass; each view stays self-contained. Ride-along prompt repair, not a contract change: a firmer trivial-session `SKIP` rule (the `FLUSH_OK` miss from red-team test 1).

**Amendment (2026-08-16, Lock the audit format).** One convention joins the locked format: when rationale for a decision was stated in-session, the Decided line carries it — "decision — stated rationale", close paraphrase or quote, nothing invented when none was stated. This is the fix for dogfood review #1's missing-culling-rationale finding, and its close-paraphrase wording is also the repair for review #2's fabricated clause and the loose-paraphrase tendency. Implemented as a prompt edit riding with the existing repairs, gated by the frozen eval regression like any prompt change. No locators are added to the what-pass: two sub-threshold findings across 29 reviewed entries do not justify extending the resolution ladder, and the weekly spot-check remains the integrity mechanism.

**Amendment (2026-08-16, the three prompt repairs).** The repairs above landed as `what-v2`/`why-v2`. The why-pass call is now structurally header + extract + restated contract (`why-v2.txt` + `why-v2-post.txt`) — the anti-capture restatement, fixing the 4/207 backfill sessions that echoed transcript text instead of JSON on large parts. Precision on the gate: the frozen set regresses the why-pass only, so the two what-pass repairs (SKIP rule, stated-rationale) ride through it unmeasured — the weekly spot-check remains their integrity mechanism.

**Amendment (2026-08-26, review residue #50).** The frozen eval set and its regression harness retired with the why-pass (ADR-0006, ticket #43), so the gate above — "the pin moves only through a regression run against the frozen eval set" — no longer exists to run. The pin itself stands, authoritative in `build/analyze.py` (`MODEL`; CONTEXT.md repeats the literal as vocabulary). A pin move is now judged like any what-pass prompt change: the weekly spot-check is the integrity mechanism, and building a fresh eval set is the price of wanting a mechanical gate back.

**Chunk overflow** (rare — extracts run ~2% of jsonl size). Why-pass: run per part and concatenate findings; session-global indices keep locators unambiguous; no dedupe pass. What-pass: run per part, then one merge call to preserve the one-entry-per-session invariant.

## Consequences

- `to-spec` builds the pipeline against fixed shapes: two prompts, one extract format with indices and a sidecar map, one resolution ladder, one failure state.
- Stored evidence is verbatim transcript text by construction, so substring-based verification (the eval's method) remains valid against production output.
- Any prompt or model edit triggers a regression run against the frozen eval set before it lands — the pin and the baseline make "did it get worse somewhere else" answerable.
- The unresolved-evidence state is visible in the why-view rather than papered over, and its rate is monitored; a rising rate is an early signal of extract or prompt drift.

**Amendment (2026-08-30, ticket #79, ADR-0016):** the what-pass has a mechanical gate again — a frozen regression set of 20 extract parts scored by `valid_entry` (`eval/what_cases.json`, `eval/what_run.py`), the price named above now paid. The prompt is `what-v3`, which brackets the extract rather than prefixing it.
