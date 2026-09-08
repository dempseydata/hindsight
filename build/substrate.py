"""The substrate scan (tickets #22, #42, #61) — the transcript JSONL
grammar in one place: one full parse per session into tool_events (paired,
deduped, consumer-classified), usage (deduped by API message id) and
command_grains, plus the mechanical adr_count derived from tool_events
(ADR-0004) and the live-session guard the fill respects (ticket #29).

A leaf module: imports extract's FILE_TOOLS and nothing from analyze —
the import direction is analyze -> substrate only (ticket #82). Also home
to former_names, the presence-history read adr_count and the how pipeline
share (ADR-0018) — here because adr_count cannot import analyze.
"""
import functools
import json
import re
import shutil
import time
from pathlib import Path

from extract import FILE_TOOLS  # the create/modify tool set

# Command grain (ticket #61): the name inside a genuine command message's
# <command-name> marker, captured verbatim.
_COMMAND_RE = re.compile(r"<command-name>(.*?)</command-name>", re.S)

# Consumer grain (ticket #42): who a tool call is charged to in the
# where-view league — ported from ccwhere's validated parse.
_CLI_WRAPPERS = {"sudo", "nohup", "time", "command", "exec", "env",
                 "do", "then", "else"}  # wrappers/keywords preceding the program
_CLI_SKIP_SEG = {"cd", "for", "while", "until", "if", "done", "fi", "elif"}


def _cli_program(command):
    """First acting program in a Bash command, or None when unextractable.
    ponytail: naive split, not a shell parser — quoted separators and
    substitutions fall through to None, which classifies as plain Bash."""
    if not command or not isinstance(command, str):
        return None
    for seg in re.split(r"\|\||&&|;|\|", command):
        toks = seg.split()
        i = 0
        while i < len(toks) and (re.match(r"^\w+=", toks[i])
                                 or toks[i] in _CLI_WRAPPERS):
            i += 1
        if i < len(toks) and toks[i] == "npx":
            i += 1
            while i < len(toks) and toks[i].startswith("-"):
                i += 1
        elif i + 1 < len(toks) and toks[i] == "pnpm" and toks[i + 1] == "dlx":
            i += 2
        if i >= len(toks):
            continue
        prog = toks[i].rsplit("/", 1)[-1]
        if prog in _CLI_SKIP_SEG:
            continue  # positions or controls flow, doesn't act
        # must look like a program name, not a stray flag or operand
        return prog if re.fullmatch(r"[A-Za-z0-9][\w.+-]*", prog) else None
    return None


_STD_DIRS = ("/bin/", "/usr/bin/", "/sbin/", "/usr/sbin/")
_SHELL_BUILTINS = {"source", "export", "set", "unset", "alias", "eval",
                   "trap", "shift", "read", "wait", "exit", "true", "false",
                   "type", "ulimit", "umask", "printf", "echo", "test"}
@functools.cache
def _cli_kind(prog):
    """OS-shipped binaries and shell builtins are 'shell' (ubiquitous,
    unprunable); everything else — installed binaries, scripts, programs no
    longer on PATH — is 'cli' (actionable). Machine-derived from PATH at
    scan time, never a curated command list."""
    if prog in _SHELL_BUILTINS:
        return "shell"
    path = shutil.which(prog)
    return "shell" if path and path.startswith(_STD_DIRS) else "cli"


def classify(name, tool_input):
    """(consumer_type, consumer, mcp_tool) for one tool_use:
    skill / mcp / cli / shell / builtin."""
    if name == "Skill":
        return "skill", str((tool_input or {}).get("skill", "?")), None
    if name == "Bash":
        prog = _cli_program((tool_input or {}).get("command"))
        if prog:
            return _cli_kind(prog), prog, None
        return "builtin", name, None
    if name.startswith("mcp__"):
        parts = name.split("__")
        server = parts[1] if len(parts) > 1 else name
        tool = "__".join(parts[2:]) if len(parts) > 2 else None
        return "mcp", server, tool
    return "builtin", name, None


