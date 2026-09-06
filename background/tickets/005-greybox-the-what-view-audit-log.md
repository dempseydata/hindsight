# #5 Greybox the what-view (audit log)

state: closed · labels: wayfinder:prototype · opened: 2026-08-01 · closed: 2026-08-03

## Question

Is the settled audit format (one file per project, newest first, ADR counts not contents) actually *reviewable* at real volume? Greybox with real dogfood data (`local-data/dogfood-hindsight-audit.md`, 18 entries; extend via harness if more volume needed). No styling — density, hierarchy, scanability only. Impeccable hooks off.

Part of #1



---

**comment · 2026-08-03**

Greybox built — awaiting review (HITL: the reviewability verdict is yours).

**Generator:** `build/prototype-what-view.py` (throwaway, stdlib only). Run `python3 build/prototype-what-view.py`, then open `local-data/prototypes/what-view-greybox.html` in a browser (session-derived content, so the HTML stays in local-data, uncommitted).

**Data:** real backfill audit entries, not the 18-entry dogfood file — career-ops (53 entries, the real-volume test), hindsight (24), my-os-my-logs (17), career-ops-CLI (12). Project switcher in the bottom bar; `←`/`→` or the arrows cycle variants; state lives in the URL.

Three structurally different takes on the settled format, all greyscale:

- **A — Journal (settled format rendered literally):** day headers, full entries newest-first, Did/Decided/Setup-changes in full. Tests whether the format survives at 53 entries or becomes a wall.
- **B — Ledger (scan then expand):** one collapsed row per session — date · title · counts (n did · n decided · n ADR) — click to read. The whole month fits on ~2 screens.
- **C — Decisions-led:** sticky date/title index on the left; **Decided** items lead each entry, Did compressed behind an expander. Tests whether decisions are the real review payload.

Screenshots at career-ops volume: `local-data/prototypes/variant-{a,b,c}.png`.

The interesting feedback is the usual prototype kind — "B's rows with C's decisions-first expansion" is a legitimate answer. Also worth judging while in there: whether ADR counts (visible in row badges / entry metas) earn their place, and what the ~half of sessions with 0 decided items should look like.


---

**comment · 2026-08-03**

**Resolution: variant B — Ledger, scan then expand.**

The settled per-project/newest-first *content* format survives at real volume (53 entries), but the presentation is B's: one collapsed row per session — date · title · counts — expanding to the full Did/Decided/Setup entry. Variant A (the format rendered literally as a journal) is a wall at this volume; C's decisions-first inversion lost to B.

Two riders from the review, both flowing to the Design-inputs bundle rather than reopening the format:

1. **Per-entry project identity** — each row should carry which project it came from, for scanning. Note the tension with "one file per project": a project chip on every row implies the ledger is (or can be) a cross-project surface, so the row schema includes project even if the storage stays per-project.
2. **Filtering** — wanted, and probably a *shared header* concern across views rather than a what-view feature; sharpens once the why-view and where-view greyboxes exist.

Left open deliberately: whether ADR counts earn their badge space, and the treatment of zero-decision sessions — judge those in the styled build, not another greybox.

**Primary source:** the prototype lives on the throwaway branch `prototype/what-view-greybox` (throwaway branch in the private working repo — not exported) (`build/prototype-what-view.py`); master keeps only this verdict.

