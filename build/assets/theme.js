// Theme pin (issue #83, ADR-0017): system preference by default; the header
// toggle cycles system → light → dark. The pin lives in localStorage, per
// browser, and is applied here — this file is inlined in <head> — before
// first paint so a pinned page never flashes the other theme. The server
// stores nothing per viewer.
(() => {
  let pin = null;
  try { pin = localStorage.getItem("theme"); } catch { /* private mode etc. */ }
  if (pin === "light" || pin === "dark") document.documentElement.dataset.theme = pin;
  document.addEventListener("DOMContentLoaded", () => {
    const b = document.getElementById("theme");
    if (!b) return;
    const label = () =>
      b.textContent = "theme: " + (document.documentElement.dataset.theme || "system");
    b.addEventListener("click", () => {
      const cur = document.documentElement.dataset.theme || "system";
      const next = cur === "system" ? "light" : cur === "light" ? "dark" : "system";
      if (next === "system") delete document.documentElement.dataset.theme;
      else document.documentElement.dataset.theme = next;
      try {
        if (next === "system") localStorage.removeItem("theme");
        else localStorage.setItem("theme", next);
      } catch { /* pin just won't survive the tab */ }
      label();
    });
    label();
  });
})();
