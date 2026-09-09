// The how-view's chosen project becomes the header filter's active chip
// (issue #10): ?p= replaces the stored chips, so the what/where a user
// navigates back to shows the project just looked at. Only an explicit
// ?p= writes — the busiest-project fallback was never chosen.
const p = new URLSearchParams(location.search).get("p");
if (p) try {
  sessionStorage.setItem("filter", JSON.stringify(
    { preset: "14", ...JSON.parse(sessionStorage.getItem("filter")), active: [p] }));
} catch { /* private mode etc. */ }
