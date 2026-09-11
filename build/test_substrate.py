"""Seam tests for the substrate scan (tickets #22, #42, #61 — build/substrate.py),
driven through the analysis-run entrypoint: tool_events/usage/command_grains
filled at sync time, consumer classification, dedup, the mechanical ADR
count, and the substrate-touching db migrations.
"""
import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

import analyze
from analyze import run_analysis
from test_helpers import (DbHelpers, ENTRY_A, ENTRY_B, REFUSAL_MD,
                          StubRunner, USAGE, _backdate, rec, write_records)


class SubstrateTest(DbHelpers, unittest.TestCase):
    """Where-view measurement substrate (ticket #22): tool_events and usage
    filled at sync time, skipped-record counting, and the mechanical ADR
    count on audit rows at assemble time."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"
        self.work = base / "analysis"

    def sync_and_fill(self):
        """The sync stage alone — substrate fill needs no model passes."""
        conn = analyze.init_db(self.db)
        try:
            analyze.sync_sessions(conn, self.root)
            analyze.fill_substrate(conn)
        finally:
            conn.close()

    def run_pipeline(self, model_runner):
        base = Path(self.tmp.name)
        run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                      model_runner=model_runner,
                      claude_dir=base / "claude", projects_dir=base / "repos")

    def test_sync_fills_tool_events_paired_by_id_and_usage(self):
        write_records(self.root / "proj-a" / "sess-tools.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "write the adr"),
            rec("assistant", "a1", "2026-08-01T10:00:05Z",
                [{"type": "text", "text": "on it"},
                 {"type": "tool_use", "id": "tu-1", "name": "Write",
                  "input": {"file_path": "/w/proj-a/docs/adr/0001-a.md", "content": "x"}},
                 {"type": "tool_use", "id": "tu-2", "name": "Bash",
                  "input": {"command": "ls"}}],
                usage=USAGE, model="m-1", id="msg-1"),
            # results out of record order: pairing is by id, not position
            rec("user", "u2", "2026-08-01T10:00:09Z",
                [{"type": "tool_result", "tool_use_id": "tu-2", "content": "ok"}]),
            rec("user", "u3", "2026-08-01T10:00:07Z",
                [{"type": "tool_result", "tool_use_id": "tu-1", "content": "ok"}]),
        ])
        self.sync_and_fill()

        events = {e["tool_use_id"]: e for e in self.rows(
            "SELECT * FROM tool_events WHERE session_id='sess-tools'")}
        self.assertEqual(set(events), {"tu-1", "tu-2"})
        self.assertEqual(events["tu-1"]["name"], "Write")
        self.assertEqual(events["tu-1"]["file_path"], "/w/proj-a/docs/adr/0001-a.md")
        self.assertEqual(events["tu-1"]["at"], "2026-08-01T10:00:05Z")
        self.assertEqual(events["tu-1"]["result_at"], "2026-08-01T10:00:07Z")
        self.assertIsNone(events["tu-2"]["file_path"])
        self.assertEqual(events["tu-2"]["result_at"], "2026-08-01T10:00:09Z")

        usage = self.rows("SELECT * FROM usage WHERE session_id='sess-tools'")
        self.assertEqual(len(usage), 1)
        u = usage[0]
        self.assertEqual((u["message_id"], u["model"]), ("msg-1", "m-1"))
        self.assertEqual(
            (u["input_tokens"], u["output_tokens"],
             u["cache_creation_input_tokens"], u["cache_read_input_tokens"]),
            (10, 20, 30, 40))

    def test_usage_dedupes_records_streaming_one_response(self):
        """Records streaming one API response each repeat the same message id
        and usage — summed naively they double-count; one row per response."""
        write_records(self.root / "proj-a" / "sess-dup.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:01Z",
                [{"type": "text", "text": "part one"}],
                usage=USAGE, model="m-1", id="msg-1"),
            rec("assistant", "a2", "2026-08-01T10:00:02Z",
                [{"type": "text", "text": "part two"}],
                usage=USAGE, model="m-1", id="msg-1"),
            rec("assistant", "a3", "2026-08-01T10:00:03Z",
                [{"type": "text", "text": "next response"}],
                usage={**USAGE, "output_tokens": 5}, model="m-1", id="msg-2"),
        ])
        self.sync_and_fill()
        total = self.rows("SELECT COUNT(*) n, SUM(output_tokens) out FROM usage"
                          " WHERE session_id='sess-dup'")[0]
        self.assertEqual((total["n"], total["out"]), (2, 25))

    def test_adr_count_two_adr_files_vs_unrelated_edit(self):
        """One ADR created + one amended (twice — distinct files, not edits)
        = 2; an unrelated-edit session = a real 0, both at assemble time."""
        adr_blocks = [
            {"type": "text", "text": "done"},
            {"type": "tool_use", "id": "t1", "name": "Write",
             "input": {"file_path": "/w/proj-a/docs/adr/0001-first.md", "content": "x"}},
            {"type": "tool_use", "id": "t2", "name": "Edit",
             "input": {"file_path": "/w/proj-a/docs/adr/0002-second.md"}},
            {"type": "tool_use", "id": "t3", "name": "Edit",
             "input": {"file_path": "/w/proj-a/docs/adr/0002-second.md"}},
            {"type": "tool_use", "id": "t4", "name": "Edit",
             "input": {"file_path": "/p/src/main.py"}},
        ]
        write_records(self.root / "proj-a" / "sess-adr.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "record the decisions"),
            rec("assistant", "a1", "2026-08-01T10:00:05Z", adr_blocks),
        ])
        write_records(self.root / "proj-a" / "sess-plain.jsonl", [
            rec("user", "u0", "2026-08-01T11:00:00Z", "tweak the code"),
            rec("assistant", "a1", "2026-08-01T11:00:05Z",
                [{"type": "text", "text": "tweaked"},
                 {"type": "tool_use", "id": "t1", "name": "Edit",
                  "input": {"file_path": "/p/src/other.py"}}]),
        ])
        self.run_pipeline(StubRunner([ENTRY_A, ENTRY_B]))

        rows = self.audit_rows()
        self.assertEqual(rows["sess-adr"]["adr_count"], 2)
        self.assertEqual(rows["sess-plain"]["adr_count"], 0)

    def test_adr_count_counts_writes_under_a_former_root(self):
        """Ticket #6 / ADR-0018: a session re-keyed to `proj-b` after the
        folder was renamed from `proj-a` wrote its ADRs under the old root;
        the count follows presence history's former names, not the current
        name alone. A stranger's `proj-a` (another identity) is not ours."""
        import substrate
        conn = analyze.init_db(self.db)
        try:
            conn.execute("INSERT INTO sessions (id, project, transcript_path,"
                         " skipped_records, folder_identity)"
                         " VALUES ('s', 'proj-b', 'x', 0, 5)")
            conn.executemany(
                "INSERT INTO project_presence (folder_identity, name, first_seen,"
                " last_seen, present) VALUES (?, ?, 't0', 't1', ?)",
                [(5, "proj-a", 0), (5, "proj-b", 1), (9, "proj-a", 1)])
            conn.executemany(
                "INSERT INTO tool_events (session_id, name, file_path) VALUES ('s', ?, ?)",
                [("Write", "/w/proj-a/docs/adr/0001.md"),
                 ("Edit", "/w/proj-a/docs/adr/0001.md"),
                 ("Edit", "/w/proj-b/docs/adr/0002.md"),
                 ("Edit", "/w/proj-c/docs/adr/0003.md")])
            self.assertEqual(substrate.adr_count(conn, "s"), 2)
        finally:
            conn.close()

    def test_tokens_queryable_per_session_day_project(self):
        def usage_rec(uuid, day, mid, tokens):
            return rec("assistant", uuid, f"{day}T10:00:00Z",
                       [{"type": "text", "text": "ok"}],
                       usage={**USAGE, "input_tokens": tokens}, model="m-1", id=mid)

        write_records(self.root / "proj-a" / "sess-x.jsonl", [
            rec("user", "u0", "2026-08-01T09:00:00Z", "task x"),
            usage_rec("a1", "2026-08-01", "mx-1", 100),
            usage_rec("a2", "2026-08-02", "mx-2", 7),  # session spans two days
        ])
        write_records(self.root / "proj-b" / "sess-y.jsonl", [
            rec("user", "u0", "2026-08-02T09:00:00Z", "task y"),
            usage_rec("a1", "2026-08-02", "my-1", 1000),
        ])
        self.sync_and_fill()

        by_session = {r["session_id"]: r["t"] for r in self.rows(
            "SELECT session_id, SUM(input_tokens) t FROM usage GROUP BY session_id")}
        self.assertEqual(by_session, {"sess-x": 107, "sess-y": 1000})

        by_day = {r["day"]: r["t"] for r in self.rows(
            "SELECT substr(at, 1, 10) day, SUM(input_tokens) t FROM usage GROUP BY day")}
        self.assertEqual(by_day, {"2026-08-01": 100, "2026-08-02": 1007})

        by_project = {r["project"]: r["t"] for r in self.rows(
            "SELECT s.project, SUM(u.input_tokens) t FROM usage u"
            " JOIN sessions s ON s.id = u.session_id GROUP BY s.project")}
        self.assertEqual(by_project, {"proj-a": 107, "proj-b": 1000})

    def test_unknown_record_types_counted_and_skipped(self):
        write_records(self.root / "proj-a" / "sess-odd.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            {"type": "flurble", "payload": {"future": True}},
            {"type": "file-history-snapshot", "snapshot": {}},
            "not json {{{",
            rec("assistant", "a1", "2026-08-01T10:00:05Z",
                [{"type": "text", "text": "done"}]),
        ])
        self.sync_and_fill()
        row = self.rows("SELECT skipped_records FROM sessions WHERE id='sess-odd'")[0]
        self.assertEqual(row["skipped_records"], 3)

    def test_missing_tool_use_id_degrades_gracefully(self):
        """Older CLIs: a tool_use without an id keeps its row unpaired; a
        tool_result without a tool_use_id is ignored — never fatal."""
        write_records(self.root / "proj-a" / "sess-old.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:05Z",
                [{"type": "tool_use", "name": "Edit",
                  "input": {"file_path": "/w/proj-a/docs/adr/0003-c.md"}}]),
            rec("user", "u2", "2026-08-01T10:00:07Z",
                [{"type": "tool_result", "content": "ok"}]),
        ])
        self.sync_and_fill()
        events = self.rows("SELECT * FROM tool_events WHERE session_id='sess-old'")
        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0]["tool_use_id"])
        self.assertIsNone(events[0]["result_at"])
        self.assertEqual(events[0]["file_path"], "/w/proj-a/docs/adr/0003-c.md")

    def test_substrate_scan_runs_once_per_session(self):
        write_records(self.root / "proj-a" / "sess-once.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:01Z",
                [{"type": "tool_use", "id": "t1", "name": "Bash",
                  "input": {"command": "ls"}}],
                usage=USAGE, model="m-1", id="msg-1"),
        ])
        self.sync_and_fill()
        self.sync_and_fill()  # session still pending, but already scanned
        self.assertEqual(len(self.rows("SELECT * FROM tool_events")), 1)
        self.assertEqual(len(self.rows("SELECT * FROM usage")), 1)

    def test_consumer_grain_classified_at_scan(self):
        """Ticket #42: every tool_use carries its consumer classification —
        skill / cli / shell / builtin / mcp, per ccwhere's validated parse."""
        write_records(self.root / "proj-a" / "sess-grain.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:05Z", [
                {"type": "tool_use", "id": "t-skill", "name": "Skill",
                 "input": {"skill": "tdd"}},
                {"type": "tool_use", "id": "t-cli", "name": "Bash",
                 "input": {"command": "not-on-any-path-xyz --run"}},
                {"type": "tool_use", "id": "t-shell", "name": "Bash",
                 "input": {"command": "echo hi"}},
                {"type": "tool_use", "id": "t-plain", "name": "Bash",
                 "input": {"command": "$(weird) | $(stuff)"}},
                {"type": "tool_use", "id": "t-mcp",
                 "name": "mcp__pw__browser_click", "input": {}},
                {"type": "tool_use", "id": "t-b", "name": "Read",
                 "input": {"file_path": "/x"}},
            ], usage=USAGE, model="m-1", id="msg-1"),
        ])
        self.sync_and_fill()
        ev = {e["tool_use_id"]: e for e in self.rows(
            "SELECT * FROM tool_events WHERE session_id='sess-grain'")}
        self.assertEqual((ev["t-skill"]["consumer_type"], ev["t-skill"]["consumer"]),
                         ("skill", "tdd"))
        self.assertEqual((ev["t-cli"]["consumer_type"], ev["t-cli"]["consumer"]),
                         ("cli", "not-on-any-path-xyz"))
        self.assertEqual((ev["t-shell"]["consumer_type"], ev["t-shell"]["consumer"]),
                         ("shell", "echo"))
        # unextractable command: plain Bash, a builtin
        self.assertEqual((ev["t-plain"]["consumer_type"], ev["t-plain"]["consumer"]),
                         ("builtin", "Bash"))
        self.assertEqual((ev["t-mcp"]["consumer_type"], ev["t-mcp"]["consumer"],
                          ev["t-mcp"]["mcp_tool"]), ("mcp", "pw", "browser_click"))
        self.assertEqual((ev["t-b"]["consumer_type"], ev["t-b"]["consumer"]),
                         ("builtin", "Read"))

    def test_error_flag_from_paired_tool_result(self):
        """Ticket #42: is_error 1/0 from the paired result; NULL (unknown,
        not a false ok) when no result ever paired."""
        write_records(self.root / "proj-a" / "sess-err.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:05Z", [
                {"type": "tool_use", "id": "t-bad", "name": "Bash",
                 "input": {"command": "ls"}},
                {"type": "tool_use", "id": "t-ok", "name": "Read",
                 "input": {"file_path": "/x"}},
                {"type": "tool_use", "id": "t-lost", "name": "Read",
                 "input": {"file_path": "/y"}},
            ], usage=USAGE, model="m-1", id="msg-1"),
            rec("user", "u2", "2026-08-01T10:00:07Z", [
                {"type": "tool_result", "tool_use_id": "t-bad",
                 "content": "boom", "is_error": True},
                {"type": "tool_result", "tool_use_id": "t-ok", "content": "ok"},
            ]),
        ])
        self.sync_and_fill()
        ev = {e["tool_use_id"]: e for e in self.rows(
            "SELECT * FROM tool_events WHERE session_id='sess-err'")}
        self.assertEqual(ev["t-bad"]["is_error"], 1)
        self.assertEqual(ev["t-ok"]["is_error"], 0)
        self.assertIsNone(ev["t-lost"]["is_error"])

    def test_message_lens_links_tool_events_to_usage(self):
        """Ticket #42: each tool_use carries the API id of the message that
        emitted it, joining to `usage` for message-lens token attribution."""
        write_records(self.root / "proj-a" / "sess-lens.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:01Z",
                [{"type": "tool_use", "id": "t1", "name": "Bash",
                  "input": {"command": "ls"}}],
                usage={**USAGE, "output_tokens": 100}, model="m-1", id="msg-1"),
            rec("assistant", "a2", "2026-08-01T10:00:02Z",
                [{"type": "tool_use", "id": "t2", "name": "Read",
                  "input": {"file_path": "/x"}}],
                usage={**USAGE, "output_tokens": 7}, model="m-1", id="msg-2"),
        ])
        self.sync_and_fill()
        by_consumer = {r["consumer"]: r["out"] for r in self.rows(
            "SELECT te.consumer, SUM(u.output_tokens) out FROM tool_events te"
            " JOIN usage u ON u.message_id = te.message_id"
            " WHERE te.session_id='sess-lens' GROUP BY te.consumer")}
        self.assertEqual(by_consumer, {"ls": 100, "Read": 7})

    def test_streamed_duplicate_tool_use_kept_once(self):
        """The records streaming one API response repeat its tool_use blocks
        (same tool_use id) — one row per call, like usage dedup (#38)."""
        block = {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "ls"}}
        write_records(self.root / "proj-a" / "sess-twin.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:01Z", [block],
                usage=USAGE, model="m-1", id="msg-1"),
            rec("assistant", "a2", "2026-08-01T10:00:01Z", [block],
                usage=USAGE, model="m-1", id="msg-1"),
        ])
        self.sync_and_fill()
        self.assertEqual(len(self.rows(
            "SELECT * FROM tool_events WHERE session_id='sess-twin'")), 1)

    def test_malformed_tool_name_counted_and_skipped(self):
        """#38 parse wart: a tool_use whose name is command text (whitespace)
        is a malformed record — counted-and-skipped, never stored as a tool."""
        write_records(self.root / "proj-a" / "sess-wart.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:01Z", [
                {"type": "tool_use", "id": "t-wart",
                 "name": "ls output/cv-*.pdf 2>&1", "input": {}},
                {"type": "tool_use", "id": "t-fine", "name": "Read",
                 "input": {"file_path": "/x"}},
            ], usage=USAGE, model="m-1", id="msg-1"),
        ])
        self.sync_and_fill()
        names = [e["name"] for e in self.rows(
            "SELECT name FROM tool_events WHERE session_id='sess-wart'")]
        self.assertEqual(names, ["Read"])
        row = self.rows("SELECT skipped_records FROM sessions"
                        " WHERE id='sess-wart'")[0]
        self.assertEqual(row["skipped_records"], 1)

    def test_non_string_tool_use_fields_counted_never_fatal(self):
        """Ticket #50: a tool_use name that isn't a string is malformed
        (counted-and-skipped); a Bash command that isn't a string degrades
        to plain Bash — neither is a TypeError aborting the whole run."""
        write_records(self.root / "proj-a" / "sess-shapes.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:01Z", [
                {"type": "tool_use", "id": "t-listname",
                 "name": ["ls", "-la"], "input": {}},
                {"type": "tool_use", "id": "t-listcmd", "name": "Bash",
                 "input": {"command": ["ls", "-la"]}},
            ], usage=USAGE, model="m-1", id="msg-1"),
        ])
        self.sync_and_fill()
        rows = self.rows(
            "SELECT * FROM tool_events WHERE session_id='sess-shapes'")
        self.assertEqual([(r["name"], r["consumer_type"], r["consumer"])
                          for r in rows], [("Bash", "builtin", "Bash")])
        self.assertEqual(self.rows("SELECT skipped_records FROM sessions"
                                   " WHERE id='sess-shapes'")[0]["skipped_records"], 1)

    def test_malformed_name_streamed_twice_counted_once(self):
        """Ticket #50: dedup fires before the malformed skip, so one
        malformed call streamed across records counts skipped once."""
        block = {"type": "tool_use", "id": "t-wart",
                 "name": "ls -la 2>&1", "input": {}}
        write_records(self.root / "proj-a" / "sess-wart2.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:01Z", [block],
                usage=USAGE, model="m-1", id="msg-1"),
            rec("assistant", "a2", "2026-08-01T10:00:01Z", [block],
                usage=USAGE, model="m-1", id="msg-1"),
        ])
        self.sync_and_fill()
        self.assertEqual(self.rows("SELECT skipped_records FROM sessions"
                                   " WHERE id='sess-wart2'")[0]["skipped_records"], 1)

    def test_command_grains_captured_verbatim_from_command_messages(self):
        """Ticket #61: a user-typed slash command — a user message starting
        with a <command-…> marker, either <command-name> or <command-message>
        leading — lands in command_grains verbatim with its timestamp; a
        marker quoted mid-text (analysis extracts) is not a grain."""
        write_records(self.root / "proj-a" / "sess-cmd.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z",
                "<command-name>/clear</command-name>\n"
                "            <command-message>clear</command-message>\n"
                "            <command-args></command-args>"),
            rec("user", "u1", "2026-08-01T10:01:00Z",
                "<command-message>wayfinder</command-message>\n"
                "<command-name>/mattpocock-skills:wayfinder</command-name>\n"
                "<command-args>map is 58</command-args>"),
            rec("user", "u2", "2026-08-01T10:02:00Z",
                "quoting an extract: <command-name>/fake</command-name>"),
            rec("user", "u3", "2026-08-01T10:03:00Z", "plain message"),
        ])
        self.sync_and_fill()
        grains = self.rows("SELECT command, at FROM command_grains"
                           " WHERE session_id='sess-cmd' ORDER BY at")
        self.assertEqual(
            [(g["command"], g["at"]) for g in grains],
            [("/clear", "2026-08-01T10:00:00Z"),
             ("/mattpocock-skills:wayfinder", "2026-08-01T10:01:00Z")])

    def test_command_grains_rescanned_when_transcript_grew(self):
        """Ticket #29 invalidation covers command grains: a not-yet-done
        session that grew is rescanned from the full transcript without
        duplicating the grains scanned from the prefix."""
        path = self.root / "proj-a" / "sess-cmdgrow.jsonl"
        cmd = ("<command-name>/one</command-name>\n"
               "<command-message>one</command-message>")
        recs = [rec("user", "u0", "2026-08-01T10:00:00Z", cmd)]
        write_records(path, recs)
        self.run_pipeline(StubRunner([""]))  # what-pass fails: partial
        recs.append(rec("user", "u1", "2026-08-01T10:10:00Z",
                        cmd.replace("one", "two")))
        write_records(path, recs)
        self.run_pipeline(StubRunner([ENTRY_A]))
        grains = self.rows("SELECT command FROM command_grains"
                           " WHERE session_id='sess-cmdgrow' ORDER BY at")
        self.assertEqual([g["command"] for g in grains], ["/one", "/two"])

    # Issue #13: subagent transcripts (<session>/subagents/agent-<id>.jsonl)
    # are filed under the parent session, agent id on every row.
    def _parent_and_subagent(self, sid="sess-par", parent=True):
        root = self.root / "proj-a"
        if parent:
            write_records(root / f"{sid}.jsonl", [
                rec("user", "u0", "2026-08-01T10:00:00Z", "do the task"),
                rec("assistant", "a0", "2026-08-01T10:00:05Z",
                    [{"type": "text", "text": "spawning"},
                     {"type": "tool_use", "id": "tu-p", "name": "Agent",
                      "input": {"prompt": "go"}}],
                    usage=USAGE, model="m-1", id="msg-p")])
        write_records(root / sid / "subagents" / "agent-abc123.jsonl", [
            {**rec("user", "s0", "2026-08-01T10:00:06Z", "go"),
             "sessionId": sid, "agentId": "abc123", "isSidechain": True},
            {**rec("assistant", "s1", "2026-08-01T10:00:08Z",
                   [{"type": "text", "text": "subagent secret text"},
                    {"type": "tool_use", "id": "tu-s", "name": "Skill",
                     "input": {"skill": "grilling"}}],
                   usage={**USAGE, "output_tokens": 7}, model="m-1", id="msg-s"),
             "sessionId": sid, "agentId": "abc123", "isSidechain": True},
            {"type": "attachment", "attachment": {}},  # a record the scan skips
        ])
        return root / f"{sid}.jsonl"

    def test_subagent_transcript_is_filed_under_the_parent_session(self):
        """Issue #13 acceptance: the session's usage is parent + subagent; the
        subagent's tool calls carry its agent id, the parent's own rows carry
        NULL; the subagent transcript is recorded against the parent, never as
        a session of its own; its skipped records count on the parent."""
        self._parent_and_subagent()
        self.sync_and_fill()

        self.assertEqual([r["id"] for r in self.rows("SELECT id FROM sessions")],
                         ["sess-par"])
        usage = self.rows("SELECT agent_id, output_tokens FROM usage"
                          " WHERE session_id='sess-par' ORDER BY at")
        self.assertEqual([(u["agent_id"], u["output_tokens"]) for u in usage],
                         [(None, 20), ("abc123", 7)])
        events = {e["tool_use_id"]: e["agent_id"] for e in self.rows(
            "SELECT tool_use_id, agent_id FROM tool_events WHERE session_id='sess-par'")}
        self.assertEqual(events, {"tu-p": None, "tu-s": "abc123"})
        subs = self.rows("SELECT * FROM subagent_transcripts")
        self.assertEqual([(s["session_id"], s["agent_id"]) for s in subs],
                         [("sess-par", "abc123")])
        self.assertTrue(subs[0]["path"].endswith("agent-abc123.jsonl"))
        self.assertEqual(subs[0]["size"], Path(subs[0]["path"]).stat().st_size)
        self.assertEqual(self.rows("SELECT skipped_records FROM sessions")[0]
                         ["skipped_records"], 1)

    def test_excluded_parent_subagent_transcript_writes_no_rows(self):
        """Self-exclusion is inherited from the parent id: a subagent has no
        prompt signature of its own and is never scanned alone."""
        root = self.root / "proj-a"
        write_records(root / "sess-self.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z",
                "You are generating one audit-log entry for...")])
        self._parent_and_subagent("sess-self", parent=False)
        self.sync_and_fill()
        self.assertEqual(self.rows("SELECT * FROM usage"), [])
        self.assertEqual(self.rows("SELECT * FROM subagent_transcripts"), [])
        self.assertEqual(self.rows("SELECT * FROM sessions"), [])

    def test_fresh_subagent_transcript_holds_the_parent_live(self):
        """The live-session guard covers the parent when any of its subagent
        transcripts is fresh — scanning then would cache a truncated agent."""
        path = self._parent_and_subagent()
        sub = path.parent / "sess-par" / "subagents" / "agent-abc123.jsonl"
        now = time.time()
        os.utime(sub, (now, now))
        self.sync_and_fill()
        self.assertIsNone(self.rows("SELECT skipped_records FROM sessions")[0]
                          ["skipped_records"])
        self.assertEqual(self.rows("SELECT * FROM usage"), [])

    def test_command_grain_migration_rescans_scanned_sessions(self):
        """Ticket #61: a pre-#61 db (user_version 2) has every scanned
        session whose transcript survives rescanned on init_db — command
        grains appear, and refilled tool_events heal any truncated tail
        (#59) — while a vanished transcript keeps its old rows."""
        write_records(self.root / "proj-a" / "sess-v2.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z",
                "<command-name>/tdd</command-name>\n"
                "<command-message>tdd</command-message>"),
            rec("assistant", "a1", "2026-08-01T10:00:05Z",
                [{"type": "tool_use", "id": "t1", "name": "Bash",
                  "input": {"command": "ls"}}]),
        ])
        conn = analyze.init_db(self.db)
        live = str(self.root / "proj-a" / "sess-v2.jsonl")
        conn.execute("INSERT INTO sessions (id, project, transcript_path,"
                     " status, skipped_records) VALUES"
                     " ('sess-v2', 'proj-a', ?, 'done', 0)", (live,))
        conn.execute("INSERT INTO sessions (id, project, transcript_path,"
                     " status, skipped_records) VALUES"
                     " ('sess-gone', 'proj-a', '/nowhere/g.jsonl', 'done', 1)")
        # the pre-#61 scan: tool_events truncated, no command grains
        conn.execute("INSERT INTO tool_events (session_id, name)"
                     " VALUES ('sess-gone', 'Read')")
        conn.execute("PRAGMA user_version = 2")
        conn.commit()
        conn.close()

        analyze.init_db(self.db).close()  # the migration itself must refill
        grains = self.rows("SELECT command FROM command_grains"
                           " WHERE session_id='sess-v2'")
        self.assertEqual([g["command"] for g in grains], ["/tdd"])
        events = self.rows("SELECT name FROM tool_events"
                           " WHERE session_id='sess-v2'")
        self.assertEqual([e["name"] for e in events], ["Bash"])
        gone = self.rows("SELECT name FROM tool_events"
                         " WHERE session_id='sess-gone'")
        self.assertEqual([e["name"] for e in gone], ["Read"])
        conn = sqlite3.connect(self.db)
        try:
            self.assertEqual(
                conn.execute("PRAGMA user_version").fetchone()[0], 8)
        finally:
            conn.close()

    def test_local_day_buckets_by_operator_clock(self):
        """Ticket #74 / ADR-0014: a stored UTC timestamp buckets to the
        operator's local day. A bare day is already a bucket and passes
        through — converting one twice would walk it a day west."""
        self.assertEqual(analyze.local_day("2026-08-29T00:13:55.057Z"),
                         "2026-08-28")
        self.assertEqual(analyze.local_day("2026-08-29T12:00:00Z"), "2026-08-29")
        self.assertEqual(analyze.local_day("2026-08-28"), "2026-08-28")
        self.assertEqual(analyze.local_day(None), "")
        self.assertEqual(analyze.local_day("not a timestamp"), "not a time")

    def test_local_day_migration_redates_stored_session_days(self):
        """Ticket #74: `sessions.date` is a stored bucket, so migration 5
        re-derives it from the transcript head rather than converting a day
        that has lost its clock time. A vanished transcript keeps its
        UTC date — a guess is not a re-derivation."""
        live = self.root / "proj-a" / "sess-eve.jsonl"
        write_records(live, [rec("user", "u0", "2026-08-29T00:13:55.057Z", "hi")])
        conn = analyze.init_db(self.db)
        conn.execute("INSERT INTO sessions (id, project, transcript_path,"
                     " date, status) VALUES ('sess-eve', 'proj-a', ?,"
                     " '2026-08-29', 'done')", (str(live),))
        conn.execute("INSERT INTO sessions (id, project, transcript_path,"
                     " date, status) VALUES ('sess-gone', 'proj-a',"
                     " '/nowhere/g.jsonl', '2026-08-29', 'done')")
        conn.execute("INSERT INTO audit (session_id, date, skip,"
                     " prompt_version, model) VALUES"
                     " ('sess-eve', '2026-08-29', 1, 'what-v1', 'm')")
        conn.execute("PRAGMA user_version = 4")  # pre-#74 db
        conn.commit()
        conn.close()

        analyze.init_db(self.db).close()
        dates = {r["id"]: r["date"] for r in self.rows(
            "SELECT id, date FROM sessions")}
        self.assertEqual(dates["sess-eve"], "2026-08-28")
        self.assertEqual(dates["sess-gone"], "2026-08-29")
        self.assertEqual(self.rows("SELECT date FROM audit")[0]["date"],
                         "2026-08-28")

    def test_migration_sniffs_run_once_per_db(self):
        """Ticket #50: PRAGMA user_version gates the migration sniffs — a
        table named `runs` created after the first init_db survives later
        init_db calls instead of being destroyed on every startup."""
        analyze.init_db(self.db).close()
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        conn = analyze.init_db(self.db)
        try:
            self.assertEqual(
                conn.execute("PRAGMA user_version").fetchone()[0], 8)
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("runs", tables)
        finally:
            conn.close()

    def test_migration_purges_stored_refusal_rows(self):
        """Ticket #38: a db carrying refusal text as skip=0 audit rows
        (stored before the contract gate existed) has those rows deleted
        and their sessions set pending on the next init_db; entry and SKIP
        rows untouched. Gated: runs once per db."""
        conn = analyze.init_db(self.db)
        conn.execute("INSERT INTO sessions (id, transcript_path, status) VALUES"
                     " ('s-bad', '/t/a.jsonl', 'done'),"
                     " ('s-good', '/t/b.jsonl', 'done'),"
                     " ('s-skip', '/t/c.jsonl', 'done')")
        conn.execute(
            "INSERT INTO audit (session_id, skip, markdown, prompt_version, model)"
            " VALUES ('s-bad', 0, ?, 'what-v1', 'm'),"
            " ('s-good', 0, ?, 'what-v1', 'm'),"
            " ('s-skip', 1, NULL, 'what-v1', 'm')", (REFUSAL_MD, ENTRY_A))
        conn.execute("PRAGMA user_version = 1")  # pre-#38 db
        conn.commit()
        conn.close()

        analyze.init_db(self.db).close()
        self.assertEqual(set(self.audit_rows()), {"s-good", "s-skip"})
        statuses = self.session_statuses()
        self.assertEqual(statuses["s-bad"], "pending")
        self.assertEqual(statuses["s-good"], "done")
        self.assertEqual(statuses["s-skip"], "done")
        conn = sqlite3.connect(self.db)
        try:
            self.assertEqual(
                conn.execute("PRAGMA user_version").fetchone()[0], 8)
        finally:
            conn.close()

    def test_migration_backfills_grains_where_transcript_survives(self):
        """A pre-#42 db: init_db adds the grain columns, resets the scanned
        marker (dropping stale substrate rows) wherever the transcript
        survives, and refills in the same call (ticket #50) — no
        caller-dependent wipe-to-refill window; a session whose transcript
        vanished keeps its old rows, grain columns NULL."""
        write_records(self.root / "proj-a" / "sess-live.jsonl", [
            rec("user", "u0", "2026-08-01T10:00:00Z", "task"),
            rec("assistant", "a1", "2026-08-01T10:00:01Z",
                [{"type": "tool_use", "id": "t1", "name": "Skill",
                  "input": {"skill": "tdd"}}],
                usage=USAGE, model="m-1", id="msg-1"),
        ])
        self.db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db)
        conn.executescript("""
            CREATE TABLE sessions (
              id TEXT PRIMARY KEY, project TEXT, transcript_path TEXT NOT NULL,
              date TEXT, cli_version TEXT, size INTEGER,
              status TEXT NOT NULL DEFAULT 'pending', skipped_records INTEGER);
            CREATE TABLE tool_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL, tool_use_id TEXT, name TEXT,
              at TEXT, result_at TEXT, file_path TEXT);
            CREATE TABLE usage (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL, message_id TEXT, at TEXT, model TEXT,
              input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
              cache_creation_input_tokens INTEGER NOT NULL,
              cache_read_input_tokens INTEGER NOT NULL);
        """)
        live = str(self.root / "proj-a" / "sess-live.jsonl")
        conn.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)",
                     ("sess-live", "proj-a", live, "2026-08-01", None, 1, "pending", 0))
        conn.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)",
                     ("sess-gone", "proj-a", "/nowhere/gone.jsonl",
                      "2026-08-01", None, 1, "pending", 2))
        for sid in ("sess-live", "sess-gone", "sess-gone"):  # gone: pre-dedup twin
            conn.execute("INSERT INTO tool_events (session_id, tool_use_id,"
                         " name, at, result_at, file_path)"
                         " VALUES (?, 't-old', 'Bash', NULL, NULL, NULL)", (sid,))
        conn.commit()
        conn.close()

        # no explicit fill_substrate: the migration itself must refill
        analyze.init_db(self.db).close()

        live_rows = self.rows(
            "SELECT * FROM tool_events WHERE session_id='sess-live'")
        self.assertEqual([(r["name"], r["consumer_type"], r["consumer"])
                          for r in live_rows], [("Skill", "skill", "tdd")])
        gone = self.rows("SELECT * FROM tool_events WHERE session_id='sess-gone'")
        self.assertEqual([(r["name"], r["consumer_type"]) for r in gone],
                         [("Bash", None)])
        self.assertEqual(self.rows("SELECT skipped_records FROM sessions"
                                   " WHERE id='sess-gone'")[0]["skipped_records"], 2)


