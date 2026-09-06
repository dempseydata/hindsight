# #53 Fixed-width main tables on /what and /where — full browser width is unwieldy on big screens

state: closed · labels: needs-triage · opened: 2026-08-26 · closed: 2026-08-26

The main tables on both views stretch to full browser width; on a large monitor the eye-travel between columns makes rows hard to scan. Change to a fixed (max-)width for ease of use.

Open questions for triage:
- Cap the whole page (`main` max-width) or just the tables? A page cap keeps the header chart and panels aligned with the tables.
- What width? Observability tools typically cap dense tables around 1100–1400px.
- Centre the capped content or keep it left-anchored?



---

**comment · 2026-08-26**

Shipped in dbc1f42: page-level cap — body max-width 1280px, centred, html painted --o-bg so the gutters match. Answers the triage questions: whole-page cap (keeps chart/chips/panels aligned with the tables), 1280px, centred. Verified at a 2200px viewport on /where.

