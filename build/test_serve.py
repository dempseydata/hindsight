"""Tests for the on-demand foreground server (ticket #44).

External behaviour at the HTTP boundary plus the chip policy: GET pages
from a server on an ephemeral port over a fixture DB, assert the chrome
data and the read-only guarantee.
"""
import http.client
import os
import re
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path

import analyze
import listener
import serve

# Day buckets are the operator's local day (ADR-0014), so the fixtures
# need a pinned zone or they assert whatever the runner's clock says.
os.environ["TZ"] = "America/New_York"
time.tzset()


def fixture_db(path):
    """The real schemas — analyze.init_db plus the listener's otel tables —
    so the fixture can't drift from production DDL (ticket #50)."""
    conn = analyze.init_db(path)
    conn.executescript(listener.SCHEMA)
    sessions = [
        ("s1", "big", "2026-08-01"), ("s2", "big", "2026-08-03"),
        ("s3", "small", "2026-08-02"),
        # ledger-heavy, transcripts pruned: sessions but no usage rows
        ("s4", "pruned", "2026-08-02"), ("s5", "pruned", "2026-08-04"),
        # scratch path: heavy but never a chip
        ("s6", "-private-tmp-scratch", "2026-08-04"),
        # synced but not yet analyzed: no audit row
        ("s7", "big", "2026-08-05"),
    ]
    conn.executemany("INSERT INTO sessions (id, project, transcript_path,"
                     " date, status) VALUES (?, ?, 'x', ?, 'done')", sessions)
    # transcript pruned before it was ever extracted (ticket #78)
    conn.execute("INSERT INTO sessions (id, project, transcript_path, date,"
                 " status) VALUES ('s8', 'pruned', 'x', '2026-08-03', 'lost')")
    # extractor found nothing (#2): no audit row, but not pending either
    conn.execute("INSERT INTO sessions (id, project, transcript_path, date,"
                 " status) VALUES ('s9', 'big', 'x', '2026-08-05', 'empty')")
    usage = [
        ("s1", "m1", "2026-08-01T10:00:00Z", 1000, 200, 50, 90000),
        ("s1", "m1b", "2026-08-01T11:00:00Z", 500, 100, 0, 10000),
        ("s2", "m2", "2026-08-03T10:00:00Z", 2000, 300, 60, 80000),
        # s2 crossing midnight: usage past MAX(sessions.date) (ticket #50)
        ("s2", "m2b", "2026-08-06T12:00:00Z", 100, 10, 0, 0),
        ("s3", "m3", "2026-08-02T10:00:00Z", 10, 5, 0, 100),
        # s3's evening session: 01:00Z is the operator's previous day
        # (ticket #74) — the row that separates local bucketing from a
        # raw UTC slice
        ("s3", "m3b", "2026-08-03T01:00:00Z", 100, 10, 0, 0),
        ("s6", "m6", "2026-08-04T10:00:00Z", 5000, 500, 0, 200000),
    ]
    conn.executemany("""INSERT INTO usage (session_id, message_id, at,
        input_tokens, output_tokens, cache_creation_input_tokens,
        cache_read_input_tokens) VALUES (?, ?, ?, ?, ?, ?, ?)""", usage)
    # s1 spawned one subagent (issue #13): its usage files under s1 with the
    # agent id on the row, and the transcript is recorded against s1
    conn.execute("""INSERT INTO usage (session_id, message_id, at, input_tokens,
        output_tokens, cache_creation_input_tokens, cache_read_input_tokens,
        agent_id) VALUES ('s1', 'ms', '2026-08-01T10:30:00Z', 100, 0, 0, 0, 'ag1')""")
    conn.execute("INSERT INTO subagent_transcripts (session_id, agent_id, path,"
                 " size) VALUES ('s1', 'ag1', 'x', 1)")
    tool_events = [
        # cli call in m1, paired 2s later, ok
        ("s1", "t1", "Bash", "2026-08-01T10:00:00Z", "2026-08-01T10:00:02Z",
         "m1", "cli", "gh", None, 0),
        # mcp call in m1, errored
        ("s1", "t2", "mcp__srv__do", "2026-08-01T10:00:03Z",
         "2026-08-01T10:00:04Z", "m1", "mcp", "srv", "do", 1),
        # skill call never paired: is_error NULL = unknown, no duration
        ("s1", "t3", "Skill", "2026-08-01T11:00:00Z", None,
         "mx", "skill", "grilling", None, None),
        # pruned-transcript row: no grains at all — unknown, not zero
        ("s2", "t4", "Bash", "2026-08-03T10:00:00Z", None,
         None, None, None, None, None),
    ]
    conn.executemany("""INSERT INTO tool_events (session_id, tool_use_id,
        name, at, result_at, message_id, consumer_type, consumer, mcp_tool,
        is_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", tool_events)
    otel = [
        ("api_request", "s1", "2026-08-03T09:00:00Z",
         '{"model": "claude-sonnet-5", "duration_ms": "1500",'
         ' "session.id": "s1"}'),
        ("hindsight.hook", "s1", "2026-08-04T09:00:00Z",
         '{"hook.event": "Stop", "hook.cpu_ms": 80.5,'
         ' "hook.duration_ms": 1.2}'),
        # reliability panel (#14): two retries and one exhaustion on s1 —
        # the CLI stringifies numbers on some paths, so one of each shape
        ("api_error", "s1", "2026-08-03T09:00:01Z",
         '{"model": "claude-sonnet-5", "status_code": 429, "attempt": 1,'
         ' "session.id": "s1"}'),
        ("api_error", "s1", "2026-08-03T09:00:02Z",
         '{"model": "claude-sonnet-5", "status_code": "429", "attempt": "2",'
         ' "session.id": "s1"}'),
        ("api_retries_exhausted", "s1", "2026-08-03T09:00:03Z",
         '{"model": "claude-sonnet-5", "status_code": 529, "total_attempts": 11,'
         ' "total_retry_duration_ms": "273269", "session.id": "s1"}'),
        # one server: a failure and a connection in the same session
        ("mcp_server_connection", "s1", "2026-08-03T09:00:00Z",
         '{"server_name": "plugin:gh", "status": "failed", "duration_ms": "12"}'),
        ("mcp_server_connection", "s3", "2026-08-03T10:00:00Z",
         '{"server_name": "plugin:gh", "status": "connected", "duration_ms": 30}'),
        # self-excluded analysis session (x1): must not render. A session
        # OTEL saw but sync never did (u1): kept, project unknown
        ("api_error", "x1", "2026-08-03T09:00:00Z",
         '{"model": "claude-haiku-4-5-20251001", "status_code": 429}'),
        ("mcp_server_connection", "x1", "2026-08-03T09:00:00Z",
         '{"server_name": "plugin:gh", "status": "failed"}'),
        ("mcp_server_connection", "u1", "2026-08-03T11:00:00Z",
         '{"server_name": "plugin:gh", "status": "failed"}'),
    ]
    conn.executemany("""INSERT INTO otel_events (event_name, session_id,
        timestamp, attributes) VALUES (?, ?, ?, ?)""", otel)
    conn.execute("INSERT INTO excluded_sessions VALUES ('x1')")
    sunk = [
        (None, "claude-md", None, "~/.claude/CLAUDE.md", "p", 300),
        ("big", "skill", "plug", "sk", "p", 1000),
        ("big", "command", None, "cmd", "p", 50),
    ]
    conn.executemany("INSERT INTO sunk_cost VALUES (?, ?, ?, ?, ?, ?)", sunk)
    audit = [
        ("s1", "big", "2026-08-01", 0,
         "### Shipped the widget\n- **Did:**\n  - Built it\n  - Tested it\n"
         "- **Decided:**\n  - Ship on Friday", 2),
        ("s2", "big", "2026-08-03", 1, None, None),          # SKIP
        ("s3", "small", "2026-08-02", 0,
         "I'm ready to help, but I don't see a transcript.", None),  # #38 row
        ("s4", "pruned", "2026-08-02", 0,
         "### Paragraph entry\n\n**Did:** Read a; wrote b; shipped c.", None),
        ("s5", "pruned", "2026-08-04", 1, None, None),
        ("s6", "-private-tmp-scratch", "2026-08-04", 1, None, None),
    ]
    conn.executemany("""INSERT INTO audit VALUES (?, ?, ?, ?, ?, 'what-v1',
        'test-model', ?)""", audit)
    # how-view (ticket #65): "big" declares and has a stored narrative whose
    # hash will not match the live ledger (stale); "small" declares an
    # invalid fence; "pruned" declares nothing and must not be selectable
    conn.executemany("INSERT INTO command_grains (session_id, command, at)"
                     " VALUES (?, ?, ?)", [
        ("s1", "/grill-me", "2026-08-01T09:00:00Z"),
        ("s1", "/grill-me", "2026-08-01T09:30:00Z"),
        ("s1", "/grill-me", "2026-08-01T09:45:00Z"),
        ("s2", "/implement", "2026-08-03T10:00:00Z"),
        ("s2", "/implement", "2026-08-03T10:30:00Z"),
        ("s2", "/implement", "2026-08-03T10:45:00Z"),
        ("s3", "/implement", "2026-08-02T10:00:00Z")])
    conn.execute("INSERT INTO status_narrative VALUES ('big', 'oldhash',"
                 " ?, 'status-v1', 'test-model', '2026-08-05T00:00:00Z')",
                 ('{"Built": ["Widget shipped — Aug 1"], "Reversed": [],'
                  ' "Now": ["Build, since Aug 3: widget"]}',))
    # Presence as the last analysis run observed it (ticket #57, ADR-0009):
    # `pruned` is a chip whose folder is gone, so it hides; the scratch dir is
    # gone too but never held a chip, so it must not reach the hidden count.
    conn.executemany(
        "INSERT INTO project_presence (folder_identity, name, first_seen,"
        " last_seen, present) VALUES (NULL, ?, '2026-08-05T00:00:00Z',"
        " '2026-08-05T00:00:00Z', ?)",
        [("small", 1), ("pruned", 0), ("-private-tmp-scratch", 0)])
    # `big` was renamed from `old-big` (ticket #6, ADR-0018): one identity,
    # two names in the history; s1 wrote a file under the old root
    conn.executemany(
        "INSERT INTO project_presence (folder_identity, name, first_seen,"
        " last_seen, present) VALUES (7, ?, ?, '2026-08-05T00:00:00Z', ?)",
        [("old-big", "2026-07-01T00:00:00Z", 0), ("big", "2026-08-05T00:00:00Z", 1)])
    conn.execute("UPDATE sessions SET folder_identity = 7 WHERE project = 'big'")
    conn.execute("INSERT INTO tool_events (session_id, name, at, file_path,"
                 " consumer_type, consumer) VALUES ('s1', 'Write',"
                 " '2026-08-01T09:50:00Z', ?, 'builtin', 'Write')",
                 (str(Path(path).parent / "old-big" / "notes.md"),))
    conn.commit()
    conn.close()


DECL = "---\nstages:\n  - name: Ideate\n    commands: [grill-me]\n" \
       "  - name: Build\n    commands: [implement]\n    skills: [grilling]\n---\n"


def fixture_projects(root):
    for name, text in (("big", DECL), ("small", DECL.replace("commands", "cmds", 1))):
        d = Path(root) / name / ".claude"
        d.mkdir(parents=True)
        (d / "my-process.md").write_text(text)


class ChipPolicyTest(unittest.TestCase):
    def test_thresholds_and_scratch_exclusion(self):
        projects = [("big", 20, 96_000_000), ("tiny", 1, 40),
                    ("pruned", 80, None), ("-private-tmp-scratch", 100, 900_000_000)]
        chips, tail = serve.chip_rows(projects)
        # big clears the token leg, pruned the session leg (80 of 201
        # sessions, tokens unknown); tiny clears neither at 1%; scratch is
        # heavy on both legs but a filesystem path
        self.assertEqual(chips, ["big", "pruned"])
        self.assertEqual(tail, 2)

    def test_token_order(self):
        projects = [("a", 5, 100), ("b", 5, 900)]
        chips, _ = serve.chip_rows(projects)
        self.assertEqual(chips, ["b", "a"])

    def test_pre_substrate_zero_tokens_disables_token_leg(self):
        """Ticket #50: before the first substrate scan all tokens are 0/None
        — 0 >= 0 must not hand every project a chip via the token leg."""
        chips, tail = serve.chip_rows([("big", 990, None), ("tiny", 5, None)])
        self.assertEqual(chips, ["big"])
        self.assertEqual(tail, 1)


class ParseEntryTest(unittest.TestCase):
    def test_bullet_sections(self):
        e = serve.parse_entry(
            "### Title here\n- **Did:**\n  - one\n  - two\n"
            "- **Decided:**\n  - a call\n- **Setup changes:**\n  - a hook")
        self.assertEqual(e["title"], "Title here")
        names = [(s["name"], s["n"]) for s in e["sections"]]
        self.assertEqual(names, [("Did", 2), ("Decided", 1),
                                 ("Setup changes", 1)])
        self.assertFalse(e["sections"][0]["para"])

    def test_paragraph_sections_count_semicolon_clauses(self):
        e = serve.parse_entry(
            "### T\n\n**Did:** Read a; wrote b; shipped c.\n\n"
            "**Decided:** Just one thing.")
        did = e["sections"][0]
        self.assertTrue(did["para"])
        self.assertEqual(did["n"], 3)
        self.assertEqual(len(did["items"]), 1)     # kept whole for display
        self.assertEqual(e["sections"][1]["n"], 1)

    def test_refusal_text_is_unparseable(self):
        self.assertIsNone(serve.parse_entry("I'm ready to help, but..."))
        self.assertIsNone(serve.parse_entry(None))


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "hindsight.db"
        fixture_db(cls.db)
        fixture_projects(cls.tmp.name)
        cls.server = serve.make_server(0, cls.db, cls.tmp.name)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", path)
        r = c.getresponse()
        body = r.read().decode()
        c.close()
        return r, body

    def test_root_redirects_to_what(self):
        r, _ = self.get("/")
        self.assertEqual(r.status, 302)
        self.assertEqual(r.getheader("Location"), "/what")

    def test_views_render_chrome(self):
        for view in ("what", "where"):
            r, body = self.get(f"/{view}")
            self.assertEqual(r.status, 200)
            self.assertIn("--o-bg", body)            # tokens.css inlined
            self.assertIn('data-p="big"', body)      # chip
            self.assertIn('data-p="pruned"', body)   # session-leg chip
            self.assertNotIn("-private-tmp-scratch</button>", body)
            self.assertIn("synced through 2026-08-05", body)

    def test_theme_toggle_in_shared_chrome(self):
        """#83 (ADR-0017): three-state theme pin — the toggle button and the
        pre-paint pin script render in every view; the light token set rides
        in the inlined contract behind the media guard and the pin blocks."""
        for view in ("what", "where", "how"):
            _, body = self.get(f"/{view}")
            self.assertIn('<button id="theme"></button>', body)
            self.assertIn('localStorage.getItem("theme")', body)
            self.assertIn("prefers-color-scheme: light", body)
            self.assertIn(':root[data-theme="light"]', body)
            self.assertIn(':root[data-theme="dark"]', body)

    def test_how_view_valid_stale_narrative(self):
        r, body = self.get("/how")                 # default: busiest declaring
        self.assertEqual(r.status, 200)
        self.assertIn('aria-current=page>big</a>', body)
        self.assertIn('href="/how?p=small"', body)
        self.assertNotIn("?p=pruned", body)        # undeclared: no view
        self.assertIn("Widget shipped", body)      # narrative shown...
        self.assertIn("stale", body)               # ...but marked stale
        self.assertIn("<b>Build</b> since 2026-08-01 · 2 runs", body)
        # stage hue on both sides, current run badged (ticket #71)
        self.assertIn('class="panel run" style="--stage: var(--o-stage-2)"><div class="who"><b>Build<span class=now>now</span>', body)
        self.assertIn('class="panel stage" style="--stage: var(--o-stage-2)"><b>Build', body)
        self.assertIn("used: grilling, implement", body)
        self.assertIn("Stated process", body)
        self.assertNotIn('id="chart"', body)       # no shared filter chrome
        self.assertNotIn("const DATA", body)       # no filter data blob (#83:
        # the theme pin script is shared chrome and does render here)

    def test_former_name_in_how_header_and_nowhere_else(self):
        """Ticket #6 / ADR-0018: the how-view header says "formerly old-big"
        for the renamed project; the write under the old root is a trail
        event named relative to the root, so the former name appears in
        the header line only. A never-renamed project has no such line,
        and the ledger, chips and where-view render no former name."""
        _, body = self.get("/how?p=big")
        self.assertIn("formerly old-big", body)
        self.assertEqual(body.count("old-big"), 1)
        self.assertIn("write notes.md ×1", body)   # under the former root
        _, body = self.get("/how?p=small")
        self.assertNotIn("formerly", body)
        for view in ("what", "where"):
            _, body = self.get(f"/{view}")
            self.assertNotIn("old-big", body)
            self.assertNotIn("formerly", body)

    def test_how_view_invalid_and_unknown(self):
        _, body = self.get("/how?p=small")
        self.assertIn("Declaration invalid", body)
        self.assertIn("line 4: unknown key `cmds`", body)
        self.assertIn("unbucketed", body)
        self.assertIn("used: implement", body)     # trail still shown
        self.assertNotIn("Status", body)
        _, body = self.get("/how?p=nope")
        self.assertIn('aria-current=page>big</a>', body)  # falls back
        self.assertIn("nope declares no process", body)
        self.assertIn("active days", body)              # tally on invalid too

    def test_what_view_embeds_ledger(self):
        _, body = self.get("/what")
        self.assertIn('"title": "Shipped the widget"', body)
        self.assertIn('"adr": 2', body)
        self.assertIn('"skip": 1', body)           # SKIP rows ride along
        self.assertIn('"raw"', body)               # #38 row tolerated
        self.assertIn('id="ledger"', body)
        self.assertIn('"lost": 1', body)
        self.assertIn("unrecoverable", body)      # #78 one-liner + summary term
        self.assertIn('"empty": 1', body)          # #2 empty row rides along
        self.assertIn('"sub": 1', body)            # #13 subagent note
        self.assertIn("subagents", body)           # what.js renders the note
        self.assertNotIn('"title": "Shipped the widget"',
                         self.get("/where")[1])    # blob is what-view only

    def test_what_data_order_and_shape(self):
        conn = serve.open_db(self.db)
        rows = serve.what_data(conn)
        conn.close()
        self.assertEqual(len(rows), 10)            # 9 sessions + s2's #9 continuation
        self.assertEqual([r["d"] for r in rows],
                         sorted([r["d"] for r in rows], reverse=True))
        by_id = {r["id"]: r for r in rows if "cont" not in r}
        self.assertEqual(by_id["s1"]["sections"][0]["n"], 2)
        self.assertNotIn("title", by_id["s3"])     # refusal row -> raw only
        self.assertIn("raw", by_id["s3"])
        self.assertNotIn("raw", by_id["s2"])       # SKIP: no entry at all
        self.assertEqual(by_id["s7"]["pend"], 1)   # unanalyzed still listed
        self.assertEqual(by_id["s8"]["lost"], 1)   # #78: lost, not pending
        self.assertNotIn("pend", by_id["s8"])
        self.assertEqual(by_id["s9"]["empty"], 1)  # #2: empty, not pending
        self.assertNotIn("pend", by_id["s9"])
        # #13: the mechanical "N subagents" note, from the transcripts
        # recorded against the session — only where there are any
        self.assertEqual(by_id["s1"]["sub"], 1)
        self.assertNotIn("sub", by_id["s2"])

    def test_what_ledger_files_a_session_under_each_active_day(self):
        """#9: s2 has usage on 2026-08-03 and 2026-08-06 — the full row
        under the first, a thin continuation with the note under the second,
        each day once; nine distinct ids for the summary line to count."""
        conn = serve.open_db(self.db)
        rows = serve.what_data(conn)
        conn.close()
        s2 = [r for r in rows if r["id"] == "s2"]
        self.assertEqual([r["d"] for r in s2], ["2026-08-06", "2026-08-03"])
        self.assertEqual(s2[0], {"id": "s2", "p": "big", "d": "2026-08-06",
                                 "skip": 1, "cont": "started 2026-08-03 · day 4"})
        self.assertNotIn("cont", s2[1])
        self.assertEqual(len({r["id"] for r in rows}), 9)
        # each day lists the session once; blob order holds within a day
        self.assertEqual([r["id"] for r in rows if r["d"] == "2026-08-03"],
                         ["s8", "s2"])
        self.assertEqual([r["id"] for r in rows if r["d"] == "2026-08-06"],
                         ["s2"])
        # a usage-less session keeps its start day; one row, no note
        self.assertEqual([r["d"] for r in rows if r["id"] == "s4"],
                         ["2026-08-02"])

    def test_where_view_embeds_blob(self):
        _, body = self.get("/where")
        self.assertIn('id="league"', body)
        self.assertIn('"tools"', body)
        self.assertIn('"subd"', body)                 # #13 tile data
        self.assertIn("% of tokens", body)            # where.js renders the tile
        self.assertNotIn('"cost', body)          # pricing never rendered

    def test_where_league_category_chips_default_deliberate_adds(self):
        """#55: the league renders five category chips — mcp/cli/skill on,
        shell/builtin off — so built-ins don't drown the deliberate adds."""
        _, body = self.get("/where")
        for cat in ("mcp", "cli", "skill"):
            self.assertIn(f'<button class="on" aria-pressed="true"'
                          f' data-t="{cat}">{cat}</button>', body)
        for cat in ("shell", "builtin"):
            self.assertIn(f'<button aria-pressed="false"'
                          f' data-t="{cat}">{cat}</button>', body)

    def test_where_data_shape(self):
        conn = serve.open_db(self.db)
        w = serve.where_data(conn)
        conn.close()
        by = {(r["ty"], r["c"]): r for r in w["tools"]}
        # paired call carries its duration; errors counted per call
        self.assertEqual(by[("cli", "gh")]["durs"], [2000])
        self.assertEqual(by[("cli", "gh")]["e"], 0)
        self.assertEqual(by[("mcp", "srv")]["e"], 1)
        self.assertEqual(by[("mcp", "srv")]["mt"], "do")
        # unpaired call: unknown (nu), no duration, not an error
        self.assertEqual(by[("skill", "grilling")]["nu"], 1)
        self.assertEqual(by[("skill", "grilling")]["durs"], [])
        # pruned-transcript row rides along unclassified, never dropped
        self.assertEqual(by[("", "")]["n"], 1)
        # message lens charges only the invoking response (m1, not m1b)
        lens = {(r["ty"], r["c"]): r["t"] for r in w["lens"]}
        self.assertEqual(lens[("cli", "gh")], [1000, 200, 50, 90000])
        self.assertNotIn(("skill", "grilling"), lens)   # mx has no usage row
        # session lens index reaches every usage row of the session
        cs = {(r["ty"], r["c"]): r["s"] for r in w["cs"]}
        s1_tokens = sum(sum(w["sess"][i]["t"]) for i in cs[("cli", "gh")])
        self.assertEqual(s1_tokens, 1000 + 200 + 50 + 90000 + 500 + 100 + 10000 + 100)
        # #13: the session's subagent count rides on its sess row (absent
        # when none); subagent tokens at day grain, the tiles' own base
        [s1] = [s for s in w["sess"] if s.get("na")]
        self.assertEqual(s1["na"], 1)
        self.assertEqual(s1["t"], [1600, 300, 50, 100000])
        self.assertEqual(w["subd"], [{"d": "2026-08-01", "p": "big",
                                      "t": [100, 0, 0, 0]}])
        # measured median: first usage row per session, per project
        self.assertEqual(w["med"]["big"]["n"], 2)
        self.assertEqual(w["med"]["big"]["med"], (91050 + 82060) // 2)
        # latency from OTEL api_request; coverage + exclusion stated
        self.assertEqual(w["lat"][0]["durs"], [1500])
        self.assertEqual(w["lat"][0]["m"], "sonnet-5")
        self.assertEqual(w["hooks"][0]["cpu"], 80.5)
        self.assertEqual(w["cov"]["excluded"], 1)
        self.assertEqual(w["cov"]["usage_sessions"], 4)
        self.assertEqual(w["cov"]["hook"], "2026-08-04")

    def test_where_data_reliability(self):
        """#14: retries and MCP connection health at event grain — day and
        project on every row so the chrome's filters apply, the session id
        as the evidence, numbers coerced whatever shape the CLI sent them
        in, self-excluded sessions dropped, and a session sync never saw
        kept with its project unknown — never silently thinned."""
        conn = serve.open_db(self.db)
        w = serve.where_data(conn)
        conn.close()
        self.assertEqual(w["retries"], [
            {"d": "2026-08-03", "p": "big", "sid": "s1", "m": "sonnet-5",
             "ex": False, "ms": None},
            {"d": "2026-08-03", "p": "big", "sid": "s1", "m": "sonnet-5",
             "ex": False, "ms": None},
            {"d": "2026-08-03", "p": "big", "sid": "s1", "m": "sonnet-5",
             "ex": True, "ms": 273269}])
        self.assertEqual(w["conn"], [
            {"d": "2026-08-03", "p": "big", "sid": "s1", "srv": "plugin:gh",
             "st": "failed", "ms": 12},
            {"d": "2026-08-03", "p": "small", "sid": "s3", "srv": "plugin:gh",
             "st": "connected", "ms": 30},
            {"d": "2026-08-03", "p": None, "sid": "u1", "srv": "plugin:gh",
             "st": "failed", "ms": None}])

    def test_where_view_has_reliability_panel(self):
        _, body = self.get("/where")
        self.assertIn('id="retries"', body)
        self.assertIn('id="conn"', body)
        self.assertIn('"retries"', body)
        self.assertIn('"conn"', body)

    def test_unknown_path_404s(self):
        r, _ = self.get("/nope")
        self.assertEqual(r.status, 404)

    def test_header_data_range_and_days(self):
        conn = serve.open_db(self.db)
        data = serve.header_data(conn)
        conn.close()
        # range end reaches s2's midnight-crossing usage day (2026-08-06),
        # past MAX(sessions.date) = 2026-08-05 (ticket #50)
        self.assertEqual(data["range"], ["2026-08-01", "2026-08-06"])
        self.assertEqual(data["synced"], "2026-08-05")
        # ticket #74: s3's 2026-08-03T01:00Z row is the operator's 08-02,
        # so "small" occupies one local day, not two UTC ones
        self.assertEqual({r["d"] for r in data["days"] if r["p"] == "small"},
                         {"2026-08-02"})
        self.assertEqual(data["sessions"], 9)
        # per (day, project) grain; pruned has sessions but no day rows
        self.assertNotIn("pruned", {r["p"] for r in data["days"]})

    def test_hidden_projects_are_the_chips_whose_folder_is_gone(self):
        """Ticket #57 / ADR-0009: hiding is chips-only, and only chips count
        — the scratch dir is absent too but never held one."""
        conn = serve.open_db(self.db)
        data = serve.header_data(conn)
        conn.close()
        self.assertEqual(data["chips"], ["big", "small", "pruned"])
        self.assertEqual(data["hidden"], ["pruned"])
        self.assertEqual(data["tail"], 1)   # unchanged by hiding
        # ledger, chart and totals never see it: pruned's sessions still count
        self.assertEqual(data["sessions"], 9)

    def test_hidden_chip_renders_marked_with_a_reveal_toggle(self):
        for view in ("what", "where"):
            _, body = self.get(f"/{view}")
            self.assertIn('<button data-p="pruned" data-hidden>', body)
            self.assertIn('<button data-p="big">', body)
            self.assertIn("show hidden (1)", body)
            # the "data still counted" note is unamended (ADR-0009)
            self.assertIn("their data is still counted", body)
            self.assertIn("1 projects have no chip", body)
            # hidden by default, revealed by an ephemeral class, and
            # un-revealing drops the filter it would otherwise leave invisible
            self.assertIn("#chips button[data-hidden] { display: none; }", body)
            self.assertIn('classList.toggle("reveal", S.reveal)', body)
            self.assertIn("S.active.delete(b.dataset.p)", body)
        # a hidden project's ledger rows are untouched
        self.assertIn("Paragraph entry", self.get("/what")[1])

    def test_no_reveal_toggle_when_nothing_is_hidden(self):
        """A db no run has observed yet hides nothing — presence is stored,
        never taken at render time. A db predating the table (upgraded code,
        no run since) must render too: the server cannot create it."""
        for drop in ("DELETE FROM project_presence", "DROP TABLE project_presence"):
            self.assertNotIn("show hidden", self.serve_once(drop))

    def serve_once(self, sql):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "h.db"
            fixture_db(db)
            conn = sqlite3.connect(db)
            conn.execute(sql)
            conn.commit()
            conn.close()
            server = serve.make_server(0, db, tmp)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                c = http.client.HTTPConnection("127.0.0.1", port)
                c.request("GET", "/what")
                body = c.getresponse().read().decode()
                c.close()
            finally:
                server.shutdown()
                server.server_close()
        self.assertNotIn("data-hidden>", body)   # the CSS rule always ships
        return body

    def test_filter_state_rides_session_storage_across_views(self):
        """Issue #10: chips, window, preset and the reveal state are saved
        per tab on every change and restored before the first render, so a
        what ↔ where switch keeps the filter. On restore a hidden project's
        chip comes back active only with the reveal state that showed it
        (ADR-0009). The how-view has no filter chrome, but its ?p= writes
        the active chip, so the project looked at is selected on return."""
        for view in ("what", "where"):
            _, body = self.get(f"/{view}")
            self.assertIn('sessionStorage.setItem("filter"', body)
            self.assertIn('sessionStorage.getItem("filter")', body)
            self.assertIn('S.reveal ? "#chips button" : "#chips button:not([data-hidden])"', body)
            self.assertIn('restore() || applyPreset("14")', body)
            # the how-view is chosen by ?p=, so the nav link carries the active chip
            self.assertIn("""querySelector('header nav a[href^="/how"]').href""", body)
        self.assertIn('active: [p]', self.get("/how")[1])

    def test_chart_columns_keyboard_accessible(self):
        """Ticket #50 P2: day columns are focusable buttons with an
        Enter/Space handler — presets are not the only time filter."""
        _, body = self.get("/what")
        self.assertIn('tabindex="0" role="button"', body)
        self.assertIn('addEventListener("keydown"', body)

    def test_connection_is_read_only(self):
        conn = serve.open_db(self.db)
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE scribble (x)")
        conn.close()

    def test_page_renders_through_a_held_write(self):
        """Issue #12: the db is WAL, so a reader never queues behind a
        writer's lock — a request issued during a long analyze.py
        transaction returns 200 now, not a 500 once the default 5 s
        timeout expires."""
        writer = sqlite3.connect(self.db)
        writer.execute("BEGIN EXCLUSIVE")
        writer.execute("INSERT INTO sessions (id, project, transcript_path,"
                       " date, status) VALUES ('held', 'big', 'x',"
                       " '2026-08-06', 'pending')")
        try:
            t0 = time.monotonic()
            r, _ = self.get("/what")
            self.assertEqual(r.status, 200)
            self.assertLess(time.monotonic() - t0, 2)
        finally:
            writer.rollback()
            writer.close()


class DriftTest(unittest.TestCase):
    """Ticket #81: the static where.html can't import the vocabulary (kept
    uninterpolated by design, #80) — detect divergence instead, the same
    pattern as the model-pin test in test_analyze."""

    def test_where_html_category_buttons_are_the_consumer_types(self):
        buttons = re.findall(r'data-t="([^"]+)"',
                             (serve.ASSETS / "where.html").read_text())
        self.assertEqual(sorted(buttons), sorted(analyze.CONSUMER_TYPES))
        self.assertEqual(len(buttons), len(set(buttons)))   # one chip each


class GuardsTest(unittest.TestCase):
    """Ticket #50: degenerate DBs must degrade to a message or an empty
    state, never a traceback or dead page JS."""

    def test_empty_analysis_db_pages_render(self):
        """Zero sessions, listener never ran (no otel tables): both views
        still return 200, range embeds as [null, null] for the JS guard."""
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "empty.db"
            analyze.init_db(db).close()
            server = serve.make_server(0, db, tmp)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                for view in ("what", "where", "how"):
                    c = http.client.HTTPConnection("127.0.0.1", port)
                    c.request("GET", f"/{view}")
                    r = c.getresponse()
                    body = r.read().decode()
                    c.close()
                    self.assertEqual(r.status, 200)
                    if view != "how":
                        self.assertIn('"range": [null, null]', body)
                self.assertIn("synced through never", body)
                self.assertIn("No project declares a process", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_db_missing_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "x.db"
            self.assertIn("no database", serve.db_missing(db))
            listener.init_db(db)   # listener-only db: file exists, no sessions
            self.assertIn("run an analysis first", serve.db_missing(db))
            analyze.init_db(db).close()
            self.assertIsNone(serve.db_missing(db))


if __name__ == "__main__":
    unittest.main()
