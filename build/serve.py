"""hindsight on-demand foreground server (ADR-0008, ticket #44).

  serve.py [--port N] [--db PATH]   run in the foreground (default :8321)

Started to look, Ctrl-C when done. Strictly read-only over SQLite (mode=ro
URI): never invokes the model, never writes the DB, never grows a run
button. The where-view's metrics refresh is browser reload — every GET
re-queries the DB live. design/tokens.css (the direction contract) is
inlined at render time, so a token edit shows on the next reload.

Every day bucket is the operator's local day, converted at read time from
the stored UTC timestamp (ADR-0014) — `day_sql()` in SQL, `local_day()` in
Python, both from analyze.py so the two can never drift.

Shared header chrome (both views): project chips that filter, never
switch; a stacked per-day token chart, calendar-continuous and scrollable,
newest at right; click-a-bar time filtering (day -> range -> deselect);
window presets 7/14/28/90/all, default 14, anchored to the last-synced
day; a hide-cache-reads toggle. Views mount by registering a re-render
callback via `hs.onFilter(fn)` in page JS.

What-view (ticket #45): the cross-project session ledger — one collapsed
row per audit entry (project chip · title · n did / n decided · ADR badge
when nonzero), day roll-up as render-time grouping only, expanding via
native <details> to the full Did / Decided / Setup-changes entry. SKIP
sessions render as dim one-liners; #38's malformed refusal rows are
tolerated (dim row, raw text in the expansion), never repaired here.

Where-view (ticket #48): the panel dashboard — tiles, consumer league
(dual lens: session-lens hands a consumer every session it appeared in,
message-lens only the API responses that invoked it, joined on message_id
alone per #42; category chips scope the league, mcp+cli+skill on by
default per #55), models + latency, MCP servers, CLI tools, sunk-cost
ledger, hook activity. Sparks share one 30-calendar-day axis; errors/day
render beneath calls; OTEL-fed sparks shade the pre-coverage region.
Pricing/cost columns are never rendered (ADR-0003).

How-view (ticket #65, ADR-0010/0011/0012): one declaring project at a time
(`?p=`; the selector lists projects whose `.claude/my-process.md` exists —
absent declaration = no view), rendered server-side with no script: the
status card (model-written Built / Reversed / Now from `status_narrative`,
marked stale when its ledger hash no longer matches the live ledger, the
mechanical line when absent) over the phase runs newest first, beside the
stated-process panel. The shared chips / chart / window chrome does not
appear — the choice switches, it never filters. An invalid declaration
renders its line-numbered error and the trail grouped by session.
"""
import argparse
import datetime
import html
import json
import re
import sqlite3
import statistics
import sys
from collections import Counter
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# build/ is sys.path[0] when run as a script, and importers of this module
# already resolve build/ — no path insert needed (the #50 shadowing lesson).
import how
from analyze import (DEFAULT_PROJECTS_DIR, DEFAULT_DB, LOST, REPO,  # noqa: E402 — one authority on paths
                     SECTIONS, audit_title, day_sql, local_day)
from score import BOUNDS  # noqa: E402 — narrative group names; eval/ on sys.path via analyze

TOKENS_CSS = REPO / "design" / "tokens.css"
# View CSS/JS/HTML, one file per extracted constant (ticket #80). The CSS is
# tokens only — every colour via var(--o-*), chart ink on the ink palette,
# selection on the compare hue (floor rules, tokens.css).
ASSETS = REPO / "build" / "assets"
DEFAULT_PORT = 8321

# Chip policy (judged on real data, resolution of ticket #44): a project
# gets a chip when its encoded name is not a filesystem path (leading "-"
# marks scratchpads, probes and system dirs — unreadable as chips) AND it
# clears >=1% of all-time tokens or >=1% of all-time sessions. The session
# leg keeps ledger-heavy projects whose transcripts were pruned (tokens
# unknown, never zero); all-time so the chip row is stable across window
# changes. Tail projects stay chipless but their data is always counted.
CHIP_SHARE = 0.01


def open_db(db_path):
    # The file is WAL (issue #12), so a read never waits on a writer; the
    # timeout covers the brief checkpoint lock and a db no writer has
    # switched yet, where it means "wait for the write" instead of a 500.
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)


