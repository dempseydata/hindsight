# #3 A/B: combined vs separate extraction prompts

state: closed · labels: wayfinder:research · opened: 2026-08-01 · closed: 2026-08-01

## Question

Does one combined model pass (what-view actions/decisions + why-view change rationale) match or beat two separate passes on recall and evidence quality? Run both variants over the frozen eval corpus (`ideation/eval-why-extractability/`), same sessions, same scoring. The settled "one pass, two outputs" decision hardens or falls on this.

Part of #1



---

**comment · 2026-08-01**

## Resolution: combined DEGRADES — keep two separate passes

A/B run 2026-08-01, `claude-haiku-4-5-20251001` via `claude -p`, three sessions (s380 3.1MB hindsight, d9c0 1.0MB hindsight, co23 career-ops 07-23), three variants each: separate why-pass (`prompt.txt`), separate what-pass (`audit-prompt.txt`), and a combined prompt returning `{"audit": {...}, "setup_changes": [...]}` with both task wordings kept intact and only the output envelope merged. All artifacts under `local-data/eval/ab-test/` (untracked, personal transcript text).

### Numbers

| Metric | Separate | Combined |
| --- | --- | --- |
| Ground-truth detection recall (13 tracked events) | **13/13** (s380 6/6, d9c0 3/3, co23 4/4) | **12/13** — missed the office-hours/gstack removal (E2) on s380 entirely, in both halves |
| Total change entries reported | 27 | 18 (−33%) |
| Evidence pass-rate (strict normalised substring) | **68%** (25/37; s380 69%, d9c0 42%, co23 100%) | **48%** (23/48; s380 44%, d9c0 50%, co23 67%) |
| Audit completeness (Did/Decided, side-by-side judgement) | Slightly richer: commit hashes, ThisIsMe decision (s380), /design-sync surface rule (d9c0) | Comparable core coverage; each session missing 1–2 decisions the separate pass caught |
| JSON-format failures | 0/6 calls | 0/3 calls (all fenced in ```json — known, stripped) |

### Why it loses

1. **Recall drops where it matters most.** The combined pass dropped a hard ground-truth event (E2) on the largest session, and compressed real findings elsewhere: d9c0's six real changes became two merged entries (sketch-input, /design-sync surface rule, and cross-project sync gone); co23 lost the ATS required-field rule. The pattern is attention-splitting under compression: with two jobs in one pass, the model summarises the change list instead of enumerating it, and the effect grows with extract size (s380, 66KB, was worst).
2. **Evidence quality degrades too.** 48% vs 68% strict integrity — the combined pass quoted more (3 quotes/change vs ~1.4) and paraphrased more. Moot-ish given the index-locator contract adopted after red-team test 3 (evidence is resolved mechanically, never stored from model quotes), but it points the same direction.
3. **The saving is one haiku call per session** (~6s amortised, sub-cent). Not worth one lost ground-truth event in three sessions.

**Decision: the pipeline keeps two separate passes** — audit entry and setup-change extraction as independent calls over the same extract.

### Caveats

- n=3 sessions, single run per variant; haiku sampling variance untested. A repeat run could move the small-session numbers (d9c0's 6-vs-12-quote evidence samples are tiny), but the s380 recall miss + entry-count compression is the load-bearing signal and is consistent across all three sessions.
- The combined prompt tested is one reasonable merge (kept both wordings, JSON envelope only). A merge that forces per-half enumeration ("list every change; do not merge related changes") was not tested and might close the gap — but there is no cost pressure to justify iterating on it.
- co23 ground truth is the 4 changes from red-team test 2; the separate pass's 5th finding (ATS required-field rule) is real but outside the frozen set, so it counts as extra coverage, not recall.

Combined prompt text preserved at `local-data/eval/ab-test/combined-prompt.txt` (untracked) should this be revisited.


