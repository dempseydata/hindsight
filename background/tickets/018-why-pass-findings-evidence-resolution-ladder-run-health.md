# #18 Why-pass: findings, evidence resolution ladder, run health

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-17

## Parent

#15

## What to build

The why-pass joins the analysis run: per-part calls over the same extracts, findings shaped {change, why, evidence} into `findings` + `evidence` tables, every stored span resolved through the ADR-0002 ladder — exact substring → fuzzy within message (0.6) → fuzzy over extract → unresolved, model quotes never stored. Fenced JSON tolerated and stripped. The `runs` table records per-run bookkeeping including resolution-status counts as the standing health metric against the 97% eval baseline. The backfill prototype's resolver is the reference implementation.

## Acceptance criteria

- [ ] Fixture run produces findings with evidence rows exercising all four statuses (exact, fuzzy_msg, fuzzy_global, unresolved)
- [ ] Resolved spans are verbatim transcript text (substring-verifiable); unresolved keeps the finding and locator with a NULL span
- [ ] Evidence rows carry the source transcript uuid via the sidecar map
- [ ] Findings rows carry prompt version and model
- [ ] The runs row records resolution counts and a resolution rate
- [ ] Multi-part sessions concatenate findings with session-global indices, no dedupe pass

## Blocked by

- #17


---

**comment · 2026-08-17**

Implemented in cb124bc: the why-pass joins the analysis run in build/analyze.py — per-part calls over the same extracts, findings into `findings` + `evidence`, every locator resolved through the ADR-0002 ladder, `runs` row with resolution counts and rate. All acceptance criteria verified by seam-2 tests (stubbed runner): fixture exercising all four statuses (exact / fuzzy_msg / fuzzy_global / unresolved); resolved spans transcript-derived (exact span substring-verified, fuzzy spans from the matched window, never the model quote); unresolved keeps finding + locator with NULL span; evidence rows carry the sidecar uuid; findings rows carry prompt version (why-v1, prompt moved to build/prompts/) and model; multi-part sessions concatenate findings with session-global indices, no dedupe. Post-review hardening rode along: the ladder now has a single shared implementation in eval/resolve.py (type-guarded against malformed model JSON), model pin single-sourced from eval/corpus.json, cache validation with .bad quarantine, and excluded-session memory in sync. Full build/ suite: 29 tests green.

