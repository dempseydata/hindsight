# #10 Freeze the eval set and thresholds

state: closed · labels: wayfinder:task · opened: 2026-08-01 · closed: 2026-08-01

## Question

Extend the corpus with silent-change days and additional ordinary days, then freeze: the session set, the scoring scripts, and numeric thresholds (detection recall, rationale match, evidence resolution, false-positive ceiling) — before implementation, per the Evaluation discipline. This is the standing regression set for every future prompt/model change.

Part of #1



---

**comment · 2026-08-01**

## Resolution: frozen — corpus extended, harness on the ADR-0002 contract, floors fixed before baseline

**The standing regression set lives in `eval/`** (commit 9714cb9): `corpus.json` (machine-readable ground truth), `extract.py` / `why-prompt.txt` / `resolve.py` / `score.py` (the ADR-0002 contract: indexed extracts + uuid sidecar, `{msg, quote}` locators, exact→fuzzy(0.6)→unresolved ladder), and `run.sh <tag>` to run the whole thing (~9 haiku calls, minutes). Transcript snapshots and run outputs stay untracked in `local-data/eval/` (sha256-pinned in the README — sources were snapshotted because Claude Code prunes transcripts; one source, cw20, had already gone missing from its expected location and was recovered by content-matching).

### Corpus: 6 → 9 sessions, 4 projects, 15 ground-truth events

Added per the ticket:
- **cos30** (career-ops 07-30) — **silent-change day**: the official-plugin batch auto-update landed 17:32 *mid-session*, machine-driven, never discussed. Forbidden-anchor scoring asserts it is never attributed.
- **tin30** (thisisme 07-30) — additional ordinary-day negative.
- **tim27** (thisisme 07-27) — cross-project positive: the template migration, git-anchored (`6bc87b4`), answering the dry run's extractability-bias caveat.
- co23's day also carries the v1.22.0 auto-update commit as a fabrication guard (it landed after session end; cos30 is the load-bearing silent test). Correction found en route: co23's true source is session `4ea86257` (07-21→23), not the 07-23-starting session.

### Floors (fixed before the baseline ran) and baseline (`claude-haiku-4-5-20251001`)

| Metric | Floor | Baseline |
| --- | --- | --- |
| M1 detection recall | ≥ 13/15 | **14/15** (miss: E6 DESIGN.md demotion — detected in the dry run; sampling) |
| M2 rationale match | ≥ 80% | **14/14** |
| M3 evidence resolution | ≥ 90% | **97%** (62/64; 35 exact, 20 fuzzy-in-msg, 7 fuzzy-global) |
| M4a silent-change attributions | 0 | **0** |
| M4b negative-day false positives | ≤ 1 | **0** — all four negatives returned `[]` |

Regression semantics per ADR-0002: any prompt/model change must clear every floor **and** match-or-beat baseline M1/M3 without increasing M4. Freeze-time calibration (scorer prefer-unmatched fix, E3 anchor widening, one cos30 finding verified on disk and promoted to ground truth) is recorded in the README; no thresholds moved after seeing results.

Bonus signal: the cos30 session surfaced a real, undocumented process change (an ask-first house rule for an email tool, verified in that project's config) — the why-pass finding real changes outside hindsight's own project history.

Scope note: this set regresses the **why-pass** only; the what-pass has no mechanical ground truth by design — its check remains the weekly spot-check (ADR-0002).


---

**comment · 2026-08-01**

Frozen; eval/ committed as 9714cb9. The backfill (#11) is now unblocked.

