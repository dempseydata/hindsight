# #84 First run proven on a clean environment

state: closed · labels: ready-for-agent · opened: 2026-09-01 · closed: 2026-09-01

## Parent

#56

## What to build

From a fresh clone with no local data, the steps a stranger would follow — initialise, run an analysis against their own Claude Code history, serve — reach rendered views without a crash. The empty-DB RangeError and listener-only-DB guards landed with ticket #50; this ticket finds and fixes whatever a genuinely clean run still trips on (missing directories, no launchd jobs, hook not registered, no OTEL listener), operating everything on-demand only. Its output is the verified, minimal step list that the run-it documentation ticket writes down.

## Acceptance criteria

- [ ] A run from a fresh clone (no local data present) reaches the served views with zero console errors and no traceback, on a machine state that has never run hindsight
- [ ] Absence of the ingest listener, launchd jobs and the self-instrumentation hook degrades to documented, non-fatal behaviour (coverage-window honesty, not crashes)
- [ ] The verified step list is posted on this ticket for the run-it documentation to transcribe

## Blocked by

None — can start immediately.


---

**comment · 2026-09-01**

## Verified first-run step list (for the run-it documentation, #86)

Proven 2026-09-01 on a fresh clone with a synthetic clean machine state (empty transcript archive, no `~/Documents/Claude`, no listener, no launchd jobs, no hook registered), then again with one real transcript through the full pipeline including the model call. Exercised under both Apple CLT Python 3.9.6 and Homebrew 3.14 — stdlib only, nothing to install.

### The steps

1. **`git clone <repo> && cd hindsight`** — no pip, no venv, no build step. Requires: macOS, `python3` (3.9+ verified), `git`, and the `claude` CLI on PATH (the machine has Claude Code history by definition).
2. **`python3 build/analyze.py`** — the first analysis run, against `~/.claude/projects`. Creates `local-data/` and the DB itself. What a clean state does, verified:
   - No transcripts at all → completes, exit 0.
   - `~/Documents/Claude` absent → sunk-cost workspace level and presence observation skip silently.
   - A transcript written in the last 5 minutes stays `pending` (live-session guard) until a later run.
   - `claude` not resolvable → **was a raw `FileNotFoundError` traceback that also skipped the backstop/sunk-cost tail; now pauses like limit exhaustion** (one stderr line, sessions stay pending, mechanical scans still land, exit 0). Fixed on this ticket.
3. **`python3 build/serve.py`** → `http://127.0.0.1:8321/what`. Run before step 2 it refuses with `no database … run an analysis first` (exit 1) — by design, same answer for a listener-only DB.

Everything else is optional and on-demand:

- **Ingest listener** (`python3 build/listener.py install`, launchd) — absent, OTEL-fed panels state "capture began —" and shade the pre-coverage region; nothing crashes.
- **Self-instrumentation hook** — registration snippet in `build/hook.py`'s docstring (the command path is machine-specific — the hard-wired list, #86). Absent: hook panel renders headers over no rows. With the hook registered but no listener: silent exit in ~0.13 s.
- **Nightly analysis** (`python3 build/analyze.py install`) — not exercised live (it installs a real launchd job); code-read only. Its plist bakes the installing shell's PATH precisely because launchd's default lacks `claude` — the crash fixed above was that failure mode's worst case.

### Evidence

- Empty state: analyze exit 0; `/what`, `/where`, `/how` (plus `?p=` variants) all HTTP 200; **zero browser console errors or warnings** on all three (Playwright, Chromium).
- Populated (1 real transcript): sync → greedy extract → what-pass model call → audit entry rendered in the ledger; substrate filled (21 tool events, 13 usage rows); all three views console-clean; coverage-window honesty confirmed ("OTEL capture from — · hooks from —", "synced through never" before any sync).
- Full test suite green before and after the fix; the fix carries `test_default_model_runner_missing_binary_pauses`.



---

**comment · 2026-09-01**

All three acceptance criteria met: clean-state run verified live (zero console errors on all views, both empty and populated), degradation of absent listener/launchd/hook confirmed non-fatal and honest, step list posted above for #86 to transcribe. Fix landed in da7ae30.

