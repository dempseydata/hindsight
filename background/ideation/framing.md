# Hindsight — ideation framing

**Date:** 2026-07-31
**Method:** Six forcing questions (my-process.md, Ideate phase), run against the premise before any divergence.
**Verdict:** Premise passes. Exit ideation toward definition, gated by one eval (see Open risks).

## Problem statement

I run a skill- and MCP-heavy Claude Code setup across many independent projects, and I evolve that setup constantly. Three questions about my own usage are currently unanswerable, or answerable only by a tool I intend to supersede:

- **Where** did my tokens go? (input/output/cache economics; sunk session-start cost of CLAUDE.md and skills per project; per-skill/MCP/CLI usage counts and per-call token cost)
- **What** did I actually do? (a pseudo-audit of actions and decisions taken per session, per day, per project — reviewable over time)
- **Why** did my process change? (a record of how my system/project setup evolved — skills added and cut, processes rewritten — and the driver behind each change)

Hindsight is one local application answering all three over the transcript history already on disk.

## Supersession decisions

| Prior work | State | Decision |
| --- | --- | --- |
| **ccwhere** — a previous incarnation, limited in functionality; a learning exercise that informed hindsight | Shipped: Python package, tests, OpenSpec, ADRs | **Superseded.** Its scope *is* the where-view. Full rebuild accepted (UI changes wanted anyway), but its paid-for decisions — no daemon (ADR-0001), read-only, 5-minute liveness window, stdlib-only, no proxy, no cloud — are re-litigated deliberately at definition, not forgotten. Its PRD's competitive analysis and non-goals remain live reference. |
| **ccwhy** — a definition-stage sibling, never built | Definition only, zero code | **Split.** Its observability half — tracking setup evolution and the why behind changes — is absorbed as the why-view. Its memory-curation half (gated curator feeding memories back into Claude Code) is **parked, not absorbed**: it is an actuator and collides with the read-only posture. Possibly a later addition to the why-view; not v1. |

Rationale for one product, not three: chunks 1–3 of the original idea were ccwhere features and chunk 5 was ccwhy's thesis; only the audit chunk was new. Consolidation was chosen explicitly over a third parallel product.

## Forcing-question answers (evidence, honestly graded)

1. **Demand reality** — Demand is me; the test is therefore "acted-upon insights", not interest. ccwhere cleared its own bar: its findings drove a real skills cleanup and a full project restructure. Strong, by personal-tool standards.
2. **Status quo** — The status quo was ccwhere + vibes. Resolved by explicit supersession rather than quiet rebuilding.
3. **Desperate specificity** — Solo builder-operator, one user, open-sourced afterward. No imagined customer.
4. **Narrowest wedge** — The what/why pair. The where-view is a rebuild of known-buildable scope; the audit and change-rationale views are the only insights nothing on disk currently produces.
5. **Observation & surprise** — Both acted-upon ccwhere insights were *setup-evolution events* (skill cleanup, project restructure) — precisely what the why-view would record. The user's own behaviour is the strongest argument for the new wedge.
6. **Future-fit** — The where-view is the most commoditisable: Anthropic keeps expanding native usage reporting (`/usage`, `/context`, OTEL), and first-party analytics would eat it. The what/why audit trail is durable — only a local tool over full history can reconstruct decisions across months. Centre of gravity belongs on what/why.

## Dual purpose (load-bearing)

This build is also an end-to-end evaluation of the rebuilt toolchain and process (my-process.md), through to a deployed app. Following the process honestly is a stated goal of the project, not overhead.

## Open risks

1. **Why-extractability — RESOLVED 2026-07-31, wedge confirmed.** Eval run per the discipline (`eval-why-extractability/`): detection 6/6 ground-truth events, rationale match 6/6, zero false positives on the control probe — but model-quoted evidence failed verbatim verification (54% strict). Carried constraint: the pipeline attaches evidence mechanically (resolve model locators to true spans); model-quoted text is never stored as evidence. Untested residual: detection of silent setup changes made without in-session discussion — the what-view's mechanical detection must backstop the model.
2. **Audit-view definition is soft.** "Actions/decisions taken per session" needs sharpening: which actions count, at what granularity, reviewed how often. Candidate for brief divergence if definition stalls — otherwise settle it in the spec.
3. **Two-personality risk.** If memory-curation creeps back in before the observability product is settled, the read-only posture breaks. Parked means parked.

## Also wanted (features, not premise)

- Config options: which projects appear in views by default, and similar defaults. Falls out of the spec.
- UI changes relative to ccwhere (unspecified as yet; Design phase owns this).

## Exit

To **definition**, not further divergence — the premise is clear and the risk is extractability, not idea-shortage. First gate: the why-extractability eval (Open risk 1). Then `grill-with-docs` at the top of Build writes CONTEXT.md + ADRs per process.
