# #85 README core: why + how, screenshots, MIT, description

state: closed · labels: ready-for-agent · opened: 2026-09-01 · closed: 2026-09-01

## Parent

#56

## What to build

The repo tells its story to a reader who reads nothing else. A short README carrying the claims and linking the evidence: three real-data screenshots (where / what / how views); a *why* section compressed from the ideation framing, including the honest built-for-one-user demand statement; a *how* section giving the phase map with the named skills, the recurring evaluation discipline, and one or two reversals told plainly (the dropped why-view, the lost-sessions retention race), linking to the process file, the ADRs and the closed issues. MIT LICENSE file at root. Repo description set. The ideation framing's predecessor citations reworded to URL-free prose (a previous incarnation, limited in functionality, a learning exercise that informed hindsight).

## Acceptance criteria

- [ ] README with the three sections' claims and working links to the evidence (run-it section may be a stub pending its own ticket)
- [ ] Three current screenshots on real data, rendered from the served UI
- [ ] LICENSE file, MIT
- [ ] Repo description set on GitHub
- [ ] No URL to CCwhere or ccwhy anywhere in tracked files; lineage stated in prose only

## Blocked by

None — can start immediately.


---

**comment · 2026-09-01**

Shipped in 1e0408b. README (why / how / run-it stub → #86) with three dark-theme screenshots rendered from the live UI on the real DB; MIT LICENSE; repo description set; framing.md predecessor citations reworded to URL-free prose — the tracked-files URL grep is clean. Two-axis review: spec 5/5 criteria met; standards found no hard violations, and its one substantive judgement call ("nothing leaves it" over-claimed — extracts do go to the claude CLI) was fixed to "the derived data never leaves it" before commit.

