# Automation — the model passes

Two LLM workflows, both inside the analysis run, both through `claude -p` as a subprocess. No
agents, no tool calling, no webhooks. Nothing the model emits is executed; everything it emits is
gated, then stored as prose or JSON.

## A1 — What-pass (one audit entry per session)

| | |
| --- | --- |
| Trigger | Every `pending`/`partial` session on each analysis run; automatic, no approval gate |
| Owner | `analyze.process_session` → `call_cached` → `default_model_runner` (`analyze.py:598-693, 745-761`) |
| Command | `claude -p --model claude-haiku-4-5-20251001`, prompt on stdin, `cwd=REPO`, 300 s timeout |
| Inputs the model may read | The extract only: user and assistant message text (1,500 chars per piece, 180 K per part) and `[Edit: <path>]` markers. Tool results, file contents, `~/.claude` config: never (`extract.py:19, 42-44, 61-63`) |
| Tool surface | **None.** `-p` is a single completion; no MCP, no filesystem, no shell is reachable from the prompt |
| Steering (prompt) | `build/prompts/what-v3.txt` — extract bracketed by the contract before and after (ADR-0016); multi-part sessions merged by `merge-v1.txt` over the part outputs only |
| Hard guardrails (not prompt) | Model pin; serial calls; `valid_entry`: after fence-stripping, output must be exactly `SKIP` or start with `###`, else not written, not cached, session → `partial` (`analyze.py:592-615`); hindsight's own sessions excluded by prompt signature before extraction (ADR-0003) |
| Output contract | Markdown: `### <title>` then Did / Decided / Setup-changes sections, or the literal `SKIP`. Parsed further only for display (`serve.py:148`, `what.js`) |
| App-owned side effects | INSERT OR REPLACE `audit(session_id, project, date, skip, markdown, prompt_version, model, adr_count)`; `sessions.status`, `audited_size`; cache file on disk |
| Agent-owned | Nothing. The model proposes an entry; the app decides whether it is well-formed and records it verbatim |
| Failure handling | Timeout → `None` → `partial`, retried next run. `FileNotFoundError` (no CLI) or "limit" in stderr → `LimitExhausted`, loop stops, resumes next run. No retry bound by design (ADR-0016) |
| Audit trail | `audit.prompt_version` + `audit.model` on every row; raw output in `local-data/analysis/what-v3/`; rejects echoed (80 chars) to `~/Library/Logs/hindsight/analyze.log` |
| Rate limit / kill switch | The CLI's own rate limit is the ceiling. Kill switch: `analyze.py uninstall` (nightly) — no in-app toggle |

## A2 — Status narrative (one per declaring project)

| | |
| --- | --- |
| Trigger | End of each unpaused run, per project with a valid `.claude/my-process.md` and ≥ 1 phase run; skipped when the ledger hash is unchanged (`analyze.py:697-739`) |
| Inputs the model may read | `{project, as_of, stages, runs: [{stage, start, end, titles}]}` — audit **titles** only (`how.py:295`). No transcript text, no file contents |
| Tool surface | None (same `claude -p`) |
| Steering | `build/prompts/status-v1.txt` + the ledger JSON appended (`score.ledger_prompt`) |
| Hard guardrails | `score.parse` (JSON, fence-tolerant) then `score.contract` floors M3–M6: every line shares ≥ 2 content words with the ledger (traced); every line carries a date inside the run window (dated); a `Now` line names the current stage and start date; each of `Built`/`Reversed`/`Now` is a list within `BOUNDS` (8/4/3), `Built` and `Now` non-empty (`score.py:64-138`) |
| Output contract | JSON `{"Built": [..], "Reversed": [..], "Now": [..]}` |
| App-owned side effects | INSERT OR REPLACE `status_narrative(project, ledger_hash, narrative, prompt_version, model, generated_at)`; on rejection nothing is written and the stale row stays with a mismatching hash (retried next run) |
| Failure handling | Whole pass wrapped; any exception prints `narrative pass failed` and the mechanical tail still runs (`analyze.py:954-960`) |
| Standing evaluation | `eval/` — frozen ledger set and what-pass regression set, mechanical scoring, no judge (`eval/README.md`). `score.py` is the same code used at write time, so the eval and the gate cannot drift apart |

## What the model can and cannot cause

- Can: write one markdown entry per session and one JSON narrative per project, both shape-checked.
- Cannot: read files, run tools, reach the network, alter transcripts, or influence which sessions are analysed next. A prompt-injection payload in a transcript can at most produce a malformed or misleading entry — malformed is rejected; misleading is what the eval set exists to catch.
- Rendering of model prose is HTML-escaped server-side; `what.js` re-adds `<b>`/`<code>` from escaped text only ([flows.md](flows.md) F4).

## Other automation

- Impeccable's Claude Code hooks (`PostToolUse`, `Stop`) run in the *development* session on this repo, not in the product. Out of scope here; see `.claude/my-process.md`.
- No webhooks, no external automation, no scheduled model calls outside A1/A2.
