# #77 A narrative group of null takes down the whole analysis run

state: closed · labels: bug · opened: 2026-08-29 · closed: 2026-08-29

Found by `/code-review` while landing #74. Pre-existing since **#68**.

## Symptom

`refresh_narratives` (`build/analyze.py:902`) validates the model's JSON with `isinstance(out, dict)` and nothing more. `eval/score.py` `contract()` then iterates the three group values. A response shaped `{"Built": [...], "Reversed": null, "Now": [...]}` — which the prompt practically invites, since "nothing reversed" is the common case — raises `TypeError`.

`run_analysis` catches only `LimitExhausted`, so the exception escapes the narrative pass and kills the rest of the run: `capture_backstop` and `scan_sunk_cost` never execute.

Reproduced.

## Notes

Same call site as #(the eval/score NULL-date issue). The write-time gate is supposed to be the thing that makes bad model output safe to ignore; instead a malformed shape takes the whole run down.

## Likely fix

Validate the shape, not just the type: three known keys, each a list of strings, coerce or reject. A rejected narrative should degrade to the mechanical status (ADR-0012's designed fallback), not abort the run — and the narrative pass belongs inside a `try` that lets the run finish either way.



---

**comment · 2026-08-29**

Fixed in 6cd31d7.

Fixed in `eval/score.py` rather than at the call site, because `score()` and `contract()` each built the groups with the same `out.get(g, [])` and both crashed on it — patching only `refresh_narratives` would have left the eval path broken on the same input. `groups_of()` is now the one reader; `bounded` requires each group to actually be a list.

**Rejected wholesale, not coerced.** `[]` is the contract and `null` is not a synonym for it. Coercing would have stored a narrative silently missing a group, and `bounded` would have passed it — the honesty grammar inverted. Rejection already has a designed landing place: no row stored, the how-view falls back to the mechanical status (ADR-0012), the next run retries. That is the same path any other gate rejection takes, so this adds no new failure mode.

Second half done too: the call site now catches any narrative failure, logs it to stderr and lets the run finish. `capture_backstop` and `scan_sunk_cost` are mechanical fact and were being traded for a model nicety.

Tests: two malformed shapes added to `test_refusal_and_off_contract_not_stored`, plus `test_narrative_failure_does_not_abort_the_run` (patches the pass to raise, asserts the backstop blob still lands). Three shape assertions in `score.py --selfcheck`. 128 tests green.