def scan_transcript(path):
    """One full parse of a transcript into the where-view substrate (tickets
    #22, #42) plus command grains (ticket #61). Returns (events, usage_rows,
    commands, skipped): events as dicts keyed by tool_events column name,
    with tool_use/tool_result paired by id — a tool_use without an id (older
    CLIs) keeps its row with result_at/is_error NULL, a tool_result without
    a tool_use_id is ignored. Duplicate tool_use ids (the records streaming
    one response repeat its blocks) keep one row; a tool_use whose name
    holds command text (whitespace — the #38 parse wart) or is not a string
    at all is malformed and counts as skipped once. commands as
    [command, at]: a user-typed slash command injects its skill with no
    Skill tool_use, visible only as a user message *starting* with a
    <command-…> marker (either <command-name> or <command-message> leads;
    the starts-with rule is #59's parse-level finding — a grep would count
    quoted markers inside analysis extracts); the name is captured verbatim.
    usage_rows as [message_id, at, model, in, out, cache_creation,
    cache_read], deduped by API message id; skipped also counts unparseable
    lines and record types the scan doesn't consume — counted, never
    fatal."""
    events, results, usage, commands, skipped, seen_ids = [], {}, {}, [], 0, set()
    with Path(path).open() as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            t, m = e.get("type"), e.get("message")
            content = m.get("content") if isinstance(m, dict) else None
            if t == "assistant":
                mid = m.get("id") if isinstance(m, dict) else None
                u = m.get("usage") if isinstance(m, dict) else None
                if isinstance(u, dict):
                    key = mid or e.get("uuid") or ("anon", len(usage))
                    usage[key] = [mid, e.get("timestamp"), m.get("model"),
                                  u.get("input_tokens") or 0,
                                  u.get("output_tokens") or 0,
                                  u.get("cache_creation_input_tokens") or 0,
                                  u.get("cache_read_input_tokens") or 0]
                for c in (content if isinstance(content, list) else []):
                    if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                        continue
                    name, tid = c.get("name"), c.get("id")
                    # dedup before the malformation skips, so one malformed
                    # call streamed across records counts skipped once
                    if tid in seen_ids:
                        continue
                    if tid:
                        seen_ids.add(tid)
                    if name is not None and not isinstance(name, str):
                        skipped += 1  # non-string name: same wart, other face
                        continue
                    # ponytail: whitespace is the malformation tell (#38) — a
                    # single-token command stored as a name would slip through.
                    if name and re.search(r"\s", name):
                        skipped += 1
                        continue
                    inp = c.get("input") if isinstance(c.get("input"), dict) else {}
                    ctype, consumer, mcp_tool = (classify(name, inp) if name
                                                 else (None, None, None))
                    events.append({
                        "tool_use_id": tid, "name": name,
                        "at": e.get("timestamp"), "result_at": None,
                        "file_path": inp.get("file_path") or inp.get("notebook_path"),
                        "message_id": mid, "consumer_type": ctype,
                        "consumer": consumer, "mcp_tool": mcp_tool,
                        "is_error": None})
            elif t == "user":
                # ponytail: string content only — every real command message
                # observed is plain-string (209/209 across 69 transcripts);
                # widen if the CLI ever writes command markers into blocks.
                if isinstance(content, str) and content.lstrip().startswith("<command-"):
                    cm = _COMMAND_RE.search(content)
                    if cm:
                        commands.append([cm.group(1), e.get("timestamp")])
                for c in (content if isinstance(content, list) else []):
                    if (isinstance(c, dict) and c.get("type") == "tool_result"
                            and c.get("tool_use_id")):
                        results[c["tool_use_id"]] = (
                            e.get("timestamp"), 1 if c.get("is_error") else 0)
            else:
                skipped += 1
    for ev in events:
        r = results.get(ev["tool_use_id"]) if ev["tool_use_id"] else None
        if r:
            ev["result_at"], ev["is_error"] = r
    return events, list(usage.values()), commands, skipped


