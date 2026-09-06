# Ingest schema verification — real payloads vs the command-centre review's claims

**Date:** 2026-08-01. Resolves wayfinder ticket [#2](../tickets/002-verify-ingest-schemas-against-real-payloads.md).
**Method:** stdlib OTLP capture stub (`local-data/otel-capture/stub.py`, port 4318) + one telemetry-enabled `claude -p` probe session exercising Bash and Write; JSONL checks on the probe session plus three large real sessions. Cross-checked against the official monitoring docs (<https://code.claude.com/docs/en/monitoring-usage>).
**Versions observed:** OTEL payloads from CLI **2.1.91** (Homebrew); JSONL from **2.1.91, 2.1.209, 2.1.220**. Raw captures in `local-data/otel-capture/` (gitignored — contain account identifiers).

## Verdict on the review's claims

| Claim (`command-centre-review.md`) | Verdict |
| --- | --- |
| Env config: `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_{LOGS,METRICS}_EXPORTER=otlp`, OTLP/HTTP JSON endpoint, `OTEL_LOG_TOOL_DETAILS=1` | **Confirmed live.** Payloads arrived on `/v1/logs` + `/v1/metrics` as JSON (chunked transfer encoding, not gzip — ingest must handle chunked bodies). `settings.json` `env` block is a real mechanism. |
| `tool_decision` (edit accept/reject) | **Confirmed live** — `{tool_name, decision: accept/reject, source: config/hook/user_*}` + metric `claude_code.code_edit_tool.decision`. |
| `api_error` detail with attempt counts | **Documented, not exercised** — official docs: `error`, `status_code`, `attempt`, `model`. No reason to doubt. |
| Compaction events | **Corrected.** No dedicated compaction event exists. Compaction is inferable only from `query_source: "compact"` on `api_request`/`assistant_response` — and `query_source` was **absent** on 2.1.91 payloads (newer versions only). Treat compaction detection as version-dependent, not guaranteed. |
| Hook execution timings | **Falsified.** User-level SessionStart/PreToolUse/PostToolUse hooks were active during the probe; no hook event of any kind appeared, and none exists in the official event list. The "hook activity" insight has no OTEL source. Options: self-instrument (a hook that POSTs its own timing to the listener) or drop the insight. |
| Precise MCP server/tool attribution | **Documented, not exercised** — `mcp_server.name`/`mcp_tool.name` on api_request/cost/token metrics, `mcp_server_connection` event, MCP names in `tool_parameters` (requires `OTEL_LOG_TOOL_DETAILS=1`). |
| `claude_code.{commit,pull_request,lines_of_code}.count` | **lines_of_code.count confirmed live**; commit/PR counters documented (not exercised — probe made no commits). |
| Delta counters, `SUM(value)` correct | **Confirmed live** — all sums arrived `isMonotonic: true`, `aggregationTemporality: 1` (DELTA; the documented default). |
| JSONL `message.usage` fields | **Confirmed** — `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` present on every assistant record with usage, all three versions. Extra fields vary by version: `cache_creation` (object), `service_tier`, `inference_geo`, and on newer versions `iterations`, `server_tool_use`, `speed`. |
| `tool_use`/`tool_result` pairing by `tool_use_id` | **Confirmed** — 507/507 paired across three large sessions (222, 171, 114), zero orphans in completed sessions. `is_error` present on failed results. The 10-min orphan cap remains sensible for crashed sessions. |

## Verified OTEL shapes (as observed, 2.1.91)

Transport: OTLP/HTTP JSON, `POST /v1/logs` + `/v1/metrics`, `Transfer-Encoding: chunked`, exporter `OTel-OTLP-Exporter-JavaScript/0.208.0`. Resource attrs: `service.name: claude-code`, `service.version`, `os.type`, `os.version`, `host.arch`.

**Log events observed** (all carry `event.name`, `event.timestamp`, `event.sequence`, `session.id`, `prompt.id` (not on 2.1.91's user_prompt — newer), `terminal.type`, `organization.id`, `user.{id,email,account_id,account_uuid}`):

- `user_prompt` — `prompt_length`, `prompt` (only because `OTEL_LOG_USER_PROMPTS=1`)
- `tool_decision` — `tool_name`, `decision`, `source`
- `tool_result` — `tool_name`, `success`, `duration_ms`, `tool_result_size_bytes`, `tool_input`/`tool_parameters` (from `OTEL_LOG_TOOL_DETAILS=1`; `tool_parameters` present only on some tools). **No `tool_use_id` at 2.1.91** — current docs list it, so OTEL↔JSONL joins by tool id are version-gated; join on `session.id` + time otherwise.
- `api_request` — `model`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `cost_usd`, `duration_ms`, `speed`. (Note: OTEL has `cost_usd`; JSONL does not — cost from JSONL must be computed from tokens × price.)

Documented but unobserved (newer CLI or untriggered): `assistant_response`, `api_error`, `api_refusal`, `permission_mode_changed`, `auth`, `mcp_server_connection`, `internal_error`, `plugin_installed`/`plugin_loaded`, raw-API-body events.

**Metrics observed:** `claude_code.session.count`, `.cost.usage`, `.token.usage` (attr `type`: input/output/cacheRead/cacheCreation), `.lines_of_code.count` (attr `type`: added/removed), `.code_edit_tool.decision` (attrs `decision`, `source`, `language`, `tool_name`). All DELTA monotonic sums. Documented but unobserved: `.commit.count`, `.pull_request.count`, `.active_time.total`.

## Verified JSONL shapes (2.1.91–2.1.220)

- Record `type` values seen: `user`, `assistant`, `system`, `attachment`, `queue-operation`, `file-history-snapshot`, `file-history-delta`, `last-prompt`, `ai-title`, `custom-title`, `summary` — and the set grows with versions. **Ingest constraint: switch on known types, silently count-and-skip unknown ones** (reinforces the per-row fault-tolerance rule).
- `assistant` records: `message.usage` as above; `message.content[]` items of `type: tool_use` carry `id`, `name`, `input`.
- `user` records: `message.content[]` items of `type: tool_result` carry `tool_use_id`, `content`, `is_error`.
- Records carry `version` (CLI), `sessionId`, `timestamp`, `cwd`, `gitBranch`, `isSidechain`, `uuid`/`parentUuid` — enough for session attribution and subagent separation.

## Consequences for the build

1. The **hook-activity insight** (where-view) is unsourced as specced — decide at the where-view greybox: self-instrument via a hook POSTing to the listener, or drop it.
2. **Attribute variance across CLI versions is the norm** (`tool_use_id`, `query_source`, usage extras). The ingest contract must treat attributes as optional-by-default; only `event.name` + `session.id` are load-bearing.
3. The listener must accept **chunked** OTLP/HTTP JSON — trivial with a real HTTP server, but the capture stub's first version silently read zero-byte bodies; worth a regression test.
4. OTEL events carry **account identifiers and (with the detail flags) prompt text and tool inputs** — local-only storage stance already covers this, but exports/screenshots must treat the OTEL tables as sensitive.
