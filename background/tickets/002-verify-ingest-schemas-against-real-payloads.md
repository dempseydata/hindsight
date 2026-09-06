# #2 Verify ingest schemas against real payloads

state: closed · labels: wayfinder:task · opened: 2026-08-01 · closed: 2026-08-01

## Question

Are the OTEL event names/attributes and JSONL usage shapes what `definition/command-centre-review.md` claims (sourced from a third-party doc, untrusted)? Enable OTEL locally against a capture stub, collect real `/v1/logs` + `/v1/metrics` payloads, diff against the review's schema claims, and record the verified shapes. Also confirm JSONL `message.usage` fields and `tool_use`/`tool_result` pairing assumptions on current-format sessions.

Part of #1



---

**comment · 2026-08-01**

## Resolution

Verified against real payloads (OTLP capture stub + telemetry-enabled probe session, CLI 2.1.91; JSONL across 2.1.91/2.1.209/2.1.220) and cross-checked with the official monitoring docs. Full record: [`definition/ingest-schema-verification.md`](../definition/ingest-schema-verification.md) (commit 7df019e). Raw captures in `local-data/otel-capture/` (gitignored — contain account identifiers).

**Confirmed:** env-var config mechanism and `/v1/logs` + `/v1/metrics` OTLP/HTTP JSON endpoints; `tool_decision` with accept/reject + source; delta-temporality monotonic sums (`SUM(value)` correct); `claude_code.{session,cost,token,lines_of_code,code_edit_tool}` metrics live; JSONL `message.usage` carries all four token fields on every version checked; `tool_use`/`tool_result` pairing by `tool_use_id` is airtight — 507/507 paired across three large sessions, `is_error` present. `api_error` (with `attempt`), MCP attribution, and commit/PR counters are officially documented but weren't exercised by the probe.

**Corrected (the untrusted doc was wrong):**
1. **Hook execution timings — falsified.** Hooks were active during the probe; no hook event exists in OTEL logs, metrics, or the official event list. The where-view "hook activity" insight has no OTEL source: either self-instrument (a hook POSTing its own timing to the listener) or drop it. Decide at the where-view greybox.
2. **Compaction — no dedicated event.** Only inferable from `query_source: "compact"` on `api_request`/`assistant_response`, and that attribute is absent on older CLIs (not present at 2.1.91). Version-dependent, not guaranteed.

**New build constraints surfaced:** OTLP arrives with chunked transfer encoding (a naive reader gets zero-byte bodies — regression-test this); attributes vary by CLI version, so only `event.name` + `session.id` may be load-bearing (`tool_use_id` is missing from 2.1.91 `tool_result` events — OTEL↔JSONL joins are version-gated); JSONL record types grow over time (`ai-title`, `custom-title`, `file-history-delta`, …) — count-and-skip unknown types; OTEL rows carry account identifiers and, with detail flags, prompt/tool text — treat those tables as sensitive. Bonus: OTEL `api_request` carries `cost_usd`, which JSONL lacks.


