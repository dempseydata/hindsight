# #61 Command grain: capture user-typed slash commands in the substrate scan

state: closed · labels: wayfinder:task · opened: 2026-08-26 · closed: 2026-08-27

## Question

Land the **command grain** in the substrate scan: parse `<command-name>` markers verbatim from transcripts' user messages into a new grain type, so user-typed slash commands — invisible to `tool_events` because a typed command injects its skill without a Skill tool call — become queryable. The probe's motivating number: this folder's transcripts hold 196 `/wayfinder` invocations while `tool_events` holds zero.

Scope:

- Schema + scan: a new grain row type (or table — implementer's call against the existing grain design from #42), carrying the command name verbatim, session, and timestamp.
- Backfill existing synced sessions, same posture as #42's backfill.
- Note: `build/extract.py` line 57 deliberately *skips* `<command-name>` messages for the what-pass — capture must not disturb that skip; the grain belongs to the substrate scan in `analyze.py`.
- CONTEXT.md already defines the term (command grain); update if the implementation diverges from the definition.

AFK task: mechanical parsing, decided by ADR-0010 — nothing to decide beyond implementation detail.


## Scoping from the coverage research (#59)

- **The migration must reset `skipped_records` for `done` sessions** (precedent in analyze.py's existing migration block), or the ~70 already-scanned sessions ship without command grains. That forced rescan also heals two Skill rows lost from session `49f47ede` to a mid-flight scan — for free.
- The "196 /wayfinder invocations" figure above is grep-inflated by analysis sessions quoting extracts; the genuine typed-command count in real sessions is **95**. The motivation stands unchanged — `tool_events` still holds zero.
- Pruned sessions' commands are recoverable from the verbatim backfill extracts, if backfill coverage is wanted.



---

**comment · 2026-08-27**

## Resolution: landed as commit 94b094b

**Schema — its own table, not tool_events rows.** `command_grains(session_id, command, at)`: a command grain is not a tool call (no tool_use id, no result, no consumer), and rows inside `tool_events` would surface as a phantom category in the where-view consumer league (#55's chips). The scan (`scan_transcript`) now returns commands alongside events/usage; `fill_substrate` writes them; growth invalidation (#29) and the migration wipe clear them — all delete sites now share a `SUBSTRATE_TABLES` constant so the next substrate table can't be forgotten at one of them.

**Parse rule — #59's, verbatim.** A grain is a user message whose string content *starts* with a `<command-…>` marker (either `<command-name>` or `<command-message>` may lead), name captured verbatim from `<command-name>…</command-name>`. String content only: 209/209 command messages across the real corpus are plain strings, and per-block matching would readmit the quoted-marker false-positive class #59 identified. Local commands (`/clear`, `/compact`, `/model`) are captured too — verbatim means verbatim; the how-view filters at read time if it wants to.

**Migration + backfill.** `user_version` 3: every scanned session whose transcript survives is reset and refilled in the same `init_db` call (#50's no-window rule; `serve.py` is read-only and never migrates). Run against the live db: **190 grains across 59 sessions** (hindsight: 80 across 40 — consistent with #59's 95-across-48-on-disk once pruned and sync-lagged sessions are netted out). The forced rescan healed both prefix-truncated tails, including `49f47ede`'s two lost Skill rows. All 157 still-unscanned sessions are pruned-transcript history — NULL by design, #59's accepted residual.

**Deliberately not done.** Pruned sessions' commands from backfill extracts: accepted as absent for now (#59 allowed either); the extracts survive if the how-view ever misses them. `extract.py` untouched per the ticket — but review found its skip misses message-leading command messages, leaking boilerplate into what-pass extracts: filed as #66, out of this map's scope. A `session_id` index on the substrate tables was declined on measurement (16K rows; sub-ms scans) — the upgrade path if the tables grow ~20×.

CONTEXT.md's command-grain and substrate-scan entries updated to match. Ride-along commit 3eeb912 landed ADR-0009/0010/0011 and the charting vocabulary that prior sessions authored but never committed — CONTEXT.md was citing decision records absent from the repo.


