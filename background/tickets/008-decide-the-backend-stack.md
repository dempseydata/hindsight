# #8 Decide the backend stack

state: closed · labels: wayfinder:grilling · opened: 2026-08-01 · closed: 2026-08-01

## Question

Pipeline + listener stack: ccwhere's stdlib-only posture (zero pip deps, OTLP listener via stdlib http.server) vs FastAPI-style convenience? Includes the model-runner decision: `claude -p` on subscription vs API key, and what that means for cost and for strangers later. Informed by verified payload shapes.

Part of #1



---

**comment · 2026-08-01**

## Resolution

Recorded as [ADR-0003](../../docs/adr/0003-backend-stack.md) (commit 77f36a9). Three decisions, grilled with the operator:

**Model runner: `claude -p` on subscription.** Zero marginal cost, zero dependencies, identical transport to the eval harness — so the eval evidence transfers directly. Stronger for strangers, not weaker: any hindsight user already has `claude` installed and authenticated. Accepted consequences: analysis runs create their own transcripts and **must be excluded via the per-view include/exclude config** (named config requirement); revisit trigger is backfill/routine runs exhausting subscription limits → swap transport to the API SDK (ADR-0002 already declares transport an implementation detail; no eval regression needed for a transport swap).

**Listener: stdlib `http.server`.** The verified requirements (chunked OTLP/HTTP JSON on two paths, always-200, per-row fault tolerance) are fully covered. FastAPI rejected on the merits: strict validation is the *wrong behaviour* for version-varying telemetry whose contract is optional-by-default. Chunked bodies handled explicitly with the regression test flagged in the schema verification.

**Dependencies: zero pip packages for pipeline + listener, ADR-gated exceptions.** Everything v1 needs is stdlib (`sqlite3`, `hashlib`, `difflib`, `json`, `http.server`, `subprocess`). **UI stack explicitly excluded** — the Design phase owns it; this decision does not bind it.

Unblocks `to-spec` ownership of the DB schema and pipeline detail: extraction contract (ADR-0002) and stack are both now settled.


---

**comment · 2026-08-01**

Resolved — see resolution comment above. Decision indexed on the map.


---

**comment · 2026-08-01**

Amendment (commit 1ea0041): limit exhaustion is a designed pause, not the swap trigger — transcripts persist and unanalysed sessions wait for the reset; the pipeline must fail gracefully and resume. Switching to the API SDK is an operator judgement ("waiting became intolerable"), not an automatic threshold. ADR-0003 and the map updated to match.

