# ADR-0003: Backend stack — `claude -p` on subscription, stdlib listener, zero pip deps

**Date:** 2026-08-01 · **Status:** accepted · **Decides:** Decide the backend stack

## Context

ccwhere shipped with zero runtime dependencies as an explicit PRD success metric; the hindsight definition carried "stdlib-only" as a re-litigation candidate because of the model pipeline and the always-on listener. The verified payload shapes (`definition/ingest-schema-verification.md`) fix what the listener must do: accept chunked OTLP/HTTP JSON on `/v1/logs` + `/v1/metrics`, treat every attribute as optional (variance across CLI versions is the norm), per-row fault tolerance, always return 200. The eval harness (`ideation/eval-why-extractability/`) already drives the pinned model via `claude -p`.

## Decision

**Model runner: `claude -p` on the operator's subscription**, invoking the model pinned by ADR-0002. Zero marginal cost, zero dependencies, no key management, and identical transport to the eval — so the measured eval behaviour transfers directly. For strangers later this is the *stronger* story: any hindsight user is by definition a Claude Code user with `claude` installed and authenticated (subscription or API key), so there is no setup and no separate bill. Two consequences are accepted and mitigated:

- **Self-observation:** `claude -p` analysis runs create their own transcripts under `~/.claude`; hindsight must exclude them via the planned per-view project include/exclude config. This is a named requirement on the config surface, not an optional nicety.
- **Limits and the revisit trigger:** hitting subscription usage limits is a designed-for pause, not a failure — transcripts persist on disk and the listener keeps ingesting, so unanalysed sessions simply wait for the next run after the reset. The pipeline must fail gracefully: recognise the limit error, leave sessions marked unanalysed, resume cleanly. Switching transport to the Anthropic SDK on an API key happens only if the operator judges the waiting intolerable — an operator call, not an automatic threshold. ADR-0002 already declares transport an implementation detail — prompts and model are unchanged by a transport swap, so no eval regression is required, though a spot-check is cheap and sensible.

**Listener: stdlib `http.server`.** The verified requirements are deliberately dumb and fully covered. A validation framework (FastAPI/pydantic) is rejected on the merits, not just on weight: strict validation is the *wrong behaviour* for version-varying telemetry whose contract is "optional-by-default, keep whatever arrives". Chunked transfer-encoding is handled explicitly and guarded by a regression test (the capture stub's first version silently read zero-byte bodies).

**Dependencies: zero pip packages for pipeline + listener, as an ADR-gated default.** Everything v1 needs is stdlib: `sqlite3`, `hashlib` (content-addressed blobs), `difflib` (the 0.6 fuzzy resolution ladder), `json`, `http.server`, `subprocess`. Any future exception requires an ADR stating why. **The UI stack is explicitly out of scope** — the Design phase owns it; a frontend framework chosen there does not violate this decision.

## Consequences

- Install remains clone-and-run; the launchd-managed listener has no third-party packages to break silently on a Python upgrade.
- Marginal model cost is $0 for the operator; the open-source cost story is "bring your existing Claude Code auth".
- Backfill pace is bounded by subscription limits; waiting for the reset is the default response, and the switch condition above is an operator judgement rather than a threshold — the decision degrades gracefully instead of being re-litigated ad hoc.
- `to-spec` can now own the DB schema and pipeline detail — extraction contract (ADR-0002) and stack are both settled.
