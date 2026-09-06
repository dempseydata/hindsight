# #56 Publish hindsight as evidence: why / how / run-it README, MIT, public flip, CCwhere retired

state: open · labels: needs-triage · opened: 2026-08-26 · closed: 

Redefined 2026-09-01 by a `grill-with-docs` session (six forcing questions, demand first). Original framing — "make hindsight deployable by others" — was the wrong product: the reader never deploys anything.

## Reader

1. **A hiring manager** evaluating whether I drove a build with AI or prompted a dashboard into existence. Reads the README, nothing else.
2. **A fellow AI knowledge worker** — reads *how* as "what stack and process, can I borrow it"; the only reader who might reach *run it*.

## Claim

*Why I built it · how I built it · if you want it, how to run it* — in that order of weight.

## Demand

None, and stated as such. The repo's purpose is evidence; "built for one user" (framing.md, July) is part of the case, not a weakness to hide. CCwhere and ccwhy are being deleted, so this repo becomes the **only** public evidence of the line of work. It currently has no README, no description, no license, and is private.

## Decisions

- **README** — short. Carries the claims, links the evidence. Three screenshots (where / what / how) on real data. *Why*: three paragraphs compressed from `ideation/framing.md`. *How*: the phase map (ideate → design → build) with the named skills, the recurring evaluation discipline, and one or two reversals told plainly (ADR-0006 dropped a view; #78 the retention race) — links to `.claude/my-process.md`, `docs/adr/`, the closed issues. *Run it*: below.
- **Run section bar: document, don't automate.** macOS + launchd assumed and said so. A "hard-wired to this Mac" list (`build/hook.py:21-25` absolute path first). Privacy stated plainly: the DB is transcript-derived text in `local-data/`, gitignored, never leaves the machine (ADR-0001, ADR-0003). Fix #50 so the documented first run on an empty DB survives. Installer, `uvx`, Linux/systemd **deferred** until a real second user appears — cheap to reverse, so no ADR.
- **License: MIT** (as CCwhere was).
- **Lineage: CCwhere deleted, not archived.** Cited in prose only — "a previous incarnation, limited in functionality, a learning exercise that informed the thinking behind hindsight" — no URL to rot. `framing.md`'s supersession table gets the same edit.
- **Not touched**: `my-process.md` stays in `.claude/` (live config — its being live is the evidence). Real audit titles in `eval/cases.json` stay — they show the eval set was drawn from real data.

## Sequence

1. README, LICENSE, repo description, #50 fix, hard-wired list
2. Read-through of issues + phase docs (skim: no paths/emails/secrets found in any issue body), then `security-preflight`
3. Flip public
4. Delete CCwhere and ccwhy — **strictly after 3**; never a gap with no public evidence

## Next

`to-tickets` for the tracer-bullet breakdown.


