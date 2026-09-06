# #36 Decide the UI stack

state: closed · labels: wayfinder:grilling · opened: 2026-08-18 · closed: 2026-08-20

Part of #30

## Question

ADR-0003 explicitly excluded the UI stack and assigned it to the Design phase exit — that is this ticket. For a local-first, single-user app over SQLite: static HTML regenerated per analysis run (the greybox pattern) vs a small local server vs something else? What dependency policy for the UI (the pipeline's zero-pip-dep default explicitly does not bind it)? How does Claude Design's output (tokens, comps) map onto the chosen stack? Where do the two refresh controls live (analysis run vs the where-view's metrics refresh — ADR-0001 keeps them separate)? Blocked by Narrow because the chosen direction's motion/interaction ambitions inform the stack. Reasoning captured ADR-ready for grill-with-docs.



---

**comment · 2026-08-20**

## Resolution

**1. Serving model: on-demand foreground local server** — stdlib `http.server`, started when you want to look, stopped when done. Reads SQLite live (the listener keeps writing beneath it), renders both views plus shared header chrome. **Strictly read-only**: never invokes the model, never writes the DB. This is the "on-demand foreground dashboard" ADR-0001 already names — a foreground command, not a second daemon, so the ADR's boundary test is untouched. The static-regeneration greybox pattern is retired for the product: its refresh-during-active-use loop (rerun + reload, every time) was its real weakness, and live reads make ⌘R the whole story.

**2. UI dependency policy: zero-dep vanilla.** Python-assembled HTML, one inline stylesheet, vanilla JS for the interactions, sparks as inline SVG (a bar spark on the shared 30-day axis is ~30 `<rect>`s — the delta prototypes proved the shape at real volume). No npm, no build step, no CDN fetches (the floor's no-runtime-font-fetch rule, same spirit for scripts). The backend's zero-pip-dep rule was never binding here — this is the UI's own rule, decided on its own merits: two read-only views of filter-and-expand sit below the size where a framework pays, and Claude Design emits HTML/CSS anyway, so a framework would mean translating its output rather than adopting it. **Exceptions require an ADR**, mirroring the backend's escape-hatch discipline.

**3. Claude Design → repo: tokens are code, comps are reference.** The V3 Indigo-deck token contract (from [Narrow #35](035-narrow-one-direction-three-variants-one-winner.md)) lands as a committed `tokens.css` — the single source of truth the server inlines into every page at render time; `/design-sync pull` (run from VS Code only, per map notes) refreshes it. Comp markup is never imported — artboards are mockup-shaped; page structure comes from the greybox-validated layouts, matched to the comps by eye. The pull itself belongs to [Exit package #37](037-exit-package-tokens-in-the-repo-handoff-to-build.md).

**4. The two refresh controls** (ADR-0001 keeps them separate):
- **Where-view metrics refresh = browser reload.** Live reads make a dedicated control unnecessary; no button, no polling auto-refresh.
- **Analysis run = CLI, plus a nightly launchd calendar job** (`StartCalendarInterval`) invoking the same command. Fact corrected during grilling: **no nightly existed** — only the ingest listener (`com.hindsight.ingest.plist`) is scheduled today; analysis had only ever run by hand. The nightly is a scheduled *invocation* of the on-demand app, not a background *process*; ADR-0003 already designed analysis for unattended runs (subscription-limit pause/resume, self-observation exclusion). The server never grows a run button — a POST shelling out to `claude -p` would make the server an orchestrator, hold a long request open, and handle the limit-pause badly.

**Carried to grill-with-docs / Build:**
- A one-line clarifying note on ADR-0001's "schedules nothing" sentence (scheduled invocation ≠ background process).
- The nightly plist as a small build ticket.
- The what-view header's coverage/last-analysed line is the staleness prompt (existing honesty rule).



---

**comment · 2026-08-20**

Resolved — UI stack decided; reasoning captured ADR-ready above.

