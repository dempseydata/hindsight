# Automation — the model passes

Two LLM workflows, both inside the nightly analysis run (`cli/analyze.py`, launchd at 03:00), both
through `claude -p` as a subprocess. No agents, no tool calling, no SDK, no webhooks. Nothing the model
emits is executed; everything it emits is gated, then stored as prose or JSON. A third model consumer,
the evaluation harness under `eval/`, is operator-run only.

**One call shape for everything:** `default_model_runner` → `claude -p --model claude-haiku-4-5-20251001`,
prompt on stdin, `capture_output`, `timeout=300`, `cwd=REPO`. The pin is `analyze.MODEL`; `eval/cases.json`
and `eval/what_cases.json` carry the same string. `-p` is a single completion: no MCP, no filesystem, no
shell is reachable from the prompt. Calls are serial (a deliberate pause boundary).

## A1 — What-pass (one audit entry per session)

| | |
| --- | --- |
| Trigger | Every `pending`/`partial` session on each run; automatic, no approval gate. A *live* transcript (modified inside `_is_live`'s window, subagents included) is skipped until the next run |
| Owner | `process_session` → `call_cached` → `default_model_runner`; loop in `run_analysis` |
| Inputs the model may read | The extract only (`cli/extract.py`): user and assistant text, 1,500 chars per piece, 180 K chars per part, plus `[Edit: <path>]` markers. Tool results, meta lines, slash-command messages, subagent transcripts (ADR-0019), file contents, `~/.claude` config: never |
| Steering (prompt) | `cli/prompts/what-v3.txt` — the extract sits in a `BEGIN/END TRANSCRIPT EXTRACT` block, named as data, with the output contract restated *after* it (ADR-0016). Multi-part sessions: `merge-v1.txt` over the part outputs only. Trivial-session `SKIP` is a prompt instruction, not code |
| Hard guardrails (not prompt) | Model pin · self-exclusion: a transcript whose head matches `ANALYSIS_SIGS` (hindsight's own prompts) goes to `excluded_sessions`, never audited (ADR-0003) · `valid_entry` (#38): after fence-stripping the output must be exactly `SKIP` or open with `###`, else not written, not cached, session → `partial` · cache dir keyed by `PROMPT_VERSION`, so a version bump never reuses stale output · re-audit only once ≥ 25 % of the transcript (`REAUDIT_SHARE`, against `audited_size`) is unseen |
| Output contract | Markdown: `### <title>` then Did / Decided / Setup-changes, or the literal `SKIP`. Parsed further only for display (`serve.py`, `what.js`) |
| App-owned side effects | `INSERT OR REPLACE audit(session_id, project, date, skip, markdown, prompt_version, model, adr_count)`; `sessions.status` → `done`, `audited_size`; cache file under `<work dir>/what-v3/` (`$CLAUDE_PLUGIN_DATA/analysis`, else `local-data/analysis` for a working-copy run) |
| Agent-owned | Nothing. The model proposes an entry; the app decides whether it is well-formed and records it verbatim |
| Failure handling | Timeout or non-zero exit → `None` → `partial`, retried next run, **no retry bound by design** (ADR-0016). `claude` not on PATH, or `limit` in stderr → `LimitExhausted`: the session loop breaks, the narrative pass is skipped, the mechanical tail still runs, everything unreached resumes next run |
| Logging | `audit.prompt_version` + `audit.model` per row; a gate rejection prints `rejected <cache file>: '<80 chars>'` to stderr; `claude --version` once per run; all to `<home>/logs/analyze.log` under the nightly (`--log`) |

## A2 — Status narrative (one per declaring project)

| | |
| --- | --- |
| Trigger | End of each *unpaused* run, per project whose `.claude/my-process.md` declaration is valid and has ≥ 1 phase run; skipped when `(ledger_hash, STATUS_VERSION, MODEL)` — the hash over ledger plus ADR headers — already matches a stored row (`refresh_narratives`) |
| Inputs the model may read | `{project, as_of, stages, runs: [{stage, start, end, titles}], adrs: [{number, date, title, status, touches}]}` — `how.ledger`; run titles are audit **titles** only, ADR headers are read mechanically from `<root>/docs/adr` (ADR-0035 §3). No transcript text, no other file contents. Since #17 the ledger includes `off-script` runs (a label never in `stages`) and treats `/compact` as a session boundary, so the model now sees days spent outside the declared stages (ADR-0010 amended) |
| Steering | `cli/prompts/status-v2.txt` + the ledger and ADR headers JSON appended (`score.ledger_prompt`) |
| Hard guardrails | `score.parse` (JSON, fence-tolerant; non-JSON → skipped) then `score.contract_v2`, floors M3–M6 (`eval/score.py`): every line shares ≥ 2 content words with the ledger (or with ADR titles when it names an ADR, every named ADR present); every date is in the run span or an ADR date — Superseded lines carry two, in order; a `Now` line names the current stage and start day; Standing 3–8, Superseded ≤ 6, Now 1–3, all lists. Same function as the eval — no second implementation |
| Output contract | JSON `{"Standing": [..], "Superseded": [..], "Now": [..]}` (status-v2, ADR-0035) |
| App-owned side effects | `INSERT OR REPLACE status_narrative(project, ledger_hash, narrative, prompt_version, model, generated_at)`. On rejection nothing is written: the last good row stays and renders **stale** (hash mismatch); with no row ever stored the view shows the mechanical status |
| Failure handling | `LimitExhausted` → pass skipped, retried next run; any other exception prints `narrative pass failed` and the backstop / sunk-cost scans still run (#77) |

## Not model calls, but shaping what the model sees

- **Schema-drift guard** (ADR-0020, #15): `check_drift` runs after the substrate scan, before the model loop. A trip writes a `breakage` row and a banner on every view, optionally a macOS notification; **the run and both model passes continue** through it. `analyze.py acknowledge-breakage <id>` closes a row; a guard bug is caught and logged, never fatal.
- **Growth / re-audit** (`invalidate_grown`): substrate is always topped up; the audit entry is rewritten only past `REAUDIT_SHARE`, so a resumed session does not re-fire A1 nightly.

## A3 — Evaluation harness (`eval/`, operator-run, never nightly)

| Set | Runner · manifest · scorer | Calls | Verdict |
| --- | --- | --- | --- |
| Status narrative (ADR-0035) | `eval/run_v2.py` · `eval/status_v2_cases.json` (5 frozen ledgers + ADR headers, #95) · `eval/score.py` `score_v2` M1–M6 | 3 rounds × 5 × `claude -p`, `ThreadPoolExecutor(5)` | ACCEPT only if every case passes in all three rounds |
| What-pass (ADR-0016) | `eval/what_run.py` · `eval/what_cases.json` (20 case ids; extracts under gitignored `local-data/eval/what/extracts/`) · `analyze.valid_entry` itself | 20 × `default_model_runner`, `ThreadPoolExecutor(4)` | ACCEPT only if every output passes the gate and every expected SKIP/entry holds |

Outputs land under `local-data/eval/…/runs/<tag>/` (untracked). Both runners are the gate before any
edit to a prompt file or to `MODEL`; the threshold is decided before the edit (`eval/README.md`).

**So-what view — dropped, no code.** ADR-0021–0025 designed a fourth view with a conditional model
synthesis (Stage B) and fixed its go/no-go before a dry run (#27). The dry run was no-go on both arms;
ADR-0026 then dropped the whole view, Stage A included. Nothing exists under `cli/` or `eval/` for it:
the dry-run script lived on a throwaway branch and its rating sheets stay under `local-data/eval/so-what/`,
uncommitted. `eval/score.py`'s selfcheck aside, only the two sets above are live.

## Controls

| Control | Where |
| --- | --- |
| Approval gate | None per call; the operator's gate is installing the job at all |
| Kill switch | `/hindsight:ops uninstall` removes both launchd jobs (the database stays); no in-app toggle. Removing `claude` from PATH pauses model calls without stopping the mechanical run |
| Rate limit | The CLI's own limit; `LimitExhausted` is the designed pause, not an error |
| Retries | Per session, once per nightly run, unbounded; per narrative, once per run while the ledger hash is unmatched |
| Cost ceiling | At most one A1 call per part (plus one merge) per new/grown session, at most one A2 call per declaring project whose ledger moved |

## What the model can and cannot cause

- Can: write one markdown entry per session and one JSON narrative per project, both shape-checked.
- Cannot: read files, run tools, reach the network, alter transcripts, or influence which sessions are analysed next. A prompt-injection payload in a transcript can at most produce a malformed or misleading entry — malformed is rejected; misleading is what the eval sets exist to catch.
- Rendering of model prose is HTML-escaped server-side; `what.js` re-adds `<b>`/`<code>` from escaped text only ([flows.md](flows.md) F4).

## Other automation

- Impeccable's Claude Code hooks (`PostToolUse`, `Stop`) run in the *development* session on this repo, not in the product. See `.claude/my-process.md`.
- No webhooks, no external automation, no scheduled model calls outside A1/A2.
