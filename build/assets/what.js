
{
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");   // quote-safe: esc output lands in attributes too
const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
  .replace(/`([^`]+)`/g, "<code>$1</code>");
const secN = (r, name) => (r.sections || []).find(s => s.name === name)?.n ?? 0;
// a continuation row (#9) is a thin pointer: the entry lives on the session's first row
const full = Object.fromEntries(WHAT.filter(r => !r.cont).map(r => [r.id, r]));
// vocabulary at render (ADR-0028): the stored headers stay Did / Decided
const SECTION_LABEL = { Did: "Actions", Decided: "Decisions" };
const counts = r => ({ actions: secN(r, "Did"), decisions: secN(r, "Decided"), adrs: r.adr || 0 });

function rowHtml(r, open) {
  const cont = r.cont ? `<span class="cont">${r.cont}</span>` : "";
  // #13: mechanical note — the session spawned subagents, whose tokens and
  // tool calls are counted in it (their work is the session's work)
  const sub = r.sub ? `<span class="cont" title="subagent transcripts filed under this session — their tokens count here">${r.sub} subagent${r.sub > 1 ? "s" : ""}</span>` : "";
  const chip = `<span class="pchip" title="${esc(r.p)}">${esc(r.p)}</span>${cont}${sub}`;
  if (r.lost)
    return `<div class="row srow">${chip}<span class="ttl dim">transcript pruned before analysis \u2014 unrecoverable</span></div>`;
  if (r.empty)
    return `<div class="row srow">${chip}<span class="ttl dim">empty session \u2014 nothing to analyze</span></div>`;
  if (r.pend)
    return `<div class="row srow">${chip}<span class="ttl dim">synced, not yet analyzed \u2014 run an analysis</span></div>`;
  if (r.skip)
    return `<div class="row srow">${chip}<span class="ttl dim">trivial session \u2014 skipped</span></div>`;
  const attrs = `data-id="${r.id}" data-day="${r.d}"`;
  const op = open.has(r.id + "@" + r.d) ? " open" : "";
  if (r.title == null)
    return `<details class="row" ${attrs}${op}><summary>${chip}<span class="ttl dim">no entry \u2014 the model refused this session (defect #38)</span></summary><div class="entry"><pre>${esc(r.raw)}</pre></div></details>`;
  const adr = r.adr >= 1 ? `<span class="adr">${r.adr} ADR</span>` : "";
  const pl = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
  const cnt = `${pl(secN(r, "Did"), "action")} \u00b7 ${pl(secN(r, "Decided"), "decision")}`;
  const secs = (r.sections || []).map(s => `<h3>${esc(SECTION_LABEL[s.name] ?? s.name)}</h3>`
    + (s.para ? `<p>${inline(s.items[0])}</p>`
              : `<ul>${s.items.map(i => `<li>${inline(i)}</li>`).join("")}</ul>`)).join("");
  return `<details class="row" ${attrs}${op}><summary>${chip}<span class="ttl">${inline(r.title)}</span><span class="cnt">${cnt}${adr}</span></summary><div class="entry">${secs}</div></details>`;
}

// The header visual on this view (ADR-0028): a session heatmap, one cell
// per local day of DATA.range, Monday at top, a column per calendar week,
// newest at right. Heat keys to the pressed tile; counts are client-side
// under the project filter and follow the ledger rule: a session on every
// day it has a row, actions / decisions / ADRs on the first row alone —
// where the entry lives. A cell is a .col in #chart; chrome.js owns the click.
const KEYS = [["sessions", "sessions"], ["actions", "actions"],
              ["decisions", "decisions"], ["adrs", "ADRs"]];
