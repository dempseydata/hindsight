
const S = { active: new Set(), tFrom: null, tTo: null, hideCR: false, preset: "14", reveal: false };
const subs = [];
const fmt = n => n == null ? "\u2014" : n >= 1e9 ? (n / 1e9).toFixed(1) + "B"
  : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : "" + n;
const inWin = d => !S.tFrom || (d >= S.tFrom && d <= (S.tTo || S.tFrom));
const inProj = p => S.active.size === 0 || S.active.has(p);
window.hs = { S, DATA, fmt, inWin, inProj, addDays, onFilter: f => subs.push(f) };

function addDays(d, n) {
  const t = new Date(d + "T00:00:00Z");
  t.setUTCDate(t.getUTCDate() + n);
  return t.toISOString().slice(0, 10);
}
function applyPreset(w) {
  S.preset = w;
  // empty db: no last day to anchor to — presets degrade to "all" (ticket #50)
  if (w === "all" || !DATA.range[1]) S.tFrom = S.tTo = null;
  else { S.tTo = DATA.range[1]; S.tFrom = addDays(S.tTo, 1 - +w); }
  changed();
}
function toggleDay(d) {
  S.preset = null;                     // a chart click overrides the preset
  if (S.tFrom === d && !S.tTo) S.tFrom = null;
  else if (!S.tFrom || S.tTo) { S.tFrom = d; S.tTo = null; }
  else [S.tFrom, S.tTo] = [S.tFrom, d].sort();
  changed();
}
let scrolled = false;
function renderChart() {
  const ch = document.getElementById("chart");
  if (!DATA.range[0]) {
    ch.innerHTML = '<p class="note">no usage yet \u2014 run an analysis first</p>';
    return;
  }
  const byDay = {};
  for (const r of DATA.days) {
    if (!inProj(r.p)) continue;
    const t = byDay[r.d] ??= [0, 0, 0, 0];
    r.t.forEach((n, k) => t[k] += n);
  }
  const rows = [];
  for (let d = DATA.range[0]; d <= DATA.range[1]; d = addDays(d, 1))
    rows.push({ d, t: byDay[d] });   // missing day = gap, never zero
  const bw = 14, gap = 3, h = 96, axis = 16;
  const val = t => t ? t[0] + t[1] + t[2] + (S.hideCR ? 0 : t[3]) : 0;
  const peak = Math.max(1, ...rows.map(r => val(r.t)));
  let out = "";
  rows.forEach((r, i) => {
    const x = i * (bw + gap);
    let y = h;
    if (r.t) r.t.forEach((n, k) => {
      if (!n || (S.hideCR && k === 3)) return;
      const bh = n / peak * (h - 12);
      y -= bh;
      out += `<rect class="seg${k}" x="${x}" y="${y.toFixed(1)}" width="${bw}" height="${bh.toFixed(1)}"/>`;
    });
    if (i % 7 === 0 || i === rows.length - 1)
      out += `<text class="axis" x="${x + bw / 2}" y="${h + 12}" text-anchor="middle">${r.d.slice(5)}</text>`;
    const sel = S.tFrom && r.d >= S.tFrom && r.d <= (S.tTo || S.tFrom);
    const tip = r.t ? `in ${fmt(r.t[0])} \u00b7 out ${fmt(r.t[1])} \u00b7 cache-create ${fmt(r.t[2])} \u00b7 cache-read ${fmt(r.t[3])}` : "no data";
    if (sel) out += `<rect class="selrule" x="${x - gap / 2}" y="${h + 1}" width="${bw + gap}" height="2"/>`;
    out += `<rect class="col${sel ? " sel" : ""}" data-date="${r.d}" tabindex="0" role="button" aria-pressed="${!!sel}" aria-label="${r.d}, ${tip}" x="${x - gap / 2}" y="0" width="${bw + gap}" height="${h + axis}"><title>${r.d} \u00b7 ${tip}</title></rect>`;
  });
  const sl = ch.scrollLeft;
  ch.innerHTML = `<svg width="${rows.length * (bw + gap) + 12}" height="${h + axis}">${out}</svg>`;
  ch.scrollLeft = scrolled ? sl : ch.scrollWidth;   // newest at right on load
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
function changed() { renderChart(); syncCtl(); subs.forEach(f => f(S)); save(); }
// The filter survives the what ↔ where navigation (issue #10): saved per tab
// in sessionStorage on every change, restored ahead of the first render. Gone
// when the tab closes; a reload keeps the filter instead of resetting — accepted.
function save() {
  try { sessionStorage.setItem("filter", JSON.stringify({ ...S, active: [...S.active] })); }
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
    else { S.preset = null; S.tFrom = f.tFrom; S.tTo = f.tTo; changed(); }
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
  if (col) toggleDay(col.dataset.date);
});
// keyboard access to day columns (ticket #50): Enter/Space act like a click;
// the re-render replaces the SVG, so focus is restored to the same day
document.addEventListener("keydown", e => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const col = e.target.closest("#chart .col");
  if (!col) return;
  e.preventDefault();
  const d = col.dataset.date;
  toggleDay(d);
  document.querySelector(`#chart .col[data-date="${d}"]`)?.focus();
});
document.getElementById("hidecr").addEventListener("change", e => {
  S.hideCR = e.target.checked; changed();
});
restore() || applyPreset("14");