def former_names(conn, project):
    """The names this project carried before its current one, oldest first
    (ADR-0018): every other name presence history has seen under the folder
    identity the project's own sessions carry. The identity comes from the
    sessions, not from the presence flag, so a project deleted after a
    rename keeps its past; a vacated name (`hindsight`, held in turn by two
    inodes, now holding only name-only sessions) claims neither successor.
    Empty for a name-only project or one never renamed."""
    return [n for (n,) in conn.execute(
        "SELECT p.name FROM sessions s JOIN project_presence p"
        " ON p.folder_identity = s.folder_identity"
        " WHERE s.project = ? AND p.name != s.project"
        " GROUP BY p.name ORDER BY MIN(p.first_seen)", (project,))]


def adr_count(conn, sid):
    """The mechanical ADR count (ADR-0004): distinct files under the
    project's docs/adr/ created or modified by the session's tool events —
    semantics "ADRs touched", never model-derived. NULL when the session was
    never substrate-scanned (transcript gone before scanning), so an unknown
    reads as unknown, not a false zero. A write recorded under a former
    name's root counts too (ADR-0018): the session was re-keyed, its paths
    were not.
    ponytail: project scoping is a path-segment match — file-tool paths are
    absolute and workspace projects live at .../<project>/; a project whose
    name is a mangled transcript dirname (outside the workspace) counts 0.
    Resolve against the repo's real path if that ever matters."""
    row = conn.execute("SELECT project, skipped_records FROM sessions WHERE id=?",
                       (sid,)).fetchone()
    if row is None or row[1] is None:
        return None
    names = [row[0], *former_names(conn, row[0])]
    marks = ", ".join("?" * len(FILE_TOOLS))
    roots = " OR ".join("file_path LIKE ?" for _ in names)
    return conn.execute(
        f"SELECT COUNT(DISTINCT file_path) FROM tool_events WHERE session_id=?"
        f" AND name IN ({marks}) AND ({roots})",
        (sid, *sorted(FILE_TOOLS), *(f"%/{n}/docs/adr/%" for n in names))).fetchone()[0]


def fill_substrate(conn):
    """The sync stage that fills tool_events + usage + command_grains for
    every session not yet scanned — sessions newly synced this run, and
    sessions that predate the substrate (the ticket-#20 backfill import) on
    their next run, whose existing audit rows get adr_count stamped here.
    sessions.skipped_records doubles as the scanned marker: NULL means never
    scanned, and a vanished transcript stays NULL rather than reading as an
    empty session."""
    todo = conn.execute("SELECT id, transcript_path FROM sessions"
                        " WHERE skipped_records IS NULL").fetchall()
    for sid, path in todo:
        if not Path(path).exists() or _is_live(path):
            continue
        events, usage_rows, commands, skipped = scan_transcript(path)
        conn.executemany(
            "INSERT INTO tool_events (session_id, tool_use_id, name, at,"
            " result_at, file_path, message_id, consumer_type, consumer,"
            " mcp_tool, is_error) VALUES (:session_id, :tool_use_id, :name,"
            " :at, :result_at, :file_path, :message_id, :consumer_type,"
            " :consumer, :mcp_tool, :is_error)",
            [{**ev, "session_id": sid} for ev in events])
        conn.executemany(
            "INSERT INTO usage (session_id, message_id, at, model, input_tokens,"
            " output_tokens, cache_creation_input_tokens, cache_read_input_tokens)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [(sid, *u) for u in usage_rows])
        conn.executemany(
            "INSERT INTO command_grains (session_id, command, at)"
            " VALUES (?, ?, ?)", [(sid, *c) for c in commands])
        conn.execute("UPDATE sessions SET skipped_records=? WHERE id=?",
                     (skipped, sid))
        conn.execute("UPDATE audit SET adr_count=? WHERE session_id=?",
                     (adr_count(conn, sid), sid))
        conn.commit()  # per session — short write transactions on a shared db


LIVE_WINDOW_S = 300  # transcript written this recently = session still live


def _is_live(path):
    """A transcript modified within the window is a live session (ticket #29):
    extracting it mid-flight would cache a truncated prefix forever. Skipped
    sessions stay pending/partial for the next run."""
    p = Path(path)
    return p.exists() and time.time() - p.stat().st_mtime < LIVE_WINDOW_S
