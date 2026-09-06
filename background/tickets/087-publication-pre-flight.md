# #87 Publication pre-flight

state: closed · labels: ready-for-agent · opened: 2026-09-01 · closed: 2026-09-01

## Parent

#56

## What to build

The repo is confirmed safe to flip public. A read-through of all issue bodies and comments and the phase docs for anything profile-unworthy (an earlier automated skim found no local paths, emails or secrets in issue bodies — this is the human-judgement pass), plus a security-preflight run over the repo as it will be published. Output is a go/no-go note on this ticket listing anything found and how it was resolved.

## Acceptance criteria

- [ ] All issues (bodies + comments) and phase docs read through; findings listed or 'none' stated
- [ ] security-preflight run and passed on the flip-ready tree
- [ ] Go/no-go note posted on this ticket

## Blocked by

- #85
- #86


---

**comment · 2026-09-01**

## Go/no-go: **NO-GO as the remote stands today — GO once the short pre-flip list below is cleared.**

Everything mechanical is clean. What remains is one deliberate decision about job-search visibility, plus two actions that belong to #88's flip sequence.

### What was checked

- All 88 issues, bodies **and** comments, read in full (the human-judgement pass this ticket asked for).
- Every tracked doc read in full: `ideation/`, `definition/`, `design/`, all 17 ADRs, `docs/agents/`, README, CONTEXT.md, DESIGN.md, `what-is-installed.md`, prompts, eval fixtures; `Main.dc.html`/`canvas.json` grepped and skimmed; all three screenshots inspected.
- Every ref: full `git log -p` history sweep over all branches and tags, all 418 historical paths, plus a per-branch content sweep of the five pushed and two local-only branches.
- `security-preflight` run over the tree as it will publish (verdict at the end).

### Clean — stated explicitly