def chip_rows(projects):
    """projects: [(name, sessions, tokens-or-None)] -> chip names, tail count.
    A leg whose total is zero (pre-substrate db) is off, not all-pass —
    0 >= 0 must never hand every project a chip."""
    total_tok = sum(t or 0 for _, _, t in projects)
    total_sess = sum(s for _, s, _ in projects)
    chips = [(p, s, t or 0) for p, s, t in projects
             if not p.startswith("-")
             and ((total_tok and (t or 0) >= total_tok * CHIP_SHARE)
                  or (total_sess and s >= total_sess * CHIP_SHARE))]
    chips.sort(key=lambda r: (-r[2], -r[1], r[0]))
    return [p for p, _, _ in chips], len(projects) - len(chips)


def hidden_projects(conn):
    """Projects whose workspace folder was absent under every name it has
    carried when the last analysis run looked (ADR-0009, extended by
    ADR-0018's presence history: a name is hidden only when none of its
    rows — across whatever identity has held it — says present, so a name
    a rename just vacated never shadows the different project that has
    since taken it up). Read-only: the observation is stored, never taken
    here — no filesystem opinions at render time. Empty until a run has
    observed, so an un-analysed db hides nothing. A db predating the table
    hides nothing either: the server is read-only, so only the next run
    can create it."""
    if not conn.execute("SELECT 1 FROM sqlite_master"
                        " WHERE name = 'project_presence'").fetchone():
        return set()
    return {p for (p,) in conn.execute(
        "SELECT name FROM project_presence GROUP BY name HAVING MAX(present) = 0")}


def header_data(conn):
    days = [{"d": d, "p": p, "t": [i, o, cc, cr]} for d, p, i, o, cc, cr in
            conn.execute(f"""
        SELECT {day_sql("u.at")}, s.project,
               SUM(u.input_tokens), SUM(u.output_tokens),
               SUM(u.cache_creation_input_tokens), SUM(u.cache_read_input_tokens)
        FROM usage u JOIN sessions s ON s.id = u.session_id
        WHERE u.at IS NOT NULL GROUP BY 1, 2""")]
    projects = list(conn.execute("""
        SELECT s.project, COUNT(DISTINCT s.id),
               SUM(u.input_tokens + u.output_tokens
                   + u.cache_creation_input_tokens + u.cache_read_input_tokens)
        FROM sessions s LEFT JOIN usage u ON u.session_id = s.id
        GROUP BY s.project"""))
    chips, tail = chip_rows(projects)
    # Hiding is chips-only: `tail`, the chart, the ledger, the league and the
    # totals never see it — a hidden project's data behaves like a chipless
    # tail project's (ADR-0009).
    hidden = hidden_projects(conn)
    last_synced = conn.execute("SELECT MAX(date) FROM sessions").fetchone()[0]
    # Range end covers usage days too: sessions.date is the *start* day, so a
    # session crossing midnight puts usage rows past it — the chart and the
    # window presets must still reach them (ticket #50).
    last_day = max((r["d"] for r in days), default=None)
    end = max((d for d in (last_synced, last_day) if d), default=None)
    first_day = min((r["d"] for r in days), default=end)
    return {"days": days, "range": [first_day, end], "chips": chips,
            "hidden": [p for p in chips if p in hidden], "tail": tail,
            "sessions": sum(s for _, s, _ in projects), "synced": last_synced}


_SECTION_RE = {
    name: re.compile(
        rf"\*\*{name}:\*\*(.*?)(?=\n\s*[-*]?\s*\*\*(?:{'|'.join(SECTIONS)}):\*\*|\Z)",
        re.S)
    for name in SECTIONS}


def parse_entry(md):
    """Audit markdown -> {title, sections}; None when unparseable (#38 rows).

    Section names are the audit format locked by ADR-0004, not free prompt
    text — a prompt edit that reshapes them is a format change and goes
    through that ADR, at which point this parser moves with it.

    Two shapes exist in the corpus: bullet sections (`- **Did:**` with
    nested items) and paragraph sections (`**Did:** a; b; c`). Items are
    the nested bullets, or the semicolon-separated clauses of a paragraph
    (kept as one block for display, counted for the row).
    """
    title = audit_title(md)
    if title is None:
        return None
    sections = []
    for name in SECTIONS:
        sm = _SECTION_RE[name].search(md)
        if not sm:
            continue
        body = sm.group(1).strip()
        items = [i.strip() for i in re.findall(r"^\s*[-*]\s+(.*\S)", body, re.M)]
        if items:
            sections.append({"name": name, "items": items, "para": False,
                             "n": len(items)})
        elif body:
            sections.append({"name": name, "items": [body], "para": True,
                             "n": len([c for c in re.split(r";\s+", body) if c.strip()])})
    return {"title": title, "sections": sections}


