# #16 Ingest listener: OTLP in, SQLite rows out

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-16

## Parent

#15

## What to build

The single sanctioned background process: a stdlib `http.server` OTLP listener on `/v1/logs` + `/v1/metrics`, launchd-managed, writing `otel_events` and `otel_metrics` rows to the SQLite store. Real Claude Code payloads — chunked transfer-encoding, version-varying attributes, the odd malformed row — arrive and persist; nothing crashes the process and the client always gets 200. Creates the store file and its own tables idempotently. Only `event.name` + `session.id` are load-bearing; every other attribute is optional-by-default, kept as JSON (ADR-0001, ADR-0003, verified shapes in the ingest-schema-verification doc).

## Acceptance criteria

- [ ] Listener receives a real captured OTLP logs payload with chunked transfer encoding and persists event rows (the zero-byte-body regression is a named test)
- [ ] Metrics payload persists with name, timestamp, value, and attributes JSON
- [ ] A malformed row is counted-and-skipped per-row; the rest of the batch persists; response is still 200
- [ ] Unknown event names and missing attributes persist without error
- [ ] launchd plist installs and the listener survives restart
- [ ] Seam-1 tests run against the listener on a test port with no network beyond localhost
- [ ] Zero pip dependencies

## Blocked by

- None — can start immediately.


---

**comment · 2026-08-16**

Implemented in 9be4f1d (build/listener.py + build/test_listener.py). All acceptance criteria verified: chunked real-payload ingest with the zero-byte-body regression as a named test; metrics rows with name/timestamp/value/attributes JSON; per-row count-and-skip with the batch's good rows persisting (container-level rollback found in review, fixed, regression-tested); unknown events and missing attributes persist; launchd plist installed with KeepAlive respawn verified live; 11 seam-1 tests on an ephemeral localhost port; zero pip dependencies. Listener is running now; telemetry env enabled user-level 2026-08-16 — the coverage window starts today.