- **Secrets: zero**, in the tree and in the entire history of every ref. The single pattern hit is placeholder help text (`<the printed sk-ant-oat01-… token>`) in a since-deleted vendored skill file — not a credential.
- **Emails/phones/addresses: zero** in content. All 97 commits are the one public identity (`dempseydata <dempseydata@gmail.com>`).
- **No `.env`, `.db`, `.jsonl`, or `local-data/` file was ever committed on any ref.** `local-data/` has been gitignored since the first greybox branch; every prototype writes only there.
- Both servers bind `127.0.0.1` only; session-derived text is HTML-escaped server-side (`serve.py`) and client-side (`esc()` in `what.js`/`where.js`); stdlib-only so no dependency audit applies; wiki has no content; LICENSE is MIT.
- Mitigations that already existed and read well: career-ops was deliberately dropped from the eval set (#67), `eval/corpus.json` was deliberately deleted from master (`8cdf8be`), and `eval/README.md` states the "nothing personal in a ledger" rule.

### Fixed on master in this ticket (commit `4366cde`)

1. **`.gitignore` hardened**: `.playwright-mcp/`, `terminal.png`, `graphify-out/`, `.impeccable/`. The first two were the worst latent leak found anywhere — untracked but one `git add -A` from publishing: `.playwright-mcp/` page snapshots dump the live what-view ledger verbatim, including ~40 named employers with scores and reject decisions from a job-search project (a live offer via a named recruiting firm among them); `terminal.png` renders the same ledger.
2. **ADR-0013 and ADR-0016**: the two verbatim career-ops quotes naming employers ([employer A] role tracker; [employer B] application) replaced with marked redactions — each ADR's technical point is intact.
3. **CLAUDE.md** stale mission line (`why the process changed` → `how the process ran`, matching ADR-0006 and the README) and **`what-is-installed.md`**'s spent one-time template section removed.

Tests: 147/147 pass after the edits. Note the redactions clean the **tip** only — the original quotes remain reachable in git history (`git log -S`); see the decision below.

### Must do before the flip (mechanical — belongs in #88)

1. **Delete (or filter-rewrite) four pushed branches**: `prototype/design-delta-pass`, `prototype/what-view-greybox`, `prototype/where-view-greybox`, `research/taste-references`. All four still carry `eval/corpus.json` + the pre-sanitisation `eval/README.md` that master deliberately deleted in `8cdf8be` — career-ops job-hunt content (comp-gate salary-range rules, ATS form conventions, the Gmail ask-first rule, a private repo's commit hash + message, cross-project session ids). `git push origin --delete <branch>` for each. Trade-off to be aware of: issues #5, #12, #30, #32, #33 cite these branches as the prototypes' "primary source", so deletion turns those links dead — the issues' verdict text stands alone, which was the stated intent ("master keeps only the verdict"). `research/db-coverage` is fine to keep (its only exposure is a home-dir path, consistent with the README's stated hard-wired-paths policy).
2. **Never push** the local-only `prototype/why-view-greybox` (same `eval/corpus.json`) or `prototype/how-view-greybox`.
3. **Push master** — origin is currently behind (tickets #84–#87's commits are local only), so the flip would otherwise publish a stale tip without the MIT license, README, or these redactions.

### The one decision only you can make: job-search visibility

Even after the fixes above, the published repo will disclose that you run a job-search automation project, to the exact audience the README names (a hiring manager). The remaining carriers:

- **Issue #73** quotes the *"Updated [employer A] role tracker with recruiter…"* audit entry verbatim; **#31/#38** contain a recognisable `ls output/cv-…` filename; **#10** names the Gmail ask-first rule in `career-ops/modes/_custom.md`; **#44** states career-ops took **88%** of tokens in one window; **#3** discusses the ATS required-field rule; `definition/red-team-tests.md` cites career-ops' `auto_pdf_score_threshold: 3.9`.
- **`docs/screenshots/what.png`** (the README hero) shows `career-ops · Job evaluation + CV pipeline repairs` and an unpublished article title from `content`.
- **Git history** retains the pre-redaction ADR text.

**Recommendation** (middle path, consistent with the repo's working-record ethos): accept that career-ops *exists* and is visibly a job-hunt project — it is woven through the issue history and un-redactable piecemeal — but remove the employer-naming specifics: (a) edit #73, #31, #38 (and #10 if you judge the Gmail line sensitive); (b) regenerate `what.png` with the career-ops/content chips filtered off — one click, still real data; (c) skip a master history rewrite — it would falsify the "repo as honest working record" premise for two mild quotes that only deliberate archaeology surfaces. **Caveat that makes the issue edits a manual step:** on a public repo, issue edit history is visible to everyone — after editing, delete the prior revisions via the edit-history dropdown ("…" → edited → Delete revision), or the redaction is cosmetic. Alternatively, accept all of it as-is — the content is professional in tone throughout; the exposure is the *fact* of an active job search, not anything embarrassing.

Minor accepts, listed for completeness (no action recommended): the "I am EST" timezone remark in #74; claude.ai artifact links in #34/#35/ADR-0007/build-handoff that will 404 for readers; `.claude/settings.json`'s machine paths, sibling-project names, and broad wildcards (live config, consistent with the README's hard-wired-paths honesty); home-directory paths in #59 and `research/db-coverage.md` (same policy); the "broken binaries" remark about a third-party skill in #7.

### security-preflight verdict

**Part 1: pass** on the flip-ready tree — no secrets (tree or history), no injection surface beyond the localhost read-only server (parameterized SQLite throughout, HTML escaping both sides), no auth surface (binds `127.0.0.1`, read-only), no dependencies to audit (stdlib-only), abuse protection n/a for a local tool. **Part 2: n/a** — nothing here exposes a public chat or agent; the one outbound path is the owner's own `claude` CLI, as the README's privacy section states.

*(Read-throughs and branch sweep fanned out to three sub-agents with a shared rubric; every finding quoted above was verified against the source before action.)*



---

**comment · 2026-09-01**

All three acceptance criteria met: read-throughs done with findings listed above, security-preflight run (Part 1 pass, Part 2 n/a), go/no-go note posted. The flip itself (#88) picks up the note's pre-flip list.


---

**comment · 2026-09-01**

Sanitisation executed (follow-up to the go/no-go note above):

- **Branches**: `prototype/design-delta-pass`, `prototype/what-view-greybox`, `prototype/where-view-greybox`, `research/taste-references` deleted from origin. Remote now holds only `master` and `research/db-coverage`. Local copies (incl. the never-pushed `prototype/why-view-greybox`) remain on this machine.
- **Issues**: #73 ([employer A] quote), #31 and #38 (`cv-…` filename) edited via API; zero matches on re-check. **Manual step outstanding: delete the prior revisions via each item's edit-history dropdown ("…" → edited → Delete revision) before the flip** — edit history is publicly visible on a public repo.
- **Screenshot**: `docs/screenshots/what.png` regenerated (`cd7be26`) with chips filtered to hindsight + thisisme — same view, same dimensions, real data, no private-project session titles.

Master remains unpushed by design; push + flip are #88's sequence.

