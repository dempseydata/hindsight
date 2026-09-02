# ADR-0006: v1 ships two views — the why-view is dropped wholesale

**Date:** 2026-08-24 · **Status:** accepted · **Decides:** issue #39 (operator decision, 2026-08-19), recorded at the top of Build per the handoff

## Context

Hindsight was framed as three views: **where** (where did my tokens go), **what** (what did I actually do), **why** (why did my process change). The delta-pass review (#31) put real pages side by side and exposed a redundancy: the what ledger is exactly the asked-for pseudo-audit of actions and decisions, and the why-view's prose payload near-duplicates it — both run the same stated-rationale convention, so a Decided line and a finding's why-line are frequently the same sentence, and same-session near-duplicate findings inflated the sameness further. The why-pass also carried almost the entire standing eval burden (frozen eval set, regression gate, resolution-rate health metric).

## Decision

**v1 is two views — what and where — plus shared header chrome. The why-view is dropped wholesale:** its surface, the why-pass pipeline (prompts, model calls) as a v1 requirement, and the eval burden that existed almost entirely for it.

Counter-arguments considered and set aside: (1) the why-view's differentiating half — the silent-change backstop strand — was empty at review time (0 change events, 19h-old baseline), so the redundancy impression was partly an artifact; (2) verbatim substring-verified evidence is something audit entries structurally lack; (3) change-centric lookup ("when did X change and why") is one row in why, a cross-session scan in what; (4) a merge option (backstop strand + evidence drill-down folded into the what ledger) and a 5-question falsification test were offered. The operator chose the clean cut.

**Stays:** the silent-change backstop *capture* (built, cheap) — it renders nowhere in v1. Shared header chrome validated via the why greybox — shared-owned, unaffected by the drop. **Recorded, not planned:** a future effort may fold change events into the what ledger as a mechanical strand ("changed, no stated rationale").

## Consequences

- Why-pass removal from `analyze.py` and the schema is Build-effort work, ticketed on map #40 — not part of this decision's write-up.
- `CONTEXT.md` is pruned to the two-view framing: findings/evidence, evaluation, and why-pass vocabulary removed (glossary deliberately ahead of the code until the removal ticket lands).
- `eval/` loses its only consumer; the regression gate and resolution-rate health metric retire with it.
- Backfill findings rows in the DB become historical data with no renderer; the schema-removal ticket decides their fate.
- Greybox verdict history (#6, the delta-pass D2 ruling in #31) stays as the route walked; #39 supersedes their forward-looking force.
