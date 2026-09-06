# #67 Status narrative: frozen eval set and threshold

state: closed · labels: wayfinder:grilling · opened: 2026-08-28 · closed: 2026-08-29

Part of #58

## Question

Before any prompt is written: what is the bar for the status narrative (ADR-0012)? Decide the frozen eval set and the numeric threshold — the `tdd` red step for model output.

- **Set**: run ledgers from real projects in `local-data/hindsight.db` (hindsight, thisisme, career-ops at minimum; ideally snapshots at two or three dates each so "Now" moves), with hand-written expected fact lists in the three fixed groups (Built / Reversed / Now).
- **Score**: what counts as a correct line — traceability to ledger entries (every claim must map to an audit title or run), dating, group placement, nothing invented. Normalised substring matching worked for the audit eval; decide whether it holds here or whether a judge is needed.
- **Threshold**, decided now: below what pass-rate does the view fall back to the mechanical line?
- **Model**: the cheapest that clears the bar — same posture as the audit pass.

Output: `eval/` set + scorer, and the threshold written into the resolution before the narrative pass ticket starts.



---

**comment · 2026-08-29**

## Resolution

**The bar is set, before any prompt exists** — commit b6214a6, `eval/`.

**Set — five frozen run ledgers, not transcripts.** ADR-0012 makes the ledger the narrative's sole input, so the fixtures are ledgers (`eval/cases.json`, committed in full — nothing personal in a ledger), cut from real data via `build/how.py`'s trail with the greybox's event-run grain: hindsight at 08-20 / 08-25 / 08-27 (Now moves Plan → Plan → Plan across different work; why-view drop then why-pass removal appear as Reversed at different dates), thisisme at 08-16 / 08-25 (sparse; no Build run — invention bait; two Reversed facts from titles alone). Each carries hand-written expected facts in the three groups with substring anchors, plus forbidden anchors (post-snapshot or invented). **career-ops was dropped**: the operator ruled that a project without a `my-process.md` declaration gets no narrative at all — ADR-0012's "undivided run" sentence is struck and the amendment recorded on the ADR.

**Score — mechanical, no judge.** Per case: M1 recall (expected fact's anchor in a line of the *right* group); M2 forbidden = 0; M3 untraced = 0 (every line shares ≥ 2 content words with the ledger's stages + titles); M4 undated = 0 (every line dated, inside the ledger span); M5 a Now line names the current stage and its start date; M6 bounded (three groups, Built ≤ 8 / Reversed ≤ 4 / Now ≤ 3). Misplacement is reported, not floored — it already costs recall, and placement is the model's one judgement. A judge model was rejected: a second call per case, its own variance, and exactly the unverifiable thing the eval exists to catch. Known ceiling: a true line paraphrasing every ledger word fails M3 — the prompt keeps the operator's vocabulary, which ADR-0012 requires anyway.

**Threshold, decided now:** a case passes only when every floor holds, with **recall ≥ 80%**; a prompt/model is **ACCEPTed only when all five cases pass** and matches-or-beats the recorded baseline. Calibration: the greybox's hand-written stand-in scores 16/18 recall on hindsight@08-27 (it omitted hook self-instrumentation — a real gap) and fails on one undated Now line — both correct verdicts, and 90% would have failed a hand answer.

**"Falls back to the mechanical line" means two gates:** the eval gate above (pre-ship, needs ground truth) and a **write-time contract gate** per generated narrative — M3, M4, M5, M6 are ground-truth-free and run against the live ledger at write time, importing the same functions from `score.py`; a narrative failing any is not stored and the view renders the mechanical status with the absence stated.

**Model:** pin `claude-haiku-4-5-20251001`, the audit's; escalate a tier only after two prompt iterations fail ACCEPT, recording the failing run tag.

**Output contract for #68:** `{"Built": [...], "Reversed": [...], "Now": [...]}` — the scorer reads exactly this. Runner: `eval/run.py <prompt> <tag>`, 5 haiku calls. No baseline yet — #68 records it on its first ACCEPT.


