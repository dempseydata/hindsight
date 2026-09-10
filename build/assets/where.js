
{
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const fmt = hs.fmt;
const fmtMs = v => v >= 60000 ? (v / 60000).toFixed(1) + "min"
  : v >= 1000 ? (v / 1000).toFixed(1) + "s" : Math.round(v) + "ms";
const pct = (durs, q) => durs.length ? durs[Math.ceil(durs.length * q / 100) - 1] : null;
const ms = v => v == null ? '<span class="dim">\u2014</span>' : fmtMs(v);
const val4 = t => t[0] + t[1] + t[2] + (hs.S.hideCR ? 0 : t[3]);
// undated rows can't be windowed — project filter only, never dropped
const keep = r => r.d ? (hs.inWin(r.d) && hs.inProj(r.p)) : hs.inProj(r.p);
const merged = durs => durs.flat().sort((a, b) => a - b);
// per-day calls (and errors) accumulator shared by league/mcp/cli
const bump = (o, r) => {
  if (!r.d) return;
  o.perDay[r.d] = (o.perDay[r.d] || 0) + r.n;
  if (r.e) o.errDay[r.d] = (o.errDay[r.d] || 0) + r.e;
};

// the spark system: one shared 30-calendar-day axis, own peak per spark
// (empty db: no anchor day, no axis — sparks render as empty svgs)
const SPARK_DAYS = DATA.range[1]
  ? Array.from({ length: 30 }, (_, i) => hs.addDays(DATA.range[1], i - 29))
  : [];
const BW = 3, GAP = 1, SH = 14, EH = 6;
function sparkSvg(perDay, o = {}) {
  const peak = Math.max(1, ...SPARK_DAYS.map(d => perDay[d] || 0));
  const hasErr = o.err && SPARK_DAYS.some(d => o.err[d]);
  const epeak = hasErr ? Math.max(1, ...SPARK_DAYS.map(d => o.err[d] || 0)) : 1;
  const H = SH + (hasErr ? EH + 2 : 0);
  let out = "";
  if (o.covFrom && o.covFrom > SPARK_DAYS[0]) {
    // shaded region = capture did not exist yet, not zero activity
    const n = SPARK_DAYS.filter(d => d < o.covFrom).length;
    out += `<rect x="0" y="0" width="${n * (BW + GAP)}" height="${H}" fill="var(--o-gapline)" opacity="var(--o-wash-precov)"/>`;
  }
  SPARK_DAYS.forEach((d, i) => {
    const x = i * (BW + GAP), n = perDay[d] || 0;
    if (n) {
      const bh = Math.max(1, n / peak * SH);
      out += `<rect x="${x}" y="${(SH - bh).toFixed(1)}" width="${BW}" height="${bh.toFixed(1)}" fill="var(--o-spark)"/>`;
    }
    if (hasErr && o.err[d]) {
      const eh = Math.max(1, o.err[d] / epeak * EH);
      out += `<rect x="${x}" y="${(SH + 2 + EH - eh).toFixed(1)}" width="${BW}" height="${eh.toFixed(1)}" fill="var(--o-problem)"/>`;
    }
    out += `<rect x="${x}" y="0" width="${BW + GAP}" height="${H}" fill="transparent"><title>${d} \u00b7 ${n} calls${o.err ? ` \u00b7 ${o.err[d] || 0} err` : ""}</title></rect>`;
  });
  return `<svg class="spark" width="${SPARK_DAYS.length * (BW + GAP)}" height="${H}">${out}</svg>`;
}
const table = (head, rows) => `<table><tr>${head.map(h =>
  `<th${h.n ? ' class="num"' : ""}>${h.h ?? h}</th>`).join("")}</tr>${rows.map(r =>
  `<tr>${r.map(c => `<td${c.n ? ' class="num"' : ""}>${c.h ?? c}</td>`).join("")}</tr>`).join("")}</table>`;
const num = v => ({ n: 1, h: v == null ? '<span class="dim">\u2014</span>' : fmt(v) });
const errHtml = (e, nu) => (e ? `<span class="err">${e}</span>` : '<span class="dim">0</span>')
  + (nu ? `<span class="dim" title="unpaired calls \u2014 unknown, not ok"> +${nu}?</span>` : "");
const errCell = (e, nu) => ({ n: 1, h: errHtml(e, nu) });

function tilesHtml() {
  const t = [0, 0, 0, 0];
  for (const r of DATA.days) if (keep(r)) r.t.forEach((n, k) => t[k] += n);
  const sessions = WHERE.sess.filter(keep).length;
  let calls = 0;
  for (const r of WHERE.tools) if (keep(r)) calls += r.n;
  // #13: two numbers, no list — subagents spawned by sessions in view
  // (first-day attributed, like the sessions tile) and the share of the
  // view's tokens they spent (day grain, the same base as the token tiles)
  let agents = 0, subTok = 0;
  for (const s of WHERE.sess) if (s.na && keep(s)) agents += s.na;
  for (const r of WHERE.subd) if (keep(r)) subTok += val4(r.t);
  const all = val4(t);  // same toggle as the numerator
  const share = all ? Math.round(subTok / all * 100) : 0;
  return [["input", t[0]], ["output", t[1]], ["cache create", t[2]],
          ["cache read", t[3]], ["sessions", sessions], ["tool calls", calls],
          [`subagents · ${share}% of tokens`, agents]]
    .map(([l, v]) => `<div class="tile"><b>${fmt(v)}</b><span>${l}</span></div>`).join("");
}

// consumer league — membership is all-time >=5 calls (stable across window
// changes); the tail (visible categories, #55) rides in one collapsed row.
// First/last used are all-time facts, not window-scoped.
const allCalls = {}, allSpan = {};
for (const r of WHERE.tools) {
  if (!r.ty) continue;
  const k = r.ty + "|" + r.c;
  allCalls[k] = (allCalls[k] || 0) + r.n;
  if (r.d) {
    const s = allSpan[k] ??= [r.d, r.d];
    if (r.d < s[0]) s[0] = r.d;
    if (r.d > s[1]) s[1] = r.d;
  }
}

// #55: league-only category filter, defaults from the server-rendered .on
// chips. A consumer_type without a chip fails open — a future category
// renders until a chip exists for it, it never silently vanishes.
const KNOWN = new Set([...document.querySelectorAll("#cats button")]
  .map(b => b.dataset.t));
const CATS = new Set([...document.querySelectorAll("#cats button.on")]
  .map(b => b.dataset.t));

function leagueHtml(open) {
  const g = {};
  let unclassified = 0, hidden = 0;
  for (const r of WHERE.tools) {
    if (!r.ty) { if (keep(r)) unclassified += r.n; continue; }
    if (KNOWN.has(r.ty) && !CATS.has(r.ty)) {
      if (keep(r)) hidden += r.n;
      continue;
    }
    if (!keep(r)) continue;
    const o = g[r.ty + "|" + r.c] ??= { ty: r.ty, c: r.c, n: 0, e: 0, nu: 0,
      durs: [], perDay: {}, errDay: {}, days: new Set(), proj: {}, mcp: {} };
    o.n += r.n; o.e += r.e; o.nu += r.nu; o.durs.push(r.durs);
    bump(o, r);
    if (r.d) o.days.add(r.d);
    o.proj[r.p] = (o.proj[r.p] || 0) + r.n;
    if (r.mt) o.mcp[r.mt] = (o.mcp[r.mt] || 0) + r.n;
  }
  for (const r of WHERE.lens) {
    const o = g[r.ty + "|" + r.c];
    if (o && keep(r)) o.msg = (o.msg || 0) + val4(r.t);
  }
  const sessTok = WHERE.sess.map(s => keep(s) ? val4(s.t) : 0);
  for (const r of WHERE.cs) {
    const o = g[r.ty + "|" + r.c];
    if (o) o.sess = r.s.reduce((a, i) => a + sessTok[i], 0);
  }
  const rows = Object.entries(g).filter(([k]) => allCalls[k] >= 5)
    .sort((a, b) => (b[1].msg || 0) - (a[1].msg || 0) || b[1].n - a[1].n);
  const tail = Object.entries(g).filter(([k]) => allCalls[k] < 5);
  const tailCalls = tail.reduce((a, [, o]) => a + o.n, 0);
  const head = `<div class="lghead"><span>consumer</span><span>calls/day \u00b7 errors below</span>
    <span class="num">calls</span><span class="num">err</span>
    <span class="num" title="every session the consumer appeared in">sess-lens</span>
    <span class="num" title="only the API responses that invoked it">msg-lens</span></div>`;
  let out = "";
  for (const [k, o] of rows) {
    const durs = merged(o.durs);
    const span = allSpan[k] || ["\u2014", "\u2014"];
    const projs = Object.entries(o.proj).sort((a, b) => b[1] - a[1]);
    const mcp = Object.entries(o.mcp).sort((a, b) => b[1] - a[1]);
    out += `<details data-k="${esc(k)}"${open.has(k) ? " open" : ""}><summary>
      <span><span class="pchip">${o.ty}</span> ${esc(o.c)}</span>
      ${sparkSvg(o.perDay, { err: o.e ? o.errDay : null })}
      <span class="num">${fmt(o.n)}</span><span class="num">${errHtml(o.e, o.nu)}</span>
      <span class="num">${o.sess ? fmt(o.sess) : '<span class="dim">\u2014</span>'}</span>
      <span class="num">${o.msg ? fmt(o.msg) : '<span class="dim">\u2014</span>'}</span></summary>
      <div class="detail">
      <p><b>${o.days.size}</b> active days in window \u00b7 first used ${span[0]} \u00b7 last used ${span[1]} (all time)</p>
      <p>latency p50 ${ms(pct(durs, 50))} \u00b7 p95 ${ms(pct(durs, 95))} \u00b7 max ${ms(durs[durs.length - 1])}
         \u00b7 errors <b>${o.e}</b>${o.nu ? ` (+${o.nu} unpaired \u2014 unknown, not ok)` : ""}</p>
      ${mcp.length ? `<p>tools: ${mcp.map(([t, n]) => `${esc(t)} \u00d7${n}`).join(" \u00b7 ")}</p>` : ""}
      <p>projects: ${projs.slice(0, 6).map(([p, n]) => `${esc(p)} \u00d7${n}`).join(" \u00b7 ")}${projs.length > 6 ? ` \u00b7 +${projs.length - 6} more` : ""}</p>
      </div></details>`;
  }
  if (tail.length)
    out += `<details class="sub" data-k="_tail"${open.has("_tail") ? " open" : ""}><summary style="padding:.3rem .6rem">
      ${tail.length} visible-category consumers under 5 all-time calls \u00b7 ${tailCalls} calls in window</summary>
      <p class="detail dim">${tail.sort((a, b) => b[1].n - a[1].n).map(([, o]) =>
        `${esc(o.c)} <span class="pchip">${o.ty}</span> \u00d7${o.n}`).join(" \u00b7 ")}</p></details>`;
  out = out ? head + out : '<p class="dim">none in filter</p>';
  if (hidden)
    out += `<p class="note">${fmt(hidden)} calls in window sit in switched-off
      categories \u2014 the chips above re-add them; always counted in the tiles.</p>`;
  if (unclassified)
    out += `<p class="note">${fmt(unclassified)} calls in window carry no consumer grain
      (transcripts pruned before the substrate scan) \u2014 unknown, not zero; counted
      in the tiles, absent from this league and its chips.</p>`;
  return out;
}

function modelsHtml() {
  const g = {}, perDay = {};
  for (const r of WHERE.models) {
    if (!keep(r)) continue;
    const o = g[r.m] ??= { n: 0, t: [0, 0, 0, 0] };
    o.n += r.n; r.t.forEach((n, k) => o.t[k] += n);
    const pd = perDay[r.m] ??= {};
    pd[r.d] = (pd[r.d] || 0) + r.n;
  }
  const lat = {};
  for (const r of WHERE.lat) if (keep(r)) (lat[r.m] ??= []).push(r.durs);
  const rows = Object.entries(g).sort((a, b) => b[1].t[1] - a[1].t[1]).map(([m, o]) => {
    const durs = merged(lat[m] || []);
    return [esc(m), sparkSvg(perDay[m] || {}), num(o.n), num(o.t[0]), num(o.t[1]),
            num(o.t[2]), num(o.t[3]), { n: 1, h: ms(pct(durs, 50)) }, { n: 1, h: ms(pct(durs, 95)) }];
  });
  return table(["model", "msgs/day", { h: "msgs", n: 1 }, { h: "in", n: 1 },
                { h: "out", n: 1 }, { h: "cache cr", n: 1 }, { h: "cache rd", n: 1 },
                { h: "api p50", n: 1 }, { h: "api p95", n: 1 }], rows);
}

function mcpHtml(open) {
  const srv = {};
  for (const r of WHERE.tools) {
    if (r.ty !== "mcp" || !keep(r)) continue;
    const s = srv[r.c] ??= { n: 0, e: 0, tools: {} };
    s.n += r.n; s.e += r.e;
    const t = s.tools[r.mt || "?"] ??= { n: 0, e: 0, nu: 0, durs: [], perDay: {}, errDay: {} };
    t.n += r.n; t.e += r.e; t.nu += r.nu; t.durs.push(r.durs);
    bump(t, r);
  }
  const servers = Object.entries(srv).sort((a, b) => b[1].n - a[1].n);
  return servers.map(([name, s], i) => {
    const rows = Object.entries(s.tools).sort((a, b) => b[1].n - a[1].n).map(([tool, t]) => {
      const durs = merged(t.durs);
      return [esc(tool), sparkSvg(t.perDay, { err: t.e ? t.errDay : null }),
              num(t.n), errCell(t.e, t.nu), { n: 1, h: ms(pct(durs, 50)) }, { n: 1, h: ms(pct(durs, 95)) }];
    });
    const op = open.has(name) || (i === 0 && !open.size);
    return `<details class="sub" data-k="${esc(name)}"${op ? " open" : ""}><summary>
      <b>${esc(name)}</b> \u00b7 ${fmt(s.n)} calls${s.e ? ` \u00b7 <span class="err">${s.e} errors</span>` : ""}</summary>
      ${table(["tool", "calls/day", { h: "calls", n: 1 }, { h: "err", n: 1 },
               { h: "p50", n: 1 }, { h: "p95", n: 1 }], rows)}</details>`;
  }).join("") || '<p class="dim">none in filter</p>';
}

function cliHtml(open) {
  const g = {};
  for (const r of WHERE.tools) {
    if (r.ty !== "cli" || !keep(r)) continue;
    const o = g[r.c] ??= { n: 0, e: 0, nu: 0, durs: [], perDay: {}, errDay: {}, proj: new Set() };
    o.n += r.n; o.e += r.e; o.nu += r.nu; o.durs.push(r.durs);
    o.proj.add(r.p);
    bump(o, r);
  }
  const main = Object.entries(g).filter(([c]) => allCalls["cli|" + c] >= 5)
    .sort((a, b) => b[1].n - a[1].n);
  const lump = Object.entries(g).filter(([c]) => allCalls["cli|" + c] < 5)
    .sort((a, b) => b[1].n - a[1].n);
  const rows = main.map(([c, o]) => {
    const durs = merged(o.durs);
    return [esc(c), sparkSvg(o.perDay, { err: o.e ? o.errDay : null }), num(o.n),
            errCell(o.e, o.nu), { n: 1, h: ms(pct(durs, 50)) }, { n: 1, h: ms(pct(durs, 95)) },
            { h: `<span class="dim" title="${esc([...o.proj].join(", "))}">${o.proj.size}</span>`, n: 1 }];
  });
  const lumpCalls = lump.reduce((a, [, o]) => a + o.n, 0);
  const lumpHtml = lump.length ? `<details class="sub" data-k="_lump"${open.has("_lump") ? " open" : ""}>
    <summary>${lump.length} programs under 5 all-time calls \u00b7 ${lumpCalls} calls in window
    <span class="dim">(one-offs and Bash-parse leakage \u2014 known scan ceiling)</span></summary>
    <p class="detail dim">${lump.map(([c, o]) => `${esc(c)} \u00d7${o.n}`).join(" \u00b7 ")}</p></details>` : "";
  return table(["program", "calls/day", { h: "calls", n: 1 }, { h: "err", n: 1 },
                { h: "p50", n: 1 }, { h: "p95", n: 1 }, { h: "projects", n: 1 }], rows) + lumpHtml;
}

function sunkHtml(open) {
  // all-time, filesystem-of-today; project chips apply, the window doesn't
  const byProj = {};
  for (const r of WHERE.sunk) {
    const key = r.p ?? "";
    if (r.p && !hs.inProj(r.p)) continue;
    (byProj[key] ??= []).push(r);
  }
  const projs = Object.keys(byProj).sort((a, b) => {
    if (a === "") return -1;
    if (b === "") return 1;
    return (WHERE.med[b]?.med || 0) - (WHERE.med[a]?.med || 0);
  });
  return projs.map(p => {
    const rows = byProj[p];
    const cats = {};
    for (const r of rows) (cats[r.cat] ??= []).push(r);
    const skills = cats.skill || [], cmds = cats.command || [];
    const cmTok = (cats["claude-md"] || []).reduce((a, r) => a + r.tok, 0);
    const mcpTok = (cats.mcp || []).reduce((a, r) => a + r.tok, 0);
    const byPlugin = {};
    for (const r of [...skills, ...cmds]) (byPlugin[r.pl || "(standalone)"] ??= []).push(r);
    const plugHtml = Object.entries(byPlugin).sort((a, b) => b[1].length - a[1].length)
      .map(([pl, list]) => {
        const cat = list.reduce((a, r) => a + r.tok, 0);
        const items = list.sort((a, b) => b.tok - a.tok).slice(0, 15).map(r =>
          `<div>${esc(r.name)} <span class="pchip">${r.cat}</span> ${fmt(r.tok)} tok</div>`).join("")
          + (list.length > 15 ? `<div>\u2026 ${list.length - 15} more</div>` : "");
        return `<details class="grp"><summary><b>${esc(pl)}</b> \u00b7 ${list.length} entries
          \u00b7 eager stub ~${fmt(25 * list.length)} tok \u00b7 catalog ${fmt(cat)} tok</summary>
          <div class="items">${items}</div></details>`;
      }).join("");
    const cmHtml = (cats["claude-md"] || []).map(r =>
      `<div class="items">${esc(r.name)} \u00b7 ${fmt(r.tok)} tok</div>`).join("");
    const m = WHERE.med[p];
    const name = p === "" ? "(user scope \u2014 paid by every session)" : esc(p);
    const key = p === "" ? "_user" : p;
    const op = open.size ? open.has(key) : p === "";
    return `<details data-k="${esc(key)}"${op ? " open" : ""}><summary><b>${name}</b>
      <span class="dim">\u00b7 CLAUDE.md ${fmt(cmTok)} \u00b7 ${skills.length} skills
      \u00b7 ${cmds.length} commands \u00b7 mcp ${fmt(mcpTok)}</span>${m ?
      ` \u00b7 <span class="med">${fmt(m.med)}</span> <span class="dim">measured median (${m.n} sessions)</span>` : ""}</summary>
      ${cmHtml}${plugHtml}</details>`;
  }).join("");
}

function hooksHtml() {
  const g = {};
  for (const h of WHERE.hooks) {
    if (h.d && !hs.inWin(h.d)) continue;     // user-scope: no project filter
    const o = g[h.ev] ??= { n: 0, cpu: [], dur: [], perDay: {} };
    o.n++;
    if (h.cpu != null) o.cpu.push(h.cpu);
    if (h.dur != null) o.dur.push(h.dur);
    o.perDay[h.d] = (o.perDay[h.d] || 0) + 1;
  }
  const rows = Object.entries(g).sort((a, b) => b[1].n - a[1].n).map(([ev, o]) => {
    o.cpu.sort((a, b) => a - b); o.dur.sort((a, b) => a - b);
    return [esc(ev), sparkSvg(o.perDay, { covFrom: WHERE.cov.hook }), num(o.n),
            { n: 1, h: ms(pct(o.cpu, 50)) }, { n: 1, h: ms(pct(o.cpu, 95)) },
            { n: 1, h: `<span class="dim">${o.dur.length ? fmtMs(pct(o.dur, 50)) : "\u2014"}</span>` }];
  });
  return table(["hook event", "firings/day", { h: "firings", n: 1 },
                { h: "cpu p50", n: 1 }, { h: "cpu p95", n: 1 },
                { h: "dur p50", n: 1 }], rows);
}

const openIn = sel => new Set([...document.querySelectorAll(sel + " details[open]")]
  .map(d => d.dataset.k).filter(Boolean));
// chip toggles repaint the league alone — the other panels ignore CATS, and
// a full renderWhere() would spring their collapsed <details> back open
const renderLeague = () =>
  document.getElementById("league").innerHTML = leagueHtml(openIn("#league"));

function renderWhere() {
  const mcpOpen = openIn("#mcp"), cliOpen = openIn("#cli"),
        sunkOpen = openIn("#sunk");
  document.getElementById("tiles").innerHTML = tilesHtml();
  renderLeague();
  document.getElementById("models").innerHTML = modelsHtml();
  document.getElementById("mcp").innerHTML = mcpHtml(mcpOpen);
  document.getElementById("cli").innerHTML = cliHtml(cliOpen);
  document.getElementById("sunk").innerHTML = sunkHtml(sunkOpen);
  document.getElementById("hooks").innerHTML = hooksHtml();
}
// coverage honesty: one global line + per-panel notes; OTEL-fed sparks
// additionally shade their pre-coverage region (judged: in-chart beats
// banner walls — see ticket #48's resolution)
document.getElementById("wcov").textContent = `usage for ${WHERE.cov.usage_sessions} of ${WHERE.cov.sessions} synced sessions (${WHERE.cov.span[0]} \u2192 ${WHERE.cov.span[1]}; pruned transcripts read unknown, never zero) \u00b7 OTEL capture from ${WHERE.cov.otel || "\u2014"} \u00b7 hooks from ${WHERE.cov.hook || "\u2014"} \u00b7 ${WHERE.cov.excluded} of hindsight's own analysis sessions excluded from everything here`;
document.getElementById("mnote").textContent = `token counts come from the transcript scan (full span); api latency from OTEL api_request \u2014 capture began ${WHERE.cov.otel || "\u2014"}, so models unused since then read \u2014. No pricing columns, ever (ADR-0003).`;
document.getElementById("snote").textContent = `what a session pays before the first prompt \u2014 ${WHERE.cov.excluded} of hindsight's own analysis sessions self-excluded. Reads today's filesystem, all-time \u2014 the window doesn't apply, project chips do. size/4 estimates; the measured median (first usage row per session) carries authority \u2014 the gap between itemized eager cost and the median is system-prompt/built-in overhead, invisible to the file scan.`;
document.getElementById("hnote").textContent = `cpu_ms carries the table: per-firing process CPU including interpreter startup (ADR-0005). duration_ms (dim) times the script body only \u2014 clock starts after spawn, stops before the POST. True wall cost, spawn\u2192exit including timeout waits, is not captured. Capture began ${WHERE.cov.hook || "\u2014"} \u2014 the shaded spark region predates it. Hooks are user-scope: project chips don't apply.`;
document.getElementById("cats").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  CATS.has(b.dataset.t) ? CATS.delete(b.dataset.t) : CATS.add(b.dataset.t);
  b.classList.toggle("on", CATS.has(b.dataset.t));
  b.setAttribute("aria-pressed", CATS.has(b.dataset.t));
  renderLeague();
});
hs.onFilter(renderWhere);
renderWhere();
}