def subagent_counts(conn):
    """{session_id: subagent transcripts filed under it} (issue #13) — the
    mechanical count both views' "N subagents" read; sessions with none absent."""
    return dict(conn.execute("SELECT session_id, COUNT(*) FROM subagent_transcripts"
                             " GROUP BY session_id"))


def what_data(conn):
    """One row per session, newest day first — the cross-project ledger.

    LEFT JOIN so synced-but-unanalyzed sessions still get a (pending) row:
    the ledger must never silently omit a session the coverage line counts.
    A `lost` session (ticket #78) is the one place status is a view input:
    without it, "not yet" and "never" render identically.

    A session is filed under every local day it had usage (issue #9), so
    the ledger and the chart agree on which days are empty: the full row
    under its first active day, then a thin continuation row per later day
    — id, project, day, the status flags and a `cont` note — that what.js
    resolves to the entry by id. A session with no usage keeps its start day
    alone; an undated one can't be windowed and stays one always-shown row.

    `sub` is the count of subagent transcripts filed under the session
    (issue #13) — a mechanical note so a large total has a visible cause;
    absent when there are none.
    """
    days = {sid: sorted(ds.split(",")) for sid, ds in conn.execute(f"""
            SELECT session_id, GROUP_CONCAT(d) FROM (
                SELECT DISTINCT session_id, {day_sql("at")} AS d
                FROM usage WHERE at IS NOT NULL)
            GROUP BY session_id""")}
    subs = subagent_counts(conn)
    rows = []
    for sid, project, date, skip, md, adr, pend, status in conn.execute("""
            SELECT s.id, s.project, s.date, a.skip, a.markdown, a.adr_count,
                   a.session_id IS NULL, s.status
            FROM sessions s LEFT JOIN audit a ON a.session_id = s.id
            ORDER BY s.date DESC, s.rowid DESC"""):
        r = {"id": sid, "p": project, "d": date, "skip": skip, "adr": adr}
        if sid in subs:
            r["sub"] = subs[sid]
        if status == LOST and pend:  # an entry always outranks the status
            # the blob key is the serve<->what.js contract (pinned by
            # test_serve's rendering asserts), not the status vocabulary —
            # equal to it only by coincidence, so a literal like "pend" below
            r["lost"] = 1
        elif status == "empty":  # #2: nothing extractable, never an audit row
            r["empty"] = 1
        elif pend:
            r["pend"] = 1
        elif not skip:
            entry = parse_entry(md)
            if entry is None:
                r["raw"] = md or ""
            else:
                r.update(entry)
        rows.append(r)
        active = days.get(sid) if date else None
        if active:
            r["d"] = first = active[0]
            flags = {k: 1 for k in ("skip", "pend", "lost", "empty") if r.get(k)}
            for day in active[1:]:   # day N counts calendar days, not resumes
                n = (datetime.date.fromisoformat(day)
                     - datetime.date.fromisoformat(first)).days + 1
                rows.append({"id": sid, "p": project, "d": day, **flags,
                             "cont": f"started {first} · day {n}"})
    # newest day first, undated last; stable, so a continuation lists after
    # the sessions that actually started that day
    rows.sort(key=lambda r: r["d"] or "", reverse=True)
    return rows


