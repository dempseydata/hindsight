# DB session coverage: 70 in the DB vs ~853 transcripts on disk

**Ticket:** [#59](../tickets/059-research-db-session-coverage-70-in-the-db-vs-853-transcripts.md) · **Date:** 2026-08-26 · **Method:** exhaustive cross-reference of session ids in `~/.claude/projects/<project-key>/` against `local-data/hindsight.db` (`sessions`, `excluded_sessions`, `tool_events`), plus a parse-level scan of every transcript for genuine deliberate-process signal.

## The partition (exact, no residue)

At measurement time the directory held **854** top-level `*.jsonl` files (the probe's 853 plus one new session). Every one of them falls into exactly one class:

| Category | Files | Explanation |
| --- | ---: | --- |
| Real sessions, in `sessions` | 50 | Inventoried and substrate-scanned; all 50 are `status='done'` |
| Self-analysis chaff, in `excluded_sessions` | 776 | Hindsight's own nightly `claude -p` audit/what-pass sessions. They land in this project dir because `analyze.py` runs from the repo. ADR-0003 self-exclusion by prompt signature (`ANALYSIS_SIGS`, `build/analyze.py`); 12/12 random sample verified, and **zero** of the 776 contain genuine signal |
| Not yet synced: last night's chaff | 20 | mtime 03:03–03:16 today (the 03:00 run); heads match `ANALYSIS_SIGS`; will enter `excluded_sessions` on the next sync |
| Not yet synced: today's real sessions | 8 | Post-date the last nightly sync (max `sessions.date` = 2026-08-25); will enter `sessions` as pending on the next run. Includes this research session itself |
| **Total** | **854** | |

Two adjacent populations, outside the 854 but part of the story:

- **Subagent sidecars: 98 JSONLs** under 30 `<session-id>/subagents/` directories. Excluded from the inventory by glob depth (`sync_sessions` globs `*/*.jsonl` — deliberate). They carry **no** deliberate-process signal: zero genuine `Skill` tool_use blocks, and operators do not type slash commands into subagents (the 10 sidecars grep-matching `<command-name>` are all quoted transcript content, e.g. agents reading transcripts).
- **20 DB sessions with no transcript on disk** (dated Jul 14–21). The CLI pruned these transcripts; the DB is preserving history the disk has lost — coverage in the *other* direction. All 20 still have verbatim backfill extracts under `local-data/backfill/extracts/`.

So the headline "70 vs 853" decomposes as: 70 DB sessions = 50 on disk + 20 pruned-but-remembered; 853–854 files = those 50 + 776 excluded analysis chaff + 28 not-yet-synced. **91% of the directory is hindsight's own analysis exhaust**, not operator sessions.

## Q1 — Is the deliberate-process signal fully represented?

Parse-level scan (not naive grep — analysis sessions quote transcript extracts that themselves contain `<command-name>`, inflating grep counts; this is where the ADR-0010 figure of 196 `/wayfinder` hits came from): a genuine command is a user message *starting* with a `<command-…>` marker; a genuine skill call is an actual `tool_use` block named `Skill`.

- **50 sessions on disk carry genuine signal** (48 with typed commands — 95 command invocations — and 36 with Skill calls). **42 are in the DB, 8 are today's not-yet-synced sessions, and 0 were wrongly excluded.** The signature filter has no false positives against real sessions.
- **Skill invocations in the DB:** of the 30 signal sessions in the DB with Skill calls on disk, **29 are fully represented** in `tool_events`. One (`49f47ede`, Aug 25) was substrate-scanned mid-flight and then marked done: its last 26 tool events — including `Skill(mattpocock-skills:code-review)` and `Skill(ponytail:ponytail-review)` — are absent. A second done session (`8ff4f412`) is missing 15 tail tool events, none of them skills. Mechanism: `invalidate_grown` (`build/analyze.py`) deliberately never revisits `status='done'` sessions ("prefix semantics"), and the ticket-#29 live-window guard is only 300 s — a session idle >5 min then resumed defeats it.
- **Command grains: not in the DB at all yet.** No table carries them; ADR-0010 already commits to adding the grain. This is planned build work, not a coverage defect — but it means the how-view cannot draw its command trail from the DB *as currently synced*.
- The 8 unsynced sessions are ordinary nightly-cadence lag, self-healing.

**Answer: nothing with signal is wrongly missing, but the DB as it stands cannot yet feed the trail** — command grains don't exist yet (planned), and two done sessions have truncated event tails (2 lost Skill rows in one of them).

## Q2 — Does the substrate scan need repairing before the how-view ships?

The 70-vs-853 gap itself is **fully explained** — every file is accounted for and rightly placed. No unexplained residue, no defect in the exclusion filter, no sidecar leakage. But two bounded items must ride along with the already-planned command-grain work:

1. **The command-grain migration must force a rescan of done sessions.** `fill_substrate` only scans `skipped_records IS NULL`; done sessions are never revisited. Precedent exists in `analyze.py`'s migration block (reset `skipped_records=NULL` when a column is missing) — the command grain needs the same reset, or all 70 existing sessions ship without commands. For the 20 pruned sessions, command grains must come from the backfill extracts (verbatim; markers verified present) or be accepted as absent.
2. **The forced rescan heals the truncated tails for free.** Rescanning done sessions from today's full files recovers the 41 missing tail events (including the 2 Skill rows) for the on-disk sessions. No separate repair needed — just don't scope the migration's rescan to "commands only".

Residual, accepted: 9 sessions (Jul 14–21, transcripts pruned before the substrate pass existed) have `skipped_records IS NULL` and can never get `tool_events` from transcripts — bounded, early-project, extracts survive if it ever matters.

## Verdict

Gap fully explained; the exclusion machinery is sound and nothing that belongs in the DB is missing from it. The one pre-ship requirement is already implied by ADR-0010: when the command grain lands, its migration must rescan done sessions (not just new ones), which simultaneously repairs the two prefix-truncated event trails.
