# #55 Consumer league: filter builtin/shell out by default, chips to re-add categories

state: closed · labels: needs-triage · opened: 2026-08-26 · closed: 2026-08-26

The consumer league on /where includes many built-in and shell functions, drowning out the things deliberately added to the system (MCP servers, CLIs, skills). Filter builtin and shell out by default, with a way to add them back.

Proposed: category chips — mcp / cli / skill / shell / builtin — defaulting to mcp+cli+skill on.

Data fact (checked 2026-08-26): tool_events.consumer_type has exactly these five categories plus 2,626 rows with an empty consumer_type (unclassified). The chip design must decide where unclassified rows go — their own chip, folded into a default-off bucket, or always shown.

Open questions:
- Do the league's ≥5-calls membership floor and the tail count recompute against the filtered set or the full set?
- Does the filter state persist (URL param?) or reset per load?



---

**comment · 2026-08-26**

Shipped in 761e127. The open questions, as settled:

- **Floor and tail:** the ≥5-calls membership floor stays **all-time per consumer** — category filtering removes whole categories, never calls within a consumer, so recomputing it against the filtered set would change nothing but stability. The **tail recomputes against the visible categories**, otherwise hidden shell/builtin consumers leak back through the tail row and defeat the filter; its summary line says "visible-category consumers".
- **Persistence:** **resets per load** to mcp+cli+skill. Every existing chrome filter (project chips, window, hide-cache-reads) is in-memory with no URL params anywhere in the app; a URL param for this one filter would be an inconsistent one-off.
- **Unclassified rows** (2,626 empty `consumer_type`): unchanged — they have no consumer name to row under, so they keep their existing honesty note beneath the league and get **no chip**.

Two behaviors beyond the ticket text, out of the review pass:

- **Unknown categories fail open.** A future `consumer_type` that `classify()` grows (no chip exists for it) renders in the league unconditionally rather than being silently dropped — verified end-to-end against a seeded DB copy.
- **Switched-off calls are tallied**, not vanished: a note beneath the league counts calls hidden by the chips ("always counted in the tiles"), so the tile↔league gap is always explained. The CLI panel's note and the league prose were rescoped to match, and all toggle chips (including the pre-existing project/window chips) gained `aria-pressed`.