def shaped(version, i, extra=None):
    """One full-shaped user/assistant record pair under `version` — every
    FIELD_CONTRACT key present (issue #15)."""
    u = {**rec("user", f"u{i}", "2026-08-01T10:00:00Z",
               [{"type": "tool_result", "tool_use_id": f"t{i-1}", "content": "ok"},
                {"type": "text", "text": "go"}]), "version": version, **(extra or {})}
    a = {**rec("assistant", f"a{i}", "2026-08-01T10:00:01Z",
               [{"type": "text", "text": "ok"},
                {"type": "tool_use", "id": f"t{i}", "name": "Bash",
                 "input": {"command": "ls"}}],
               usage=USAGE, model="m", id=f"m{i}"), "version": version, **(extra or {})}
    return [u, a]


class FieldHistogramTest(DbHelpers, unittest.TestCase):
    """The field histogram (issue #15): counted in the one scan, per record
    version, stored per session, summed per version by the guard."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"

    def sync_and_fill(self):
        conn = analyze.init_db(self.db)
        try:
            analyze.sync_sessions(conn, self.root)
            analyze.fill_substrate(conn)
        finally:
            conn.close()

    def hist(self):
        conn = analyze.init_db(self.db)
        try:
            return analyze.version_histogram(conn)
        finally:
            conn.close()

    def test_every_contract_key_counted_per_record_version(self):
        # one transcript, records from two CLIs (never per session)
        recs = [r for i in range(3) for r in shaped("2.1.1", i)]
        recs += [r for i in range(3, 5) for r in shaped("2.1.2", i)]
        recs += [{"type": "attachment", "attachment": {}}]  # no version: ''
        write_records(self.root / "p" / "s1.jsonl", recs)
        self.sync_and_fill()
        h = self.hist()
        self.assertEqual(h["2.1.1"]["record"], {"*": 6, "user": 3, "assistant": 3})
        self.assertEqual(h["2.1.2"]["record"]["*"], 4)
        self.assertEqual(h[""]["record"], {"*": 1, "attachment": 1})
        for scope, key in analyze.FIELD_CONTRACT:
            self.assertEqual(h["2.1.1"][scope][key], h["2.1.1"][scope]["*"],
                             (scope, key))
        # block-type distribution and a non-contract key both counted
        self.assertEqual(h["2.1.1"]["assistant.message.content"],
                         {"text": 3, "tool_use": 3})
        self.assertEqual(h["2.1.1"]["user.message.content.tool_result"]["content"], 3)

    def test_rescan_leaves_counts_equal_to_a_fresh_scan(self):
        """A schema-bump rescan and a growth top-up both wipe per session,
        so the summed histogram never double-counts."""
        write_records(self.root / "p" / "s1.jsonl",
                      [r for i in range(4) for r in shaped("2.1.1", i)])
        self.sync_and_fill()
        fresh = self.hist()
        conn = analyze.init_db(self.db)
        analyze._reset_scanned(conn)         # the schema-bump path
        analyze.fill_substrate(conn)
        conn.close()
        self.assertEqual(self.hist(), fresh)
        # growth: the transcript gains two pairs; the top-up rescans whole
        with (self.root / "p" / "s1.jsonl").open("a") as f:
            for r in [r for i in range(4, 6) for r in shaped("2.1.1", i)]:
                f.write(json.dumps(r) + "\n")
        _backdate(self.root / "p" / "s1.jsonl")
        conn = analyze.init_db(self.db)
        analyze.invalidate_grown(conn, self.tmp.name)
        analyze.fill_substrate(conn)
        conn.close()
        self.assertEqual(self.hist()["2.1.1"]["record"]["*"], 12)


if __name__ == "__main__":
    unittest.main()
