# #68 Status narrative pass: prompt, storage, write-time gate

state: closed · labels: wayfinder:task · opened: 2026-08-28 · closed: 2026-08-29

Part of #58

## Question

The narrative pass itself, against the bar from the eval ticket: prompt, storage, gate.

- Input contract: the run ledger only (stage, date range, audit titles per run — `build/how.py` runs, not transcripts).
- Output contract: the three-group fact list (Built / Reversed / Now), write-time-gated like the what-pass (#38) — a refusal or off-contract output is not stored.
- Trigger and storage: generated after a sync when the ledger has changed (keyed on ledger content), persisted in the DB, never on page load (ADR-0008 read-only server). Where in `analyze.py`'s run does it sit, and what does the nightly job do?
- Regression: the eval runs on every prompt or model change.

Resolves when the pass clears the threshold on the frozen set and the stored object is what the styled view (#65) reads.



---

**comment · 2026-08-29**

## Resolution

Landed in 60672a1. The pass clears the frozen set and the stored object is what #65 reads.

**Input contract.** `build/how.py` `run_ledger` builds the run ledger from the bucketed trail (≥3 fold, majority titling with ties to the newest run, titles in first-appearance order). Cut at each fixture's `as_of`, it reproduces all five frozen ledgers in `eval/cases.json` byte-for-byte — so the eval measured the real input, not a stand-in. `how_data()` now returns `runs` (empty unless the declaration is valid).

**Prompt and bar.** `build/prompts/status-v1.txt`, haiku pinned. Nine eval runs (record in `eval/README.md`): recall was 48/52 from the first draft; every iteration after that was about fidelity — keep the titles' verb forms, quote Reversed lines verbatim, name pieces inside grouped lines, split mixed titles, no bare fragments. **r8 and r9 both ACCEPT 5/5** — the recorded baseline (recall 9/9, 15/15, 18/18, 4/4, 5/6). Haiku holds; no escalation. Residual variance is one placement judgement ("invert ticket ordering" as Built vs Reversed), inside the floor. Two scorer precision fixes on the way — `dates_in` read "4 decisions" as 4 December and "#18-19" as a date — parsing only, no anchor or floor moved; both in `--selfcheck`. Known ceiling stands: `promote PRD` is one content word.

**Storage and trigger.** New `status_narrative` table: one row per project — `ledger_hash`, `narrative` (the three-group JSON), `prompt_version`, `model`, `generated_at`. `analyze.refresh_narratives` runs inside `run_analysis` **after the session loop** (the ledger is made of audit titles) and before the backstop; it regenerates only when the `(ledger content hash, prompt version, model)` triple changed, so a quiet project costs nothing and the nightly makes at most one extra call per declaring project whose ledger moved. Skipped after a limit pause (it would only hit the same limit). The server never touches it (ADR-0008 intact); hindsight's own narrative calls are self-excluded by prompt signature.

**Write-time gate.** `eval/score.py` `contract()` — M3 traceability, M4 dating, M5 Now line, M6 bounds — extracted from the scorer and imported by the pass: one implementation. Non-JSON, refusal or off-contract output is not stored. **Decision recorded as an ADR-0012 amendment:** a gated-out *regeneration* leaves the last good narrative in place, stale (its `ledger_hash` no longer matches the live ledger), rather than deleting it; "refused" is absence only when nothing was ever stored. #65 states staleness — hash the live ledger, compare.

**Regression.** `eval/run.py` and the live pass now share `score.ledger_prompt`, so the eval scores exactly what production sends; a test pins `cases.json`'s model to `analyze.MODEL`. Any edit to the prompt bumps `STATUS_VERSION` and reruns the set first.

**Live.** Ran on the real DB: narratives stored for hindsight (6 Built / 2 Reversed / 1 Now) and thisisme (7 / 1 / 1), both through the gate. Two robustness fixes surfaced by the live run, both in the shared path: `init_db` connects with a 30 s busy timeout, and the pass materialises its project list before the model loop — an open read cursor across a minute-long call deadlocked against the listener's pending write.

**For #65 (the styled view):** read `status_narrative` by project; render the three groups above the runs; compare `ledger_hash` to the live ledger's hash for the stale marker; absent row → mechanical status (current run + tally) with the absence stated.