def where_data(conn):
    """The where-view blob, at (day, project) grain so the chrome's filters
    reshape every panel client-side.

    Pruned-transcript tool rows (NULL grains) ride along with ty '' —
    unknown, never dropped or reclassified at render time. Durations come
    from tool_use->tool_result pairing; unpaired calls count but carry no
    duration and read unknown (nu), not ok.
    """
    tools = []
    for d, p, ty, c, mt, n, e, nu, durs in conn.execute(f"""
            SELECT {day_sql("t.at")}, s.project,
                   COALESCE(t.consumer_type, ''), COALESCE(t.consumer, ''),
                   COALESCE(t.mcp_tool, ''), COUNT(*),
                   COALESCE(SUM(t.is_error), 0), SUM(t.is_error IS NULL),
                   GROUP_CONCAT(CASE WHEN t.result_at >= t.at THEN
                       CAST((julianday(t.result_at) - julianday(t.at))
                            * 86400000 AS INTEGER) END)
            FROM tool_events t JOIN sessions s ON s.id = t.session_id
            GROUP BY 1, 2, 3, 4, 5"""):
        r = {"d": d, "p": p, "ty": ty, "c": c, "n": n, "e": e, "nu": nu,
             "durs": sorted(int(x) for x in durs.split(",")) if durs else []}
        if mt:
            r["mt"] = mt
        tools.append(r)

    # message lens: distinct (consumer, message) pairs joined to usage on
    # message_id alone (globally unique — the #42 join contract)
    lens = [{"ty": ty, "c": c, "d": d, "p": p, "t": [i, o, cc, cr]}
            for ty, c, d, p, i, o, cc, cr in conn.execute(f"""
            SELECT g.consumer_type, g.consumer, {day_sql("u.at")},
                   s.project, SUM(u.input_tokens), SUM(u.output_tokens),
                   SUM(u.cache_creation_input_tokens),
                   SUM(u.cache_read_input_tokens)
            FROM (SELECT DISTINCT consumer_type, consumer, message_id
                  FROM tool_events
                  WHERE consumer_type IS NOT NULL
                    AND message_id IS NOT NULL) g
            JOIN usage u ON u.message_id = g.message_id
            JOIN sessions s ON s.id = u.session_id
            GROUP BY 1, 2, 3, 4""")]

    # session lens: sessions with known usage only (pruned = unknown). A
    # session's subagent count rides along as `na` (issue #13) — the tile's
    # agent count, attributed to the session's first day like the sessions
    # tile beside it; absent when none.
    subs = subagent_counts(conn)
    sess, sidx = [], {}
    for sid, p, d, i, o, cc, cr in conn.execute(f"""
            SELECT u.session_id, s.project, MIN({day_sql("u.at")}),
                   SUM(u.input_tokens), SUM(u.output_tokens),
                   SUM(u.cache_creation_input_tokens),
                   SUM(u.cache_read_input_tokens)
            FROM usage u JOIN sessions s ON s.id = u.session_id
            GROUP BY u.session_id"""):
        sidx[sid] = len(sess)
        sess.append({"p": p, "d": d, "t": [i, o, cc, cr],
                     **({"na": subs[sid]} if sid in subs else {})})
    # subagent tokens at (day, project) grain — the same base as the header's
    # day rows the tiles sum, so the tile's share is a true ratio in any window
    subd = [{"d": d, "p": p, "t": [i, o, cc, cr]}
            for d, p, i, o, cc, cr in conn.execute(f"""
            SELECT {day_sql("u.at")}, s.project,
                   SUM(u.input_tokens), SUM(u.output_tokens),
                   SUM(u.cache_creation_input_tokens),
                   SUM(u.cache_read_input_tokens)
            FROM usage u JOIN sessions s ON s.id = u.session_id
            WHERE u.agent_id IS NOT NULL GROUP BY 1, 2""")]
    cs = {}
    for ty, c, sid in conn.execute("""
            SELECT DISTINCT consumer_type, consumer, session_id
            FROM tool_events WHERE consumer_type IS NOT NULL"""):
        if sid in sidx:
            cs.setdefault((ty, c), []).append(sidx[sid])
    cons_sess = [{"ty": ty, "c": c, "s": v} for (ty, c), v in cs.items()]

    models = [{"d": d, "p": p, "m": m.replace("claude-", ""), "n": n,
               "t": [i, o, cc, cr]}
              for d, p, m, n, i, o, cc, cr in conn.execute(f"""
            SELECT {day_sql("u.at")}, s.project, u.model, COUNT(*),
                   SUM(u.input_tokens), SUM(u.output_tokens),
                   SUM(u.cache_creation_input_tokens),
                   SUM(u.cache_read_input_tokens)
            FROM usage u JOIN sessions s ON s.id = u.session_id
            WHERE u.model IS NOT NULL AND u.model != '<synthetic>'
            GROUP BY 1, 2, 3""")]

    # A db the listener never touched has no otel tables — latency and hook
    # panels read empty, coverage reads "—", nothing raises (ticket #50).
    has_otel = conn.execute("SELECT 1 FROM sqlite_master"
                            " WHERE name = 'otel_events'").fetchone()

    proj = dict(conn.execute("SELECT id, project FROM sessions"))
    lat = {}
    for ts, attrs in conn.execute("""
            SELECT timestamp, attributes FROM otel_events
            WHERE event_name = 'api_request'""") if has_otel else []:
        a = json.loads(attrs)
        dur = _ms(a.get("duration_ms"))
        if dur is None:
            continue
        key = (local_day(ts), proj.get(a.get("session.id")),
               (a.get("model") or "?").replace("claude-", ""))
        lat.setdefault(key, []).append(dur)
    lat_rows = [{"d": d, "p": p, "m": m, "durs": sorted(v)}
                for (d, p, m), v in lat.items()]

    # reliability panel (#14): retries and MCP connection health at event
    # grain, the session id as the evidence. Self-excluded analysis sessions
    # drop out, as the coverage line promises; a session OTEL saw but sync
    # never did keeps its rows with the project unknown (NULL), like the
    # latency rows above — never dropped.
    retries, mcp_conn = [], []
    for name, ts, sid, p, attrs in conn.execute("""
            SELECT o.event_name, o.timestamp, o.session_id, s.project,
                   o.attributes
            FROM otel_events o LEFT JOIN sessions s ON s.id = o.session_id
            WHERE o.event_name IN ('api_error', 'api_retries_exhausted',
                                   'mcp_server_connection')
              AND o.session_id NOT IN (SELECT id FROM excluded_sessions)
            ORDER BY o.timestamp""") if has_otel else []:
        a = json.loads(attrs)
        r = {"d": local_day(ts), "p": p, "sid": sid}
        if name == "mcp_server_connection":
            mcp_conn.append({**r, "srv": a.get("server_name") or "?",
                             "st": a.get("status") or "?",
                             "ms": _ms(a.get("duration_ms"))})
        else:
            ex = name == "api_retries_exhausted"
            retries.append({**r, "m": (a.get("model") or "?").replace("claude-", ""),
                            "ex": ex,
                            "ms": _ms(a.get("total_retry_duration_ms")) if ex else None})

    hooks = []
    for ts, attrs in conn.execute("""
            SELECT timestamp, attributes FROM otel_events
            WHERE event_name = 'hindsight.hook'""") if has_otel else []:
        a = json.loads(attrs)
        hooks.append({"d": local_day(ts),
                      "ev": a.get("hook.event") or "unknown",
                      "cpu": a.get("hook.cpu_ms"),
                      "dur": a.get("hook.duration_ms")})

    sunk = [{"p": p, "cat": cat, "pl": pl, "name": n, "tok": t}
            for p, cat, pl, n, t in conn.execute(
                "SELECT project, category, plugin, name, tokens "
                "FROM sunk_cost")]
    med = {}
    for p, v in conn.execute("""
            SELECT s.project, f.v FROM sessions s JOIN (
              SELECT session_id, input_tokens + cache_read_input_tokens
                     + cache_creation_input_tokens v,
                     ROW_NUMBER() OVER (PARTITION BY session_id
                                        ORDER BY at) rn
              FROM usage) f ON f.session_id = s.id AND f.rn = 1"""):
        med.setdefault(p, []).append(v)
    medians = {p: {"med": int(statistics.median(v)), "n": len(v)}
               for p, v in med.items()}

    one = lambda sql: conn.execute(sql).fetchone()[0]
    cov = {"usage_sessions": len(sess),
           "sessions": one("SELECT COUNT(*) FROM sessions"),
           "span": list(conn.execute(
               f"SELECT MIN({day_sql('at')}), MAX({day_sql('at')})"
               " FROM usage").fetchone()),
           "otel": (local_day(one("SELECT MIN(timestamp) FROM otel_events"))
                    if has_otel else ""),
           "hook": min((h["d"] for h in hooks), default=None),
           "excluded": one("SELECT COUNT(*) FROM excluded_sessions")}
    return {"tools": tools, "lens": lens, "sess": sess, "subd": subd, "cs": cons_sess,
            "models": models, "lat": lat_rows, "hooks": hooks,
            "retries": retries, "conn": mcp_conn,
            "sunk": sunk, "med": medians, "cov": cov}


