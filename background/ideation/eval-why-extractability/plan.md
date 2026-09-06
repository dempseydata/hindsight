# Eval: is "why did my process change" extractable from transcripts?

**Date:** 2026-07-31 (written before the run; thresholds frozen here)
**Moment:** "Before committing to a design" (my-process.md, Evaluation discipline)
**Assumption under test:** A cheap model, reading a session transcript's conversational text, can (a) detect setup/process changes, (b) state the driver behind each, (c) quote verbatim evidence — well enough to justify designing the why-view around model inference.

## Method

- **Corpus (real, not synthetic):** hindsight-project sessions bracketing two dated ground-truth commits — `380c98cd` (3.1MB, 2026-07-26 evening → 07-27, brackets `f2caa9b` "Rebuild the toolchain: plugins over copied files") and `d9c01e38` (1.0MB, 07-27 → 07-30, follow-on process work after `51a13d1` "Add an evaluation discipline"). One smaller session with no established ground truth (`2eab2d43`, 07-24) is included as an exploratory precision probe, scored qualitatively only.
- **Extraction:** user text + assistant text blocks only (tool results and meta lines dropped; Edit/Write targets kept as one-line markers). Chunked to fit the model context; per-message and total caps applied by `extract.py`.
- **Model:** `claude-haiku-4-5-20251001` via `claude -p` (cheapest model plausibly able to hold the judgement).
- **Task prompt:** return strict JSON: a list of `{change, why, evidence: [verbatim quotes]}` for setup/process changes only (skills, plugins, process docs, config) — not product code changes.
- **Scoring:** `score.py` — mechanical where possible.

## Ground-truth events (from git history + my-process.md "What was cut, and why")

| ID | Event | Documented why |
| --- | --- | --- |
| E1 | BMAD CIS: 22 of 23 skills removed | Overlap with grilling/to-spec/code-review etc.; gated form-fills; persona boilerplate |
| E2 | gstack `office-hours` removed | Competed with `grilling`; shelled out to binaries never installed (failed open); forcing questions salvaged |
| E3 | OpenSpec removed from this project | Replaced by `to-spec` → `to-tickets` → `implement` |
| E4 | Copied Matt Pocock + impeccable skills replaced by plugins | Copies are snapshots that go stale silently; upstream already renamed commands |
| E5 | Evaluation discipline added to the process | Model-output quality is untestable by tdd/code-review; a prompt has no compiler |
| E6 | DESIGN.md v1.2 demoted to a quality floor; palette per product | v1.2 mandated a Mintlify look that impeccable's own detectors flag |

## Metrics and thresholds (decided now, not after)

| # | Metric | Threshold | On failure |
| --- | --- | --- | --- |
| M1 | Evidence integrity: % of quoted evidence that substring-verifies against the fed extract (normalised: lowercase, collapsed whitespace) | ≥ 90% | Model-quoted evidence is unreliable → pipeline must attach evidence mechanically (spans/offsets), never ask the model to quote |
| M2 | Detection recall: ground-truth events surfaced across the two evidenced sessions | ≥ 4 of 6 | Why-view demoted to change-*detection* (what changed, when) without inferred drivers |
| M3 | Rationale match: of detected ground-truth events, % whose stated why is consistent with the documented rationale | ≥ 50% | Why-view ships change + evidence links, driver field dropped or marked speculative |

M2/M3 event-matching is keyword-anchored (e.g. E2 requires mention of office-hours/gstack; E4 requires plugin-vs-copy framing) with judgement recorded per event in results.md.

## Known limitations, accepted for a dry run

- The chosen sessions are also where my-process.md was *written*, so rationale appears unusually explicitly in conversation. This biases toward extractability; a pass here is necessary, not sufficient. A later eval should test days where changes happened without a process-doc rewrite.
- No true negative control with established ground truth; the 07-24 probe is qualitative.
- Truncation caps may drop evidence; misses are checked against what was actually fed before counting against M2.
