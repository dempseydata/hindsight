# Results: why-extractability eval

**Date:** 2026-07-31. Thresholds were frozen in `plan.md` before the run.
**Verdict: the wedge is CONFIRMED, with one hard design constraint.** "Why did my process change" is extractable from conversational transcript text by a cheap model — but model-quoted evidence is not verbatim-reliable, so the pipeline must attach evidence mechanically.

## Scores against the frozen thresholds

| # | Metric | Threshold | Result | Verdict |
| --- | --- | --- | --- | --- |
| M1 | Evidence integrity (strict normalised substring) | ≥ 90% | **54%** (13/24; 42% on s380, 100% on d9c0). Loose matching (punctuation stripped) only lifts it to 71% | **FAIL** |
| M2 | Detection recall over 6 ground-truth events | ≥ 4/6 | **6/6** — BMAD cut, office-hours cut, OpenSpec removal, copies→plugins (both Matt Pocock and impeccable, separately), evaluation discipline, DESIGN.md demotion | **PASS** |
| M3 | Rationale match on detected events | ≥ 50% | **6/6** — every stated why is consistent with the documented rationale (e.g. office-hours: "shells to missing gstack binaries; six questions preserved in my-process.md") | **PASS** |

Precision probes (qualitative): the no-known-changes session (`2eab2d43`, 07-24) returned an empty list — no false positives. The follow-on session (`d9c0`) surfaced 3 changes not in the ground-truth set (wireframe step added, Claude Design adopted as default, last30days plugin installed disabled) — all real, matching the current uncommitted my-process.md state, at 100% evidence integrity.

## The M1 failure, diagnosed

Failed quotes are **light paraphrase, not fabrication**. Example — source (fed extract, line 467):

> `office-hours` is 1697 lines whose entire preamble shells out to `~/.claude/skills/gstack/bin/` binaries that were never installed

haiku's "verbatim" quote:

> `office-hours` is 1697 lines whose entire preamble shells out to gstack bin binaries that were never installed

Other failures stitched adjacent sentences into one "quote". Content faithful; characters not. This independently re-confirms the constraint from the earlier ccwhy-era eval: **you cannot substring-verify a quote the model has retold — evidence must be captured mechanically.**

## Consequences carried into definition

1. **Confirmed:** the why-view designs around cheap-model inference over conversational text (user + assistant text blocks only — tool results were dropped and detection was still 6/6; the 3.1MB session reduced to 66KB of signal).
2. **Design constraint (from M1):** the model proposes findings; the *pipeline* resolves and attaches evidence — model returns an approximate locator (message index / search phrase), pipeline fuzzy-matches to the true span and stores the verbatim text with its source offset. Model-quoted text is never stored as evidence.
3. **Model/cost:** `claude-haiku-4-5-20251001` suffices for this judgement; three calls covered ~90KB of extract in ~2 minutes. "Cheap enough to run often" holds.

## Standing caveat (from plan.md)

These sessions *discussed* the process changes explicitly while making them — extractability bias in the corpus. Detection on days where setup changes happen silently (a config edit with no conversation about it) is untested; the what-view's mechanical change-detection (file mtimes, settings diffs) should backstop the why-view rather than the model being the only detector.

## Artifacts

> **Graduated 2026-08-01** (ticket #10): the standing regression harness now lives in `eval/` at the repo root, upgraded to the ADR-0002 contract (indexed extracts, `{msg, quote}` locators, resolution ladder) with a 9-session frozen corpus and baseline. This directory remains the dry-run record; the scripts below are its historical snapshot.

`plan.md` (frozen thresholds) · `prompt.txt` · `extract.py` · `score.py` — rerunnable end to end. Session-derived data (`extracts/`, `outputs/`, `dogfood/`) lives untracked in `local-data/eval/` — it contains verbatim personal transcript text and is never committed (see `.gitignore`).