def _ms(v):
    """An OTEL millisecond attribute as an int, or None — the CLI sends
    numbers as ints on some paths and as strings on others."""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None




def declaring_projects(conn, projects_dir):
    """Selector entries: projects in the DB whose declaration file exists
    (#64 addendum — absent = no view), busiest first."""
    return [p for (p,) in conn.execute(
        "SELECT project FROM sessions WHERE project IS NOT NULL"
        " GROUP BY project ORDER BY COUNT(*) DESC, project")
        if (Path(projects_dir) / p / ".claude" / "my-process.md").is_file()]


def _hue(d, stage):
    """Inline `--stage` for a declared stage: -1..-5 in declaration order,
    cycling past five (tokens.css)."""
    names = [s["name"] for s in d["declaration"]["stages"]]
    return f' style="--stage: var(--o-stage-{names.index(stage) % 5 + 1})"'


def _span(a, b):
    """Day-granular date or range, escaped like everything from the DB."""
    a, b = html.escape(local_day(a) or "?"), html.escape(local_day(b) or "?")
    return a if a == b else f"{a} → {b}"


def _status(conn, d):
    """The status card: how.narrative's row (already judged stale or not —
    the data seam lives beside the writer, #81), else the mechanical line —
    nothing generated here (ADR-0008), and no SQL here either."""
    runs = d["runs"]
    nar = how.narrative(conn, d["project"], d)
    out = ['<div class="panel status"><h2>Status</h2>']
    if nar:
        out.append('<div class="facts">')
        for g in BOUNDS:  # the contract's group names, in contract order
            items = nar["facts"].get(g) or []
            out.append(f"<div><h3>{g}</h3><ul>" + ("".join(
                f"<li>{html.escape(x)}</li>" for x in items)
                or '<li class="none">nothing</li>') + "</ul></div>")
        out.append("</div>")
        out.append(f'<p class="mech">narrative written {html.escape(nar["written_day"])}'
                   f" by {html.escape(nar['model'])}"
                   + (' · <span class="stale">stale — the ledger has moved'
                      " since; the next analysis run regenerates it</span>"
                      if nar["stale"] else "")
                   + "</p>")
    else:
        out.append('<p>No status narrative yet — it is written by the analysis'
                   " run once this project has phase runs.</p>")
    if runs:
        now, tally = runs[-1], Counter(r["stage"] for r in runs)
        out.append(f'<p class="mech"><b>{html.escape(now["stage"])}</b> since {html.escape(now["start"])}'
                   f" · {len(runs)} runs · {len(d['sessions'])} sessions"
                   f" · {_span(d['trail'][0]['at'], d['trail'][-1]['at'])} · "
                   + " · ".join(f"{html.escape(s['name'])} ×{tally.get(s['name'], 0)}"
                                     for s in d["declaration"]["stages"]) + "</p>")
    out.append("</div>")
    return "".join(out)


