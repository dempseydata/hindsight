# eval/ — the status-v2 regression set (ADR-0035, #73)

**Frozen 2026-11-19** (#95), **before any `status-v2` prompt was written**.
Design settled in #73. Any edit to the `status-v2` prompt or its model pin
runs this first and lands only on ACCEPT. The v1 set below is kept as the
record; #96 retired `status-v1` from the live pass.

## What is scored

The input is **the run ledger plus the project's ADR headers** (ADR-0035 §3),
plus the title changes derived from the runs at call time (ADR-0040),
read by `cli/how.py`: `ledger()` and `adr_headers(root)`. Each header has a
number, a date (from the header, else from the commit that added the file), a
title, a status line, and `touches` (the Supersedes/Amends/Touches fields,
verbatim). Only `<root>/docs/adr` is read. Five cases, in
`status_v2_cases.json`:

| case | runs | ADRs | Now | expected |
| --- | --- | --- | --- | --- |
| hindsight@live | 10 | 39 | Plan since Nov 13 | Superseded: so-what view dropped (ADR-0026); hook self-instrumentation → ADR-0033. `so-what` forbidden in Standing |
| hindsight@2026-09-15 | 2 | 25 | Plan since Sep 11 | Standing: the so-what view. Forbidden anywhere: `adr-0026`, `not built`, `so-what (view) (is) dropped`; `so-what` forbidden in Superseded (a bare `dropped` cannot be: ADR-0006's title says the why-view is dropped) |
| explainer@live | 8 | 21 | Build since Sep 30 | Superseded: npm-link install → plugin layout (ADR-0011) |
| thisisme@live | 5 | 0 | Plan since Aug 17 | Superseded from titles alone: OpenSpec closed; schema ordering inverted to content-first |
| skills-playground@live | 2 | 0 | off-script since Sep 23 | Superseded must be `[]` |

**How they were cut.** The live cases come from a migrated copy of the live
store, with ADR headers read from each project's folder after hindsight's
status-line backfill (0006 amended by 0010; 0021–0025 dropped by 0026).

`hindsight@2026-09-15` re-runs `run_ledger` over the trail up to the cut day.
Its ADR headers are read from git at `6b6d473`, the last commit on that day.
A session with events after the cut keeps those events but loses its title,
because the title was written after the session ended. ("Closed map #18 after
Stage B evaluation" ran into 09-16.)

thisisme keeps 11 ADRs under `build/docs/adr`. They are not read, so it stays
the no-ADR, title-stated case that #73 resolved.

**Output contract:**

```json
{"Standing": ["…"], "Superseded": ["…"], "Now": ["…"]}
```

## Metrics and floors (fixed before any prompt)

Per case, from `score.py` `score_v2`. M3 to M7 are `contract_v2`, the
write-time gate #96 imports.

| # | Metric | Floor |
| --- | --- | --- |
| M1 | Recall: expected facts whose anchor lands in the right group | ≥ 80% of facts, and **100% of Superseded facts** |
| M2 | Forbidden: lines hitting a forbidden anchor. A string counts in any group; `{"anchor", "group"}` counts only in its group. The empty anchor matches every line, so `{"anchor": "", "group": "Superseded"}` means Superseded must be `[]` | 0 |
| M3 | Untraced: a line shares < 2 content words with the ledger's stages and titles. Words shared only with ADR titles count when the line names an ADR number. Any ADR number named must exist in the input | 0 |
| M4 | Undated: every date in a line is in the ledger span or equals an ADR date. Standing and Now lines need ≥ 1 date; Superseded lines need ≥ 2, in order (order is checked on Superseded only) | 0 |
| M5 | Now: a Now line names the current stage and its start date | required |
| M6 | Bounded: all three groups are lists; Standing 3–8, Superseded ≤ 6, Now 1–3 | required |
| M7 | Listed (added 2026-11-20, ADR-0040, before `v2-p11`): every title change (`title_changes`; a close of a thing too, ADR-0041) shares ≥ 2 content words with a Superseded line | 0 |

The expected facts are #73's anchors, plus thisisme's two. #73 names no
thisisme facts, only "the titles state the changes", so its pair is carried
over from the v1 set's thisisme Reversed facts (OpenSpec closed; ordering
inverted). The operator ratified the pair on 2026-11-19, before any model
output. For most cases M1 means only the Superseded half. Standing coverage
is not measured.

Anchors are OR-substrings and cannot require both sides of a supersession. A
Superseded line that names only the old side still needs two dates (M4) and a
trace (M3), so it cannot be a bare mention.

**ACCEPT** needs **at least 39 of 45 cases passing** across three
consecutive serial sweeps of one prompt on `claude-haiku-4-5-20251001` (each
sweep is one `run_v2.py` run: 3 rounds × 5 cases). Until this decision the bar was
15/15 in a single sweep; see the operator decision below. The runner also reports each
Superseded fact's hit rate across the rounds. Wording drift is not floored.
Escalate one model tier only after two prompt iterations fail ACCEPT, and
record the failing run's tag.

```sh
python3 eval/score.py --selfcheck                         # v1 and v2 floors
python3 eval/run_v2.py cli/prompts/status-v2.txt <tag>    # 3 rounds × 5 cases
```

Outputs go to `local-data/eval/runs/<tag>/r1..r3/` (untracked).

**Calibration.** An empty stub card fails every case (`cli/test_how.py`
`StatusV2Cases`). A hand-written correct card for hindsight@live passes, with
7 lines and 2/2 Superseded, so the floors can be reached. No model output
existed when the set was frozen.

## Record: `status-v2` — not accepted, parked for the operator (2026-11-19, #96)

No case, anchor, floor or scorer line moved. Two confounds void every run
before `v2-p6-sonnet-nohooks`:

- **Leaked answers (`v2-p1` to `v2-p5`).** The prompt's examples quoted the
  frozen set's anchors and titles ("so-what view", "npm link install", "close
  OpenSpec", "content-first"). `test_status_prompt_carries_no_eval_answers`
  now fails on any anchor, or on any four-word run of a case title or ADR
  title, in the live prompt.
- **Hook leak (`v2-p1` to `v2-p6-sonnet-clean`).** The operator's user-level
  SessionStart hook reached every `claude -p` call. Fixed in 23e50f8
  (`disableAllHooks`); the what-eval re-ran 20/20.

| tag | model | passed | note |
| --- | --- | --- | --- |
| `v2-p1`..`v2-p4` | haiku | 6, 10, 10, 14 /15 | void: leaked answers, hook leak |
| `v2-p4-sonnet`, `v2-p5-sonnet` | sonnet | 14, 15 /15 | void: same; p5's "ACCEPT" withdrawn |
| `v2-p6-sonnet-clean` | sonnet | 11/15 | void: hook leak (a reply suffix, two empty calls) |
| `v2-p6-sonnet-nohooks` | sonnet | 12/15 | first clean run; npm-link named by the wrong half of ADR-0010's title |
| `v2-p7-haiku` | haiku | **14/15** | best clean run; thisisme r1 dropped a current-run title |
| `v2-p7-sonnet` | sonnet | 10/15 | npm-link 0/3, one 300 s timeout |
| `v2-p8-haiku` | haiku | 11/15 | a title-pass rule made Haiku over-eager; reverted |
| `v2-p7-haiku-serial-a` | haiku | 11/15 | serial, no timeouts. Dated cut: so-what missed from Standing (r1), placed in Superseded (r2); thisisme OpenSpec missed; skills-playground Standing empty (M6) |
| `v2-p7-haiku-serial-b` | haiku | 14/15 | serial. Dated cut r1: so-what missed from Standing and placed in Superseded |
| `v2-p9-haiku` | haiku | 12/15 | serial. New rule: an in-force ADR is Standing and never on either side of a Superseded arrow. Dated cut passed r1 and r3; r2 timed out at 300 s with one call in flight. thisisme content-first missed (r1); explainer r2 Now gave a wrong start date (M5) |
| `v2-p10-haiku` | haiku | 12/15 | serial. p9 plus "search every part of every title; one find does not end the search". thisisme failed r1 (0/2: the title-stated change copied verbatim into Standing and Now) and r2 (OpenSpec); explainer r2 named the "symlink or plugin" half of ADR-0010. Reverted to p9 |
| `v2-p11-haiku` | haiku | **14/15** | serial, ADR-0040 input and M7. thisisme 6/6 facts; M7 unlisted 0 in all 15 calls; no timeouts. explainer r1 omitted ADR-0010 → ADR-0011: p9's rule forbids an in-force ADR on the replacing side, and ADR-0011 is that side. The rule is wrong, not the model |
| `v2-p12-haiku` | haiku | 12/15 | serial. p11 with p9's rule fixed: an in-force ADR may be the replacing side only when another ADR's status line names it. Every Superseded fact 3/3 in every case, the first sweep to do so. Failures are Standing and Now: hindsight@live r2 a Standing line saying the so-what view was dropped (M2); dated cut r3 so-what missed from Standing and an untraced Now line; skills-playground r3 Standing empty (M6) |
| `v2-p13-haiku` | haiku | 13/15 | serial. p12 plus: Standing is never under 3 lines, and a one-run project's titles are its Standing. skills-playground and the dated cut 3/3. hindsight@live r1 a Standing line saying the so-what view was dropped (M2); thisisme r1 OpenSpec missed (a close change, model-judged by ADR-0040) |
| `v2-p13-haiku-b` | haiku | 11/15 | serial, p13 unchanged. thisisme r1 OpenSpec missed; hindsight@live r1 two undated Standing lines (M4); dated cut r1 so-what missed from Standing; explainer r3 "removed fix loop" not listed under Superseded (M7) |
| `v2-p13-haiku-c` | haiku | 13/15 | serial, p13 unchanged. thisisme r3 OpenSpec missed; explainer r3 omitted ADR-0010 → ADR-0011 |
| `v2-p14-haiku-a` | haiku | 13/15 | serial, ADR-0041 input. Dated cut r1 so-what placed in Now, not Standing; thisisme r1 OpenSpec missed (M7 unlisted, as ADR-0041 expected) |
| `v2-p14-haiku-b` | haiku | 13/15 | serial, p14 unchanged. explainer r2 omitted ADR-0010 → ADR-0011; hindsight@live r3 a Standing line saying the so-what view was dropped (M2) |
| `v2-p14-haiku-c` | haiku | 14/15 | serial, p14 unchanged. explainer r3 omitted ADR-0010 → ADR-0011 |

**Escalation tried and withdrawn.** Sonnet was pinned after `v2-p4` on
confounded evidence. Clean runs of the same prompt put Haiku ahead (14 v 10),
so the pin stays on Haiku.

**Operator decision (2026-11-20, later): ACCEPT is ≥ 39/45 pooled over three
sweeps.** The how-view is an approximation for the operator, not an
auditable record (ADR-0012's posture). The goal is a card that is right
about 90% of the time. An all-or-nothing 15/15 passes a true-90% prompt only
21% of the time. ≥ 39/45 passes it 84% of the time, and passes a true-80%
prompt 18% of the time. The cases, anchors, floors and the write-time gate
(M3–M7) do not change. The earlier decision is kept below as the record.

**Operator decision (2026-11-20, superseded the same day): the bar stays at 15/15.** Two more serial
sweeps of `v2-p7` (above) put it at 39/45 across three sweeps, about a
1-in-8 chance of a clean sweep. The failures are not noise. Half fall on
`hindsight@2026-09-15`, where Haiku treats a decision still in force at the
cut as superseded, or leaves it out of Standing. M2 fired twice, so a split
bar (M1 by hit rate, M2–M6 strict) would not have accepted `v2-p7` either.
The runner is now serial, like the live pass. `v2-p9`'s serial timeout shows
concurrency was not the whole cause: the 300 s limit (`CALL_TIMEOUT`, shared
with the live pass) can still be hit. Still open: `dates_in` reads "Mon D-D"
as a second date.

`v2-p9` is kept although its sweep scored lower than `v2-p7`'s mean. The new
rule fixed the dated cut in both calls that completed (p7 failed it in 3 of 9).
The remaining failures fall on cases the rule cannot reach: thisisme has no
ADRs, and the explainer Now date is unrelated. One sweep cannot separate 12 from
p7's 13 on average.

**Title-stated supersessions resist prompt rules.** Across the five clean
Haiku sweeps of p7, p9 and p10, thisisme failed 5 of 15 calls. Every miss is a
change stated only in a run title, in a project with no ADRs. The prompt already
names the verbs and has an example almost the same as the missed title. p10's
search instruction made it worse (3 misses in 3 rounds against 1).

**ADR-0040 (2026-11-20).** Title-stated changes are now found by code
(`score.title_changes`) and sent as `changes`. M7 joins the floors before
`v2-p11`. No case or anchor moved. Re-scored under M7 for the record only, the
earlier clean runs fall to 6–9 /15, because no earlier prompt was asked to list
the strong changes in hindsight and explainer.

**`v2-p13` pooled: 37/45 → REJECT** (13 + 11 + 13; the bar is 39). Eight
failed calls: thisisme's OpenSpec close 3 (it passes 6 of 9 calls; every other Superseded fact
passes at least 8 of 9), and five singletons spread across M2, M4, M7 and two misses. OpenSpec
is the one failure that repeats. It is a "close" change, which ADR-0040 leaves to the model's
judgement. Without it the pool is 40/45.

**ADR-0041 (2026-11-20).** A close that survives the finished-work filters (a ticket, an
inquiry, or no thing named) is a mandatory change like the strong verbs, and binds M7. In the frozen
set that leaves exactly "close OpenSpec". The prompt (`v2-p14`) drops the close judgement. No case,
anchor or floor moved.

**`v2-p14` pooled: 40/45 → ACCEPT** (13 + 13 + 14). Superseded facts across the 9 calls per case:
hindsight 9/9 and 9/9, thisisme OpenSpec 8/9 (from 6/9 under p13) and content-first 9/9,
explainer ADR-0010 → ADR-0011 7/9. The five failures are the known minority ones: explainer's
ADR-0011 twice, OpenSpec once, the so-what view placed wrongly once in Now and once in a
Standing line (M2). No timeouts.

The prompt is accepted at `v2-p14`.

---

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
| content@2026-09-09 | 5 declared | 7 | off-script since Sep 8 | added 2026-09-11 (issue #17): two off-script runs, the current one included; three title-less runs — invention bait |

Fixtures were cut from `local-data/hindsight.db` via `cli/how.py`'s trail with
the greybox's event-run grain (≥3 fold, majority titling, ticket #64). They are
frozen JSON — the real ledger builder lands with the narrative pass (#68) and
the fixtures do not depend on it.

The real ledger builder (`cli/how.py` `run_ledger`, ticket #68) reproduces all
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
only when **every case passes**; regression semantics as before — a candidate
also has to match-or-beat the recorded baseline's recall and line counts.

**The sixth case (issue #17, 2026-09-11).** Off-script events form phase runs
under the label `off-script`, which the ledger's `stages` list never carries,
so the model meets a run whose stage is not a declared stage. The five frozen
cases hold no such run and could not measure that; `content@2026-09-09` was
cut from the live ledger the day the change landed, with the current run
off-script and an earlier one mid-history. Its Now fact anchors on the label
itself — the card must state the run as work done under `off-script`, not
narrate it as a stage. Reversed is empty by expectation: the one candidate,
"Pivoted … thesis", uses a verb the prompt's Reversed list does not name, and
placement is the model's judgement — it is expected under Built as work done.

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
python3 eval/run.py cli/prompts/status-v1.txt <tag>   # 5 haiku calls, ~1 min
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
| r10 | (variance run — issue #17 landed, prompt untouched) | ACCEPT 5/5 — recall 9/9, 14/15, 16/18, 4/4, 5/6 |
| r11 | (same prompt; sixth case `content@2026-09-09` added) | ACCEPT 6/6 — content 8/8, 8 lines; its Now line reads `off-script, since Sep 8: Create content-specific process model; …` — the run stated as work done under the label, not as a stage |

All runs sit under the one label `status-v1` because no narrative was
ever stored under an earlier draft — a prompt edit *after* this baseline bumps
the version. Baseline numbers a candidate must match-or-beat (r9, and r11 for
the sixth case): recall 9/9, 15/15, 18/18, 4/4, 5/6, 8/8; lines 8, 9, 11, 5, 9, 8. The one residual misplacement is
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
python3 eval/what_run.py cli/prompts/what-v2.txt <tag>   # 20 haiku calls, ~1 min
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
