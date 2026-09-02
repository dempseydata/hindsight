#!/usr/bin/env python3
"""Hindsight analysis-run entrypoint — the what-pass (ticket #17).

On-demand, end to end: syncs new sessions from a transcript archive into
`sessions` (hindsight's own `claude -p` analysis sessions excluded by prompt
signature, ADR-0003), extracts per ADR-0002 (indexed pieces, sidecar uuid
map, 180K chunk cap — build/extract.py), then per session runs the frozen
what-pass over the extract (-> `audit`; multi-part sessions get the merge
call). The why-pass and its findings/evidence/runs tables were removed
wholesale per ADR-0006 (ticket #43) — v1 is two views, what and where.

Sync also fills the where-view measurement substrate (tickets #22, #42):
every newly seen (and any not-yet-scanned, e.g. backfill-imported) session's
transcript is parsed once into `tool_events` (tool_use/tool_result paired by
id, deduped across streamed records, each call carrying its consumer
classification, error flag, and emitting message id — the message-lens join
to usage), `usage` (per-API-response token counts by model, deduped by
message id), and `command_grains` (ticket #61: user-typed slash commands,
parsed verbatim from <command-name> markers — a typed command injects its
skill with no Skill tool call, so it is invisible to tool_events), making
tokens per session/day/project plain-SQL questions regardless of OTEL
coverage. Unknown record types are counted-and-skipped, never fatal.
The mechanical ADR count (ADR-0004) is computed from tool_events onto each
audit row at assemble time — "ADRs touched", never model-derived; NULL, not
a false zero, when a session was never scanned.

After the session loop the status-narrative pass runs (ADR-0012, ticket
#68): per declaring project, the how-view run ledger (build/how.py) is
hashed, and when it, the prompt version or the model changed, one model
call writes a Built/Reversed/Now fact list into `status_narrative` —
write-time gated by the eval's floors (eval/score.py), never on page load.

Then the silent-change backstop runs (ticket #21):
snapshots of the ~/.claude text-config surface, structural
installed_plugins.json diffs, and project `.claude` git commits, stored as
content-addressed blobs with one change_events table (diffs are render-time,
not stored). The first capture is a silent baseline. Renders nowhere in v1
(ADR-0006) — capture only.

The sunk-cost scan (ticket #24) then rebuilds `sunk_cost`: what a session
pays at start before the first prompt — the CLAUDE.md chain with @-imports
expanded, skill and command descriptions, MCP config — itemised per project
(user-scope rows carry NULL project), plugins as a grouping level, the
plugin registry keyed by install path so a skill behind duplicate install
records counts once. Full replace per run.

Idempotent: a session already `done` is never reprocessed. Model outputs are
cached on disk; an invalid/failed output is left uncached so the next run
retries it. Subscription-limit exhaustion (the model runner raises
LimitExhausted) pauses the run cleanly — sessions not yet reached stay
`pending`/`partial` and the next run resumes them. A session whose transcript
is gone before it was ever extracted is `lost` — terminal, never retried
(ticket #78, ADR-0015).

Usage: analyze.py [--root DIR] [--db PATH] [--work-dir DIR]
       analyze.py install       write + start the nightly launchd calendar job
       analyze.py uninstall     stop the job + remove the plist

The nightly is a scheduled *invocation* of this on-demand command, not a
background process (ADR-0001 amendment 2026-08-24). launchd calendar jobs
run on wake if the Mac was asleep at 03:00, and are skipped if powered off.
"""
import argparse
import hashlib
import json
import os
import plistlib
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
from substrate import _is_live, adr_count, fill_substrate  # noqa: E402
from sunk_cost import PLUGINS_FILE, plugin_entries, scan_sunk_cost  # noqa: E402

DEFAULT_TRANSCRIPTS = Path.home() / ".claude" / "projects"
DEFAULT_DB = REPO / "local-data" / "hindsight.db"
DEFAULT_WORK_DIR = REPO / "local-data" / "analysis"
DEFAULT_CLAUDE_DIR = Path.home() / ".claude"
# The workspace layout (each dir one project repo) — CLI-overridable.
DEFAULT_PROJECTS_DIR = Path.home() / "Documents" / "Claude"


# Day bucketing (ADR-0014, ticket #74): timestamps are stored UTC, every
# calendar-day bucket is the operator's local day. One SQL fragment and one
# Python equivalent, so the two can never drift apart.
def day_sql(col):
    return f"substr(datetime({col}, 'localtime'), 1, 10)"


def local_day(ts):
    """Local calendar day of a stored UTC timestamp. A bare `YYYY-MM-DD` is
    already a bucket and passes through untouched — converting one twice
    would shift it a day west. Anything unparseable keeps the old prefix
    slice rather than vanishing."""
    s = str(ts or "")
    if "T" not in s:
        return s[:10]
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s[:10]
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%Y-%m-%d")

# The ~/.claude text-config surface (ticket #21): the top-level operator-
# editable text configs. Plugins are diffed structurally from their own file;
# transcripts, caches and binaries are not config.
# ponytail: a fixed filename list — widen (agents/, hooks/, commands/) if a
# silent change ever lands outside it.
BACKSTOP_SURFACE = ("CLAUDE.md", "settings.json", "settings.local.json",
                    "keybindings.json", "mcp.json")
# backstop_state marker key: present once the silent baseline is recorded.
BASELINE_KEY = "__baseline__"

