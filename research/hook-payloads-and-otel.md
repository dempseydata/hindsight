# Hook payloads and OTel fields: what carries the transcript, for which sessions

Research for [#61](https://github.com/dempseydata/hindsight/issues/61), part of map #59. Read 2026-11-13 against Claude Code 2.1.325 docs.

**Sources.** H = [Hooks reference](https://code.claude.com/docs/en/hooks) · M = [Monitoring (OpenTelemetry)](https://code.claude.com/docs/en/monitoring-usage) · C = [Changelog](https://code.claude.com/docs/en/changelog) · D = [`.claude` directory](https://code.claude.com/docs/en/claude-directory) · S = [Sessions](https://code.claude.com/docs/en/sessions). **Store** = a read-only count over v1's own `otel_events` (attribute *names* and event counts only, no values), 2026-08-16 → 2026-11-14.

Each claim is marked **verified** (doc says so, URL given) or **inferred** (reasoned, or observed in the store but not stated by a doc).

## Answer

1. **Every hook event carries `transcript_path`.** It is a common input field, and every event's example payload in H shows it (33 events). It is always the *parent* session's transcript. Only `SubagentStop` adds `agent_transcript_path`, the subagent's own file under `subagents/`. **verified** (H, common input fields; SubagentStop input)
2. **Which events fire where.**
   - **Subagents:** `SubagentStart` and `SubagentStop` fire per subagent. `Stop` fires for the main agent only. Settings hooks also fire *inside* a subagent for tool events, with `agent_id`/`agent_type` added. **verified** (H)
   - **Resumed sessions:** `SessionStart` fires with `source: "resume"` (or `"fork"`). `SessionEnd` fires on exit and on an interactive `/resume` switch (`reason: "resume"`). **verified** (H)
   - **Desktop app (Code tab):** H says the same events fire "wherever it runs … the Desktop app". **verified** (H). The store agrees: `SessionStart`, `Stop` and `SubagentStop` firings come overwhelmingly from `terminal.type = non-interactive`. That this tag means Desktop is **inferred**.
3. **OTel carries everything mechanical:** tokens and cost per request, every tool decision and result with its error, API errors, retries, refusals, compactions, subagent completion and hook execution. It is keyed by `session.id`, `prompt.id` and `agent_id`. A transcript has to be read only for conversation text. Even that is available from OTel behind opt-in flags, but truncated, and only for user prompts and assistant *text*: no thinking, no tool-use blocks. **verified** (M)
4. **One correction for v1's record.** OTel *does* emit hook telemetry: `hook_execution_start`, `hook_execution_complete` and `hook_registered`. The store has held about 68k of them since its first day, 2026-08-16. The definition-phase finding "Hook execution timings — falsified", which ADR-0001's amendment and ADR-0005 rest on, is itself wrong. The probe most likely missed them. **verified** (M; Store). The probe-miss explanation is **inferred**.

## 1. Hook payloads

### Common input fields (all events) — verified, H § Common input fields

| Field | Note |
| --- | --- |
| `session_id` | |
| `prompt_id` | Equals OTel `prompt.id`, so it joins hook rows to telemetry. Absent before the first user input |
| `transcript_path` | Parent transcript. "Written asynchronously and may lag the in-memory conversation". It may lack the current turn when a hook fires |
| `cwd` | |
| `scratchpad_dir` | v2.1.257+ |
| `permission_mode` | Not on every event |
| `effort` | `{level}`. Present on tool-context events, `Stop` and `SubagentStop` |
| `hook_event_name` | |
| `agent_id`, `agent_type` | Present when the hook fires inside a subagent or teammate, or under `--agent` |

### Event-specific fields that matter for capture — verified, H per-event "input" sections

| Event | Adds | Capture relevance |
| --- | --- | --- |
| `SessionStart` | `source` (`startup`/`resume`/`clear`/`compact`/`fork`), `model` (optional), `agent_type`, `session_title`. On resume or fork with prior output: `seconds_since_last_response`, `context_tokens`, `prompt_cache_likely_expired`, `estimated_cache_write_usd` (v2.1.251+) | Marks resumes explicitly, so ADR-0013's resume detection could read this instead of inferring from growth |
| `UserPromptSubmit` | `prompt` | The prompt text, verbatim |
| `Stop` | `stop_hook_active`, `last_assistant_message`, `background_tasks`, `session_crons` | H: use `last_assistant_message` rather than reading the transcript, because the file "isn't guaranteed to include the final message at Stop time". Does not fire on a user interrupt. API errors fire `StopFailure` instead |
| `StopFailure` | `error` (type: `rate_limit`, `overloaded`, `billing_error`, …), `error_details`, `last_assistant_message` (the API error string) | |
| `SubagentStart` | `agent_id`, `agent_type` | Also fires when a subagent is resumed, and per message for in-process teammates |
| `SubagentStop` | `stop_hook_active`, `agent_id`, `agent_type`, **`agent_transcript_path`**, `last_assistant_message`, `background_tasks`, `session_crons` | Also fires for internal agents (prompt suggestions, `/btw`). For those, `agent_type` is the session's own agent, or `""` |
| `SessionEnd` | `reason`: `clear`, `resume`, `logout`, `prompt_input_exit`, `other` | Default timeout 1.5 s (`CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` or a per-hook `timeout` raises it). No decision control |
| `PostToolUse` | `tool_name`, `tool_input`, `tool_response`, `tool_use_id`, `duration_ms` | Full tool result |
| `PostToolUseFailure` | `tool_name`, `tool_input`, `tool_use_id`, `error`, `is_interrupt`, `duration_ms` | Does not fire for validation rejections or permission denials (`PermissionDenied` covers those) |
| `PreCompact` / `PostCompact` | `trigger`, `custom_instructions` / `compact_summary` | |

### Which sessions fire them

- Settings, policy and plugin hooks run inside subagents. Tool events there carry `agent_id`/`agent_type`. A `Stop` hook declared in a subagent's frontmatter is converted to `SubagentStop`. **verified** (H § Hooks in skills and agents)
- The same hook events fire in the terminal, IDE extensions, the Desktop app and cloud sessions. Cloud sessions do not read the local `~/.claude/settings.json`, so v1's user-scope hook will not run there. **verified** (H, intro and § Hook locations)
- In `-p`/SDK runs, async hooks still running at teardown are killed. **verified** (H § async hooks). Claude Desktop hosts Claude Code through the SDK's `canUseTool` path. **verified** (H § Notification). So Desktop sessions are SDK-hosted. **inferred**
- Store, as observed: `SubagentStop` fired 571 times, 23 of them from nested subagents (with `agent_id`). `SessionStart` fired 746 times and `Stop` 2,817. More than 99% of each came from `terminal.type = non-interactive`, the rest from `Apple_Terminal`. **inferred** that non-interactive equals Desktop: `app.entrypoint` would say so (`claude-desktop` for the Code tab, verified in M), but it is off by default (`OTEL_METRICS_INCLUDE_ENTRYPOINT`) and absent from the store.
- **`SessionEnd` is unobserved.** No `SessionEnd` hook is registered (`hook_registered` lists none). Hook telemetry fires only for events that have a matching hook, so the store cannot say whether `SessionEnd` fires reliably in Desktop. The docs do not single Desktop out either. The changelog shows a history of it not firing: on interactive `/resume` (fixed 2.1.79) and on exit with a background command running (fixed 2.1.300). Its 1.5 s default budget is tight. Treat `SessionEnd` as best-effort, and keep a sweep as the backstop. **inferred**
- Past `transcript_path` bugs: it pointed to the wrong directory for resumed or forked sessions (fixed 2.1.72), and to a non-existent path after `EnterWorktree` (fixed 2.1.141). **verified** (C). Validate that the path exists before reading it.

## 2. What OTel carries (so the transcript is read only for what it alone holds)

Common to all events: `session.id`, `prompt.id`, `event.timestamp`, `event.sequence` (per *process*, not per session, so sort by timestamp), and `agent_id`/`parent_agent_id` (v2.1.310+, absent on main-session events). Metrics never carry `prompt.id` or `agent_id`. **verified** (M § Standard attributes, § Event correlation)

| Need | OTel source | Fields |
| --- | --- | --- |
| Tokens / cost per request | `api_request` event | `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `cache_creation_5m_tokens`, `cache_creation_1h_tokens`, `cost_usd`, `cost_usd_micros`, `model`, `duration_ms`, `query_source`, `request_id`, `effort`, `speed`, plus attribution `agent.name`, `skill.name`, `plugin.name`, `mcp_server.name`, `mcp_tool.name` |
| Tokens / cost aggregate | `claude_code.token.usage`, `claude_code.cost.usage` metrics | `type`, `model`, `query_source` (`main`/`subagent`/`auxiliary`), same attribution |
| Tool decisions | `tool_decision` event; `code_edit_tool.decision` metric | `tool_name`, `tool_use_id`, `decision` (accept/reject), `source` (`config`/`hook`/`user_permanent`/`user_temporary`/`user_abort`/`user_reject`), `permission_mode`, `tool_source`, `classifier_verdict` |
| Tool outcomes / errors | `tool_result` event | `success`, `duration_ms`, `error_type`, `error` (full text only with `OTEL_LOG_TOOL_DETAILS=1`), `tool_input`/`tool_parameters` (details on; values truncated at 512 chars, about 4K per payload), sizes. Rejected calls emit no `tool_result` |
| API errors | `api_error`, `api_retries_exhausted`, `api_refusal` | `error`, `status_code`, `attempt` / `total_attempts`, `total_retry_duration_ms` / refusal `category` |
| Compaction | `compaction` | `trigger`, `success`, `pre_tokens`, `post_tokens`, `duration_ms`, `error` |
| Subagents | `subagent_completed` | `agent_type`, `agent.source`, `total_tool_uses`, `duration_ms`, `model`/`final_model`. `total_tokens` covers the *final request only*, so use the token metric with `query_source=subagent` for totals |
| Hook execution | `hook_execution_start` / `_complete`, `hook_registered` | `hook_event`, `hook_name`, `num_hooks`, `num_success`, `num_blocking`, `num_non_blocking_error`, `num_cancelled`, **`total_duration_ms`** (wall clock of all matching hooks), output-size counts (v2.1.280+) |
| Session counts / resume | `claude_code.session.count` metric | `start_type`: `fresh`/`resume`/`continue`/`agents_view` |
| Transcript retention | `retention_sweep` | `transcripts_deleted`, `period_days`, … — tells you when transcripts were pruned (relevant to ADR-0015 `lost`) |

All rows above are **verified** (M § Metrics, § Events).

### What only the transcript holds

- **User prompt text.** Redacted in OTel unless `OTEL_LOG_USER_PROMPTS=1`. The store has it redacted, so this flag is off today. The `UserPromptSubmit` hook payload has it verbatim regardless. **verified** (M, H); flag state from Store
- **Assistant text.** `assistant_response` carries it only with `OTEL_LOG_ASSISTANT_RESPONSES=1` (or inherited from the prompts flag), and only text blocks: thinking and tool-use blocks are excluded. `Stop`/`SubagentStop` `last_assistant_message` gives the *final* message of each turn only. **verified** (M, H)
- **Tool result content.** Only via tracing with `OTEL_LOG_TOOL_CONTENT=1`. The hook `tool_response` on `PostToolUse` has it. **verified** (M, H)
- **Full fidelity, including history.** `OTEL_LOG_RAW_API_BODIES=file:<dir>` writes untruncated request and response bodies to disk. This is a transcript substitute in all but name, and very large. **verified** (M)
- Content attributes truncate at `CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH` (default 61,440 UTF-16 units). **verified** (M)
- **Stability.** The transcript entry format is "internal to Claude Code and changes between versions" (S). Joins to it via `message.uuid`, `request_id` → `requestId` and `tool_use_id` are explicitly version-specific (M). The hook and OTel field lists are the documented contract. The JSONL is not. **verified**

So the mechanical half of v2's raw capture can come from OTel and hook payloads alone. A transcript read is needed for conversation text (unless the content flags are turned on), and for anything in the gap between what OTel truncates and what the what-pass extract needs. **inferred**

## 3. Implications for v1's record (not decisions; for the map)

- **ADR-0001 amendment and ADR-0005's premise are falsified.** OTel's `hook_execution_complete.total_duration_ms` is the spawn-side wall clock that ADR-0005 says "is visible only to the spawning harness and is not captured". It is captured, and it has been in the store since day one. `build/hook.py` remains the only source for the SessionStart folder inode (ADR-0018) and for per-firing CPU. Its timing role may be redundant. **verified** (M; Store) / judgement **inferred**
- **A hook already passes `transcript_path` on every firing.** `build/hook.py` reads only `hook_event_name`, `session_id` and `cwd`. A v2 capture hook on `Stop` + `SubagentStop` (+ `SessionEnd`, best-effort) gets both transcript paths with no directory glob. The ADR-0019 subagent layout is confirmed as documented (D: `projects/<project>/<session>/subagents/`). **verified** (H, D)
- **Desktop transcripts are exempt from the retention sweep at any age** (v2.1.248+, unless `desktopSessionCleanupPeriodDays` is set). CLI transcripts follow `cleanupPeriodDays` (default 30). This bears on ADR-0015's loss model. **verified** (D)
- Turning on `OTEL_METRICS_INCLUDE_ENTRYPOINT=true` would make the Desktop/CLI split a fact rather than an inference. **verified** that the flag exists (M)

## Where the docs are silent

- Whether `SessionEnd` fires when the Desktop app closes a session window or quits, or when a process is killed.
- Whether `Stop` fires for a turn ended by an API error *and* retried successfully (only "API errors fire StopFailure instead" is stated).
- Ordering guarantees between the hook firing and the transcript flush, beyond "may lag".
- What `terminal.type = non-interactive` maps to.
