# ADR-0024: Stage A is computed per request with the window in the URL; Stage B is stored like the status narrative

**Date:** 2026-09-12 · **Status:** accepted · **Decides:** [issue #25](https://github.com/dempseydata/hindsight/issues/25); map [#18](https://github.com/dempseydata/hindsight/issues/18) · **Touches:** ADR-0008, ADR-0012, ADR-0022

## Context

ADR-0022 exported the placement question: the so-what view reads the shared header window, so Stage A is computed at render time or cached per window, and Stage B, if built, fixes its own window and is stored. The ticket framed the render-time option as "as the how-view trail is". That option does not exist for a windowed view: the header window is browser state (`sessionStorage`, CONTEXT.md *filter state*), the what and where views ship one blob per request and fold it by the window in JS, and the server never sees a window at all. The how-view is server-rendered only because it reads a project, carried as `?p=`, and no window.

The Stage A prototype ([#19](https://github.com/dempseydata/hindsight/issues/19)) recorded no timing, so it was measured for this ticket over the real database (337 sessions, 29,917 tool events, 27,297 usage rows): one project-window costs 115–275 ms unindexed and 16–206 ms with three indexes; six projects at 14 days cost 790 ms serial unindexed; the where-view already renders in 694 ms with a 1.2 MB blob. A day-grain aggregate that would let the browser fold Stage A is 2,251 rows, about 117 KB. Cost decides nothing: every route is under the where-view's existing render.

What decides it is the second consumer. Stage B, if built, needs Stage A's pattern set for its fixed window computed in the analysis run, in Python. A Stage A that lived in JS would then be a second definition of the same signals, in a language the test suite does not cover.

## Decision

- **Stage A is a Python function over the database, computed per request.** The so-what page carries its window and active projects in the URL; a chip or bar click on this view navigates, as the how-view's `?p=` does, rather than folding in place. One definition serves the page and the analysis run.
- **Indexes, no cache.** Three indexes — `tool_events(session_id, at)`, `usage(session_id, at)`, `sessions(project, date)` — join the analysis run's schema DDL, the run being the only writer (ADR-0008). Every request computes fresh against a database the listener keeps writing; there is nothing to invalidate and no state on the server.
- **Stage B, if built, mirrors `status_narrative`** (ADR-0012): one row per project keyed on a content hash of the pattern set for its fixed window, with the findings, prompt version, model, generation time and the window's bounds; regenerated only when hash, prompt version or model moves; a regeneration that fails the write-time gate leaves the last good row in place, marked stale. Staleness is judged at render time by recomputing Stage A for the stored window and comparing hashes — cheap under the first decision.
- **The run computes Stage A only as Stage B's input.** Without Stage B nothing is stored or logged; a pattern surfacing anywhere beyond the view stays in the map's fog.

## Considered options

- **Browser folding** (the where-view's mechanics): the server ships day-grain aggregates, JS computes patterns per window. Instant filter response, no navigation, ~117 KB. Rejected because Stage B makes the Python definition mandatory and this would be its untested twin; and the floors of ADR-0022 would be JS constants beside Python ones.
- **A per-window cache in the server process.** Faster repeat renders of a render that is already under 250 ms per project; would need a staleness rule against live writes. Machinery guarding nothing.
- **Stored patterns per project at analysis time.** Already rejected by ADR-0022 for an arbitrary window; its only surviving form is storing the day-grain aggregate, which is browser folding with a table.
- **Unindexed.** Acceptable today (790 ms for six projects); the indexes cost one DDL line each and cut the worst case by a third and the typical case by an order of magnitude.

## Consequences

- The so-what view is the first windowed view rendered server-side: the chrome's `changed()` on this view navigates with the filter state in the query string instead of re-folding. The build ticket carries that one branch in `chrome.js`.
- CONTEXT.md's *window* names the URL as this view's carrier; *filter state* records the exception; *finding* names the storage.
- The greybox ([#28](https://github.com/dempseydata/hindsight/issues/28)) builds Stage A as the function the server will call, over the same query shapes as the prototype; the prototype's SQL is its input, not its code.
- If Stage B is built, its table, gate and stale rule are copied from `status_narrative`, not designed afresh.