let heatKey = "sessions";
function dayCounts() {
  const by = {};
  for (const r of WHAT) {
    if (!r.d || !hs.inProj(r.p)) continue;
    const c = by[r.d] ??= { ids: new Set(), actions: 0, decisions: 0, adrs: 0 };
    c.ids.add(r.id);
    if (!r.cont) for (const [k, v] of Object.entries(counts(r))) c[k] += v;
  }
  return by;
}
const dow = d => (new Date(d + "T00:00:00Z").getUTCDay() + 6) % 7;   // Monday 0
const month = d => new Date(d + "T00:00:00Z").toLocaleString("en", { month: "short", timeZone: "UTC" });
function renderHeat() {
  if (!DATA.range[0]) return hs.mount('<p class="note">no usage yet \u2014 run an analysis first</p>');
  const by = dayCounts();
  const val = c => !c ? 0 : heatKey === "sessions" ? c.ids.size : c[heatKey];
  const cs = 12, gap = 2, pitch = cs + gap, top = 12, left = 24;   // left: the day labels
  // the grid spans the ledger too: a pruned session keeps its start day with
  // no usage row, so the ledger can begin before the usage range does
  const from = WHAT.reduce((m, r) => r.d && r.d < m ? r.d : m, DATA.range[0]), to = DATA.range[1];
  let peak = 1;
  for (let d = from; d <= to; d = hs.addDays(d, 1)) peak = Math.max(peak, val(by[d]));
  let out = "", cols = 0;
  for (const [row, l] of [[0, "Mon"], [4, "Fri"]])
    out += `<text class="axis" x="0" y="${top + row * pitch + 9.5}">${l}</text>`;
  for (let d = from, i = dow(from); d <= to; d = hs.addDays(d, 1), i++) {
    const col = Math.floor(i / 7), x = left + col * pitch, y = top + (i % 7) * pitch;
    cols = col + 1;
    if (d.endsWith("-01")) out += `<text class="axis" x="${x}" y="9">${month(d)}</text>`;
    const c = by[d], v = val(c), lvl = v ? Math.ceil(v / peak * 4) : 0;
    const sel = hs.inWin(d);   // the window: the set, else the preset range
    const tip = `sessions ${c ? c.ids.size : 0} \u00b7 actions ${c?.actions ?? 0} \u00b7 decisions ${c?.decisions ?? 0} \u00b7 ADRs ${c?.adrs ?? 0}`;
    out += `<rect class="col${lvl ? " l" + lvl : ""}${sel ? " sel" : ""}" data-date="${d}" tabindex="0" role="button" aria-pressed="${sel}" aria-label="${d}, ${tip}" x="${x}" y="${y}" width="${cs}" height="${cs}"><title>${d} \u00b7 ${tip}</title></rect>`;
  }
  hs.mount(`<svg width="${left + cols * pitch + 12}" height="${top + 7 * pitch}">${out}</svg>`);
}
// four tiles over the visible window; a radio group whose pressed one keys the heat
function tilesHtml(sess) {
  const n = f => sess.filter(f).length;
  const tot = { sessions: sess.length, actions: 0, decisions: 0, adrs: 0 };
  for (const r of sess) for (const [k, v] of Object.entries(counts(full[r.id]))) tot[k] += v;
  const q = [["trivial", n(r => r.skip)], ["awaiting analysis", n(r => r.pend)],
             ["unrecoverable", n(r => r.lost)]].filter(([l, v]) => v || l === "trivial");
  const sub = { sessions: ["in view", ...q.map(([l, v]) => `${v} ${l}`)].join(" \u00b7 ") };
  return KEYS.map(([k, l]) => `<button class="tile" data-k="${k}" aria-pressed="${k === heatKey}"><b>${hs.fmt(tot[k])}</b><span>${l}${sub[k] ? " \u00b7 " + sub[k] : ""}</span></button>`).join("");
}
document.getElementById("wtiles").addEventListener("click", e => {
  const b = e.target.closest("button[data-k]");
  if (!b) return;
  heatKey = b.dataset.k;   // in place, so a keyboard press keeps its focus
  document.querySelectorAll("#wtiles button").forEach(t => t.setAttribute("aria-pressed", t === b));
  renderHeat();
});

let anchored = false;   // the session anchor scrolls once, on the render that finds it
function renderWhat() {
  renderHeat();
  const open = new Set([...document.querySelectorAll("#ledger details[open]")]
    .map(d => d.dataset.id + "@" + d.dataset.day));
  // undated sessions can't be windowed — always shown, never silently dropped
  const vis = WHAT.filter(r => r.d ? (hs.inWin(r.d) && hs.inProj(r.p))
                                   : hs.inProj(r.p));
  let out = "", day = null;
  for (const r of vis) {
    if (r.d !== day) { day = r.d; out += `<h2 class="day">${day ?? "undated"}</h2>`; }
    out += rowHtml(r.cont ? { ...full[r.id], d: r.d, cont: r.cont } : r, open);
  }
  document.getElementById("ledger").innerHTML =
    out || '<p class="note">no sessions in this window</p>';
  // a session in view on several days counts once
  const sess = [...new Map(vis.map(r => [r.id, r])).values()];
  document.getElementById("wtiles").innerHTML = tilesHtml(sess);
  // session anchor (ADR-0023): /what#<sid> opens and scrolls to the first
  // row carrying the id, never touches filter state; a row outside the
  // filter is stated under the ledger, not silently nothing
  const want = decodeURIComponent(location.hash.slice(1));
  if (!want) return;
  const el = document.querySelector(`#ledger details[data-id="${CSS.escape(want)}"]`);
  if (el) { if (!anchored) { el.open = true; el.scrollIntoView(); anchored = true; } }
  else document.getElementById("ledger").insertAdjacentHTML("beforeend",
    `<p class="note">session ${esc(want)} is outside the current filter \u2014 widen the window or project chips</p>`);
}
hs.onFilter(renderWhat);
renderWhat();
}
