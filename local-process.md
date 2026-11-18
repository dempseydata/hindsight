---
stages:
  - name: Ideate
    commands: [brainstorm, discover, write-prd, red-team-prd, pre-mortem, write-stories, test-scenarios, grill-me]
    paths: [background/ideation/, background/definition/]
  - name: Design
    commands: [design-sync, impeccable]
    paths: [background/design/, design/]
  - name: Plan
    commands: [wayfinder, grill-with-docs, to-spec, to-tickets, setup-matt-pocock-skills]
    skills: [grilling, domain-modeling, research, prototype]
    paths: [docs/adr/, CONTEXT.md]
  - name: Build
    commands: [mp-night-shift, implement, code-review, ponytail-review, diagnosing-bugs, ponytail-audit]
    skills: [tdd, code-review, playwright-cli]
    paths: [build/, cli/, skills/, eval/]
  - name: Release
    commands: [security-preflight, graphify, document-app, release-notes]
---
# Hindsight's process declaration

This file deviates from the house master (ADR-0032), so it restates every stage whole: a
`local-process.md` replaces the master's declaration, it never patches it. It differs from the
house default in its paths: the record lives under `background/` (born public), deterministic
code under `cli/` (`build/` before the plugin layout, kept so past work still buckets) and the plugin's skills under `skills/` (ADR-0036), and `eval/`, the
regression harness for model passes, counts as Build. The prose of the process itself stays in
the house master.
