# #88 Flip public, retire predecessors

state: open · labels: ready-for-agent · opened: 2026-09-01 · closed: 

## Parent

#56

## What to build

The evidence goes live, with no window in which the profile has none. Flip hindsight to public with description and topics in place; then — strictly after the flip — delete the CCwhere and ccwhy repos; finally check the profile cold, as the reader would, to confirm the case reads as intended (hindsight visible, README renders, screenshots load, license shown, closed-issue history browsable).

## Acceptance criteria

- [ ] hindsight public, description and topics set
- [ ] CCwhere and ccwhy deleted only after the flip is confirmed live
- [ ] Cold profile check done; result noted on this ticket

## Blocked by

- #87


---

**comment · 2026-09-02**

Plan reshaped (2026-09-01): **this repo never flips public**. Publication is now an export, per the Publication section added to my-standards/pipeline.md.

- Public artifact: https://github.com/dempseydata/hindsight-app — app-only export (build/, eval/, docs/adr/ with links converted to plain text, docs/screenshots/, design/tokens.css, CONTEXT.md, rewritten README, MIT). Fresh single-commit history; full test suite passes in the export tree (one live-fixture test fixed to skip on app-only checkouts, `7c62a00` here). Created **private** pending owner review; flip to public is one click.
- This repo stays private permanently: tickets, phase docs, toolchain, history. The #87 issue-revision purges are therefore moot (issues never publish); the branch deletions and redactions stand as belt-and-braces.
- Remaining for this ticket: owner reviews hindsight-app and flips it public; retire the ccwhere/ccwhy repos; check the profile cold, as the reader would.

