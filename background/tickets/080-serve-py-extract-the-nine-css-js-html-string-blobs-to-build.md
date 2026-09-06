# #80 serve.py: extract the nine CSS/JS/HTML string blobs to build/assets/, read per request (review C1)

state: closed · labels: ready-for-agent · opened: 2026-08-30 · closed: 2026-08-30

> *Settled by grilling on 2026-08-30 (architecture review, candidate C1). Implement in a fresh session.*

## Summary

47% of `build/serve.py` (~660 of 1414 lines) is CSS/JS/HTML inside plain `"""` string literals — invisible to every linter, editor and test. Extract the nine blobs to asset files read from disk at render time, over the same seam `design/tokens.css` already uses (`TOKENS_CSS.read_text()` at render, ADR-0008-blessed). **This change ships byte-identical pages.**

## Established facts (verified during review)

- All nine constants (`CHROME_CSS`, `WHAT_CSS`, `WHERE_CSS`, `HOW_CSS`, `CHROME_JS`, `WHAT_JS`, `WHERE_JS`, `WHAT_HTML`, `WHERE_HTML`) are plain strings — no f-string interpolation. Data crosses separately (`const WHAT = {_blob(...)};` prepended at serve.py:1306/1309), so the JS files are pure static.
- `tokens.css` is read per request inside `render` (serve.py:1288) — the seam's cadence is already edit-and-refresh.
- `test_serve.py` touches the blobs only through the rendered body (`assertIn(..., body)`) — extraction breaks no test when content is inlined unchanged.
- Trap: the JS contains `·`-style escapes that Python evaluates at parse time. The files must be produced by **dumping the evaluated constant values**, never by copy-pasting source text.

## Decisions (all settled — do not re-litigate)

1. **Per-request reads**, matching the tokens.css seam exactly. No read-at-import (that re-creates the prompt-file staleness problem for zero gain on localhost).
2. **Flat `build/assets/`, one file per constant, nine files**: `chrome.css`, `what.css`, `where.css`, `how.css`, `chrome.js`, `what.js`, `where.js`, `what.html`, `where.html`. `design/tokens.css` stays exactly where it is — it is the contract.
3. **A two-line `_asset(name)` helper** — `(ASSETS / name).read_text()` — called at the six composition sites in `render`/`how_html`; the nine constants are deleted outright. No per-blob functions.
4. **Impeccable hooks stay on** (this is real build). Findings on the newly-visible files are queued as tickets, never fixed inline.
5. **Docs**: one-line amendment to ADR-0008 recording the asset files; no new ADR; no CONTEXT.md change ("asset" is not domain vocabulary).

## Method

1. One-off script imports the current `serve.py` and writes each evaluated constant to its file under `build/assets/`.
2. Edit `serve.py`: delete the nine constants, add `_asset()`, rewrite the six composition sites (`render` at ~1296/1305–1309/1325/1343, `how_html` path at ~1296).
3. Amend ADR-0008.

## Acceptance criteria

- [ ] With the server on the same DB: `curl` of `/` (what), the where view, the how view and one how-view project page is **byte-identical** before vs after (empty diff). This is the whole proof.
- [ ] Full test suite green with **zero test edits**.
- [ ] `serve.py` ≈ 750 lines; nine files under `build/assets/`; `design/tokens.css` untouched.
- [ ] ADR-0008 carries the one-line amendment.

## Out of scope (candidates from the same review, separate tickets if picked)

- JS dedup — two escape functions, window/project predicate ×2, accumulate-and-spark hunk ×3, two bar-chart renderers, the three-region grid column coupling (review C7).
- Migrating `ServerTest` asserts from rendered bytes to data dicts (review C6).
- Any styling change. The operator's colour review of the current UI is a Design-phase follow-up once the CSS is inspectable — raise separately.



---

**comment · 2026-08-30**

Implemented in 6e7aca0. All acceptance criteria met: byte-identical curl diff on /what, /where, /how and /how?p=hindsight (verified against a DB copy, old code vs new); full suite green (142 tests, zero test edits); serve.py 1414 → 657 lines; nine files under build/assets/; design/tokens.css untouched; ADR-0008 amended. Two-axis review: Spec — fully conformant, no findings. Standards — no hard violations; two judgement calls fixed pre-commit (floor-rules comment relocated in serve.py, 'blob' wording dropped to avoid glossary drift). Out-of-scope candidates (JS dedup, ServerTest data-dict asserts, colour review) remain unticketed per the issue.

