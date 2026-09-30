// Glyphs derived from Tabler Icons 3.48.0 (https://tabler.io/icons) —
// © 2020–2026 Paweł Kuna, MIT licence, full text in LICENSES/tabler-icons.txt.
// Some paths are verbatim, some simplified (ADR-0029 §7, #47). Nothing is
// vendored and there is no webfont: each path renders as 16px inline SVG.
// Keyed by Tabler's glyph name; route-slash is route with a slash (ADR-0030 §2).
const ICONS = {
  "list": "M9 6h11M9 12h11M9 18h11M5 6v.01M5 12v.01M5 18v.01",
  "chart-pie": "M10 3.2a9 9 0 1 0 10.8 10.8a1 1 0 0 0-1-1h-6.8a2 2 0 0 1-2-2v-7a.9 .9 0 0 0-1-.8M15 3.5a9 9 0 0 1 5.5 5.5h-4.5a1 1 0 0 1-1-1v-4.5",
  "route": "M3 19a2 2 0 1 0 4 0a2 2 0 0 0-4 0M19 7a2 2 0 1 0 0-4a2 2 0 0 0 0 4M11 19h5.5a3.5 3.5 0 0 0 0-7h-8a3.5 3.5 0 0 1 0-7h4.5",
  "calendar": "M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-12a2 2 0 0 1-2-2zM16 3v4M8 3v4M4 11h16",
  "chart-bar": "M3 13h6v7h-6zM15 8h6v12h-6zM9 4h6v16h-6z",
  "trophy": "M8 21h8M12 17v4M7 4h10M17 4v8a5 5 0 0 1-10 0v-8M3 9a2 2 0 1 0 4 0a2 2 0 1 0-4 0M17 9a2 2 0 1 0 4 0a2 2 0 1 0-4 0",
  "cpu": "M5 5h14v14h-14zM9 9h6v6h-6zM3 10h2M3 14h2M10 3v2M14 3v2M21 10h-2M21 14h-2M14 21v-2M10 21v-2",
  "plug": "M9.8 6l8.2 8.2l-2 2a5.8 5.8 0 1 1-8.2-8.2zM4 20l3.5-3.5M15 4l-3.5 3.5M20 9l-3.5 3.5",
  "terminal": "M5 7l5 5l-5 5M12 19h7",
  "hourglass": "M6.5 7h11M6 20v-2a6 6 0 1 1 12 0v2a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1zM6 4v2a6 6 0 1 0 12 0v-2a1 1 0 0 0-1-1h-10a1 1 0 0 0-1 1z",
  "activity": "M3 12h4l3 8l4-16l3 8h4",
  "bolt": "M13 3v7h6l-8 11v-7h-6l8-11",
  "clock": "M3 12a9 9 0 1 0 18 0a9 9 0 1 0-18 0M12 8v4l3 3",
  "list-check": "M3.5 5.5l1.5 1.5l2.5-2.5M3.5 11.5l1.5 1.5l2.5-2.5M3.5 17.5l1.5 1.5l2.5-2.5M11 6h9M11 12h9M11 18h9",
  "route-slash": "M3 19a2 2 0 1 0 4 0a2 2 0 0 0-4 0M19 7a2 2 0 1 0 0-4a2 2 0 0 0 0 4M11 19h5.5a3.5 3.5 0 0 0 0-7h-8a3.5 3.5 0 0 1 0-7h4.5M3 3l18 18",
  "alert-triangle": "M12 9v4M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636-2.87l-8.106-13.536a1.914 1.914 0 0 0-3.274 0zM12 16h.01",
  "help-circle": "M3 12a9 9 0 1 0 18 0a9 9 0 1 0-18 0M12 17v.01M12 13.5a1.5 1.5 0 0 1 1-1.5a2.6 2.6 0 1 0-3-4",
  "arrow-up": "M12 5v14M18 11l-6-6M6 11l6-6",
  "arrow-down": "M12 5v14M18 13l-6 6M6 13l6 6",
};
// Fill every `data-icon` placeholder under root with its glyph; the SVG
// replaces the placeholder's fallback text (`?`, `▲▼`), so the text shows
// only when the glyph cannot. JS-built markup calls this after it renders.
function fillIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach(el => {
    const p = Object.hasOwn(ICONS, el.dataset.icon) && ICONS[el.dataset.icon];
    if (p) el.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="${p}"/></svg>`;
  });
}
document.addEventListener("DOMContentLoaded", () => fillIcons());
