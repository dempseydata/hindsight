# #75 Implement ADR-0009: hide deleted projects' chips (decided in #51, never built)

state: closed · labels: enhancement, ready-for-agent · opened: 2026-08-29 · closed: 2026-08-29

Found while checking live data on 2026-08-29 (operator report: "I have deleted several project folders that are inactive, and some of their chips show up still").

## This is not a bug — it is decided work that was never built

#51 was grilled and resolved on 2026-08-26, producing **ADR-0009 — Filesystem as the curation surface** (`docs/adr/0009-filesystem-as-curation-surface.md`) and a CONTEXT.md entry. That comment closes *"Ready for `to-tickets`."* No tickets were ever cut, and nothing implements it:

- `chip_rows` in `build/serve.py` has no filesystem check — chips derive purely from all-time DB rows
- `sessions` has no `hidden` column (`id project transcript_path date cli_version size status skipped_records`)
- `build/analyze.py` records no presence observation

## Current state (2026-08-29)

4 of the 8 rendered chips point at folders that no longer exist:

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

## Scope — as already decided in ADR-0009, not reopened here

1. **Marker** — two states, present or hidden. The workspace filesystem is the curation surface; deleting or archiving the folder *is* the operator action. No hide list, no third "retired" state.
2. **Observation** — taken at analysis time and stored; the server renders the stored observation. Deletion takes effect on the next analysis run, and a recreated folder returns likewise. A dash-encoded name counts as present if *any* decoding of its dashes resolves to an existing directory — subdirectory sessions must never false-hide.
3. **Scope** — chips only. Ledger, chart, league and totals untouched; a hidden project behaves exactly like a chipless tail project. The "data still counted" note stays true unamended.
4. **Reveal** — the note line under the chips grows the hidden count plus an inline **show hidden (n)** toggle; default off, ephemeral like all chrome state; un-revealing deactivates any active hidden-project filter.

## Notes

- `build/serve.py`'s `declaring_projects` already does filesystem-at-render-time for the how-view selector; ADR-0009 deliberately chose observed-at-analysis-time instead. Do not copy the render-time pattern — reconcile with it.
- The chip policy runs on **all-time** tokens/sessions by deliberate decision (#44), so a deleted project that ever qualified holds its chip forever. That stability rationale is why hiding, not re-scoring, is the mechanism.
- `my-os` was originally *renamed* to `my-os.archive` rather than deleted — the ground truth that drove decision 1. It is now absent from the workspace entirely.
- Lowest priority of the three filed today (#73, #74): no data is at stake and the design is already written.



---

**comment · 2026-08-29**

Duplicate of #57, which is the same work with acceptance criteria already cut from ADR-0009 and marked unblocked. The live evidence filed here — the four dead chips, and that `my-os` was renamed rather than deleted — is folded into #57 as a comment so nothing is lost. Tracking there.