# what-v3 (ticket #79, ADR-0016): the extract is bracketed by the
# instructions — framed as data, output contract restated after it — so the
# model audits the transcript's last turn instead of answering it. Gated by
# eval/what_run.py. what-v2 carried the #19 ride-along repairs (firmer SKIP,
# stated-rationale Decided lines), unmeasured by design.
PROMPT_VERSION = "what-v3"
STATUS_VERSION = "status-v1"  # the how-view status narrative (ADR-0012, #68)
# The ADR-0002 model pin. Was single-sourced from eval/corpus.json; the eval
# harness retired with the why-pass (ADR-0006), so the pin lives here now.
MODEL = "claude-haiku-4-5-20251001"
PROMPTS_DIR = REPO / "build" / "prompts"
WHAT_PROMPT = (PROMPTS_DIR / f"{PROMPT_VERSION}.txt").read_text()
MERGE_PROMPT = (PROMPTS_DIR / "merge-v1.txt").read_text()
STATUS_PROMPT = (PROMPTS_DIR / f"{STATUS_VERSION}.txt").read_text()
EXTRACT_SLOT = "{{EXTRACT}}"


def what_prompt(extract, template=None):
    """Assemble the what-pass call. A template carrying EXTRACT_SLOT brackets
    the extract (what-v3+); one without is a pure prefix (what-v1/v2). Shared
    with eval/what_run.py so the eval runs exactly what production sends."""
    template = WHAT_PROMPT if template is None else template
    if EXTRACT_SLOT in template:
        return template.replace(EXTRACT_SLOT, extract, 1)
    return template + "\n" + extract


sys.path.insert(0, str(REPO / "eval"))
from score import contract, ledger_prompt, parse  # noqa: E402  the eval's floors are the write-time gate
CALL_TIMEOUT = 300

