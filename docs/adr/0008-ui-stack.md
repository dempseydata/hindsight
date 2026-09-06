# ADR-0008: UI stack — foreground stdlib server, zero-dep vanilla UI, two refresh controls

**Date:** 2026-08-24 · **Status:** accepted · **Decides:** [issue #36](../../background/tickets/036-decide-the-ui-stack.md)

## Context

The greyboxes were statically regenerated pages; the styled product needed a serving model, a UI dependency policy, a bridge from Claude Design, and an answer to refresh. ADR-0001 fixes the outer boundary: exactly one background process (the ingest listener); everything else on-demand foreground.

## Decision

1. **On-demand foreground local server** — stdlib `http.server`, started to look, stopped when done; reads SQLite live (the listener keeps writing beneath it); renders both views plus shared header chrome. **Strictly read-only:** never invokes the model, never writes the DB. This is ADR-0001's "on-demand foreground dashboard" — a foreground command, not a second daemon, so the boundary test is untouched. Static regeneration is retired: its refresh-during-active-use loop (rerun + reload, every time) was its real weakness; live reads make ⌘R the whole story.
2. **Zero-dep vanilla UI** — Python-assembled HTML, one inline stylesheet, vanilla JS, sparks as inline SVG (a bar spark on the shared 30-day axis is ~30 `<rect>`s — proven at real volume in the delta prototypes). No npm, no build step, no CDN fetches. This is the UI's own rule, not the backend's zero-pip-dep rule: two read-only views of filter-and-expand sit below the size where a framework pays, and Claude Design emits HTML/CSS anyway — a framework would mean translating its output rather than adopting it. **Exceptions require an ADR.**
3. **Tokens are code, comps are reference** — `tokens.css` committed and inlined at render time; `/design-sync pull` (from VS Code only, per the map's collision note) refreshes it; page structure comes from the greybox-validated layouts, matched to the comps by eye (see ADR-0007).
4. **Two refresh controls, kept separate** — where-view metrics refresh is browser reload (live reads; no button, no polling). Analysis runs via CLI plus a nightly launchd calendar job (`StartCalendarInterval`) invoking the same command — a scheduled *invocation* of the on-demand app, not a background *process* (see ADR-0001's 2026-08-24 amendment). No nightly existed before; only the ingest listener is scheduled today. **The server never grows a run button:** a POST shelling out to `claude -p` would make the server an orchestrator, hold a long request open, and handle the subscription-limit pause badly.

## Consequences

- The nightly plist is a small Build ticket; ADR-0003 already designed analysis for unattended runs (limit pause/resume, self-exclusion).
- The what-view header's coverage/last-analysed line is the staleness prompt (existing honesty rule) — no freshness machinery in the server.
- Any UI dependency, build step, or CDN fetch requires a new ADR.
- **Amended 2026-08-30 (ticket #80):** the view CSS/JS/HTML formerly inlined as string constants in `serve.py` lives in `build/assets/` (nine files), read per request over the same seam as `tokens.css`. Byte-identical output; no change to the zero-dep rule — still no build step.
