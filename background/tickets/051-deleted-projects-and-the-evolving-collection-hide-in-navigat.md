# #51 Deleted projects and the evolving collection: hide in navigation, never remove

state: closed · labels: needs-triage · opened: 2026-08-25 · closed: 2026-08-29

Tabled 2026-08-25, to pick up **after map #40's tickets complete**. This is a discussion (grilling material), not a pre-decided change — the operator's opening stance: something on the **navigation side, such as hiding** deleted projects, but **never fully removing** them. The real topic is how hindsight handles the evolving collection over time.

Facts to carry into that chat (established today, ticket #44):

- Hindsight is archive-first: deleting a project's working folder erases nothing — transcripts live under `~/.claude/projects/`, extracted history lives in the DB. The ledger, chart and chips all keep the project indefinitely.
- The shared chrome's chip policy runs on **all-time** tokens/sessions, deliberately, so the chip row is stable under time filtering — which also means a deleted project that ever qualified holds its chip forever. Any hiding mechanism has to reconcile with that stability rationale (resolution comment on #44).
- The sunk-cost panel is the one surface that already "forgets": it scans today's filesystem, so deleted projects drop out of the itemised side while staying in the measured medians — the existing honesty-rule framing may be a model for how other surfaces mark gone-but-remembered projects.
- Open questions for the discussion: what marks a project as deleted (filesystem absence at scan time? explicit operator action?); where hiding applies (chips only? ledger rows? chart bars?); whether hidden projects' tokens still count in totals (the chips note currently promises "data still counted"); and interaction with transcript pruning (`cleanupPeriodDays`), where absence means *unknown*, not deleted.



---

**comment · 2026-08-26**

**Grilled and decided** (grill-with-docs session, 2026-08-26). Recorded in CONTEXT.md ("Hidden project", under *The evolving collection*) and **ADR-0009 — Filesystem as the curation surface**.

The four decisions:

1. **Marker** — two states only, present or hidden. The workspace filesystem is the curation surface: deleting or archiving the folder *is* the operator action; no hide list, no third "retired" state. `ccwhere` keeps its chip until its folder is archived — self-healing, by design. (Ground truth that drove this: `my-os` was *renamed* to `my-os.archive`, not deleted — mechanical "dir absent = deleted" misfires both directions, so absence is read as the operator's gesture, not as a fact needing correction.)
2. **Observation** — at analysis time, stored; the server renders the stored observation. Deletion takes effect at the next analysis run; a recreated folder returns likewise. A dash-encoded name counts as present if *any* decoding of its dashes resolves to an existing directory (subdirectory sessions must never false-hide).
3. **Scope** — chips only. Ledger, chart, league, totals untouched: a hidden project behaves exactly like a chipless tail project, and history is never re-shaped by later deletions. The "data still counted" note stays true unamended.
4. **Reveal** — the note line under the chips (serve.py's "n projects have no chip…") grows the hidden count and an inline **show hidden (n)** toggle; default off, ephemeral like all chrome state; un-revealing deactivates any active hidden-project filter.

Ready for `to-tickets`.


---

**comment · 2026-08-29**

Discussion concluded — the build work lives in #57.

This was explicitly filed as grilling material rather than a pre-decided change, and that conversation happened: grilled 2026-08-26, resolved to **ADR-0009 — Filesystem as the curation surface**, with the *Hidden project* vocabulary added to CONTEXT.md under **The evolving collection**. The operator's opening stance held — hide on the navigation side, never remove — and the archive-first premise carried through: deleting a working folder erases nothing, since transcripts live under `~/.claude/projects/` and extracted history lives in the db.

The chip-policy tension this ticket raised (all-time chips mean a deleted project holds its chip forever) is what the decision resolves, and the implementation is specced in **#57**, which is open and unblocked.

Closing the discussion; #57 carries the remaining work.