def _runs(d):
    """Phase-run bands, newest first, each ruled in its stage hue; the current
    run wears the `now` badge (#71)."""
    out = ["<h2>Phase runs · newest first</h2>"]
    last = len(d["runs"]) - 1
    for i, (r, x) in reversed(list(enumerate(zip(d["runs"], d["run_detail"])))):
        titles = "".join(f"<li>{html.escape(t)}</li>" for t in r["titles"])
        if not titles:
            titles = '<li class="dim">no audit titles in this run</li>'
        meta = ""
        if x["names"]:
            meta += f'<p class="meta">used: {html.escape(", ".join(x["names"]))}</p>'
        if x["minor"]:
            meta += '<p class="meta">also: ' + html.escape(" · ".join(
                f"{k} {n}" for k, n in x["minor"].items())) + "</p>"
        out.append(
            f'<div class="panel run"{_hue(d, r["stage"])}>'
            f'<div class="who"><b>{html.escape(r["stage"])}'
            f'{"<span class=now>now</span>" if i == last else ""}</b>'
            f'<small>{_span(r["start"], r["end"])}</small>'
            f'<small>{x["sessions"]} session{"s" * (x["sessions"] != 1)} · {x["events"]} events</small></div>'
            f"<div><ul>{titles}</ul>{meta}</div></div>")
    return "".join(out)


def _sessions(d):
    """Invalid declaration: no stages, so no runs — the trail grouped by
    session, newest first, is the unbucketed lane (#64)."""
    per = {}
    for e in d["trail"]:
        per.setdefault(e["session_id"], []).append(e)
    out = ["<h2>Trail by session · newest first · unbucketed</h2>"]
    for sid, es in sorted(per.items(), key=lambda kv: kv[1][0]["at"] or "", reverse=True):
        t = d["sessions"].get(sid, {}).get("title")
        names = how.used_names(es)
        out.append(
            f'<div class="panel run"><div class="who"><b>{local_day(es[0]["at"]) or "?"}</b>'
            f"<small>{len(es)} events</small></div><div><ul>"
            + (f"<li>{html.escape(t)}</li>" if t else '<li class="dim">no audit title</li>')
            + "</ul>" + (f'<p class="meta">used: {html.escape(", ".join(names))}</p>'
                         if names else "") + "</div></div>")
    return "".join(out)


