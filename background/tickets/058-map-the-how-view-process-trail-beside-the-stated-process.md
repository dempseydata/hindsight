# #58 Map: the how-view — process trail beside the stated process

state: closed · labels: wayfinder:map · opened: 2026-08-26 · closed: 2026-08-29

## Destination

The how-view live post-v1: a styled `/how` view on the on-demand server — a per-project, stage-anchored process trail rendered beside the project's stated process, degrading to the raw ungrouped trail where no declaration exists — with the command grain landed in the substrate scan, the process-declaration frontmatter authored in the two declaring projects' `my-process.md` plus the template, and the DB-coverage question (70 hindsight sessions in the DB against 853 transcripts on disk) answered. Decided by ADR-0010; charted from [issue #54](054-ideate-process-view-actual-process-followed-vs-the-project-s.md).

## Notes

- **Execution is in scope for this map** — build tickets are worked here (via `implement` + `tdd`), overriding wayfinder's plan-only default. Same posture as the v1 build map.
- Read before any ticket: `docs/adr/0010-how-view-mechanical-trail-declared-stages.md`, CONTEXT.md's how-view section, `.claude/my-process.md` (the prose the frontmatter will sit atop).
- ADR-0010 is settled ground, not up for reopening: mechanical assembly with no model narrative; a deliberately dumb checker (presence, first/last-seen per stage, off-script list); juxtaposition with no order rules and no conformance verdicts; graceful degradation so nothing hides.
- Design: **no new direction-setting** — the view extends the shipped Indigo system; `design/tokens.css` and the root DESIGN.md are the contract. Prototype-first applies: the greybox ticket settles rendering with real data (Impeccable hooks **off** for that ticket only, back on after; its code dies, its answers are captured in the resolution comment). Presentation judgement calls are decided inside view tickets against real data and recorded in resolution comments — not separate tickets.
- Stack rules (ADR-0008): stdlib foreground server, strictly read-only over SQLite, zero-dep vanilla HTML/JS, no npm, no build step, no CDN.
- Real data from `local-data/hindsight.db` everywhere. The feasibility probe's evidence came from transcripts directly — the coverage research decides what the trail may rely on from the DB.
- One ticket per session; `code-review` then `/ponytail-review` before each commit.

## Decisions so far

- [Research: DB session coverage — 70 in the DB vs 853 transcripts on disk](059-research-db-session-coverage-70-in-the-db-vs-853-transcripts.md) — fully explained, no scan defect (776 files are hindsight's own analysis exhaust, plus sync lag and pruned-but-remembered history); no repair ticket, but the command-grain migration must rescan `done` sessions, which also heals two prefix-truncated event tails.
- [Process-declaration schema: the frontmatter shape for my-process.md](060-process-declaration-schema-the-frontmatter-shape-for-my-proc.md) — ADR-0011: strict hand-parsed YAML subset at line 1 of `.claude/my-process.md`, sole key `stages:` (ordered list; unique `name` + optional `commands`/`skills`/`paths`); bare names match the tail segment after the last colon, paths are root-relative with trailing-slash subtrees; absent/invalid/valid states with loud line-level invalidity and no partial salvage, duplicate markers across stages invalid; worked example adds a **Plan** stage (wayfinder → to-tickets) with Build starting at `implement`, seeding #62.

- [Command grain: capture user-typed slash commands in the substrate scan](061-command-grain-capture-user-typed-slash-commands-in-the-subst.md) — landed (94b094b): `command_grains` table filled by the substrate scan under #59's starts-with rule, verbatim names; the v3 migration rescanned all surviving history (190 grains across 59 sessions, both truncated event tails healed); extract.py untouched — its own skip gap filed as #66, outside this map.

- [Author the process declarations: three projects plus the template](062-author-the-process-declarations-three-projects-plus-the-temp.md) — landed in hindsight (c2f06dc), thisisme (6311e0e) and project-template (144537c), each with a fifth **Release** stage (security-preflight, graphify, document-app); Ontology-for-AI declares nothing — a learning project, its process file removed; matcher friction (leading slash on grains, nested path subtrees) fed to #63 and ADR-0011.

- [Trail assembly and the dumb checker: the how-view data pipeline](063-trail-assembly-and-the-dumb-checker-the-how-view-data-pipeli.md) — landed (1b7fb40): `build/how.py` parses the declaration (three states, line-numbered invalidity), assembles the trail from grains + skill calls + first-touch writes under the project root (no capture work needed — paths and skill names were already stored), and runs the dumb checker; on real data hindsight's five stages reproduce ADR-0010's chronology. Matcher decisions (one commands/skills name pool, slash stripped, longest-prefix paths) amended into ADR-0011; off-script filtering left to the greybox.

- [Greybox the how-view: rendering mechanics with real data](064-greybox-the-how-view-rendering-mechanics-with-real-data.md) — the trail is **phase runs** (consecutive same-stage events, ≥3, newest first, audit titles as summary, majority titling), not a chronology; a **status card** above it is model-written — ADR-0012 reopens ADR-0010's "no narrative" for this one artefact: a three-group fact list (Built / Reversed / Now) over the run ledger, evaluated, stored and gated like an audit; stated-process panel, both degraded states, project selector not chips (declaring projects only — absent declaration = no view, ADR-0010 amended; invalid still renders with its error), no shared chrome. Prototype dies on `prototype/how-view-greybox`.

- [Status narrative: frozen eval set and threshold](067-status-narrative-frozen-eval-set-and-threshold.md) — landed (b6214a6): five frozen run-ledger cases (hindsight ×3 dates, thisisme ×2) with hand-written Built/Reversed/Now facts; mechanical scorer (recall, forbidden, traceability, dating, Now line, bounds), no judge; **recall ≥ 80% per case, zero invention/untraced/undated, all cases must pass**; haiku pinned; M3–M6 double as the write-time gate. Undeclared projects get no narrative — ADR-0012 amended.

- [Status narrative pass: prompt, storage, write-time gate](068-status-narrative-pass-prompt-storage-write-time-gate.md) — landed (60672a1): `run_ledger` in `build/how.py` reproduces all five frozen ledgers exactly; `status-v1` on haiku ACCEPTs (baseline r8/r9, nine-run record in `eval/README.md`); `status_narrative` table written by `refresh_narratives` after the session loop, keyed on ledger hash + prompt version + model, gated by `score.contract` (M3–M6); ADR-0012 amended — a gated-out regeneration keeps the last good narrative, stale by hash mismatch, for #65 to state.

- [Styled /how view on the server](065-styled-how-view-on-the-server.md) — landed (80e6268): server-rendered, no script; declaring-project selector; status card with the stored narrative marked stale on any regeneration-key mismatch, mechanical line beneath; phase runs newest first with majority-session counts; invalid state = banner + trail by session. No per-stage hue (the label keys the stage — the ink ramp cannot carry five stages); fold threshold stays 3; `wayfinder` out of Plan (ADR-0011 amended). Browser-verified on hindsight, thisisme and a mangled declaration.

- [Session-opener noise in off-script: ignore list in the declaration, or a view-side drop](070-session-opener-noise-in-off-script-ignore-list-in-the-declar.md) — view-side fixed drop (9c5bb16): `/clear`, `/model`, `wayfinder` are set aside only when no stage claims them, and the off-script total states the exclusion per name; no `ignore:` key — a session boundary is a platform or house fact, not a project's process (ADR-0011 amended). hindsight 138 → 50 off-script events.

- [Bug: how-view lost the per-stage colour coding the greybox had](071-bug-how-view-lost-the-per-stage-colour-coding-the-greybox-ha.md) — landed (c1595a6): stage palette `--o-stage-1..5` + `-off` in tokens.css, positional per declaration, carried as the left rule on stated-process cards and run bands; current run badged `now`; ADR-0007 amended, DESIGN.md re-derived; gold-near-caution left for #69's audit to judge.

- [Floor audit of the how-view](069-floor-audit-of-the-how-view.md) — 19/20, one violation fixed (20dc519): the off-script `h2` uppercased command identifiers (`/model` → `/MODEL`) and wrapped label type to four lines; the exclusion now rides a `.mk` note in the typed case. Detector run at full fidelity — the default degraded regex fallback cannot see the inline `--stage` custom property, so it undercounts (10 findings vs 154). Gold-near-caution **accepted**: `--o-caution` renders only in the invalid banner, where no stage hue exists at all, so the two can never co-occur; the sharper adjacency is stage-2 violet vs accent (ΔE 17.4), recorded not fixed. side-tab / 10px labels / 11px body / flat hierarchy accepted with reasons; tokens.css untouched.

## Not yet specified

- Nothing. **The destination is reached** — all four criteria are met: the styled `/how` view is live (#65) with the stage palette (#71) and this floor audit (#69); the command grain landed in the substrate scan (#61); the declarations are authored in hindsight, thisisme and the template (#62); the DB-coverage question is answered (#59). No open child tickets remain.
- Carried out, not fog: thisisme and project-template still list `wayfinder` in Plan; that edit is theirs, not this map's.

## Out of scope

- Model-written narrative *of the trail* or model-driven comparison — declined in ADR-0010. **Amended by ADR-0012:** the status card is the one model-written artefact, and it carries the full Evaluation discipline (tickets #67 → #68).
- A condition-language declaration schema (`when: has-visual-surface`) — declined in ADR-0010; branching resolves at authoring time, the checker never evaluates conditions.
- Order rules and conformance verdicts — the checker stays dumb by decision, not omission; deviation is informative.
- The why-view and rationale attribution — dropped per ADR-0006; the how-view is not its resurrection.
- The process-document revisit — cleanup, retiring old-skill references, prose for the new Release stage — is the operator's separate effort, not this map's; the declarations already carry Release so the view can show it.










---

**comment · 2026-08-29**

Destination met — closing the map.

All four elements of the stated destination landed:

- **Styled `/how` on the on-demand server** — #65. Verified live this session: `/how` returns 200 off the real db, alongside `/what` and `/where`; `VIEWS = ("what", "where", "how")` in `build/serve.py`.
- **Command grain in the substrate scan** — #61.
- **Process declarations authored** — #62, in the two declaring projects plus the template. `read_declaration` parses this repo's as `valid` with five stages.
- **DB coverage question answered** — #59 (70 sessions vs 853 transcripts).

Every child ticket is closed and no open issue references this map. The follow-on defects found along the way are closed too: #69 (floor audit), #70 (session-opener noise), #71 (stage palette), #74 (local day buckets), #76, #77.

Execution-in-scope worked as intended here — build tickets were worked in the map rather than handed off, same posture as the v1 build map.

