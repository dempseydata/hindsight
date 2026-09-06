# ADR-0009: Filesystem as the curation surface for the evolving collection

**Date:** 2026-08-26 · **Status:** accepted · **Decides:** [issue #51](../../background/tickets/051-deleted-projects-and-the-evolving-collection-hide-in-navigat.md)

## Context

Hindsight is archive-first: deleting a project's working folder erases nothing, so the ledger, chart and chips keep every project forever, and the chip row slowly fills with projects the operator is done with. Something had to mark a project as no longer a navigation target. Checked against today's filesystem, the obvious mechanical rule ("dir absent = deleted") misfires in both directions: `my-os` was archived by *renaming* to `my-os.archive` (absent yet deliberately kept), while `ccwhere`/`ccwhy` are conceptually finished but still on disk.

## Decision

**The workspace filesystem is the curation surface.** Deleting or archiving a project's folder *is* the operator action; hindsight merely observes it. Exactly two states — present or hidden — with no curated hide list and no third "retired" state. Consequently there is no way to retire a project whose folder still exists; that gap is self-healing (archive the folder when done with it), and accepting it is what keeps a hide list out of the product.

- **Observed at analysis time, never render time.** The analysis run records presence; the server renders the stored observation, staying a pure renderer of DB state with no filesystem opinions at request time. A deletion takes effect at the next analysis run; a recreated folder returns at the next run.
- **Hiding means exactly one thing: no chip.** Ledger rows, chart segments, league entries and totals are untouched — a hidden project behaves like a chipless tail project, and history is never re-shaped by later deletions (the coverage-window honesty rule, applied to navigation). Preserves #44's chip-stability rationale: the chip row changes only when the filesystem changes, never with time filtering.
- **Dash-ambiguity rule:** a project counts as present if *any* decoding of its dashes resolves to an existing directory, so subdirectory sessions of live projects never false-hide.
- **Reveal is ephemeral chrome state**, not stored config: a "show hidden (n)" toggle on the note line under the chips restores hidden projects' chips; un-revealing deactivates any active hidden-project filter.

## Considered options

- **Curated hide list** — honest about hiding being a preference, but the product's first curated surface, needing a write mechanism against a deliberately read-only server, for a gesture (folder deletion/archival) the operator already makes.
- **Render-time detection** — most current, but gives the server filesystem opinions and changes chips without an analysis run; rejected to keep "the view reflects the last run" uniform.
