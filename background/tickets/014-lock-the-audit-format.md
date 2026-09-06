# #14 Lock the audit format

state: closed · labels: wayfinder:grilling · opened: 2026-08-01 · closed: 2026-08-16

## Question

Final what-view format decision: granularity, entry shape, per-project file conventions, ADR-count semantics — informed by the greybox verdict and at least review #1. Demotion path per red-team if reviews fail.

Part of #1



---

**comment · 2026-08-16**

**Resolution (2026-08-16): format locked — ADR-0004, plus an ADR-0002 amendment.**

- **Granularity:** one entry per session, flat, no revisit trigger. Day-level roll-ups are render-time grouping, never storage granularity.
- **Entry shape:** the four-section shape (title / Did / Decided / Setup changes) stands unchanged; no locators added to the what-pass. One convention joins the locked format ([ADR-0002 amendment](../../docs/adr/0002-extraction-contract.md)): when rationale for a decision was stated in-session, the Decided line carries it — close paraphrase or quote, nothing invented when none was stated. This is the fix for review #1's missing-culling-rationale finding, and its close-paraphrase wording also repairs review #2's fabricated clause and the loose-paraphrase tendency. Prompt-level, riding with the existing repairs (firmer SKIP, anti-capture), gated by the frozen eval regression.
- **Storage:** "one file per project" retired. Canonical store is one structured audit table keyed by session (project, date, skip, entry markdown), exact schema owned by to-spec. The what-view is a cross-project ledger; per-project separation is a query. No markdown export specified.
- **ADR-count semantics:** mechanical, never model-extracted — distinct files under docs/adr/ created or modified during the session, from tool events; semantics "ADRs touched". Whether it renders as a badge stays with the styled build (greybox rider).
- **Demotion path:** moot — both reviews done and passed; the two-week test closed with assumption 1 surviving.

**Primary source:** [ADR-0004](../../docs/adr/0004-audit-format.md).

