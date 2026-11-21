# Automation — the model passes

Two LLM workflows, both inside the analysis run (`cli/analyze.py`, launchd at 03:00 or on demand), both
through `claude -p` as a subprocess. No agents, no tool calling, no SDK, no webhooks. Nothing the model
emits is executed; everything it emits is gated, then stored as prose or JSON. A third model consumer,
the evaluation harness under `eval/`, is operator-run only. Two Claude Code hooks (capture, health) are
automation too, but make no model calls.

## The transport — one call shape for both passes and the what/status-v2 evals

`default_model_runner` → `claude -p --model claude-haiku-4-5-20251001 --tools "" --strict-mcp-config --settings '{"disableAllHooks": true}'`,
prompt on stdin, `capture_output`, `timeout=300`, `cwd=$TMPDIR/hindsight-model-cwd` (an empty folder). Calls are serial (a deliberate pause boundary).

| | |
| --- | --- |
| Auth | None of Hindsight's own. The child uses whatever auth the `claude` CLI has — subscription login, or an API key if the CLI is set up that way |
| Environment | Inherited whole from the parent (no `env=`): `PATH`, `TZ` (set from `HINDSIGHT_TZ`) and any `ANTHROPIC_*` variable in the shell or plist apply |
| What the flags remove | Every tool (`--tools ""`), every MCP server (`--strict-mcp-config`, no config given), every hook (`disableAllHooks`), and project `CLAUDE.md`/settings (the empty cwd) |
| What they do not remove | The user's `~/.claude/CLAUDE.md` and user settings still load. `--bare` would drop them but also drops subscription auth (code comment, ADR-0003) |
| Pin | `analyze.MODEL`; `eval/what_cases.json`, `eval/status_v2_cases.json` and `eval/cases.json` carry the same string |

**Failure mapping:** timeout → `None` (session `partial`). No `claude` on `PATH` → `LimitExhausted`.
Non-zero exit whose stderr contains `limit` (any case) → `LimitExhausted` — a bare substring match, flagged
`ponytail:` in the code: a non-limit error mentioning the word pauses the whole run, and a real limit
message without it is just a failed session. Any other non-zero exit → `None`, first 200 chars of stderr logged.

## A1 — What-pass (one audit entry per session)

