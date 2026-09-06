# #57 Hidden projects: analysis-time presence, chip hiding, reveal toggle

state: closed · labels: ready-for-agent · opened: 2026-08-26 · closed: 2026-08-29

## Parent

#51 — decided there (resolution comment 2026-08-26); rationale in ADR-0009, vocabulary in CONTEXT.md (*Hidden project*, under **The evolving collection**).

## What to build

After an analysis run, a project whose workspace folder is gone no longer offers its chip: the analysis run observes each project's folder presence and stores it, and the server renders the stored observation. The note line under the chips reports the hidden count and offers an inline **show hidden (n)** toggle that restores hidden projects' chips; un-revealing deactivates any active hidden-project filter. Hiding is chips-only — ledger rows, chart segments, league entries and totals are untouched, and a hidden project's data behaves exactly like a chipless tail project's.

Demoable against today's real DB: `my-os` (renamed to `my-os.archive`) and `career-ops-CLI` (deleted) hide; `ccwhere`/`ccwhy` (still on disk) keep their chips.

## Acceptance criteria

- [ ] The analysis run records per-project folder presence; the server reads only the stored observation (no filesystem checks at render time). A deletion takes effect at the next analysis run; a recreated folder returns at the next run.
- [ ] A dash-encoded name counts as present if *any* decoding of its dashes resolves to an existing directory — subdirectory sessions of live projects never false-hide.
- [ ] Hidden projects are excluded from the chip row by default; the existing no-chip note grows the hidden count and the **show hidden (n)** toggle (default off, ephemeral like all chrome state).
- [ ] Revealing restores hidden projects' chips under the ordinary chip policy; un-revealing deactivates any active hidden-project filter — no invisible active filters.
- [ ] Ledger, chart, league and totals are unchanged by hiding; the "data still counted" note stays true unamended.
- [ ] Tests cover the presence observation (including a dash-ambiguous name) and the chip exclusion/reveal behaviour; full suite green.

## Blocked by

None — can start immediately.


---

**comment · 2026-08-29**

## Live evidence, 2026-08-29 (folded in from #75, closed as a duplicate)

Operator report: *"I have deleted several project folders that are inactive, and some of their chips show up still."* **4 of the 8 rendered chips point at folders that no longer exist:**

| chip | workspace folder |
|---|---|
| `career-ops` | exists |
| `hindsight` | exists |
| `content` | exists |
| `thisisme` | exists |
| `my-os-my-logs` | **gone** |
| `career-ops-CLI` | **gone** |
| `my-os` | **gone** |
| `my-logs` | **gone** |

Note this supersedes the demo line in the ticket above: `my-os` was originally *renamed* to `my-os.archive` — the ground truth that drove ADR-0009's decision 1 — but is now absent from the workspace entirely. `ccwhere`/`ccwhy` no longer render chips either way.

## Confirmed unbuilt

- `chip_rows` in `build/serve.py` has no filesystem check — chips derive purely from all-time DB rows
- `sessions` has no presence column (`id project transcript_path date cli_version size status skipped_records audited_size`)
- `build/analyze.py` records no presence observation

## Implementation notes

- `build/serve.py`'s `declaring_projects` already does filesystem-at-render-time for the how-view selector. ADR-0009 deliberately chose observed-at-analysis-time instead — do not copy the render-time pattern; reconcile with it.
- The chip policy runs on **all-time** tokens/sessions by deliberate decision (#44), so a deleted project that ever qualified holds its chip forever. That stability rationale is *why* hiding, not re-scoring, is the mechanism.



---

**comment · 2026-08-29**

Built and pushed in b843379.

Presence is observed at analysis time and stored in `project_presence`; the server reads only that observation. Dash-ambiguity resolved by walking the decodings, so `my-os-my-logs` never false-hides through a live `my-os/`. Hiding is chips-only — hidden chips stay in the DOM behind a CSS rule, the no-chip note grows a `show hidden (n)` toggle, and un-revealing drops any active hidden-project filter. Tail count, chart, ledger, league and totals untouched.

Two guards separating "could not look" from "it is gone": an unreadable projects dir keeps the last observation rather than marking every project absent, and a db predating the table hides nothing (the server is read-only and cannot create it — without this, an upgraded checkout 500s on every page until the next run).

Verified read-only against the live db: hides exactly the four chips whose folders are gone (`my-os`, `my-os-my-logs`, `my-logs`, `career-ops-CLI`), keeps the four that exist. Takes effect in the UI at the next analysis run, now triggered. 136 tests green.

