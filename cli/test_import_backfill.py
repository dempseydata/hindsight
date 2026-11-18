"""Seam tests for the backfill history import (ticket #20).

External behaviour only: run the import over a fixture backfill directory
(cached extracts + what model outputs + inventory, no live model) and
assert the store rows — original prompt version, pending for incomplete
sessions, idempotent re-runs, and a subsequent analysis run that processes
pending sessions without touching imported rows.
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import analyze
from import_backfill import import_backfill
from test_helpers import (ENTRY_A, ENTRY_B, FIXTURE_TURNS,
                          MERGED_ENTRY, REFUSAL_MD, USAGE, DbHelpers,
                          StubRunner, rec, write_records, write_transcript)

MODEL = "test-model"


def write_extract(bf, sid, part, turns, start):
    """One hand-written extract part in the ADR-0002 indexed format; returns
    its slice of the sidecar index->uuid map."""
    lines = [f"[{i}] {role.upper()}: {text}"
             for i, (role, text) in enumerate(turns, start)]
    (bf / "extracts" / f"{sid}.part{part}.txt").write_text("\n\n".join(lines) + "\n")
    return {str(i): {"uuid": f"{sid}-{i}"} for i, _ in enumerate(turns, start)}


class ImportBackfillTest(DbHelpers, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.bf = base / "backfill"
        for d in ("extracts", "what"):
            (self.bf / d).mkdir(parents=True)
        self.root = base / "projects"
        self.proj = self.root / "test-project"
        self.proj.mkdir(parents=True)
        self.db = base / "hindsight.db"
        self.work = base / "analysis"

        inv_sessions = []

        def add(sid):
            inv_sessions.append({"id": sid, "path": str(self.proj / f"{sid}.jsonl"),
                                 "project": "test-project", "date": "2026-06-01",
                                 "size": 100})

        def write_map(sid, *maps):
            merged = {}
            for m in maps:
                merged.update(m)
            (self.bf / "extracts" / f"{sid}.map.json").write_text(json.dumps(merged))

        # Complete single-part session.
        add("sess-done")
        write_map("sess-done", write_extract(self.bf, "sess-done", 1, FIXTURE_TURNS, 1))
        (self.bf / "what" / "sess-done.part1.md").write_text(ENTRY_A)

        # Complete trivial session — fenced SKIP, to prove fence-stripping.
        add("sess-skip")
        write_map("sess-skip", write_extract(
            self.bf, "sess-skip", 1,
            [("user", "fix the typo"), ("assistant", "done")], 1))
        (self.bf / "what" / "sess-skip.part1.md").write_text("```markdown\nSKIP\n```")

        # Complete multi-part session: merged what entry.
        add("sess-multi")
        write_map("sess-multi",
                  write_extract(self.bf, "sess-multi", 1, FIXTURE_TURNS[:2], 1),
                  write_extract(self.bf, "sess-multi", 2, FIXTURE_TURNS[2:], 3))
        (self.bf / "what" / "sess-multi.part1.md").write_text(ENTRY_A)
        (self.bf / "what" / "sess-multi.part2.md").write_text(ENTRY_B)
        (self.bf / "what" / "sess-multi.merged.md").write_text(MERGED_ENTRY)

        # Incomplete: extracted, what missing (renamed .bad by the backfill)
        # — must import as pending, none of its cached rows stored.
        add("sess-partial")
        write_map("sess-partial", write_extract(
            self.bf, "sess-partial", 1,
            [("user", "task p"), ("assistant", "done p")], 1))

        # Never extracted (backfill never reached it).
        add("sess-noext")

        # Empty extract: sidecar map written, zero parts.
        add("sess-empty")
        write_map("sess-empty")

        (self.bf / "inventory.json").write_text(json.dumps(
            {"model": MODEL, "excluded_analysis_runs": 0, "sessions": inv_sessions}))

    def test_import_populates_store_under_original_versions(self):
        result = import_backfill(self.db, self.bf)

        self.assertEqual(self.session_statuses(), {
            "sess-done": "done", "sess-skip": "done", "sess-multi": "done",
            "sess-partial": "pending", "sess-noext": "pending",
            "sess-empty": "empty"})

        audit = self.audit_rows()
        self.assertEqual(set(audit), {"sess-done", "sess-skip", "sess-multi"})
        for row in audit.values():
            self.assertEqual(row["prompt_version"], "what-v1")
            self.assertEqual(row["model"], MODEL)
        self.assertEqual(audit["sess-done"]["markdown"], ENTRY_A)
        self.assertEqual(audit["sess-skip"]["skip"], 1)
        self.assertIsNone(audit["sess-skip"]["markdown"])
        self.assertEqual(audit["sess-multi"]["markdown"], MERGED_ENTRY)

        self.assertEqual(result["imported"], 3)
        self.assertEqual(result["statuses"],
                          {"done": 3, "empty": 1, "pending": 2, "already_present": 0})

    def test_reimport_is_idempotent(self):
        import_backfill(self.db, self.bf)
        snapshot = (self.session_statuses(), self.audit_rows())
        result = import_backfill(self.db, self.bf)
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["statuses"]["already_present"], 6)
        self.assertEqual((self.session_statuses(), self.audit_rows()), snapshot)

    def test_already_analyzed_session_is_never_touched(self):
        conn = analyze.init_db(self.db)
        conn.execute(
            "INSERT INTO sessions (id, project, transcript_path, status)"
            " VALUES ('sess-done', 'other-project', 'elsewhere.jsonl', 'done')")
        conn.commit()
        conn.close()

        result = import_backfill(self.db, self.bf)
        self.assertEqual(result["statuses"]["already_present"], 1)
        self.assertNotIn("sess-done", self.audit_rows())
        conn = sqlite3.connect(self.db)
        try:
            row = conn.execute(
                "SELECT project, transcript_path FROM sessions WHERE id='sess-done'").fetchone()
        finally:
            conn.close()
        self.assertEqual(row, ("other-project", "elsewhere.jsonl"))

    def test_imported_session_substrate_fills_on_next_run(self):
        """The import assembles audit rows before any substrate exists —
        adr_count NULL, not a false 0. The next analysis run's sync scans the
        transcript, fills tool_events/usage, and stamps the count."""
        import_backfill(self.db, self.bf)
        self.assertIsNone(self.audit_rows()["sess-done"]["adr_count"])

        write_records(self.proj / "sess-done.jsonl", [
            rec("user", "u0", "2026-06-01T10:00:00Z", "record the decision"),
            rec("assistant", "a1", "2026-06-01T10:00:05Z",
                [{"type": "text", "text": "done"},
                 {"type": "tool_use", "id": "tu-1", "name": "Write",
                  "input": {"file_path": "/w/test-project/docs/adr/0001-a.md", "content": "x"}}],
                usage=USAGE, model="m-1", id="msg-1"),
        ])
        # The two pending sessions have no transcripts: extraction fails and
        # no model call happens (StopIteration would fail the test if one did).
        base = Path(self.tmp.name)
        analyze.run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                              model_runner=StubRunner([]),
                              claude_dir=base / "claude", projects_dir=base / "repos")

        self.assertEqual(self.audit_rows()["sess-done"]["adr_count"], 1)
        self.assertEqual(len(self.rows(
            "SELECT * FROM usage WHERE session_id='sess-done'")), 1)
        self.assertEqual(self.rows(
            "SELECT name, file_path FROM tool_events WHERE session_id='sess-done'"),
            [{"name": "Write", "file_path": "/w/test-project/docs/adr/0001-a.md"}])

    def test_refusal_what_output_imports_as_pending(self):
        """Ticket #38: a cached what output holding refusal prose is not an
        entry — the session imports as pending for fresh analysis, no audit
        row, instead of done with the refusal stored skip=0."""
        inv = json.loads((self.bf / "inventory.json").read_text())
        inv["sessions"].append({"id": "sess-refuse",
                                "path": str(self.proj / "sess-refuse.jsonl"),
                                "project": "test-project",
                                "date": "2026-06-01", "size": 100})
        (self.bf / "inventory.json").write_text(json.dumps(inv))
        m = write_extract(self.bf, "sess-refuse", 1, FIXTURE_TURNS, 1)
        (self.bf / "extracts" / "sess-refuse.map.json").write_text(json.dumps(m))
        (self.bf / "what" / "sess-refuse.part1.md").write_text(REFUSAL_MD)

        result = import_backfill(self.db, self.bf)
        self.assertEqual(self.session_statuses()["sess-refuse"], "pending")
        self.assertNotIn("sess-refuse", self.audit_rows())
        self.assertEqual(result["statuses"]["pending"], 3)
        self.assertEqual(result["imported"], 3)

    def test_subsequent_analysis_processes_pending_without_touching_imported(self):
        import_backfill(self.db, self.bf)
        imported_audit = self.audit_rows()

        # Transcripts for the two pending sessions, plus one post-dating the
        # backfill snapshot (not in its inventory — the ordinary sync's job).
        write_transcript(self.proj / "sess-partial.jsonl",
                          [("user", "task p"), ("assistant", "done p")])
        write_transcript(self.proj / "sess-noext.jsonl",
                          [("user", "task n"), ("assistant", "done n")])
        write_transcript(self.proj / "sess-new.jsonl",
                          [("user", "task new"), ("assistant", "done new")])

        # Processing order (by id): sess-new, sess-noext, sess-partial — a
        # what call each; StopIteration would fail the test if any imported
        # session were re-analysed.
        stub = StubRunner([ENTRY_A, ENTRY_B, ENTRY_A])
        analyze.run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                              model_runner=stub)
        self.assertEqual(len(stub.calls), 3)

        statuses = self.session_statuses()
        for sid in ("sess-new", "sess-noext", "sess-partial"):
            self.assertEqual(statuses[sid], "done")
        self.assertEqual(statuses["sess-empty"], "empty")

        audit = self.audit_rows()
        self.assertEqual(audit["sess-partial"]["prompt_version"], analyze.PROMPT_VERSION)
        self.assertEqual(audit["sess-new"]["prompt_version"], analyze.PROMPT_VERSION)
        # Imported rows untouched: still their original version and content.
        self.assertEqual(audit["sess-done"], imported_audit["sess-done"])
        self.assertEqual(audit["sess-multi"], imported_audit["sess-multi"])


if __name__ == "__main__":
    unittest.main()