# ADR-0003 self-exclusion: hindsight's own claude -p analysis sessions are
# recognised by prompt signature and never enter the inventory.
ANALYSIS_SIGS = (
    "You are generating one audit-log entry",
    "The following are audit-log entries",
    "You are analyzing a transcript extract",
    "You are writing the status card",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  project TEXT,
  transcript_path TEXT NOT NULL,
  date TEXT,
  cli_version TEXT,
  size INTEGER,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending -> done | empty | lost; partial = retryable
  skipped_records INTEGER,  -- also the substrate-scanned marker: NULL = never scanned
  audited_size INTEGER  -- transcript size the audit entry covers (#73); NULL = never audited
);
CREATE TABLE IF NOT EXISTS audit (
  session_id TEXT PRIMARY KEY REFERENCES sessions(id),
  project TEXT,
  date TEXT,
  skip INTEGER NOT NULL,
  markdown TEXT,
  prompt_version TEXT NOT NULL,
  model TEXT NOT NULL,
  adr_count INTEGER
);
CREATE TABLE IF NOT EXISTS tool_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  tool_use_id TEXT,
  name TEXT,
  at TEXT,
  result_at TEXT,
  file_path TEXT,
  message_id TEXT,     -- API id of the emitting message: message-lens join to usage
  consumer_type TEXT,  -- 'skill' | 'mcp' | 'cli' | 'shell' | 'builtin' (ticket #42)
  consumer TEXT,
  mcp_tool TEXT,
  is_error INTEGER     -- from the paired tool_result; NULL when never paired
);
CREATE TABLE IF NOT EXISTS status_narrative (
  project TEXT PRIMARY KEY,
  ledger_hash TEXT NOT NULL,     -- sha256 of the run ledger it was written from
  narrative TEXT NOT NULL,       -- {"Built": [...], "Reversed": [...], "Now": [...]}
  prompt_version TEXT NOT NULL,
  model TEXT NOT NULL,
  generated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS command_grains (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  command TEXT NOT NULL,  -- the <command-name> text, verbatim (ticket #61)
  at TEXT
);
CREATE TABLE IF NOT EXISTS usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  message_id TEXT,
  at TEXT,
  model TEXT,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  cache_creation_input_tokens INTEGER NOT NULL,
  cache_read_input_tokens INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS excluded_sessions (
  id TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS blobs (
  hash TEXT PRIMARY KEY,
  content TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS backstop_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS change_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  observed_at TEXT NOT NULL,
  source TEXT NOT NULL,
  path TEXT NOT NULL,
  before_hash TEXT REFERENCES blobs(hash),
  after_hash TEXT REFERENCES blobs(hash)
);
CREATE TABLE IF NOT EXISTS project_presence (
  project TEXT PRIMARY KEY,
  present INTEGER NOT NULL  -- workspace folder found when this run looked (ADR-0009)
);
CREATE TABLE IF NOT EXISTS sunk_cost (
  project TEXT,            -- NULL: user scope, paid by every project's sessions
  category TEXT NOT NULL,  -- 'claude-md' | 'skill' | 'command' | 'mcp'
  plugin TEXT,             -- plugin key when the item ships in a plugin
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  tokens INTEGER NOT NULL
);
"""

# One home per analyze<->serve contract fact (ticket #81). Python consumers
# import these; non-Python consumers (the where.html category buttons, the
# what-prompt's section names as prose) are pinned by drift tests instead —
# detect divergence, don't prevent it (the model-pin pattern).
STATUSES = ("pending", "partial", "done", "empty", "lost")
# Selectable = retryable, i.e. awaiting (re)analysis — which is why the
# what-view rendering `partial` as "synced, not yet analyzed" is deliberate,
# not an oversight.
SELECTABLE = ("pending", "partial")
SELECTABLE_SQL = "(" + ", ".join(f"'{s}'" for s in SELECTABLE) + ")"
LOST = "lost"  # what serve.py reads: never extracted, transcript gone (#78)
# tool_events.consumer_type (ticket #42) — classify() emits exactly these
CONSUMER_TYPES = ("skill", "mcp", "cli", "shell", "builtin")
SKILL = "skill"  # the member the how-trail selects by name — never by index
# The audit-entry section names, locked by ADR-0004: a prompt edit that
# reshapes them is a format change and goes through that ADR.
SECTIONS = ("Did", "Decided", "Setup changes")

# The per-session substrate tables the scan fills — every wipe-for-rescan
# site (growth invalidation, migration resets) must clear all of them, or a
# rescan silently duplicates the forgotten table's rows.
SUBSTRATE_TABLES = ("tool_events", "usage", "command_grains")


class LimitExhausted(Exception):
    """Raised by a model runner on subscription-limit exhaustion (ADR-0003):
    a designed pause, not a failure — the run stops cleanly and every session
    not yet reached stays pending/partial for the next run to resume."""


class ExtractionFailed(Exception):
    """build/extract.py exited non-zero — retryable, per-session, next run."""


def init_db(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # The ingest listener writes beneath every run; a write after a
    # minute-long model call must wait for it, not fail at the 5 s default.
    conn = sqlite3.connect(db_path, timeout=30)
    conn.executescript(SCHEMA)
    # PRAGMA user_version gates the accreting migration sniffs (ticket #50):
    # each runs exactly once per db, so the #43 drops are never a standing
    # destructive startup side effect and the #42/#61 wipes can't re-fire.
    v = conn.execute("PRAGMA user_version").fetchone()[0]
    if v < 1:
        _migrate(conn)
    if v < 2:
        # Ticket #38: what-pass refusals stored as skip=0 entries by runs
        # predating the contract gate (the backfill import included) —
        # delete the rows and reprocess the sessions from their transcripts.
        conn.execute("UPDATE sessions SET status='pending' WHERE id IN"
                     " (SELECT session_id FROM audit"
                     "  WHERE skip=0 AND markdown NOT LIKE '###%')")
        conn.execute("DELETE FROM audit"
                     " WHERE skip=0 AND markdown NOT LIKE '###%'")
        conn.execute("PRAGMA user_version = 2")
        conn.commit()
    if v < 3:
        # Ticket #61: command grains are new — rescan every scanned session
        # whose transcript survives so existing sessions gain their grains
        # (the forced rescan also heals the two prefix-truncated event tails
        # found by #59). Wipe and refill in one call, per the #50 rule: no
        # caller-dependent window. A vanished transcript keeps its old rows.
        stale = [(sid,) for sid, path in conn.execute(
            "SELECT id, transcript_path FROM sessions"
            " WHERE skipped_records IS NOT NULL") if Path(path).exists()]
        for table in SUBSTRATE_TABLES:
            conn.executemany(f"DELETE FROM {table} WHERE session_id=?", stale)
        conn.executemany("UPDATE sessions SET skipped_records=NULL WHERE id=?",
                         stale)
        conn.execute("PRAGMA user_version = 3")
        conn.commit()
        fill_substrate(conn)
    if v < 4:
        # Ticket #73: resumed sessions were never rescanned, so their tails
        # never reached the db. The re-audit gate needs its own watermark —
        # an audit written before this migration covered the transcript at
        # the size then recorded, so `size` is the only evidence of what it
        # saw. Never-audited sessions stay NULL. No wipe here: the next
        # run's invalidate_grown tops up every grown session's substrate.
        if "audited_size" not in {r[1] for r in conn.execute("PRAGMA table_info(sessions)")}:
            conn.execute("ALTER TABLE sessions ADD COLUMN audited_size INTEGER")
        conn.execute("UPDATE sessions SET audited_size = size"
                     " WHERE id IN (SELECT session_id FROM audit)")
        conn.execute("PRAGMA user_version = 4")
        conn.commit()
    if v < 5:
        # Ticket #74 / ADR-0014: day buckets are the operator's local day.
        # Every other bucket converts at read time, but `sessions.date` is a
        # *stored* bucket that has already lost the clock time it would need
        # — so it re-derives from the transcript head instead. A vanished
        # transcript keeps its UTC date: a guess is not a re-derivation.
        redated = []
        for sid, path in conn.execute("SELECT id, transcript_path FROM sessions"):
            if Path(path).exists():
                date = head_scan(Path(path))[1]
                if date:
                    redated.append((date, sid))
        conn.executemany("UPDATE sessions SET date=? WHERE id=?", redated)
        conn.executemany("UPDATE audit SET date=? WHERE session_id=?", redated)
        conn.execute("PRAGMA user_version = 5")
        conn.commit()
    # Message-lens join indexes — after the gate, so a pre-#42 db grows the
    # columns before they're indexed.
    conn.executescript(
        "CREATE INDEX IF NOT EXISTS idx_tool_events_message"
        " ON tool_events(message_id);"
        " CREATE INDEX IF NOT EXISTS idx_usage_message ON usage(message_id);")
    return conn


def _migrate(conn):
    """One-shot migrations for dbs predating tickets #22/#42/#43 — every
    step is a no-op on a db created fresh from SCHEMA."""
    # Ticket-#22 columns on tables from earlier tickets — CREATE IF NOT
    # EXISTS can't add columns to a live db.
    for table, col in (("sessions", "skipped_records"), ("audit", "adr_count")):
        if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER")
    # Ticket-#42 grains on a pre-#42 db: add the columns, then reset the
    # scanned marker (dropping the stale substrate rows) wherever the
    # transcript survives, and rescan immediately — wipe and refill in one
    # place, so no caller (the backfill import included) can leave a window
    # where a pruned transcript loses its substrate for good (ticket #50).
    # A session whose transcript vanished keeps its old rows — grain columns
    # NULL, unknown rather than a false zero.
    if "consumer_type" not in {r[1] for r in conn.execute("PRAGMA table_info(tool_events)")}:
        for col in ("message_id TEXT", "consumer_type TEXT", "consumer TEXT",
                    "mcp_tool TEXT", "is_error INTEGER"):
            conn.execute(f"ALTER TABLE tool_events ADD COLUMN {col}")
        stale = [(sid,) for sid, path in conn.execute(
            "SELECT id, transcript_path FROM sessions"
            " WHERE skipped_records IS NOT NULL") if Path(path).exists()]
        for table in SUBSTRATE_TABLES:
            conn.executemany(f"DELETE FROM {table} WHERE session_id=?", stale)
        conn.executemany("UPDATE sessions SET skipped_records=NULL WHERE id=?",
                         stale)
        # The surviving old rows were scanned before dedup existed — the
        # records streaming one response repeated its tool_use blocks. One
        # row per call, in place, since their transcripts can't be rescanned.
        # ponytail: NULL-id rows stay undeduped — no key to pair them on.
        conn.execute(
            "DELETE FROM tool_events WHERE tool_use_id IS NOT NULL AND id NOT IN"
            " (SELECT MIN(id) FROM tool_events GROUP BY session_id, tool_use_id)")
        conn.commit()
        fill_substrate(conn)
    # Ticket-#43 why-pass removal (ADR-0006) on a pre-cut db: drop the
    # findings/evidence/runs tables and their rows (the raw model outputs
    # stay cached on disk under local-data/), and the change_events link
    # column that pointed into findings (ALTER ... DROP COLUMN needs
    # SQLite >= 3.35 — acceptable in a one-shot sniff, not on every start).
    conn.executescript("DROP TABLE IF EXISTS evidence;"
                       " DROP TABLE IF EXISTS findings; DROP TABLE IF EXISTS runs;")
    if "finding_id" in {r[1] for r in conn.execute("PRAGMA table_info(change_events)")}:
        conn.execute("ALTER TABLE change_events DROP COLUMN finding_id")
    conn.commit()


def audit_title(md):
    """The `### title` heading of an audit entry (ADR-0004), or None."""
    m = re.match(r"#+\s+(.+)", md or "")
    return m.group(1).strip() if m else None


def project_name(dirname):
    prefix = "-Users-andrew-Documents-Claude-"
    return dirname[len(prefix):] if dirname.startswith(prefix) else dirname


def head_scan(path):
    """(first user text, first date, cli version) from a transcript's head —
    what self-exclusion and inventory metadata read, without a full parse."""
    text, date, version = "", "", None
    with path.open() as f:
        for i, line in enumerate(f):
            if i > 50 or (text and date and version):
                break
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not date and e.get("timestamp"):
                date = local_day(e["timestamp"])
            if version is None and e.get("version"):
                version = e["version"]
            if not text and e.get("type") == "user" and not e.get("isMeta"):
                c = (e.get("message") or {}).get("content")
                if isinstance(c, str):
                    text = c
                elif isinstance(c, list):
                    text = next((x.get("text", "") for x in c
                                 if isinstance(x, dict) and x.get("type") == "text"), "")
    return text, date, version


def sync_sessions(conn, root):
    """Insert newly seen transcripts into `sessions`; self-excluded sessions
    never enter it. Excluded ids are remembered in `excluded_sessions` so each
    transcript is head-scanned once, not on every run — analysis runs mint
    fresh `claude -p` transcripts of their own, so the excluded set otherwise
    grows the rescan cost forever. All file I/O happens before the write
    transaction opens (the ingest listener shares this db and its busy
    timeout is finite). Returns the count inserted."""
    seen = {r[0] for r in conn.execute("SELECT id FROM sessions")}
    seen |= {r[0] for r in conn.execute("SELECT id FROM excluded_sessions")}
    rows, excluded = [], []
    for jsonl in sorted(Path(root).glob("*/*.jsonl")):
        sid = jsonl.stem
        if sid in seen:
            continue
        seen.add(sid)
        head, date, version = head_scan(jsonl)
        if any(sig in head[:3000] for sig in ANALYSIS_SIGS):
            excluded.append((sid,))
            continue
        rows.append((sid, project_name(jsonl.parent.name), str(jsonl), date,
                     version, jsonl.stat().st_size))
    conn.executemany(
        "INSERT INTO sessions (id, project, transcript_path, date, cli_version, size, status)"
        " VALUES (?, ?, ?, ?, ?, ?, 'pending')", rows)
    conn.executemany("INSERT INTO excluded_sessions (id) VALUES (?)", excluded)
    conn.commit()
    return len(rows)


# Ticket #73: how much of the current transcript the audit entry must be
# blind to before it is rewritten. Below it the entry still fairly describes
# the session and the model call is waste; above it the entry is reporting a
# prefix as the whole. Chosen on the 17 grown sessions found on 2026-08-29.
REAUDIT_SHARE = 0.25


def invalidate_grown(conn, work_dir):
    """Ticket #29's straddle case, widened to resumed sessions by #73: a
    transcript that grew since sync still carries caches and substrate from
    the smaller prefix.

    Substrate and audit are split, because prefix semantics only ever
    applied to one of them. `usage`/`tool_events`/`command_grains` are
    mechanical facts carrying their own timestamps, so they are **always**
    topped up, whatever the session's status — before #73 a `done` session
    was skipped outright and every resumed session's tail was lost for good
    (26.2M tokens across 17 sessions when it was found). The audit entry
    stays prefix-semantic (CONTEXT.md): a model-written summary is fairly
    "as of" its run, and it is rewritten only once REAUDIT_SHARE of the
    current transcript is unseen.

    That share is measured against `audited_size`, not `size`: topping up
    substrate moves `size` to the disk, so measuring against it would reset
    the gap on every run and a session resumed in small increments would
    drift forever without ever tripping the threshold.

    A transcript that *shrank* is left alone — pruning means unknown, and
    rescanning would overwrite what we still hold with less.

    A *live* transcript is left alone too (ticket #76). The wipe is only
    half a top-up: `fill_substrate` skips a live session (ticket #29), so
    wiping one would end the run with zero substrate rows for it. Waiting
    a run costs nothing — the tail is still on disk."""
    rows = conn.execute("SELECT id, transcript_path, size, status, audited_size"
                        " FROM sessions").fetchall()
    for sid, path, size, status, audited in rows:
        p = Path(path)
        if (not p.exists() or size is None or p.stat().st_size <= size
                or _is_live(path)):
            continue
        now = p.stat().st_size
        for table in SUBSTRATE_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE session_id=?", (sid,))
        conn.execute("UPDATE sessions SET skipped_records=NULL, size=?"
                     " WHERE id=?", (now, sid))
        reaudit = (status == "done" and audited is not None
                   and (now - audited) / now >= REAUDIT_SHARE)
        if status != "done" or reaudit:
            for f in [*(Path(work_dir) / "extracts").glob(f"{sid}.*"),
                      *(Path(work_dir) / PROMPT_VERSION).glob(f"{sid}.*")]:
                f.unlink()
        if reaudit:
            conn.execute("UPDATE sessions SET status='pending' WHERE id=?", (sid,))
    conn.commit()


def part_files(extracts_dir, session_id):
    """A session's extract parts in part-number order — shared with the
    backfill history import (ticket #20)."""
    return sorted(Path(extracts_dir).glob(f"{session_id}.part*.txt"),
                  key=lambda p: int(re.search(r"part(\d+)", p.name)[1]))


def extract_session(work_dir, session_id, transcript_path):
    """Indexed extract + sidecar map (ADR-0002), via the frozen
    build/extract.py. Raises ExtractionFailed (retryable) if the subprocess
    exits non-zero."""
    extracts_dir = Path(work_dir) / "extracts"
    prefix = extracts_dir / session_id
    if not Path(f"{prefix}.map.json").exists():
        extracts_dir.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([sys.executable, str(REPO / "build" / "extract.py"),
                            str(transcript_path), str(prefix)],
                            capture_output=True, text=True)
        if r.returncode != 0:
            raise ExtractionFailed(r.stderr.strip())
    return part_files(extracts_dir, session_id)


def is_lost(work_dir, session_id, transcript_path):
    """Ticket #78: nothing to read and nothing cached — no retry can ever
    succeed. An explicit existence test, not inferred from ExtractionFailed,
    which also covers unreadable/malformed files that remain retryable."""
    return (not Path(transcript_path).exists()
            and not (Path(work_dir) / "extracts" / f"{session_id}.map.json").exists())


def classify_and_extract(conn, work_dir):
    """The greedy pass ahead of the model loop (ticket #78): every selectable,
    quiet session is either marked `lost` or has its extract cached before a
    single model call is made — so a transcript pruned after this point loses
    nothing, and the backlog drains to `lost` on first contact with no
    migration. ExtractionFailed is swallowed: the session stays retryable."""
    rows = conn.execute(
        "SELECT s.id, s.transcript_path, a.session_id IS NOT NULL"
        " FROM sessions s LEFT JOIN audit a ON a.session_id = s.id"
        f" WHERE s.status IN {SELECTABLE_SQL}").fetchall()
    for sid, path, audited in rows:
        if _is_live(path):
            continue
        if is_lost(work_dir, sid, path):
            # A re-audit (ADR-0013) that lost its transcript before the
            # rewrite keeps the standing entry: prefix-semantic, not lost.
            _mark(conn, sid, "done" if audited else "lost")
            continue
        try:
            extract_session(work_dir, sid, path)
        except ExtractionFailed:
            pass


def strip_fences(s):
    """Tolerates and strips a leading/trailing ``` fence, with or without a
    `markdown` language tag — ADR-0002."""
    return re.sub(r"^```(?:markdown)?\s*|\s*```$", "", s.strip())


def valid_entry(md):
    """The write-time contract gate (ticket #38): a what/merge output is an
    entry (opens ###; four-section shape per ADR-0004) or a SKIP verdict.
    Anything else — refusal prose like "I don't see a transcript" — is a
    failed call, never stored as an audit row."""
    md = strip_fences(md).strip()
    return md.startswith("SKIP") or md.startswith("###")


def call_cached(model_runner, prompt, out_path):
    """Reuse a valid cached output; otherwise call the runner and cache on
    success. Empty or contract-violating output (ticket #38) returns None,
    uncached, so the next run retries it; a poisoned cached file fails the
    gate the same way and is overwritten when the retry succeeds.
    LimitExhausted propagates."""
    if out_path.exists() and out_path.stat().st_size > 0:
        cached = out_path.read_text()
        if valid_entry(cached):
            return cached
    text = model_runner(prompt)
    if not text or not text.strip() or not valid_entry(text):
        # Ticket #79: a rejection was silent and retried nightly unseen.
        head = " ".join((text or "").split())[:80]
        print(f"rejected {out_path.name}: {head!r}", file=sys.stderr)
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    return text


def _mark(conn, sid, status):
    conn.execute("UPDATE sessions SET status=? WHERE id=?", (status, sid))
    conn.commit()


def insert_results(conn, session, skip, md, what_version, model):
    """The audit row for one completed session. Shared by the analysis run
    and the backfill history import (ticket #20) — which is why prompt
    version and model are parameters, not the module constants. The
    mechanical adr_count (ADR-0004) is computed onto the audit row here,
    at assemble time — NULL if the session's substrate isn't scanned yet
    (the import path; fill_substrate stamps it on the next run)."""
    conn.execute(
        "INSERT OR REPLACE INTO audit"
        " (session_id, project, date, skip, markdown, prompt_version, model, adr_count)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (session["id"], session["project"], session["date"], skip,
         None if skip else md, what_version, model, adr_count(conn, session["id"])))


def process_session(conn, work_dir, session, model_runner):
    """Runs the what-pass (+ merge call for multi-part) for one session,
    writing its audit row on success. Raises LimitExhausted through
    uncaught, leaving the session's status untouched (still pending/partial)
    for the next run."""
    sid = session["id"]
    # Cache dir is keyed by prompt version: a version bump never reuses a
    # stale cached output under the new label.
    what_dir = Path(work_dir) / PROMPT_VERSION
    try:
        parts = extract_session(work_dir, sid, session["transcript_path"])
    except ExtractionFailed:
        _mark(conn, sid, "partial")
        return
    if not parts:
        _mark(conn, sid, "empty")
        return

    what_texts = []
    for part in parts:
        text = call_cached(model_runner, what_prompt(part.read_text()),
                            what_dir / f"{part.stem}.md")
        if text is None:
            _mark(conn, sid, "partial")
            return
        what_texts.append(text)

    if len(what_texts) > 1:
        joined = "\n\n---\n\n".join(what_texts)
        md = call_cached(model_runner, MERGE_PROMPT + "\n\n" + joined,
                          what_dir / f"{sid}.merged.md")
        if md is None:
            _mark(conn, sid, "partial")
            return
    else:
        md = what_texts[0]
    md = strip_fences(md).strip()
    skip = md.startswith("SKIP")

    insert_results(conn, session, skip, md, PROMPT_VERSION, MODEL)
    # #73's watermark: *this* pipeline audited *this* transcript at this
    # size. Set here and not in insert_results, which the backfill import
    # also calls with a size that is archive metadata, not a measurement —
    # an imported session keeps a NULL watermark and is never re-audited on
    # size grounds, since nothing records what its audit actually saw.
    conn.execute("UPDATE sessions SET audited_size = size WHERE id=?", (sid,))
    _mark(conn, sid, "done")


def refresh_narratives(conn, projects_dir, model_runner):
    """The status-narrative pass (ADR-0012, ticket #68): one bounded fact
    list per declaring project, synthesised from the run ledger alone and
    stored in `status_narrative`. Runs after the session loop (the ledger
    is made of audit titles) and only when the ledger's content, prompt
    version or model has changed — so a quiet project costs nothing and a
    page load never calls the model (ADR-0008). Write-time gate: the eval's
    ground-truth-free floors (M3–M6, eval/score.py `contract`) — a refusal,
    non-JSON or off-contract output is not stored; the previous narrative
    (if any) stays, its hash no longer matching, and the next run retries.
    LimitExhausted propagates to the caller's pause."""
    import how  # sibling module; imports analyze, so bound late
    # fetchall: an open read cursor across a minute-long model call holds a
    # SHARED lock the listener's pending write deadlocks against.
    for (project,) in conn.execute("SELECT DISTINCT project FROM sessions"
                                   " WHERE project IS NOT NULL ORDER BY 1").fetchall():
        # No valid declaration: no how-view, no narrative (#64). Asked via
        # read_declaration, ADR-0011's one read location — a second
        # `is_file()` here was a duplicate that could drift from it (#72).
        # Still a short-circuit: how_data scans every event for the project,
        # which a non-declaring project should not pay on every run.
        if how.read_declaration(Path(projects_dir) / project)[0] != "valid":
            continue
        d = how.how_data(conn, project, projects_dir)
        if not d["runs"]:
            continue
        ledger, h = how.ledger(d), how.ledger_hash(d)
        if conn.execute("SELECT 1 FROM status_narrative WHERE project=?"
                        " AND ledger_hash=? AND prompt_version=? AND model=?",
                        (project, h, STATUS_VERSION, MODEL)).fetchone():
            continue
        text = model_runner(ledger_prompt(STATUS_PROMPT, ledger))
        try:
            out = parse(text or "")
        except ValueError:
            continue
        if not isinstance(out, dict) or not contract(d["runs"], out)[0]["ok"]:
            continue
        conn.execute("INSERT OR REPLACE INTO status_narrative (project, ledger_hash,"
                     " narrative, prompt_version, model, generated_at)"
                     " VALUES (?, ?, ?, ?, ?, ?)",
                     (project, h, json.dumps(out), STATUS_VERSION, MODEL,
                      datetime.now(timezone.utc).isoformat()))
        conn.commit()


def default_model_runner(prompt):
    try:
        r = subprocess.run(["claude", "-p", "--model", MODEL], input=prompt,
                            capture_output=True, text=True, timeout=CALL_TIMEOUT, cwd=REPO)
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        # No `claude` on PATH — a machine state, not a session failure
        # (launchd's stripped default PATH is the known case; ticket #84).
        # Same designed pause as limit exhaustion: sessions stay
        # pending/partial, the mechanical tail still runs, the next run
        # with `claude` resolvable resumes.
        print("claude CLI not found on PATH — model calls paused this run",
              file=sys.stderr)
        raise LimitExhausted("claude CLI not found on PATH")
    if r.returncode != 0:
        # ponytail: bare substring match on stderr — tighten against a
        # confirmed claude -p limit-exhaustion message if this false-positives.
        if "limit" in (r.stderr or "").lower():
            raise LimitExhausted(r.stderr.strip())
        return None
    return r.stdout


def store_blob(conn, content):
    """Content-addressed storage: identical content stored once."""
    h = hashlib.sha256(content.encode()).hexdigest()
    conn.execute("INSERT OR IGNORE INTO blobs (hash, content) VALUES (?, ?)",
                 (h, content))
    return h


def add_event(conn, observed_at, source, path, before, after):
    conn.execute(
        "INSERT INTO change_events (observed_at, source, path, before_hash,"
        " after_hash) VALUES (?, ?, ?, ?, ?)",
        (observed_at, source, path, before, after))


def _set_state(conn, key, value):
    """backstop_state is the diff-against memory: a surface filename -> its
    last snapshot's blob hash, PLUGINS_FILE -> ditto, git:<repo> -> the last
    processed commit sha, BASELINE_KEY -> when the baseline was taken."""
    conn.execute("INSERT OR REPLACE INTO backstop_state (key, value)"
                 " VALUES (?, ?)", (key, value))


def _git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def _capture_project_git(conn, repo, state):
    """Change events from commits touching a project's .claude — commits
    only, never the working tree. A repo seen for the first time is its own
    silent baseline: its history predates tracking."""
    key = f"git:{repo.name}"
    head = (_git(repo, "log", "-1", "--format=%H", "--", ".claude") or "").strip()
    if not head:
        return
    prev = state.get(key)
    if prev == head:
        return
    if prev is not None:
        log = _git(repo, "log", "--reverse", "--format=%H %cI",
                   f"{prev}..{head}", "--", ".claude")
        # ponytail: prev unreachable (history rewritten) rebaselines silently;
        # walk the full log with dedupe if rewritten history ever matters.
        for line in (log or "").splitlines():
            sha, cdate = line.split()
            files = _git(repo, "diff-tree", "--no-commit-id", "--name-only",
                         "-r", sha, "--", ".claude") or ""
            for path in files.splitlines():
                before = _git(repo, "show", f"{sha}^:{path}")
                after = _git(repo, "show", f"{sha}:{path}")
                add_event(conn, cdate, "project-git", f"{repo.name}/{path}",
                          None if before is None else store_blob(conn, before),
                          None if after is None else store_blob(conn, after))
    _set_state(conn, key, head)


def _capture_plugins(conn, claude_dir, state, observed_at, baseline):
    """Structural installed_plugins.json diff: one event per plugin whose
    entry changed (install/update/remove), source `plugins-structural`.
    Before/after hashes are the whole-file blobs; the diff itself is
    render-time. Non-structural edits update the stored hash, no events."""
    pf = Path(claude_dir) / PLUGINS_FILE
    prev = state.get(PLUGINS_FILE)
    if not pf.exists():
        if prev is not None:
            add_event(conn, observed_at, "plugins-structural", PLUGINS_FILE,
                      prev, None)
            conn.execute("DELETE FROM backstop_state WHERE key=?",
                         (PLUGINS_FILE,))
        return
    content = pf.read_text()
    h = store_blob(conn, content)
    if prev is not None and prev != h:
        before = plugin_entries(conn.execute(
            "SELECT content FROM blobs WHERE hash=?", (prev,)).fetchone()[0]) or {}
        after = plugin_entries(content) or {}
        for name in sorted(set(before) | set(after)):
            if before.get(name) != after.get(name):
                add_event(conn, observed_at, "plugins-structural", name,
                          prev if name in before else None,
                          h if name in after else None)
    elif prev is None and not baseline:
        add_event(conn, observed_at, "plugins-structural", PLUGINS_FILE,
                  None, h)
    _set_state(conn, PLUGINS_FILE, h)


def capture_backstop(conn, claude_dir, projects_dir, observed_at):
    """The silent-change backstop (ticket #21), run once per analysis run:
    the mechanical owner of setup changes no conversation mentions. The
    first capture records state silently (the silent baseline); later
    captures turn every difference into a change event."""
    state = dict(conn.execute("SELECT key, value FROM backstop_state"))
    baseline = BASELINE_KEY not in state

    for name in BACKSTOP_SURFACE:
        f = Path(claude_dir) / name
        prev = state.get(name)
        if f.exists():
            h = store_blob(conn, f.read_text())
            if prev is None and not baseline:
                add_event(conn, observed_at, "snapshot", name, None, h)
            elif prev is not None and prev != h:
                add_event(conn, observed_at, "snapshot", name, prev, h)
            _set_state(conn, name, h)
        elif prev is not None:
            add_event(conn, observed_at, "snapshot", name, prev, None)
            conn.execute("DELETE FROM backstop_state WHERE key=?", (name,))

    _capture_plugins(conn, claude_dir, state, observed_at, baseline)

    if Path(projects_dir).is_dir():
        for repo in sorted(Path(projects_dir).iterdir()):
            if (repo / ".git").exists():
                _capture_project_git(conn, repo, state)

    if baseline:
        _set_state(conn, BASELINE_KEY, observed_at)
    conn.commit()


def folder_present(projects_dir, project):
    """ADR-0009: a project's workspace folder exists if *any* decoding of the
    dashes in its encoded name resolves to a directory under projects_dir.
    The encoding is lossy — `my-os-my-logs` is a session run in `my-os/my-logs`,
    a subdirectory of a live project, and must never false-hide it."""
    def walk(base, parts):
        if not parts:
            return True
        for i in range(1, len(parts) + 1):
            child = base / "-".join(parts[:i])
            if child.is_dir() and walk(child, parts[i:]):
                return True
        return False

    return walk(Path(projects_dir), project.split("-"))


def observe_presence(conn, projects_dir):
    """ADR-0009: record every project's folder presence, so the server renders
    a stored observation instead of forming filesystem opinions at request
    time. Rewritten whole each run — a deletion hides at the next run, a
    recreated folder returns at the one after it."""
    if not Path(projects_dir).is_dir():
        return  # could not look — not the same as every folder being gone
    seen = [(p, int(folder_present(projects_dir, p))) for (p,) in conn.execute(
        "SELECT DISTINCT project FROM sessions WHERE project IS NOT NULL")]
    conn.execute("DELETE FROM project_presence")
    conn.executemany("INSERT INTO project_presence (project, present)"
                     " VALUES (?, ?)", seen)
    conn.commit()


def run_analysis(root=DEFAULT_TRANSCRIPTS, db_path=DEFAULT_DB,
                  work_dir=DEFAULT_WORK_DIR, model_runner=None,
                  claude_dir=DEFAULT_CLAUDE_DIR, projects_dir=DEFAULT_PROJECTS_DIR):
    model_runner = model_runner or default_model_runner
    conn = init_db(db_path)
    try:
        sync_sessions(conn, root)
        invalidate_grown(conn, work_dir)
        fill_substrate(conn)
        classify_and_extract(conn, work_dir)
        todo = conn.execute(
            "SELECT id, project, transcript_path, date FROM sessions"
            f" WHERE status IN {SELECTABLE_SQL} ORDER BY id").fetchall()
        # ponytail: serial, one claude -p call at a time; parallelize if a
        # large run's wall-clock becomes the bottleneck — kept serial here
        # for a clean, testable limit-exhaustion pause boundary.
        for sid, project, path, date in todo:
            if _is_live(path):
                continue  # live session: stays pending for the next run
            session = {"id": sid, "project": project, "transcript_path": path, "date": date}
            try:
                process_session(conn, work_dir, session, model_runner)
            except LimitExhausted:
                paused = True
                break  # designed pause — remaining sessions stay pending/partial
        else:
            paused = False
        if not paused:  # the narrative pass would only hit the same limit
            try:
                refresh_narratives(conn, projects_dir, model_runner)
            except LimitExhausted:
                pass  # ledgers unchanged, so the next run retries
            except Exception as e:
                # Ticket #77: the narrative is a nicety with a designed
                # fallback (the mechanical status, ADR-0012); the backstop
                # and sunk-cost scans below are mechanical fact. Never trade
                # the second for the first — nothing is stored, so the next
                # run retries, exactly as a gate rejection does.
                print(f"narrative pass failed: {e!r}", file=sys.stderr)
        # Backstop after the session loop; mechanical only, so a limit
        # pause never skips it.
        capture_backstop(conn, claude_dir, projects_dir,
                         datetime.now(timezone.utc).isoformat())
        scan_sunk_cost(conn, claude_dir, projects_dir)
        observe_presence(conn, projects_dir)
    finally:
        conn.close()


NIGHTLY_LABEL = "com.hindsight.nightly"
NIGHTLY_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{NIGHTLY_LABEL}.plist"
NIGHTLY_HOUR = 3


def nightly_plist():
    log = str(REPO / "local-data" / "analyze.log")
    return plistlib.dumps({
        "Label": NIGHTLY_LABEL,
        "ProgramArguments": [sys.executable, str(Path(__file__).resolve())],
        "StartCalendarInterval": {"Hour": NIGHTLY_HOUR, "Minute": 0},
        # launchd's default PATH lacks `claude` (and the CLI-kind probes);
        # bake the installing shell's PATH, where both are known to resolve.
        "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        "StandardOutPath": log,
        "StandardErrorPath": log,
    }).decode()


def install_nightly():
    (REPO / "local-data").mkdir(parents=True, exist_ok=True)
    NIGHTLY_PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    NIGHTLY_PLIST_PATH.write_text(nightly_plist())
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(NIGHTLY_PLIST_PATH)],
                   capture_output=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(NIGHTLY_PLIST_PATH)],
                   check=True)
    print(f"installed {NIGHTLY_PLIST_PATH}, runs daily at {NIGHTLY_HOUR:02d}:00")


def uninstall_nightly():
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}",
                    str(NIGHTLY_PLIST_PATH)], capture_output=True)
    NIGHTLY_PLIST_PATH.unlink(missing_ok=True)
    print(f"removed {NIGHTLY_PLIST_PATH}")


def main(argv):
    if argv[:1] == ["install"]:
        return install_nightly()
    if argv[:1] == ["uninstall"]:
        return uninstall_nightly()
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_TRANSCRIPTS)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    ap.add_argument("--claude-dir", type=Path, default=DEFAULT_CLAUDE_DIR)
    ap.add_argument("--projects-dir", type=Path, default=DEFAULT_PROJECTS_DIR)
    args = ap.parse_args(argv)
    run_analysis(args.root, args.db, args.work_dir,
                 claude_dir=args.claude_dir, projects_dir=args.projects_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
