# ADR-0023: A pattern's evidence is the session, per row; a session id resolves to its what-ledger row

**Date:** 2026-09-11 · **Status:** accepted · **Decides:** [issue #24](https://github.com/dempseydata/hindsight/issues/24); map [#18](https://github.com/dempseydata/hindsight/issues/18) · **Touches:** ADR-0021, ADR-0022, ADR-0002

## Context

The Stage A prototype ([#19](https://github.com/dempseydata/hindsight/issues/19)) drafted a pattern schema carrying three kinds of evidence pointer — session ids, tool-use ids and message ids — because the tables hold all three: `tool_events` carries the tool-use id and the emitting message's API id, `usage` the message id. It also flagged that the how-view's trail carries no tool-use ids, as an evidence gap for this decision.

The served UI addresses none of that grain. Its routes are the three views; the what ledger renders one `<details>` row per session, keyed by `data-id`, but nothing opens a row from a URL; the where view filters by project and window only; the reliability panel states session ids as a hover title and links nowhere. The product never shows transcript text, so a tool-use id or message id is opaque to the operator — there is nothing to follow it to.

Two facts settle most of the question before it is asked. A pattern's window *is* the header filter state (ADR-0022), so the what and where views are one nav click from the so-what view with the pattern's project and window already applied. And Stage A is mechanical, run at render time or cached per window, so any pointer finer than the session is recoverable by re-running the row's own query.

## Decision

- **Click-through target: the what-ledger row.** A session id in a pattern links to `/what#<session-id>`. The fragment opens and scrolls to the first rendered row carrying that id (newest day first; a continuation row resolves to the same entry). It never touches filter state — the how-link's `?p=` remains the one sanctioned way a link writes state. When the ledger is not showing the row, one line under the ledger states that the session is outside the current filter: a gap under the coverage-window rule, never a silent nothing.
- **No per-session page.** The audit entry in the ledger is the product's only per-session artefact, and no signal in Stage A v1 needs tool-grain evidence a human can read. Deferred, not refused: the signal that needs it is the moment to design it, and it runs the house Design flow as a new surface.
- **Pointer set: session ids only.** Tool-use ids and message ids leave the pattern schema. Nothing served dereferences them; Stage B's traceability, if Stage B is built, is set membership on pattern ids ([#23](https://github.com/dempseydata/hindsight/issues/23)); and a stored pointer no one reads is a duplicate of the query with a rot risk the query does not have. The row's identity — signal, project, window, row key — is the pointer to anything finer.
- **Placement: per row, never on the pattern.** One rule for every signal: a row's session ids are the sessions its *numerator* was drawn from. Consumer rows follow their stored reason — the sessions carrying the erroring calls for error share, the sessions the consumer appeared in for token share. Drift rows carry the sessions where the newly off-script name or write path appeared. Cost-trend rows carry a session count and no list: their grain is the whole project window, whose session list is the ledger under the shared filter state. The pattern's window and baseline ranges are its coverage statement; it carries no evidence field of its own.

## Alternatives rejected

- **Ids stated, nothing clickable** (the reliability panel's posture). Zero build, but the operator copies an id with nowhere to paste it; the ledger row exists and costs a fragment handler.
- **A where-view state per session.** The where view has no session filter; adding one is a new panel, not a link.
- **Keeping the finer ids against future need.** The tables keep them; the schema need not. Adding a field when its consumer exists is cheaper than carrying one that nothing checks.
- **A link that rewrites the filter to guarantee a hit.** A second way to set state, for an edge the stated miss already covers.

## Consequences

- The prototype's "trail carries no tool-use ids" gap closes by construction: nothing asks for them.
- CONTEXT.md's *pattern* names session ids per row as its evidence; the served UI gains the *session anchor*.
- The what-view build ticket, when cut, carries the fragment handler and the miss line; the so-what view renders session ids as links to it.
- Stage B's digest, if built, cites patterns by id and sessions by id; it inherits no finer grain.

**Amendment (2026-09-16, ADR-0027, issue #32):** the served UI will render one kind of transcript text — the error line of a failed tool call, derived from its stored `error_text` — in the league row's detail, with session ids as session anchors. The rule that no other transcript text is served stands.