def _aside(d):
    """Stated-process panel (valid) or the invalidity banner; the trail
    tally closes both."""
    dec = d["declaration"]
    tally = (f'<p class="note">{len(d["sessions"])} sessions · {len(d["trail"])} trail events'
             f" · {len({local_day(e['at']) for e in d['trail']})} active days</p>")
    if dec["state"] == "invalid":
        return (f'<div class="warn"><b>Declaration invalid — ignored whole.</b>'
                f"<br>{html.escape(dec['error'])}<br><code>.claude/my-process.md</code></div>"
                + tally)
    out = ["<h2>Stated process</h2>"]
    for s, agg in zip(dec["stages"], d["summary"]):
        mk = " · ".join(f"{k}: {', '.join(s[k])}" for k in how.MARKER_KEYS if s[k])
        if agg["count"]:
            out.append(f'<div class="panel stage"{_hue(d, s["name"])}><b>{html.escape(s["name"])}</b>'
                       f'<small>{agg["count"]} events · {_span(agg["first_seen"], agg["last_seen"])}</small>'
                       f'<span class="mk">{html.escape(mk)}</span></div>')
        else:
            out.append(f'<div class="panel stage none"{_hue(d, s["name"])}><b>{html.escape(s["name"])}</b>'
                       f'<small>nothing observed</small><span class="mk">{html.escape(mk)}</span></div>')
    off, bounds = d["off_script"], d["boundaries"]
    # the exclusion rides a note, not the h2: the label style is uppercase and
    # a command name is an identifier — /model must not read as /MODEL (#69)
    excluded = (f'<p class="mk">{sum(bounds.values())} session-boundary events excluded: '
                + ", ".join(f"{html.escape(n)} ×{c}" for n, c in bounds.items()) + "</p>"
                if bounds else "")
    out.append(f'<h2 class="offh">Off-script · {sum(o["count"] for o in off)} events'
               f' · {len(off)} distinct</h2>{excluded}<details><summary>show list</summary>'
               '<ul class="off">' + "".join(
                   f'<li>{html.escape(o["kind"])} {html.escape(o["name"])} ×{o["count"]}</li>' for o in off)
               + "</ul></details>")
    out.append(tally)
    return "".join(out)


def how_html(conn, project, projects_dir):
    """Selector + the one project's view; an unknown `?p=` says so and
    falls back to the busiest declaring project."""
    projects = declaring_projects(conn, projects_dir)
    if not projects:
        return ("<p>No project declares a process — add a <code>stages:</code> fence at"
                " line 1 of a project's <code>.claude/my-process.md</code> (ADR-0011).</p>")
    unknown = ""
    if project not in projects:
        if project:
            unknown = (f'<p class="note">{html.escape(project)} declares no process'
                       " — showing the busiest declaring project</p>")
        project = projects[0]
    sel = "".join(f'<a href="/how?p={html.escape(p)}"{" aria-current=page" if p == project else ""}>'
                  f"{html.escape(p)}</a>" for p in projects)
    d = how.how_data(conn, project, projects_dir)
    body = (_status(conn, d) + _runs(d)) if d["declaration"]["state"] == "valid" else _sessions(d)
    if not d["trail"]:
        body = "<p>No trail events for this project.</p>"
    # the one place a former name is rendered (ADR-0018)
    formerly = (f'<p class="note">formerly {html.escape(", ".join(d["former"]))}</p>'
                if d["former"] else "")
    return (f'<div id="hsel">{sel}</div>{unknown}{formerly}<p class="note">the choice switches the view'
            f" — declaring projects only; a project without a declaration has no how-view</p>"
            f'<section id="how"><aside>{_aside(d)}</aside><div>{body}</div></section>')

VIEWS = ("what", "where", "how")


def _asset(name):
    """Read a build/assets file per request — the tokens.css seam (ticket #80)."""
    return (ASSETS / name).read_text()


def _blob(obj):
    """JSON safe to embed in a <script> tag (model text can hold "</...")."""
    return json.dumps(obj).replace("</", "<\\/")


def _nav(view):
    """Header nav with the current view marked."""
    return " ".join(f'<a href="/{v}"{" aria-current=page" if v == view else ""}>{v}</a>'
                    for v in VIEWS)


