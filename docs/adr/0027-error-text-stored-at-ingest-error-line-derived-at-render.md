# ADR-0027: A failed call's result text is stored at ingest — the one tool-result content the product keeps — and its error line is derived at render, never classed

**Date:** 2026-09-16 · **Status:** accepted · **Decides:** [issue #31](https://github.com/dempseydata/hindsight/issues/31), the errors-by-consumer surface ADR-0026 left unowned (grilling, 2026-09-16); §1 built by [#32](https://github.com/dempseydata/hindsight/issues/32) · **Touches:** ADR-0002, ADR-0015, ADR-0020, ADR-0023

## Context

`tool_events` carries `is_error` per call, taken from the paired `tool_result`, and the league sums it per consumer. The count is not actionable: an 11.5% sqlite3 error share over 14 days is a number with nothing behind it, because the result's text — the only thing that says *what* failed — is not stored. ADR-0002 excluded tool results from the extract, and ADR-0023 recorded that the served UI shows no transcript text; every row in the database is a fact *about* a transcript, never its content.

Read from `local-data/` on 2026-09-16 (never committed):

- 696 error rows across 119 sessions, none `lost`. **450 (65%) are still readable on disk**; 246 are already gone with their transcripts, and the share only grows.
- Result content is a string in every case; median 186 characters, p90 ~1.5K, max 10K. The whole corpus is under 1 MB.
- The first line is a header on the two largest categories — `### Error` on 149/149 MCP errors, `Exit code N` on 203/209 cli and shell errors — and the line after it groups well with no vocabulary added: 22 browser_click timeouts, 10 `Invalid arguments for tool "browser_select_option"`, a run of heredoc `bad substitution` failures under git. A Python traceback's informative line is its last: on 24 real tracebacks the last non-empty line is the exception in 20 (`sqlite3.OperationalError: database is locked`, `no such column: audited_size`).
- Shell and builtin start switched off in the league by design (#55: ubiquitous, unprunable), so a shell error share is invisible until the chip is clicked.

## Decision

1. **Stored at ingest, not read on demand.** The substrate scan keeps the failed call's result text on its `tool_events` row (`error_text`). A v9 migration resets the scanned marker and refills from surviving transcripts — the v8 pattern — so the 450 readable errors are captured now. A pruned session keeps `is_error=1` with text NULL: counted, *text not captured*, unknown never zero (ADR-0015's rule). Subagent transcripts, growth top-up and the live-session guard are covered by the existing scan path; `content` on a tool_result is read but, like `is_error`, deliberately outside the field contract (ADR-0020), so the drift guard is unchanged.
2. **The boundary, stated as a rule:** *the only tool-result content the product stores is the text of a failed call; nothing of a successful one.* This is the first stored transcript content and the first the UI renders. The rule is here so that the successful result, or the tool input that caused the error, cannot arrive as "one more column" without a decision of their own.
3. **Verbatim and uncapped; no class.** A mechanical error class (connection / lock / not-found …) is new vocabulary and a classifier that false-positives; a truncated head saves nothing measurable and destroys the traceback's last line, the one case where the tail matters. The **error line** is derived at render by two rules — last non-empty line under a traceback header, else the first line after stripping `### Error`, `Exit code N` and the `<tool_use_error>` wrapper — and identical lines group with a count. The rules live in the view, so tuning them never costs a rescan. Stated ceiling: a traceback followed by stray script output groups under that output (4 of 24).
4. **Surface: the league row, not the reliability panel.** The errors list sits in the consumer's detail block under the existing *errors N* line, scoped by the same filter state, error lines grouped count-first with the full text nested and each line's session ids linked to the session anchor `/what#<sid>` (ADR-0023). The reliability panel is OTEL-fed under the coverage-window rule and states retries and wall time; tool errors are JSONL-fed with no coverage window — a drawer there would give one panel two sources and two honesty rules. The where blob gains one per-call error list carrying both the text and its error line; the line is derived by the server at render (`where_data`), where the two rules sit at a tested seam — nothing in the browser derives, it only groups and renders (amended at `to-spec`, 2026-09-16: the client has no test seam).
5. **The hidden chip is not a bug.** #55's default answers a prunability question and stands. Each category chip carries its in-window error count, and the existing switched-off-categories note gains the error total, so a hidden error share is stated, never silent, and the chip keeps its one meaning.

## Alternatives rejected

- **Read the text from the transcript on demand.** Already misses 35% and loses more weekly; and it is a fourth transcript reader under ADR-0020's contract, at render time, in a read-only server.
- **A separate `tool_errors` table.** One row per error with a foreign key to the event it already is; a nullable column on the event is the same fact without the join.
- **Store a truncated head.** See §3.
- **An error class.** See §3 — and "is anything to be done about it" is answered by the grouped line, which is a fact, not a judgement.
- **A drawer under the reliability panel.** See §4.
- **Errors override the category chip** (a switched-off category renders its erroring rows). Two meanings for one chip, and rows that appear and vanish with the window.

## Consequences

- Migration v9: rescan of every scanned session whose transcript survives, no model calls, seconds on this machine. One nullable column; no index.
- `docs/screenshots/` of an opened league row may show real error lines after a per-image check for home paths and key shapes (the pre-commit denylist cannot read a PNG); expanded traceback text, which carries a path on every frame, stays out.
- Two sessions of build at most: scan, column, migration and tests; then blob, grouping, chip counts and the where.js work. No map.
- The error-analysis view ADR-0026 named is this, and no more: no per-session page, no error trend panel, no cross-project comparison. Any of those is a new surface and runs the Design flow.
