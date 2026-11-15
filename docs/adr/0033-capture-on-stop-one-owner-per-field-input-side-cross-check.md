# ADR-0033: Capture runs on `Stop`, each field has one owning source, and an input-side token cross-check is a breakage

**Date:** 2026-11-15 · **Status:** accepted · **Supersedes:** ADR-0005 · **Amends:** ADR-0001, ADR-0020 · **Decides:** issue #68 (map #59, v2 audit core)

## Context

v2 captures raw records on the hook, not overnight (framing brief, lessons 2–5). [Hook payloads](https://github.com/dempseydata/hindsight/issues/61) established that every hook event carries `transcript_path`, that `SubagentStop` adds `agent_transcript_path`, and that `SessionEnd` is best-effort. It also established that OTel emits hook telemetry (`hook_execution_complete`), which falsifies the premise ADR-0005 rests on. The framing brief asked for a reconciliation between OTel and transcript daily token totals, with a threshold fixed in advance.

Measured on the local store on 2026-11-15, over sessions both sources saw:

- **Output tokens do not reconcile.** The transcript's daily output total runs 0–78% below OTel's. The undercount is structural, so a gap tells you nothing about drift.
- **Input-side tokens do reconcile** (input + cache read + cache creation). From 2026-11-11 the gap opened to −10% to −18%. The cause was `prompt_suggestion` side requests rising from 10 to 95, and side requests are never written to the transcript. With the side-request sources excluded, there were 61 days with at least 50 shared requests: 51 had a gap within 1%, 60 within 3%, and the largest gap was 3.6%.

## Decision

1. **Trigger.** One hook, registered on `SessionStart`, `Stop` and `SubagentStop`. `Stop` and `SubagentStop` run capture for the transcript they name, appending from its high-water mark (ADR-0031 §2). `Stop` fires on every turn, so a session is captured as it goes, not when it ends. `SessionStart` records the folder identity (ADR-0018). `SessionEnd` is not used. The nightly sweeps every transcript whose size has passed its high-water mark, so a missed firing (a crash, a kill, a timeout) means capture runs late, never that records are lost.
2. **Write path.** The hook writes straight to SQLite (WAL mode, a busy timeout) and runs detached from the turn: a session never waits on capture. Like the listener, it is a short-lived writer started by Claude Code. Nothing new stays resident, so ADR-0001's boundary test holds. How it detaches belongs to [Plugin packaging](https://github.com/dempseydata/hindsight/issues/69).
3. **One owning source per field.**
   - **OTel owns:** tokens and cost (`api_request`), tool accept/reject decisions, API errors and retries, and hook timing (`hook_execution_complete`).
   - **The transcript owns:** conversation text, tool calls with their inputs (the trail, skill invocations, command grains, path markers), and error text (ADR-0027).
4. **Token fallback, chosen per session and labelled.** A session's tokens come from OTel if OTel saw that session. Otherwise they come from its transcript-derived or `v1` usage, labelled with that source and with the transcript's output undercount stated. Sources are never mixed within one session.
5. **Cross-check: a fourth breakage condition, at tier *problem*.** The threshold is frozen as of this ADR.
   - **Compared:** for each completed local day, OTel input-side tokens against transcript input-side tokens, over sessions both sources saw.
   - **Excluded from the OTel side:** requests whose `query_source` is on the side-request denylist (`prompt_suggestion`, `generate_session_title`, `web_search_tool`, `web_fetch_apply`, `away_summary`, `agent_summary`).
   - **Volume floor:** a day with fewer than 50 shared requests is skipped.
   - **Trip:** an absolute gap above **5%** writes one breakage row for that day.
   - **When it runs:** after derivation has caught up, and never on the current day.
   - **A new side-request source** trips the check visibly. The operator then adds it to the denylist, as a code change.
   - **Acknowledging** a row closes that day's row and shifts no baseline.
6. **Health rows are written by collection.** There is one row per source: the OTel listener, the capture hook, and the nightly or analysis run. Each holds the last success time, the last error time and the last error text. Staleness is judged by comparing sources, not by a wall-clock age. For example, if OTel has seen a `Stop` for a session more recently than capture has captured anything for it, capture is broken. How health is shown and the `SessionStart` check belong to [Plugin packaging](https://github.com/dempseydata/hindsight/issues/69).
7. **Self-instrumentation is retired.** The `hindsight.hook` OTLP event and its `hook.cpu_ms` and `hook.duration_ms` figures go. The hook panel reads `hook_execution_complete`, whose duration is the firing's true wall time, which ADR-0005 said could not be captured.

## Considered options

- **Trigger on `SessionEnd`.** Best-effort, with a history of bugs. A session's records would wait for its end.
- **Capture through the listener.** A first capture can be many megabytes, which is too much for an HTTP hop, and the turn would block on it.
- **One owner per field with no fallback.** Every session OTel never saw would read *not captured*, which is 82% of history (ADR-0031 §7), including the data we do hold.
- **Reconcile output tokens or total tokens.** Output doesn't reconcile, and a total is dominated by cache reads while carrying the output undercount anyway.
- **Reconcile all OTel requests.** This would have tripped from 2026-11-11 on a difference of scope, not of shape.
- **An allowlist of conversation sources.** A new conversation source would be dropped silently. The denylist makes a new side source trip instead.
- **Freshness as a fixed age per source.** A quiet weekend and a dead hook look the same.

## Consequences

- The 5% figure was chosen after the 61-day series had been measured. That is calibrating a guard, not grading a change, and it is frozen from here. Revisiting it needs a new ADR, never a quiet edit.
- The breakage table gains a day-level condition with no record version. ADR-0020's acknowledge-as-baseline rule does not apply to it.
- The cross-check needs `query_source` on `api_request`, which is an OTel attribute, so it works on a documented field. A day OTel missed (the listener down) has no shared sessions and is skipped, never tripped.
- Hook rows written by v1 (8,276 `hindsight.hook` events) stay in `otel_events`, but nothing reads them.
- Not verified: whether `hook_execution_complete` names the specific hook command, and whether this Claude Code version supports async hooks. The second belongs to issue #69.