def render(view, conn, query="", projects_dir=DEFAULT_PROJECTS_DIR):
    tokens = TOKENS_CSS.read_text()
    if view == "how":
        project = parse_qs(query).get("p", [""])[0]
        synced = conn.execute("SELECT MAX(date) FROM sessions").fetchone()[0]
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>hindsight · how</title>
<link rel="icon" href="data:,">
<script>{_asset("theme.js")}{_asset("how.js")}</script>
<style>{tokens}{_asset("chrome.css")}{_asset("how.css")}</style></head><body>
<header>
<button id="theme"></button>
<h1>hindsight</h1><nav>{_nav(view)}</nav>
<p class="cov">synced through {synced or "never"} · the process actually followed,
per project: a status over phase runs beside the stated process — no order rules,
no verdicts (ADR-0010)</p>
</header><main>{how_html(conn, project, projects_dir)}</main></body></html>"""
    data = header_data(conn)
    if view == "what":
        main = _asset("what.html")
        view_css, view_js = _asset("what.css"), f"const WHAT = {_blob(what_data(conn))};{_asset('what.js')}"
    else:
        main = _asset("where.html")
        view_css, view_js = _asset("where.css"), f"const WHERE = {_blob(where_data(conn))};{_asset('where.js')}"
    hidden = set(data["hidden"])
    chips = "".join(
        f'<button data-p="{html.escape(p)}"'
        f'{" data-hidden" if p in hidden else ""}>{html.escape(p)}</button>'
        for p in data["chips"])
    hidden_note = (f' · {len(hidden)} hidden — workspace folder gone at the last'
                   f' analysis run (ADR-0009): <button id="reveal"'
                   f' aria-pressed="false">show hidden ({len(hidden)})</button>'
                   if hidden else "")
    nav = _nav(view)
    blob = _blob(data)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>hindsight · {view}</title>
<link rel="icon" href="data:,">
<script>{_asset("theme.js")}</script>
<style>{tokens}{_asset("chrome.css")}{view_css}</style></head><body>
<header>
<button id="theme"></button>
<h1>hindsight</h1><nav>{nav}</nav>
<p class="cov">synced through {data["synced"] or "never"} · {data["sessions"]} sessions ·
token usage from the transcript scan — days without data render as gaps;
pruned transcripts read unknown, never zero</p>
<div id="chips">{chips}</div>
<p class="note">{data["tail"]} projects have no chip (scratch dirs, probes, low volume)
— their data is still counted; chips filter, never switch.{hidden_note}</p>
<div id="ctl">window:
{"".join(f'<button data-w="{w}">{w}</button>' for w in ("7", "14", "28", "90", "all"))}
<button id="tclear">clear</button>
<label><input type="checkbox" id="hidecr"> hide cache reads</label>
<span class="hint">click a bar to filter to a day, a second bar for a range,
the same bar again to deselect — a chart click overrides the preset</span></div>
<div id="chart"></div>
</header>
<main>{main}</main>
<script>const DATA = {blob};{_asset("chrome.js")}{view_js}</script>
</body></html>"""


def make_server(port, db_path, projects_dir=DEFAULT_PROJECTS_DIR):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path, _, query = self.path.partition("?")
            if path == "/":
                self.send_response(302)
                self.send_header("Location", "/what")
                self.end_headers()
                return
            view = path.lstrip("/")
            if view not in VIEWS:
                self.send_error(404)
                return
            conn = open_db(db_path)
            try:
                body = render(view, conn, query, projects_dir).encode()
            finally:
                conn.close()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def db_missing(db):
    """Startup guard: the reason this db can't serve, or None when it can.
    A DB file the listener created alone (otel rows only) has no sessions
    table — the same "run an analysis first" answer as no file at all."""
    if not Path(db).exists():
        return f"no database at {db} — run an analysis first"
    conn = open_db(db)
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master"
                            " WHERE name = 'sessions'").fetchone():
            return f"no analysis tables in {db} — run an analysis first"
    finally:
        conn.close()
    return None


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--projects-dir", type=Path, default=DEFAULT_PROJECTS_DIR)
    args = ap.parse_args(argv)
    port, db = args.port, args.db
    msg = db_missing(db)
    if msg:
        print(msg)
        return 1
    server = make_server(port, db, args.projects_dir)
    print(f"hindsight · http://127.0.0.1:{server.server_address[1]}/what · Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
