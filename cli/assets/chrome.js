
// Filter state shared by what and where (ADR-0028): the header visual is
// per view (a session heatmap on what, the token chart on where — each view
// renders it in its own onFilter callback), the state is not. The selection is
// a set of days; a preset range applies only while the set is empty.
const S = { active: new Set(), days: new Set(), tFrom: null, tTo: null, hideCR: false, preset: "14", reveal: false };
const subs = [];
const fmt = n => n == null ? "\u2014" : n >= 1e9 ? (n / 1e9).toFixed(1) + "B"
  : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : "" + n;
const inWin = d => S.days.size ? S.days.has(d)
  : !S.tFrom || (d >= S.tFrom && d <= (S.tTo || S.tFrom));
const inProj = p => S.active.size === 0 || S.active.has(p);
// the last day of the window, for coverage notes; null when it is "all"
const winEnd = () => S.days.size ? [...S.days].sort().at(-1) : S.tTo || S.tFrom;
window.hs = { S, DATA, fmt, inWin, inProj, winEnd, addDays, mount, selDays, priorWin, statCard,
  onFilter: f => subs.push(f) };

function addDays(d, n) {
  const t = new Date(d + "T00:00:00Z");
  t.setUTCDate(t.getUTCDate() + n);
  return t.toISOString().slice(0, 10);
}
// Stat cards (ADR-0029 §2, §5, §6; ADR-0030 §7, §8), one grammar on both
// views; `first` is the view's first synced day. The selected days, in date
// order: the set, else the preset range, else every synced day.
function selDays(first) {
  if (S.days.size) return [...S.days].sort();
  const out = [];
  for (let d = S.tFrom || first; d && d <= (S.tTo || DATA.range[1]); d = addDays(d, 1)) out.push(d);
  return out;
}
// the equal-length prior window as a day test, or null: none under a day set
// or all, and none unless it lies wholly inside the synced range
function priorWin(first) {
  if (S.days.size || !S.tFrom || !first) return null;
  const n = (Date.parse(S.tTo) - Date.parse(S.tFrom)) / 864e5 + 1;
  const from = addDays(S.tFrom, -n), to = addDays(S.tFrom, -1);
  if (from < first) return null;
  return d => d >= from && d <= to;
}
// a rounded percent against the prior window; `—` with none or nothing in it,
// no arrow at 0%. Only a cost card hues it (up problem, down ok), never caution
function delta(cur, prev, cost) {
  if (!prev) return '<span class="o-delta">\u2014</span>';
  const p = Math.round((cur - prev) / prev * 100), up = p > 0;
  if (!p) return '<span class="o-delta">0%</span>';
  return `<span class="o-delta${cost ? (up ? " o-up" : " o-down") : ""}">${up ? "+" : ""}${p}%`
    + `<span data-icon="arrow-${up ? "up" : "down"}" aria-hidden="true">${up ? "\u25b2" : "\u25bc"}</span></span>`;
}
// the trend spark: vals is one number per selected day, null for a gap
// (ADR-0030 §7). Own peak; a line over a washed area per contiguous run of
// days, a lone day a dot, so no trend is drawn across an unselected day or a gap
function trendSpark(days, vals) {
  const W = 100, H = 24, peak = Math.max(1, ...vals.filter(v => v != null));
  const x = i => (days.length > 1 ? i / (days.length - 1) * W : W / 2).toFixed(1);
  const y = i => (H - 1 - vals[i] / peak * (H - 2)).toFixed(1);
  const runs = [];
  let run = null;
  days.forEach((d, i) => {
    if (vals[i] == null) { run = null; return; }
    if (!run || addDays(days[i - 1], 1) !== d) runs.push(run = []);
    run.push(i);
  });
  const out = runs.map(r => {
    const pts = r.map(i => `${x(i)} ${y(i)}`).join("L");
    return r.length === 1 ? `<path class="dot" d="M${pts}h0"/>`
      : `<path class="area" d="M${x(r[0])} ${H}L${pts}L${x(r.at(-1))} ${H}Z"/><path class="line" d="M${pts}"/>`;
  }).join("");
  return `<svg class="o-trend-spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">${out}</svg>`;
}
// c: {label, value, prev, cost, dim, days, vals}; what's radio cards add k and pressed
function statCard(c) {
  const tag = c.k ? "button" : "div";
  return `<${tag} class="o-stat-card"${c.k ? ` data-k="${c.k}" aria-pressed="${c.pressed}"` : ""}>`
    + `<span class="o-stat-head"><span>${c.label}</span>${delta(c.value, c.prev, c.cost)}</span>`
    + `<b>${fmt(c.value)}</b><small>${c.dim || "\u00a0"}</small>${trendSpark(c.days, c.vals)}</${tag}>`;
}
function applyPreset(w) {
  S.preset = w;
  S.days.clear();
  // empty db: no last day to anchor to — presets degrade to "all" (ticket #50)
  if (w === "all" || !DATA.range[1]) S.tFrom = S.tTo = null;
  else { S.tTo = DATA.range[1]; S.tFrom = addDays(S.tTo, 1 - +w); }
  changed();
}
let lastClicked = null;   // the anchor of a shift-click range; a gesture, not filter state
function toggleDay(d, range) {
  S.preset = S.tFrom = S.tTo = null;   // a day click overrides the preset; an emptied set reads all
  if (range && lastClicked) {
    const [a, b] = [lastClicked, d].sort();
    for (let x = a; x <= b; x = addDays(x, 1)) S.days.add(x);
  } else S.days.has(d) ? S.days.delete(d) : S.days.add(d);
  lastClicked = d;
  changed();
}
// the header visual's mount: the view hands over its svg (or a note); the
// scroll position survives a re-render, and the first render lands newest-right
let scrolled = false;
function mount(html) {
  const ch = document.getElementById("chart");
  const sl = ch.scrollLeft;
  ch.innerHTML = html;
  ch.scrollLeft = scrolled ? sl : ch.scrollWidth;
  scrolled = true;
}
function syncCtl() {
  document.querySelectorAll("#chips button").forEach(b => {
    b.classList.toggle("on", S.active.has(b.dataset.p));
    b.setAttribute("aria-pressed", S.active.has(b.dataset.p));
  });
  document.querySelectorAll("#ctl button[data-w]").forEach(b => {
    b.classList.toggle("on", b.dataset.w === S.preset);
    b.setAttribute("aria-pressed", b.dataset.w === S.preset);
  });
  document.getElementById("chips").classList.toggle("reveal", S.reveal);
  document.getElementById("reveal")?.setAttribute("aria-pressed", S.reveal);
  // the how-view is one project, chosen by ?p= (issue #10): the nav link
  // carries the active chip. ponytail: first of several; how can't show more
  const [p] = S.active;
  document.querySelector('header nav a[href^="/how"]').href = p ? `/how?p=${encodeURIComponent(p)}` : "/how";
}
function changed() { syncCtl(); subs.forEach(f => f(S)); save(); }
// The filter survives the what ↔ where navigation (issue #10): saved per tab
// in sessionStorage on every change, restored ahead of the first render. Gone
// when the tab closes; a reload keeps the filter instead of resetting — accepted.
function save() {
  try { sessionStorage.setItem("filter", JSON.stringify({ ...S, active: [...S.active], days: [...S.days] })); }
  catch { /* private mode etc. — the filter just won't survive the tab */ }
}
function restore() {
  try {
    const f = JSON.parse(sessionStorage.getItem("filter"));
    if (!f) return false;
    S.reveal = !!f.reveal;
    // only a chip on show may come back active (ADR-0009): a hidden project's
    // chip is dropped unless the reveal state that showed it is restored too
    const shown = new Set([...document.querySelectorAll(
      S.reveal ? "#chips button" : "#chips button:not([data-hidden])")].map(b => b.dataset.p));
    S.active = new Set(f.active.filter(p => shown.has(p)));
    S.hideCR = !!f.hideCR;
    document.getElementById("hidecr").checked = S.hideCR;
    if (f.preset) applyPreset(f.preset);   // re-anchor to today's last day
    else { S.preset = null; S.tFrom = f.tFrom; S.tTo = f.tTo; S.days = new Set(f.days || []); changed(); }
    return true;
  } catch { return false; }
}
document.addEventListener("click", e => {
  if (e.target.closest("#reveal")) {
    S.reveal = !S.reveal;
    // un-revealing must never leave an invisible active filter (ADR-0009)
    if (!S.reveal) document.querySelectorAll("#chips button[data-hidden]").forEach(
      b => S.active.delete(b.dataset.p));
    changed(); return;
  }
  const b = e.target.closest("#chips button");
  if (b) {
    S.active.has(b.dataset.p) ? S.active.delete(b.dataset.p) : S.active.add(b.dataset.p);
    changed(); return;
  }
  const pw = e.target.closest("#ctl button[data-w]");
  if (pw) { applyPreset(pw.dataset.w); return; }
  if (e.target.closest("#tclear")) { applyPreset("all"); return; }
  const col = e.target.closest("#chart .col");
  if (col) toggleDay(col.dataset.date, e.shiftKey);
});
// keyboard access to day columns and cells (ticket #50): Enter/Space act like
// a click, Shift+Enter like a shift-click; the re-render replaces the SVG, so
// focus is restored to the same day
document.addEventListener("keydown", e => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const col = e.target.closest("#chart .col");
  if (!col) return;
  e.preventDefault();
  const d = col.dataset.date;
  toggleDay(d, e.shiftKey);
  document.querySelector(`#chart .col[data-date="${d}"]`)?.focus();
});
document.getElementById("hidecr").addEventListener("change", e => {
  S.hideCR = e.target.checked; changed();
});
restore() || applyPreset("14");
