# eval/ — the status-narrative regression set (ADR-0012)

**Frozen 2026-08-28** (ticket [#67](../background/tickets/067-status-narrative-frozen-eval-set-and-threshold.md)),
**before any prompt was written** — the `tdd` red step for model output, per
`my-process.md`'s Evaluation discipline. Any edit to the narrative prompt or its
model pin runs this first and lands only on ACCEPT.

Predecessor: the why-pass harness (frozen 2026-08-01, ticket #10, retired with
ADR-0006) — same method, ledger fixtures instead of transcript snapshots.

## What is scored

The status narrative's **input is the run ledger only** (ADR-0012), so the eval
set is five frozen ledgers, not transcripts — nothing personal, committed in full.
Only declaring projects are in the set — a project without a `my-process.md`
declaration has no how-view and so no narrative (#64 addendum; ADR-0012 amended
by #67). Snapshots are cut at dates so **Now** moves:

| case | stages | runs | Now | role |
| --- | --- | --- | --- | --- |
| hindsight@2026-08-20 | 5 declared | 4 | Plan since Aug 20 | v1 ingest built, why-view just dropped |
| hindsight@2026-08-25 | 5 declared | 6 | Plan since Aug 25 | styled v1 shipped, why-pass removed |
| hindsight@2026-08-27 | 5 declared | 10 | Plan since Aug 27 | full ledger; how-view in progress |
| thisisme@2026-08-16 | 5 declared | 3 | Design since Aug 1 | sparse; no Build run — invention bait |
| thisisme@2026-08-25 | 5 declared | 4 | Plan since Aug 16 | two Reversed facts from titles alone |

Fixtures were cut from `local-data/hindsight.db` via `build/how.py`'s trail with
the greybox's event-run grain (≥3 fold, majority titling, ticket #64). They are
frozen JSON — the real ledger builder lands with the narrative pass (#68) and
the fixtures do not depend on it.

The real ledger builder (`build/how.py` `run_ledger`, ticket #68) reproduces all
five frozen ledgers byte-for-byte when the live trail is cut at each `as_of`.

**Output contract** the narrative pass must emit — the scorer reads exactly this:

```json
{"Built": ["…"], "Reversed": ["…"], "Now": ["…"]}
```

## Metrics and floors (fixed before any run)

Per case, from `score.py`:

| # | Metric | Floor | What it guards |
| --- | --- | --- | --- |
| M1 | Recall — expected facts whose anchor lands in a line of the **right** group | ≥ 80% of the case's facts | Selection: the status covers what the ledger shows |
| M2 | Forbidden — lines hitting a post-snapshot/invented anchor | 0 | Invention |
| M3 | Untraced — lines sharing < 2 content words with the ledger's stages + titles | 0 | Traceability: every claim maps to ledger entries |
| M4 | Undated — lines with no date, or a date outside the ledger span | 0 | Dating |
| M5 | Now — a Now line names the current stage **and** its start date | required | The one mechanical fact the card must state |
| M6 | Bounded — all three groups present, Built ≤ 8 / Reversed ≤ 4 / Now ≤ 3, Built and Now non-empty | required | A bounded list, not prose |

A case **passes** only when every floor holds. The set **ACCEPTs** a prompt/model
only when **all five cases pass**; regression semantics as before — a candidate
also has to match-or-beat the recorded baseline's recall and line counts.

**Misplaced** (anchor found only in the wrong group) is reported, not floored: it
already costs M1, and placement is the model's one judgement, so it shows up as
recall, not as a separate axis.

Scoring is **mechanical, no judge**: normalised substring anchors (the method
that held for the why-pass), word-overlap traceability, date parsing. A judge
model would cost a second call per case, add its own variance, and be exactly
the unverifiable thing the eval is meant to catch. The ceiling is known: a line
that paraphrases every ledger word fails M3 even if true — the prompt should
keep the operator's own vocabulary (ADR-0012 says so anyway).

## The runtime gate (what "falls back to the mechanical line" means)

Two gates, different jobs:

- **Eval gate** (this set, pre-ship): decides whether a prompt/model may run at
  all. Recall needs ground truth, so it lives only here.
- **Write-time contract gate** (per generated narrative, like #38 for the
  what-pass): **M3, M4, M5 and M6 are ground-truth-free** and run against the live ledger at write time. A
  narrative failing any of them is rejected and not stored — the view renders
  the mechanical status (current run + tally) with the absence stated. Same
  function — `score.contract`, imported by `analyze.refresh_narratives`; no
  second implementation.

## Model

Pin: `claude-haiku-4-5-20251001` — the audit's pin, the cheapest model on hand.
Escalate to the next tier only if haiku fails ACCEPT after two prompt
iterations; record the failing run's tag when doing so.

## Running it

```sh
python3 eval/score.py --selfcheck                 # scorer sanity
python3 eval/run.py build/prompts/status-v1.txt <tag>   # 5 haiku calls, ~1 min
python3 eval/score.py eval/cases.json <case> <out.json>  # re-score one output
```

Outputs land in `local-data/eval/runs/<tag>/` (untracked). The TOTAL line reads
ACCEPT/REJECT.

## Calibration record

Scorer checked against the greybox's hand-written stand-in for hindsight@08-27
before freezing: 17/18 recall (it omitted hook self-instrumentation — a real
gap), one undated Now line ("Design has never been a majority run") — both
correct verdicts under the rules above. No anchor was loosened after seeing a
model output; no model output existed yet.

**Two scorer precision fixes after seeing model output (ticket #68)** — both in
`dates_in`, neither an anchor or floor: "4 decisions" was read as 4 December
(`dec` prefix-matched any word; months now match full names only) and a ticket
range "#18-19" as month 18 (the numeric form now requires `MM` in 01–12). Each
had produced a false UNDATED on a correctly dated line; both are in `--selfcheck`.
The known ceiling stands: a true line can still fail M3 on short words —
`promote PRD` counts one content word, `PRD` being three letters.

## Baseline

**`status-v1` on haiku — ACCEPT, recorded from runs `status-v1-r8` and `-r9`**
(two consecutive ACCEPTs; ticket #68, 2026-08-28). Nine runs to get there:

| run | prompt change | result |
| --- | --- | --- |
| r1 | first draft | REJECT 0/5 — recall 48/52 already; `dropped` paraphrased `drop` (M3), sparse-case facts placed in Now |
| r2 | Built covers the current run; keep the titles' verb forms | ACCEPT 5/5 |
| r3 | (variance run, same prompt) | REJECT 3/5 — scorer `dec`isions bug + current-run work back in Now |
| r4 | name pieces inside grouped lines; split mixed titles; built-then-reversed in both groups | 5/5 after the scorer fixes |
| r5 | (variance run) | REJECT 3/5 — `why-view dropped` again |
| r6 | Reversed lines quote the title verbatim, with an example | ACCEPT 5/5 |
| r7 | (variance run) | REJECT 4/5 — bare `promote PRD` line (the M3 ceiling) |
| r8 | ≥3 title words per line; fold short items into their run's line | ACCEPT 5/5 |
| r9 | (variance run) | ACCEPT 5/5 |

All nine runs sit under the one label `status-v1` because no narrative was
ever stored under an earlier draft — a prompt edit *after* this baseline bumps
the version. Baseline numbers a candidate must match-or-beat (r9): recall 9/9, 15/15,
18/18, 4/4, 5/6; lines 8, 9, 11, 5, 9. The one residual misplacement is
"invert ticket ordering" (thisisme@08-25), which haiku reads as work done
rather than a reversal in about half of runs — inside the recall floor, and
placement is the model's one judgement. No escalation from haiku.

---

# The what-pass regression set (ticket #79, ADR-0016)

**Frozen 2026-08-30**, before `what-v3` was run. Cases are frozen extract parts
from the live cache (personal text: `local-data/eval/what/extracts/`, never
committed); the manifest `eval/what_cases.json` carries case ids and expected
verdicts. 20 cases:

| role | count | expected |
| --- | --- | --- |
| poisoned under `what-v2` — continuation prose instead of an entry | 10 | `any` (must pass the gate) |
| good under `what-v2`, entry | 4 | `entry` |
| good under `what-v2`, SKIP — genuine one-line sessions | 2 | `SKIP` |
| false SKIP under `what-v2` — 180 KB parts, >100 user turns | 4 | `entry` (relabelled, see below) |

**Floors, fixed before the run, all required for ACCEPT:** every output passes
`valid_entry`; an expected SKIP stays SKIP; an expected entry stays an entry.
The scorer is the production gate itself (`analyze.valid_entry`) — no judge, no
anchors: the defect is a *shape* failure, and shape is mechanical.

```sh
python3 eval/what_run.py build/prompts/what-v2.txt <tag>   # 20 haiku calls, ~1 min
```

Outputs in `local-data/eval/what/runs/<tag>/`.

## Label correction, recorded

The manifest's expected verdicts were drawn from the `what-v2` cache. After
`what-v3-r1` (16/20) the four failures were all "expected SKIP" cases whose
extracts are 180 KB with 100+ user turns — mid-session slices of career-ops
work that `what-v2` had SKIPped, captured by a trivial tail turn (the same
defect, second face). `what-v2-r1` itself returned an entry for two of them.
Those four were relabelled `entry`: a stricter expectation than the one they
replaced, decided on the extract's size and turn count, not on v3's output.
No expectation was loosened. The two remaining SKIP cases are 51- and 58-byte
"reply OK" sessions.

## Baseline

| run | prompt | result |
| --- | --- | --- |
| what-v2-r1 | `what-v2` (red step) | REJECT 7/20 — 9 of 10 poisoned parts still prose, 1 empty; 2 false-SKIPs flipped to entry, 2 to prose |
| what-v3-r1 | `what-v3` | REJECT 16/20 under the uncorrected labels — the 4 "failures" were the false SKIPs, now entries |
| what-v3-r2 | `what-v3` | ACCEPT 20/20 |
| what-v3-r3 | (variance run, same prompt) | ACCEPT 20/20 |
| what-v3-r4 | header no longer claims `TOOL:` lines (code review) — the shipped text | ACCEPT 20/20 |

**Baseline: `what-v3` on haiku — ACCEPT, recorded from `what-v3-r2`, `-r3` and `-r4`**
(three consecutive ACCEPTs, 2026-08-30). No escalation from haiku.