| | |
| --- | --- |
| Trigger | Every `pending`/`partial` session on each run; automatic, no approval gate. A session whose newest raw record was captured inside `LIVE_WINDOW_S` (300 s), parent or subagent, is skipped until the next run (`held_live`) |
| Owner | `classify_and_extract` (extracts every selectable session, or marks it `lost`, before any call) → `process_session` → `call_cached` → `default_model_runner`; loop in `what_pass` |
| Inputs the model may read | The extract only (`cli/extract.py`, over the parent's raw records): user and assistant text, 1,500 chars per piece, 180 K chars per part, plus `[Edit\|Write\|MultiEdit\|NotebookEdit: <path>]` markers. Dropped: tool results, `isMeta` lines, slash-command and local-command messages, subagent transcripts (ADR-0019). **No redaction:** a secret a user pasted or an assistant echoed goes to the model verbatim, with absolute file paths |
| Steering (prompt) | `cli/prompts/what-v3.txt` — the extract fills its `{{EXTRACT}}` slot inside a `BEGIN/END TRANSCRIPT EXTRACT` block, named as data, with the output contract restated *after* it (ADR-0016). Multi-part sessions: `merge-v1.txt` over the part outputs only. Trivial-session `SKIP` is a prompt instruction, not code |
| Hard guardrails (not prompt) | The transport flags above · model pin · self-exclusion: a transcript whose head matches `ANALYSIS_SIGS` (hindsight's own prompts) goes to `excluded_sessions`, never audited (ADR-0003) · `valid_entry` (#38): after fence-stripping the output must start with `SKIP` or `###`, else not written, not cached, session → `partial` · cache dir keyed by `PROMPT_VERSION`, so a version bump never reuses stale output · re-audit only once ≥ 25 % of the parent transcript (`REAUDIT_SHARE`, against `audited_size`) is unseen; compacted sessions never |
| Output contract | Markdown: `### <title>` then Did / Decided / Setup-changes, or the literal `SKIP`. Parsed further only for display (`serve.py`, `what.js`) |
| App-owned side effects | `INSERT OR REPLACE audit(session_id, project, skip, markdown, prompt_version, model, adr_count)` — `adr_count` computed from `tool_events`, never by the model; `sessions.status` → `done`, `audited_size`; cache file under `<work dir>/what-v3/` (`$CLAUDE_PLUGIN_DATA/analysis`, else `<plugin root>/local-data/analysis`) |
| Agent-owned | Nothing. The model proposes an entry; the app decides whether it is well-formed and records it verbatim |
| Failure handling | Timeout, non-zero exit or gate rejection → `partial`, retried next run, **no retry bound by design** (ADR-0016) — a deterministically failing part is paid for every night. `LimitExhausted`: the session loop stops, the narrative pass is skipped, the mechanical tail still runs, everything unreached resumes next run |
| Logging | `audit.prompt_version` + `audit.model` per row; `rejected <cache file>: '<80 chars>'`, `model call exited N: <200 chars>`, timeouts; `claude --version` once per run; all to `<home>/logs/analyze.log` under the nightly (`--log`) |

## A2 — Status narrative (one per declaring project)

| | |
| --- | --- |
| Trigger | After the what-pass of each *unpaused* run, per project whose process declaration resolves `valid` (`how.resolve_declaration`: root `local-process.md`, else the house master, ADR-0032) and has ≥ 1 run; skipped when `(ledger_hash, STATUS_VERSION, MODEL)` already matches a stored row (`refresh_narratives`) |
| Inputs the model may read | `{project, as_of, stages, runs, adrs, changes}` — `how.ledger`: runs carry stage, start/end day and audit **titles** (themselves model-written by A1); ADR headers `{number, date, title, status, touches}` read mechanically from `<root>/docs/adr` only (ADR-0035 §3); `changes` are title-stated changes derived mechanically (ADR-0040). No transcript text, no other file contents. Runs include `off-script` ones and treat `/compact` as a session boundary (#17, ADR-0010 amended) |
| Steering | `cli/prompts/status-v2.txt` + the ledger JSON appended (`score.ledger_prompt`, shared with the eval) |
| Hard guardrails | The transport flags · `score.parse` (JSON, fence-tolerant; non-JSON → skipped) then `score.contract_v2`, floors M3–M6 (`eval/score.py`): traceability to the ledger or named ADRs, dates inside the run span or an ADR date, a `Now` line naming the current stage and start day, list bounds. Same function as the eval — no second implementation |
| Output contract | JSON `{"Standing": [..], "Superseded": [..], "Now": [..]}` (status-v2, ADR-0035) |
| App-owned side effects | `INSERT OR REPLACE status_narrative(project, ledger_hash, narrative, prompt_version, model, generated_at)`. On rejection nothing is written: the last good row stays and renders **stale** (hash mismatch); with no row ever stored the view shows the mechanical status |
| Failure handling | `LimitExhausted` → pass skipped, retried next run; any other exception is `how narrative failed:` and the backstop, sunk-cost and compaction jobs still run (ADR-0038) |

## Not model calls, but shaping what the model sees

- **Schema-drift guard** (ADR-0020, ADR-0037): `check_drift` and the cross-check run after derivation, before the model loop, only when no session is due. A trip writes a `breakage` row and a banner on every view, optionally a macOS notification; **the run and both model passes continue** through it. `analyze.py acknowledge-breakage <id>` closes a row; a guard bug is caught and logged, never fatal.
- **Growth / re-audit** (`invalidate_grown`): derived tables re-derive on any growth; the audit entry is rewritten only past `REAUDIT_SHARE`, so a resumed session does not re-fire A1 nightly — but when it does, every part is paid again.
- **Compaction** (ADR-0034): raw records past `HINDSIGHT_RAW_DAYS` go, with the session's extract and cached outputs; pending/partial sessions are held, never compacted unaudited.

## Hooks (no model calls)

| Hook | Reads | Writes | Guardrails |
| --- | --- | --- | --- |
| Capture (`capture.py`, async) | Payload `transcript_path` / `agent_transcript_path` / `cwd`; the transcript bytes past the high-water | `raw_records` (verbatim, zlib), `transcripts`, folder inode, condition-6 `breakage`, `health`. Runs `init_db`, so it can fire a migration | Never parses transcript JSON; session id from the path, never the payload; never raises into the session |
| Health (`health.py`, sync) | DB read-only; `launchctl print` | `<home>/current` (atomic re-point), `launchctl kickstart -k` on the listener — no prompt | Output only a `systemMessage` (operator-visible, not model context); silent when healthy; exceptions become one line |

## A3 — Evaluation harness (`eval/`, operator-run, never nightly)

| Set | Runner · manifest · scorer | Calls | Verdict |
| --- | --- | --- | --- |
| Status narrative (ADR-0035) | `eval/run_v2.py` · `eval/status_v2_cases.json` (5 frozen ledgers + ADR headers, #95) · `eval/score.py` `score_v2` M1–M6 | 3 rounds × 5 × `default_model_runner`, serial; asserts the manifest pin equals `analyze.MODEL` | ACCEPT only if every case passes in all three rounds |
| What-pass (ADR-0016) | `eval/what_run.py` · `eval/what_cases.json` (20 case ids; extracts under gitignored `local-data/eval/what/extracts/`) · `analyze.valid_entry` itself | 20 × `default_model_runner`, `ThreadPoolExecutor(4)` | ACCEPT only if every output passes the gate and every expected SKIP/entry holds |
| Status v1 (retired from the live pass, #96; kept as the record) | `eval/run.py` · `eval/cases.json` (6 cases) · `score` | 6 × `ThreadPoolExecutor(6)` — **its own `claude -p --model <pin>`, without the transport flags**: tools, MCP servers, hooks and the caller's cwd all apply | ACCEPT only if every case passes |

Outputs land under `local-data/eval/…/runs/<tag>/` (untracked). The runners are the gate before any
edit to a prompt file or to `MODEL`; the threshold is decided before the edit (`eval/README.md`). **The gate is process
only:** nothing — pre-commit (plugin validation and the denylist), a test, or CI (there is no `.github/`) — blocks a
prompt or pin change that skipped it.

**So-what view — dropped, no code.** ADR-0021–0025 designed a fourth view with a conditional model
synthesis (Stage B) and fixed its go/no-go before a dry run (#27). The dry run was no-go on both arms;
ADR-0026 then dropped the whole view, Stage A included. Nothing exists under `cli/` or `eval/` for it:
the dry-run script lived on a throwaway branch and its rating sheets stay under `local-data/eval/so-what/`,
uncommitted.

## Controls

| Control | Where |
| --- | --- |
| Approval gate | None per call; the operator's gate is installing the job at all |
| Kill switch | `/hindsight:ops uninstall` removes both launchd jobs (the database stays); `stop` stops only the listener. No in-app toggle. Removing `claude` from the baked `PATH` pauses model calls without stopping the mechanical run; disabling the plugin stops the hooks |
| Rate limit | The CLI's own limit; `LimitExhausted` is the designed pause, not an error |
| Retries | Next run only, no in-run retry or backoff. Per session, unbounded; per narrative, while the ledger hash is unmatched |
| Spend cap | **None.** No cap on sessions, calls or tokens per run. Per run: one A1 call per uncached part (plus one merge) per new, failing or ≥ 25 %-grown session, one A2 call per declaring project whose ledger moved. A first run over a large backlog calls back to back until done or limited. On an API-key CLI this is uncapped metered spend |
| Concurrency | Single-flight lock: one analysis run at a time (ADR-0038 §5) |

## What the model can and cannot cause

- Can: write one markdown entry per session and one JSON narrative per project, both shape-checked.
- Cannot: read files, run tools, reach MCP servers or the network through tools, alter transcripts, or influence which sessions are analysed next. A prompt-injection payload in a transcript can at most produce a malformed or misleading entry — malformed is rejected; misleading is what the eval sets exist to catch. It does still see the user's `~/.claude/CLAUDE.md`.
- Rendering of model prose is HTML-escaped server-side; `what.js` re-adds `<b>`/`<code>` from escaped text only ([flows.md](flows.md) F4).

## Code vs ADR

- **ADR-0036 §6** budgets the health hook at about 100 ms. `hooks.json` allows `timeout: 5`, and `check` can spend 1 s on each `launchctl` call plus a 1 s SQLite timeout.
- **ADR-0003** says "recognise the limit error"; the code matches any stderr containing `limit` (above).
- **ADR-0038 §5** puts the lock "in Hindsight home"; the code puts it beside the DB. Same by default, different under `--db`.

## Other automation

- Impeccable's Claude Code hooks run in the *development* session on this repo, not in the product.
- No webhooks, no external automation, no scheduled model calls outside A1/A2.
