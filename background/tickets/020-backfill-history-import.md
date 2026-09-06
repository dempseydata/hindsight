# #20 Backfill history import

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-17

## Parent

#15

## What to build

The full-history backfill's cached model outputs (207 sessions, findings + audit entries) are assembled into the store under their original prompt version — import, not re-extraction, so history costs no second pass through subscription limits. Sessions the backfill left partial, and sessions post-dating its snapshot, are left pending for fresh analysis by the ordinary run.

## Acceptance criteria

- [ ] Backfill sessions appear in sessions/audit/findings/evidence with their original prompt version and model
- [ ] Evidence statuses and spans survive the import (resolution rate matches the backfill's recorded 97%)
- [ ] Partial and post-snapshot sessions are marked pending, not imported
- [ ] Re-running the import is idempotent
- [ ] A subsequent analysis run picks up pending sessions without touching imported rows

## Blocked by

- #18


---

**comment · 2026-08-17**

Landed in 272a343. All acceptance criteria verified against the real store: 207 done sessions imported under what-v1/why-v1 (audit 152 + 55 SKIP, matching the backfill's record), 187 findings, evidence 326/336 (97.0%) vs the recorded 97% baseline, 3 partial sessions left pending, re-run is a no-op, and the seam tests cover a subsequent analysis run processing pending sessions without touching imported rows.

