# Skill-invocation coverage: which invocations v1 misses

**Ticket:** [#62](https://github.com/dempseydata/hindsight/issues/62) (part of map #59) · **Date:** 2026-11-13 · **Method:** a parse of every transcript still on disk under `~/.claude/projects/` (187 parent transcripts and their 156 subagent transcripts, sessions dated 2026-09-24 to 2026-11-11), cross-referenced against `local-data/hindsight.db` opened read-only (`sessions`, `excluded_sessions`, `tool_events`, `command_grains`).

## Answer

**On the transcripts still on disk, v1 misses no skill invocation by path.** Every skill body the CLI loaded traces to one of the two triggers v1 already captures: a `Skill` tool call (`tool_events.consumer_type = 'skill'`) or a typed slash command passing the starts-with rule (`command_grains`). Of the 93 Skill tool calls and 30 typed skill commands in sessions the database has scanned, **1** Skill call is missing, and it is ingest lag rather than a capture gap: a resumed session whose tail postdates the last run and will be topped up under ADR-0013. Miss rate by path: **0 of 123 (0%)**; including lag, **1 of 123 (0.8%)**.

The candidate paths in the ticket either route through the `Skill` tool already (plugin and model auto-invocation, inline skill mentions, skills in subagents) or never occurred in the sample (list-form command markers, `@`-included skills, queued slash commands). The gaps that do exist are in precision and history, not coverage. They are listed at the end.

## Ground truth: the skill body

Every skill load leaves one unambiguous record. A `user` record with `isMeta: true` whose text starts `Base directory for this skill:`. A body loaded by a `Skill` call carries `sourceToolUseID` equal to that call's `tool_use.id`. A body loaded by a typed command follows the `<command-name>` user message directly. So the oracle is: count the bodies, then attribute each one to its trigger.

| Bodies on disk | Count | Attributed to a `Skill` call (by `sourceToolUseID`) | Attributed to a typed command | Unattributed |
| --- | ---: | ---: | ---: | ---: |
| Parent transcripts | 95 | 64 | 31 | **0** |
| Subagent transcripts | 26 | 26 | 0 | **0** |
| **Total** | **121** | **90** | **31** | **0** |

An early attribution pass that used a record-distance window left 29 bodies unattributed. All 29 were parallel `Skill` calls issued in one assistant message, whose bodies arrive more than 12 records after the call. `sourceToolUseID` resolves every one of them. Use that field, not proximity, for any future check.

There are 98 `Skill` calls (65 parent, 33 subagent) against 90 bodies attributed to them. The 8 calls with no body are failed calls: the database holds 7 `Skill` events with `is_error = 1`. They are captured. See the precision note below.

## Per candidate path

| Path | How it shows in a transcript | Seen on disk | Captured by v1? | Missed |
| --- | --- | ---: | --- | ---: |
| `Skill` tool call, parent | `assistant` `tool_use` named `Skill`, `input.skill` | 65 | Yes, `tool_events` | 0 (1 pending top-up) |
| `Skill` tool call inside a subagent | Same, in `<session>/subagents/agent-*.jsonl` | 33 | Yes, `tool_events` with `agent_id` set (ADR-0019) | 0 |
| Plugin or model auto-invocation | Not a separate form. The model calls the `Skill` tool | Included in the 98 above | Yes | 0 |
| Typed slash command for a skill | `user` string content starting `<command-…>`, then a skill body | 31 (of 103 command markers) | Yes, `command_grains` | 0 |
| Typed command, marker in block-list content | `user` content is a list whose text block starts `<command-` | **0** | No (string-only rule) | 0 observed |
| `<command-name>` marker not at the start | Marker embedded in other text | 1 (in a subagent prompt; quoted content, no body followed) | Correctly rejected | 0 |
| Inline skill mention (`skill_mention` attachment) | `attachment.type = 'skill_mention'`, `skillName` | 8 | 7 led to a `Skill` call (captured); 1 led to nothing | 0 |
| Queued slash command (`queued_command` attachment) | A prompt queued while the model is busy | 185 queued prompts, **0** starting with `/` or holding a command marker | — | 0 observed |
| Skill re-injected after compaction (`invoked_skills` attachment) | The bodies of skills already invoked, re-sent | 1 | No, and correctly so. It re-loads an earlier invocation that was already captured | n/a |
| Nested-directory skill discovery (`dynamic_skill` attachment) | A listing of skill names found in a nested `.claude/skills` | 2 | No, and correctly so. It is availability, not invocation | n/a |
| Skill loaded by an `@`-include in a CLAUDE.md | Content arrives as memory or instructions, not as a skill body | **0**. No CLAUDE.md in the workspace `@`-includes a `SKILL.md` | Not detectable as an invocation by design | 0 observed |
| Skill preloaded through a subagent definition | Would appear as a body in a subagent transcript with no trigger | **0** unattributed subagent bodies | — | 0 observed |

The two paths that do not occur today but would be silent if they began are list-form command markers and `@`-included skills. The first breaks the `isinstance(content, str)` guard in `scan_transcript` (`build/substrate.py`; its ponytail comment already names it). The second is not an invocation in Claude Code's sense and leaves no invocation record to capture. The orphan-body count above detects both cheaply. A non-zero count of bodies with neither a matching `sourceToolUseID` nor a preceding captured marker means a new path has opened.

## Database against disk, per session

| Session state | On-disk sessions | Skill calls in transcripts | Typed skill commands | Recorded in the DB |
| --- | ---: | ---: | ---: | --- |
| Scanned (`skipped_records` not NULL) | 86 | 93 | 30 | 92 of 93 calls; 102 of 102 command markers |
| Not yet synced | 5 | 5 | 1 | No. All 5 belong to the live session running this research, which is held by the live-window rule |
| Excluded (`claude -p` analysis chaff, ADR-0003) | 96 | 0 | 0 | n/a |

The one missing call is in session `8f58795e-4860-4f0e-b89b-8efd1ffb74c0`. It was scanned at 0.88 MB, and its transcript has since grown to 2.29 MB after the last ingest. `invalidate_grown` tops it up on the next quiet run (ADR-0013). That is lag, not loss.

## Gaps that are not coverage

1. **Failed calls count as invocations.** 7 of 399 `Skill` events in the database (1.8%) have `is_error = 1`, typically a call to a skill that does not exist or is not loaded. `build/how.py` `_events` selects `consumer_type = 'skill'` without filtering `is_error`. So a failed call puts a step on the process trail, and its name can match a stage marker or show as off-script.
2. **Most command grains are not skills.** Of 103 command markers on disk, 31 loaded a skill body and 72 were built-in or local commands (for example `/reload-plugins`, `/clear`, `/exit`, `/model`, `/context`). The how-view sets aside only the session-boundary set (`/clear`, `/model`, `/compact`, `wayfinder`). Other built-ins fall to off-script. Whether a grain was a skill is decidable at scan time: a skill body follows it.
3. **History before the substrate is unknowable.** 157 of the 486 sessions in the database were never substrate-scanned, because their transcripts were pruned before the scan existed. Their invocations read unknown (NULL), not zero, as designed. Transcripts on disk reach back only to 2026-09-24, so this measurement cannot verify capture for anything older.
4. **Out of reach.** Sessions that never write to `~/.claude/projects/` (other surfaces, or another config directory) cannot be measured from here.

## Sources

- Capture code: `build/substrate.py` (`classify`, `scan_transcript`, `subagent_transcripts`, `fill_substrate`). Trail query: `build/how.py` `_events`. Growth top-up: `build/analyze.py` `invalidate_grown`. Session discovery and exclusion: `build/analyze.py` `sync_sessions` (glob `*/*.jsonl`, `ANALYSIS_SIGS`).
- Decisions: ADR-0010 and ADR-0011 (the trail and its name pool), ADR-0013 (resumed sessions are topped up), ADR-0019 (subagent transcripts filed under the parent).
- Transcript record shapes (`sourceToolUseID`, `isMeta`, the `attachment` types `skill_mention`, `queued_command`, `invoked_skills` and `dynamic_skill`) were read from the transcripts themselves (CLI versions current to 2026-11-13). They are observed, not documented, contracts. The field-contract guard (ADR-0020) is the standing check if they move.
- Database: `local-data/hindsight.db`, read-only, as of the last ingest (latest usage row 2026-11-12). Only counts are reported here.
