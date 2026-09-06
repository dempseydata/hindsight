# #42 Richer substrate scan: consumer grain, error flags, message-lens token linkage

state: closed · labels: wayfinder:task · opened: 2026-08-20 · closed: 2026-08-25

Part of #40

## Question

Extend `tool_events` with the three grains the where-view depends on (#31): skill/CLI consumer grain, per-call error flags, and message-lens token linkage. Transcript-derived, backfillable over the retained window. The consumer league, errors/day sparks, and CLI panel all wait on this.


---

**comment · 2026-08-25**

## Resolution

**Done — all grains landed, backfilled over the retained window, in commit 5242ebb.** `tool_events` now carries per call:

- **Consumer grain:** `consumer_type` / `consumer` / `mcp_tool`, classified at scan time by a near-verbatim port of ccwhere's production-validated parse (`classify`, `_cli_program`, `_cli_kind`): `skill` (Skill tool's skill), `mcp` (server + tool split), `cli` vs `shell` (Bash-command program, machine-derived from PATH at scan time — OS-shipped/builtin = shell), `builtin` (the tool itself; also the plain-Bash fallback for unextractable commands).
- **Per-call error flag:** `is_error` 1/0 from the paired tool_result, **NULL when never paired** — unknown, not a false ok.
- **Message-lens linkage:** `message_id` (the emitting API message's id) joins to `usage.message_id`, charging a consumer only the responses that invoked it — ccwhere's message-lens semantics on hindsight's schema.

**Two ingest-honesty fixes rode along (the #38 parse-wart family):**
- A tool_use whose `name` holds command text (whitespace tell) is malformed → counted-and-skipped, never stored. `ponytail:` ceiling noted: a single-token command stored as a name would still slip through.
- The records streaming one API response repeat its tool_use blocks — now deduped by tool_use_id like usage (5,900 duplicate ids existed; every count panel was inflated). Unrequested by the spec but load-bearing for the message lens (duplicates double-charge tokens); flagged by review, kept deliberately.

**Backfill (migration ran against `local-data/hindsight.db`):** grain columns added; scanned marker reset wherever the transcript survives → 93 sessions rescanned, 11,725 rows carrying grains, 0 malformed names, 0 duplicates, 327 errored calls, every grain row joinable to usage. Sessions whose transcripts were pruned keep their old rows with **NULL grains (unknown, not zero)**, deduped in place (988 rows; NULL-id rows undeduped — no key to pair on).

**Review dispositions (code-review two-axis + ponytail-review, both run pre-commit):**
- *"Three grains" vs #31's "all four":* #31's own text enumerates "(a) … Bash-command parse, skill-name capture, error flags, message linkage" — four items folding into this ticket's three (consumer grain = Bash parse + skill capture). All four are in. ccwhere's typed-slash-command events are **not** among them (they were pruning-list evidence, "never league consumers") and no in-scope panel needs them — not built.
- *Message-lens join contract:* the demonstrated join is on `message_id` alone (API ids are globally unique). **Note for the where-view ticket:** the league query decides whether to also key on `session_id`; nothing in the schema forbids either.
- Vocabulary landed in CONTEXT.md: Tool events (grains), Consumer, Session lens / message lens.

First-look distribution on real data: mcp 4,259 · builtin 3,710 · shell 2,410 · cli 1,284 (120 distinct programs) · skill 62 (21 distinct). Known ceiling from the naive Bash split (ported as-is): occasional JS keywords (`const`, `let`) leak through as cli consumers — same ceiling ccwhere shipped with, marked in code.


