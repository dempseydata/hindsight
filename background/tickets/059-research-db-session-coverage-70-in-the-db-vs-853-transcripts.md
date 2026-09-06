# #59 Research: DB session coverage — 70 in the DB vs 853 transcripts on disk

state: closed · labels: wayfinder:research · opened: 2026-08-26 · closed: 2026-08-26

## Question

ADR-0010's feasibility probe found the DB holding **70 hindsight sessions against 853 JSONL files on disk** for this folder; subagent sidecars and a pending analysis run explain some of the gap, not all. Classify the gap exhaustively — sidecar files, empty or pruned transcripts, scan filters, genuine defects — by comparing `~/.claude/projects/<project-key>/` against `local-data/hindsight.db` (`sessions`, `tool_events`, `usage`), and answer two things:

1. What may the how-view's process trail rely on from the DB as currently synced — is the deliberate-process signal (sessions where skills/commands were used) fully represented, or does the gap bite it?
2. Does anything need repairing in the substrate scan before the how-view ships, or is the gap fully explained by rows that rightly have no place in the DB?

Findings on a throwaway `research/db-coverage` branch; the resolution comment carries the classification table and the verdict.



---

**comment · 2026-08-26**

## Resolution: gap fully classified, no unexplained residue

Cross-referenced every session id in `~/.claude/projects/<project-key>/` (854 top-level JSONLs at measurement time) against `sessions` + `excluded_sessions` + `tool_events`, with a parse-level signal scan of all transcripts. Full findings: [research/db-coverage.md on `research/db-coverage`](../research/db-coverage.md).

### Classification (exact partition, 854 files)

| Category | Files | Explanation |
| --- | ---: | --- |
| Real sessions, in `sessions` | 50 | inventoried, substrate-scanned, all `done` |
| Self-analysis chaff, in `excluded_sessions` | 776 | hindsight's own nightly `claude -p` sessions, filed here because analyze.py runs from the repo; ADR-0003 signature exclusion, 12/12 sample verified, zero genuine signal |
| Not yet synced: last night's chaff | 20 | mtime 03:03–03:16 today; will join `excluded_sessions` next sync |
| Not yet synced: today's real sessions | 8 | post-date last sync; will enter as pending (includes the session running this research) |

Adjacent: **98 subagent sidecars** in 30 `<sid>/subagents/` dirs — excluded by glob depth, deliberately; zero deliberate-process signal. And the DB holds **20 sessions whose transcripts the CLI has since pruned** (Jul 14–21) — coverage in the other direction; all 20 keep verbatim backfill extracts. So 70 DB = 50 on disk + 20 pruned; 91% of the directory is analysis exhaust.

### Q1 — deliberate-process signal fully represented?

50 sessions on disk carry genuine signal (95 typed commands across 48; Skill calls in 36). **42 in the DB, 8 in today's sync lag, 0 wrongly excluded.** Skill calls are in `tool_events` for 29/30 DB sessions — one (`49f47ede`) was scanned mid-flight and marked done, losing its last 26 events incl. 2 Skill rows (`invalidate_grown` never revisits `done` rows; the 300 s live window misses idle-then-resumed sessions). Command grains are **not in the DB at all yet** — that's the ADR-0010 planned grain, not a coverage defect. Net: nothing with signal is wrongly missing, but the trail cannot be drawn from the DB *as currently synced* until the command grain lands. (Aside: ADR-0010's "196 /wayfinder invocations" was grep-inflated — analysis sessions quote extracts containing the markers; genuine typed commands number 95.)

### Q2 — repair needed before the how-view ships?

The 70-vs-853 gap itself is **fully explained** — every file rightly placed. One bounded requirement rides along with the already-planned command grain: **its migration must reset `skipped_records` for done sessions** (precedent exists in analyze.py's migration block), otherwise all 70 existing sessions ship without command grains. That forced rescan also heals the two prefix-truncated tails for free. For the 20 pruned sessions, command grains come from backfill extracts (markers verified present) or are accepted as absent. Residual accepted: 9 early sessions pruned before the substrate pass existed can never get `tool_events`.


