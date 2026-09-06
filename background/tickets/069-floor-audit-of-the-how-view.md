# #69 Floor audit of the how-view

state: closed · labels: wayfinder:task · opened: 2026-08-29 · closed: 2026-08-29

## Question

Run `/impeccable audit` over the styled `/how` view (landed in #65) and resolve what it flags against the floor — the v1 build did the same for the what/where views in #47. The direction contract (`design/tokens.css`, DESIGN.md) is not up for change; findings are fixed in `build/serve.py` HOW_CSS or recorded as accepted with a reason.


---

**comment · 2026-08-29**

## Resolution

`/impeccable audit` (4.1.1) run over the styled `/how` view — all three states rendered from real data (`local-data/hindsight.db`) and audited as shipped HTML, not as Python source: `hindsight` (valid, 5 stages), `thisisme` (valid), and a deliberately mangled declaration for the invalid lane.

**The detector was run at full fidelity, which changes what this audit is worth.** Out of the box it reports `DEGRADED — HTML parser modules unavailable`, falls back to regex, and states plainly that *"custom properties, selector matching and computed contrast are NOT evaluated; findings are an undercount, not a clean bill of health"*. Since the how-view carries its stage colour through an inline `--stage` custom property, the degraded scan cannot see the thing this ticket exists to judge. The four parser modules were installed **outside the repo** (scratchpad + a symlink into the plugin cache, both removed afterwards) — ADR-0008's no-npm rule is about the product, and nothing was added to it. Degraded run: 10 findings. Full run: 154. #47's "zero findings" was almost certainly a degraded run and should be read as such.

### Floor verdict: one violation, fixed

**Fixed** — the off-script heading carried the session-boundary exclusion *inside* the `h2`, which `#how aside h2` styles `600 10px mono, uppercase, letter-spacing .05em`. Two things went wrong at once:

1. It uppercased command **identifiers**. `/model` rendered as `/MODEL`, `/mattpocock-skills:wayfinder` as `/MATTPOCOCK-SKILLS:WAYFINDER` — names that do not exist. A view whose entire job is reporting which commands were typed must not alter their case.
2. At 260px the clause wrapped **four lines** of all-caps letterspaced 10px type, breaking mid-identifier. Label styling applied to a sentence.

The clause now rides a `.mk` note beneath the heading (11px mono, `--o-dim`, natural case); the `h2` is back to one line. Reuses the existing `.mk` style rather than adding a class — `margin-top` → `margin` so it works as a `<p>`. **tokens.css untouched**, direction contract intact. Commit 20dc519. 38/38 serve+how tests pass.

This is the honesty grammar, not taste: DESIGN.md's Mono-Datum Rule makes identifiers monospace so they read as literal, and rendering `/model` as `/MODEL` breaks that for the same reason drawing an unknown as zero would.

### Floor rules verified — every ratio computed at the size actually used

| Floor rule | Verdict |
|---|---|
| Named tokens only | ✅ every colour via `var(--o-*)`; the inline `_hue()` style carries a **token reference** (`--stage: var(--o-stage-N)`), never a literal — data-driven per-row colour with zero JS |
| Semantic roles, AA `-text` weights on text | ✅ `.warn b`/`.warn code`/`.stale` → `--o-caution-text` (12.04:1 on ground, 10.97:1 on panel) |
| Red pairs with blue, never green | ✅ nothing green; how-view adds no semantic hue |
| AA text at size used | ✅ lowest pairing is the `now` badge, `--o-accent` on panel at **6.72:1**; 10px labels are `--o-dim` at 7.02:1 (panel) / 7.72:1 (ground). `--o-faint` (3.99:1) appears only as a hover **border**, never text |
| Accent never body text / large surfaces | ✅ selector links, `aria-current` selector, the `now` badge outline |
| Chart data ink own palette | ✅ the how-view renders no chart at all |
| Long-form line-height ≥ 1.50 | ✅ body 13/1.5 inherited; `.off` list 11/1.6 |
| No runtime font fetches | ✅ system stacks |
| **Stage hues as non-text marks (ADR-0007 amendment)** | ✅ all five clear WCAG 1.4.11's 3:1 against **both** grounds by a wide margin — stage-1 8.26/9.07, stage-2 6.53/7.17, stage-3 6.69/7.34, stage-4 7.92/8.70, stage-5 10.35/11.37; `stage-off` 3.99/4.38. Pairwise ΔE76 ≥ 26.1, so five are distinguishable |

### The gold-near-caution question (#71 deferred it here) — **accepted, no change**

`--o-stage-5` #d4c95a vs `--o-caution` #e3b859 is ΔE76 **15.5**, hues 100.2° vs 84.7° — genuinely close in isolation, which is why #71 declined to settle it by eye.

It resolves on **co-occurrence**, not distance:

- `--o-caution` renders in exactly one place: the invalid-declaration banner. In the invalid state the declaration has **no stages**, so `_sessions()` renders every band on `--o-stage-off` grey and **no stage hue appears on screen at all**. Screenshot-verified. The two can never be co-present.
- The other caution call site, the `stale` marker, is `--o-caution-text` #eac878 as **inline text inside the status card**, which carries no stage rule; gold appears only as a 3px **vertical rule** on a band below it. Different weight, geometry and role, ΔE 16.7.
- `--o-compare` amber (the nearest other warm hue, ΔE 24.1) never renders here — the how-view has no chart.

So the ADR-0007 amendment stands as written.

**Sharper adjacency found, recorded not fixed:** `--o-stage-2` violet #a98cf5 vs `--o-accent` periwinkle #7c9bff is ΔE76 **17.4** — closer *in kind* than the gold pair, and unlike gold the two genuinely do co-occur (the `now` badge is accent, and it sits inside a run band whose left rule is the stage hue). Acceptable today: the badge is an outlined text chip, the rule a solid 3px bar. Worth knowing for anyone who redraws the palette.

### Accepted with reason (not floor rules)

| Detector finding | Count | Why it stands |
|---|---|---|
| `side-tab` "3px left border + 6px radius" | 21–81 | The rule **is** the data encoding — which stage this band belongs to — not a decorative accent. Decided in #71, ADR-0007 amended. Hues verified above. The detector's own exemptions cover status/alert regions and tab context but have no concept of a categorical row marker |
| `undersized-ui-text` 10px | 12 | DESIGN.md's documented Label tier, shipped since v1 (#47). Contrast 7.02–7.72:1 |
| `tiny-text` 11px body | 57 | Product-wide since v1 — the what/where baseline scan shows the same finding. Dense instrument deck read at desk distance |
| `flat-type-hierarchy` 10/11/12/13/15px | 2 | Deliberate and documented: *"hierarchy by weight and position, not size"*. The what/where baseline reports the same 1.4:1 |
| `em-dash-overuse` (advisory) | 1 | Fires on the **model-written status narrative**, not the CSS. Editing `status-v1` to chase cadence would invalidate the frozen eval baseline (#67/#68, r8/r9 ACCEPT) for a stylistic advisory the scorer does not measure. Left alone |

### Audit health score

| # | Dimension | Score | Key finding |
|---|---|---|---|
| 1 | Accessibility | 4/4 | AA fully met; every control is a native `<a>` or `<summary>`, so #47's mouse-only P2 has no analogue here |
| 2 | Performance | 4/4 | **Zero JavaScript** — the only view in the product with none. 20KB for 88 sessions / 346 events; one paint-only transition |
| 3 | Responsive | 3/4 | Selector links ~22px tall, below the 44px touch guidance — #47's accepted desktop-only posture. Layout itself is sound |
| 4 | Theming | 4/4 | Full token system incl. the inline `--stage` token reference; `color-scheme: dark`, explicit body background |
| 5 | Implementation integrity | 4/4 | Coherent with the Indigo system; every residual finding traces to a recorded decision |
| **Total** | | **19/20** | Excellent |

**Responsive, measured not eyeballed:** at a 500px viewport `scrollWidth == clientWidth` with **zero** elements extending past the edge; the 760px breakpoint collapses both grids cleanly. An early 420px screenshot appeared to clip badly — that was a **headless artefact** (Chrome clamps its viewport to 500px minimum and rendered 500px of page into a 420px image), not a layout bug. Below 500px is genuinely untested by this tool; the layout is single-column `minmax(0, 1fr)` with `word-break` on the long fields, so it should hold, but I am not claiming it verified.

**Positive findings worth keeping:** absence is drawn as absence throughout — stages with no events render as dashed `nothing observed` cards rather than vanishing; a stale narrative is marked stale rather than hidden; an invalid declaration renders its error and falls back to the unbucketed lane rather than failing silent. `--o-stage-off` grey on the unbucketed lane is honest by the same grammar: grey *is* the no-stage colour, declared as such in tokens.css.

**No P1/P2 left open, no follow-up tickets filed.** DESIGN.md needs no re-derivation — no token, type size or component changed.


