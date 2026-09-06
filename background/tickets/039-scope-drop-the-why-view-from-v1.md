# #39 Scope: drop the why-view from v1

state: closed · labels: wayfinder:grilling · opened: 2026-08-20 · closed: 2026-08-20

Part of #30

## Question

Reviewing the delta-pass pages ([#31](031-delta-pass-greyboxes-re-judged-on-the-real-backend.md)) side by side, the why-view's content does not differentiate enough from the what-view's: the what ledger is exactly the asked-for pseudo-audit of actions and decisions, and both views operate the same stated-rationale convention, so the prose payloads converge. Does the why-view stay in v1?



---

**comment · 2026-08-20**

## Resolution

**Dropped wholesale — v1 is two views: what and where.** Operator decision, 2026-08-19, made against the delta-pass pages with the counter-arguments on the table.

**The observation that drove it:** the what ledger is exactly the asked-for pseudo-audit of actions and decisions; the why-view's prose payload near-duplicates it (both run the same stated-rationale convention, so a Decided line and a finding's why-line are frequently the same sentence), and the delta pass had already flagged same-session near-duplicate findings inflating the sameness.

**Counter-arguments considered and set aside:** (1) the why-view's differentiating half — the silent-change backstop strand — was empty at review time (0 change events, 19h-old baseline), so the redundancy impression was partly an artifact; (2) verbatim substring-verified evidence is something audit entries structurally lack; (3) change-centric lookup ("when did X change and why") is one row in why, a cross-session scan in what; (4) a merge option (backstop strand + evidence drill-down folded into the what ledger) and a 5-question falsification test were offered. The operator chose the clean cut.

**What the drop entails:**

- **Dies for v1:** the why-view surface; the why-pass pipeline (prompts, model calls) as a v1 requirement — and with it the standing eval burden (frozen eval set, regression gate, resolution-rate health metric), which existed almost entirely for the why-pass. Removal from `analyze.py` and the schema is Build-effort work, ticketed there, not here.
- **Stays:** the silent-change backstop *capture* (built, cheap, ticket #21) — it renders nowhere in v1. A future effort may fold change events into the what ledger as a mechanical strand ("changed, no stated rationale"); that idea is recorded here, not planned.
- **Stays:** shared header chrome validated via the why greybox (per-day stacked chart, click-to-filter time ranges, project chips) — adopted by the where-view, unaffected by the drop.
- **Dies with it (riders pruned from the Design bundle):** the #6 noise-policy re-check, evidence/quote anatomy, the why-duplicates-quote observation, the extraction-redundancy observation (moot once the why-pass isn't run).
- **To record at Build handoff:** the ADR for this scope change (grill-with-docs owns it at the top of Build), plus CONTEXT.md's "three views" framing updated there.

Greybox verdict history ([#6](006-greybox-the-why-view-change-timeline.md), the delta-pass D2 ruling in [#31](031-delta-pass-greyboxes-re-judged-on-the-real-backend.md)) stays as the route walked — this ticket supersedes their forward-looking force.


