# #81 One home per analyze↔serve contract fact: vocabularies, sections, narrative read (review C2)

state: closed · labels: ready-for-agent · opened: 2026-08-30 · closed: 2026-08-30

> *Settled by grilling on 2026-08-30 (architecture review, candidate C2). Implement in a fresh session, **after #80** (one drift test targets the static `where.html` #80 creates; if this somehow goes first, that test targets the `WHERE_HTML` constant instead — same assertion, different read).*

## Summary

The DB schema is the analyze↔serve interface for *shape* only. Five load-bearing facts live as duplicated literals on both sides of the seam, so a one-side edit fails silently: rename a prompt section and the ledger's `n did · n decided` counts read 0 with no error; reorder the `SELECT` at serve.py:1137 and narrative staleness inverts (serve.py:1151 compares an unnamed tuple by position). Move each fact to its existing owner — the `day_sql`/`local_day`/`audit_title` pattern the repo already uses ("so the two can never drift apart").

## Decisions (all settled — do not re-litigate)

1. **No new `contract.py` module** — a module whose only job is to be imported by both sides moves complexity rather than concentrating it. Each fact goes to its existing owner; the import paths (serve→analyze, serve→how, analyze→score) all exist today.
2. **Status + selection vocabulary → `analyze.py`, beside `SCHEMA`**: `STATUSES` and `SELECTABLE = ("pending", "partial")`. The two duplicated selection predicates (analyze.py:812, 1412) build from `SELECTABLE`; serve.py imports what it reads (the `'lost'` check at serve.py:196). **No behaviour change**: `partial` rendering as "synced, not yet analyzed" is semantically right (retryable *is* awaiting analysis) — it gains a comment making it deliberate, nothing more.
3. **Consumer vocabulary → `analyze.py`**: `CONSUMER_TYPES = ("skill", "mcp", "cli", "shell", "builtin")` beside the schema comment that currently defines it (analyze.py:207). Python literals (`analyze`, `how.py:216`, serve data code) import it.
4. **Audit section names → `analyze.py`**: `SECTIONS = ("Did", "Decided", "Setup changes")` moves from serve.py:141; `parse_entry` imports it.
5. **Non-Python consumers get drift tests, not imports** (the buttons in static `where.html`, the section names as prose in `what-v3.txt` — C1/#80 deliberately made these uninterpolated): one test asserts the category buttons in `where.html` equal `analyze.CONSUMER_TYPES`; one asserts the active what-prompt names every member of `SECTIONS`. Same pattern as the existing model-pin drift test (test_analyze.py:1707): detect divergence rather than prevent it.
6. **Narrative read moves to `how.py` — the fuller seam, not a wrapper**: `how.narrative(conn, project, d) -> {"facts", "written_day", "model", "stale"} | None` runs the `SELECT`, does the three-key comparison beside `ledger_hash`, and returns a dict. serve.py's `_status` becomes pure rendering. This deletes both the positional-tuple indexing and the one SQL-inside-HTML straddle in serve.py. Writer gate (analyze.py:960) and reader then share adjacent code and the same key triple. Test home: `test_how.py` (data-level).
7. **Narrative group names**: serve.py:1145's hardcoded `("Built", "Reversed", "Now")` becomes an import from `score` (where `BOUNDS` already lives).
8. **Docs: nothing** — no new ADR (the pattern is established, nothing a future explorer would re-litigate), no CONTEXT.md change.

## Acceptance criteria

- [ ] Grep finds no literal `('pending', 'partial')` / `"lost"` / consumer-type tuple / section-name tuple / `("Built", "Reversed", "Now")` outside the owning module (SQL strings built from the constants are fine; schema comments stay as prose).
- [ ] `how.narrative` exists, tested in `test_how.py`; `_status` in serve.py contains no SQL; serve.py no longer indexes the narrative row positionally.
- [ ] The two drift tests exist and pass; forcing a divergence (e.g. removing a button) fails the test.
- [ ] Rendered views byte-identical before vs after (same curl-diff method as #80) — this change is pure relocation.
- [ ] Full test suite green.

## Out of scope

- Explicit UI handling for `partial`/`empty` beyond the clarifying comment.
- A status enum/transition table (the constants suffice; revisit only if a sixth status actually lands).
- Merging the two schema owners (`analyze.SCHEMA` vs `listener.SCHEMA`) — real friction, separate discussion.



---

**comment · 2026-08-30**

Landed in 3bf023c. All acceptance criteria verified:

- **Greps clean**: no `('pending', 'partial')` / `"lost"` / consumer-type tuple / section-name tuple / `("Built", "Reversed", "Now")` outside their owners. One deliberate carve-out beyond the SQL/prose ones the AC names: `serve.what_data`'s blob key `r["lost"]` keeps its literal — it is the serve↔what.js contract (pinned by test_serve's rendering asserts), equal to the status value only by coincidence; code review flagged that binding it to `LOST` would make a vocabulary rename silently break the JS. The status *comparison* imports `LOST`.
- **`how.narrative`** exists beside `ledger_hash`, tested data-level in test_how.py (None / current / stale-on-each-of-the-three-keys / never-stale-without-runs); `_status` has no SQL and no positional indexing.
- **Drift tests** pass and were each verified to fail on a forced divergence (button removed from where.html; section renamed in what-v3.txt).
- **Byte-identical renders**: what/where/how (+ per-project how) rendered from HEAD code vs this change over a frozen DB copy — identical. (The naive live-DB curl-diff false-positived because the listener wrote otel rows between renders.)
- **Suite green**: 148 tests OK.

One deviation from decision 3's letter, per review: how.py selects skill events via a named member `SKILL` imported from analyze rather than `CONSUMER_TYPES[0]` — both review axes flagged the positional import as reintroducing identity-by-coincidence (a reorder, legal under both drift tests, would silently flip the query).

