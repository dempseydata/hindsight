
{
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");   // quote-safe: esc output lands in attributes too
const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
  .replace(/`([^`]+)`/g, "<code>$1</code>");
const secN = (r, name) => (r.sections || []).find(s => s.name === name)?.n ?? 0;

function rowHtml(r, open) {
  const chip = `<span class="pchip" title="${esc(r.p)}">${esc(r.p)}</span>`;
  if (r.lost)
    return `<div class="row srow">${chip}<span class="ttl dim">transcript pruned before analysis \u2014 unrecoverable</span></div>`;
  if (r.empty)
    return `<div class="row srow">${chip}<span class="ttl dim">empty session \u2014 nothing to analyze</span></div>`;
  if (r.pend)
    return `<div class="row srow">${chip}<span class="ttl dim">synced, not yet analyzed \u2014 run an analysis</span></div>`;
  if (r.skip)
    return `<div class="row srow">${chip}<span class="ttl dim">trivial session \u2014 skipped</span></div>`;
  const op = open.has(r.id) ? " open" : "";
  if (r.title == null)
    return `<details class="row" data-id="${r.id}"${op}><summary>${chip}<span class="ttl dim">no entry \u2014 the model refused this session (defect #38)</span></summary><div class="entry"><pre>${esc(r.raw)}</pre></div></details>`;
  const adr = r.adr >= 1 ? `<span class="adr">${r.adr} ADR</span>` : "";
  const cnt = `${secN(r, "Did")} did \u00b7 ${secN(r, "Decided")} decided`;
  const secs = (r.sections || []).map(s => `<h3>${esc(s.name)}</h3>`
    + (s.para ? `<p>${inline(s.items[0])}</p>`
              : `<ul>${s.items.map(i => `<li>${inline(i)}</li>`).join("")}</ul>`)).join("");
  return `<details class="row" data-id="${r.id}"${op}><summary>${chip}<span class="ttl">${inline(r.title)}</span><span class="cnt">${cnt}${adr}</span></summary><div class="entry">${secs}</div></details>`;
}

function renderWhat() {
  const open = new Set([...document.querySelectorAll("#ledger details[open]")]
    .map(d => d.dataset.id));
  // undated sessions can't be windowed — always shown, never silently dropped
  const vis = WHAT.filter(r => r.d ? (hs.inWin(r.d) && hs.inProj(r.p))
                                   : hs.inProj(r.p));
  let out = "", day = null;
  for (const r of vis) {
    if (r.d !== day) { day = r.d; out += `<h2 class="day">${day ?? "undated"}</h2>`; }
    out += rowHtml(r, open);
  }
  document.getElementById("ledger").innerHTML =
    out || '<p class="note">no sessions in this window</p>';
  const triv = vis.filter(r => r.skip).length;
  const pend = vis.filter(r => r.pend).length;
  const lost = vis.filter(r => r.lost).length;
  document.getElementById("wsum").textContent =
    `${vis.length} sessions in view \u00b7 ${triv} trivial`
    + (pend ? ` \u00b7 ${pend} awaiting analysis` : "")
    + (lost ? ` \u00b7 ${lost} unrecoverable` : "")
    + " \u00b7 listed under their first day";
}
hs.onFilter(renderWhat);
renderWhat();
}
