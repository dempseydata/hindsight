# #19 The three prompt repairs, regression-gated

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-17

## Parent

#15

## What to build

The three ride-along prompt repairs land as prompt edits with a bumped prompt version, each gated by the frozen eval regression: (1) firmer trivial-session SKIP rule (ADR-0002), (2) the anti-capture repair — restate why-pass instructions after the transcript, fixing the 4/207 backfill sessions that captured the transcript on large parts, (3) the stated-rationale convention on Decided lines — close paraphrase or quote, nothing invented (ADR-0002 amendment). A prompt edit lands only if the run clears every floor and matches-or-beats baseline per the eval README's regression semantics.

## Acceptance criteria

- [ ] All three repairs applied to the product prompts under a new prompt version
- [ ] `eval/run.sh` run recorded with the result: all floors cleared, M1/M3 match-or-beat baseline, M4a/M4b not increased
- [ ] New analysis output rows carry the new prompt version
- [ ] The frozen baseline prompts remain untouched in the eval tree

## Blocked by

- #17


---

**comment · 2026-08-17**

Landed in 32bd524. All four acceptance criteria met:

- Three repairs applied as `what-v2`/`why-v2` (+`why-v2-post.txt`, the anti-capture restatement after the extract); `analyze.py` bumped to the new versions, so new audit/findings rows carry them.
- Regression recorded in `eval/README.md` (run `2026-08-16-why-v2c`): every floor cleared, M1 15/15 and M3 55/56 (98.2%) both beat baseline (14/15, 96.9%), M4a/M4b both 0 — not increased. Two rejected candidate runs also recorded (first restatement draft caused negative-session recap findings; second missed E2/E6 on the dense s380 until an exhaustiveness sentence was added).
- Baseline prompts (`why-v1`/`what-v1`) untouched; `eval/run.sh` gained a `WHY_PROMPT` override, production's `valid_why_json` gate with retry, and production-identical prompt assembly.

Precision note, recorded in ADR-0002 and the eval README: the frozen set regresses the why-pass only, so the two what-pass repairs (SKIP, stated-rationale) ride through the gate unmeasured — the weekly spot-check remains their integrity mechanism.

