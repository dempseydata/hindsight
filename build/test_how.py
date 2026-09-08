"""Tests for the how-view data pipeline (ticket #63, ADR-0010/0011):
declaration parsing with its three states, marker matching, trail assembly
and the dumb checker — over a fixture DB built from the real schema."""
import os
import tempfile
import time
import unittest
from pathlib import Path

import analyze
import how

# Day buckets are the operator's local day (ADR-0014), so the fixtures
# need a pinned zone or they assert whatever the runner's clock says.
os.environ["TZ"] = "America/New_York"
time.tzset()

VALID = """---
stages:
  - name: Plan
    commands: [wayfinder, grill-with-docs]
    skills: [grilling]
    paths: [docs/adr/, CONTEXT.md]
  - name: Build
    commands: [implement]
    skills: [tdd]
    paths: [build/]
  - name: Release
---
# prose
"""


class Parse(unittest.TestCase):
    def test_valid(self):
        state, stages, err = how.parse_declaration(VALID)
        self.assertEqual((state, err), ("valid", None))
        self.assertEqual([s["name"] for s in stages], ["Plan", "Build", "Release"])
        self.assertEqual(stages[0]["paths"], ["docs/adr/", "CONTEXT.md"])
        self.assertEqual(stages[2], {"name": "Release", "commands": [],
                                     "skills": [], "paths": []})

    def test_absent_without_fence(self):
        self.assertEqual(how.parse_declaration("# prose only\n")[0], "absent")
        self.assertEqual(how.parse_declaration("")[0], "absent")
        # fence not at line 1 is absent, not invalid
        self.assertEqual(how.parse_declaration("\n---\nstages:\n---\n")[0], "absent")

    def invalid(self, text):
        state, stages, err = how.parse_declaration(text)
        self.assertEqual(state, "invalid", text)
        self.assertEqual(stages, [])
        return err

    def test_invalid_reasons_name_the_line(self):
        self.assertIn("line 4", self.invalid("---\nstages:\n  - name: A\n    skils: [x]\n---\n"))
        self.assertIn("line 2", self.invalid("---\nversion: 1\nstages:\n---\n"))
        self.assertIn("name", self.invalid("---\nstages:\n  - commands: [x]\n---\n"))
        self.assertIn("line 4: duplicate stage", self.invalid(
            "---\nstages:\n  - name: A\n  - name: A\n---\n"))
        self.assertIn("line 6: `x` in `B` collides with `x` in `A`", self.invalid(
            "---\nstages:\n  - name: A\n    commands: [x]\n  - name: B\n    commands: [x]\n---\n"))
        # bare vs qualified forms of one name across stages is the same ambiguity
        self.assertIn("line 6", self.invalid(
            "---\nstages:\n  - name: A\n    skills: [grilling]\n  - name: B\n"
            "    commands: [p:grilling]\n---\n"))
        self.assertIn("line 6: path", self.invalid(
            "---\nstages:\n  - name: A\n    paths: [x/]\n  - name: B\n    paths: [x/]\n---\n"))
        self.assertIn("line 5: `commands` given twice", self.invalid(
            "---\nstages:\n  - name: A\n    commands: [x]\n    commands: [y]\n---\n"))
        self.assertIn("line 2", self.invalid("---\n# comment\nstages:\n---\n"))
        self.assertIn("list", self.invalid("---\nstages:\n  - name: A\n    commands: x\n---\n"))
        self.assertIn("unclosed", self.invalid("---\nstages:\n  - name: A\n"))
        self.assertIn("stages", self.invalid("---\nfoo: 1\n---\n"))

    def test_name_pool_is_shared_across_commands_and_skills(self):
        # one name pool: a name in A's commands and B's skills is ambiguous
        text = "---\nstages:\n  - name: A\n    commands: [x]\n  - name: B\n    skills: [x]\n---\n"
        self.assertEqual(how.parse_declaration(text)[0], "invalid")
        # the same name in one stage's commands and skills is not ambiguous
        text = "---\nstages:\n  - name: A\n    commands: [x]\n    skills: [x]\n---\n"
        self.assertEqual(how.parse_declaration(text)[0], "valid")
        # but a path marker may share text with a name marker
        text = "---\nstages:\n  - name: A\n    commands: [x]\n  - name: B\n    paths: [x]\n---\n"
        self.assertEqual(how.parse_declaration(text)[0], "valid")


    def test_live_fixture_hindsight_declaration(self):
        state, stages, err = how.read_declaration(analyze.REPO)
        if state == "absent":  # app-only checkout: the working repo's declaration doesn't ship
            self.skipTest("live fixture .claude/my-process.md not present")
        self.assertEqual((state, err), ("valid", None))
        self.assertEqual([s["name"] for s in stages],
                         ["Ideate", "Design", "Plan", "Build", "Release"])
        # A built-in CLI command is never declared, so it marks no stage. (The
        # declaration is the authority on which *skills* map where — it
        # evolves, so this test pins no such decision; #64 → #65 once had
        # wayfinder unmapped, and the live file has since said otherwise.)
        self.assertIsNone(how.stage_for(stages, "command", "/clear"))
        self.assertEqual(how.stage_for(stages, "command", "/mattpocock-skills:to-tickets"), "Plan")
        self.assertEqual(how.stage_for(stages, "skill", "ponytail:ponytail-review"), "Build")
        self.assertEqual(how.stage_for(stages, "write", "docs/adr/0011-x.md"), "Plan")

    def test_unreadable_file_is_invalid_not_absent(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".claude").mkdir()
            (Path(d) / ".claude" / "my-process.md").mkdir()  # a dir: exists, unreadable
            state, _, err = how.read_declaration(d)
            self.assertEqual(state, "invalid")
            self.assertIn("cannot read", err)
        self.assertEqual(how.read_declaration(Path(d) / "gone")[0], "absent")


class Match(unittest.TestCase):
    def test_tail_segment(self):
        self.assertTrue(how.match_name("grilling", "grilling"))
        self.assertTrue(how.match_name("grilling", "mattpocock-skills:grilling"))
        self.assertFalse(how.match_name("grilling", "grilling-with-pellets"))
        self.assertFalse(how.match_name("grilling", "Grilling"))
        self.assertTrue(how.match_name("a:grilling", "a:grilling"))
        self.assertFalse(how.match_name("a:grilling", "b:grilling"))

    def test_path(self):
        self.assertTrue(how.match_path("build/", "build/x/y.py"))
        self.assertFalse(how.match_path("build/", "build"))
        self.assertTrue(how.match_path("CONTEXT.md", "CONTEXT.md"))
        self.assertFalse(how.match_path("CONTEXT.md", "CONTEXT.md.bak"))
        self.assertFalse(how.match_path("build/", "Build/x"))

    def test_longest_prefix_wins_for_nested_subtrees(self):
        stages = how.parse_declaration(
            "---\nstages:\n  - name: A\n    paths: [build/]\n"
            "  - name: B\n    paths: [build/docs/]\n---\n")[1]
        self.assertEqual(how.stage_for(stages, "write", "build/docs/x.md"), "B")
        self.assertEqual(how.stage_for(stages, "write", "build/x.py"), "A")
        self.assertIsNone(how.stage_for(stages, "write", "README.md"))

    def test_skill_event_matches_command_marker_and_vice_versa(self):
        stages = how.parse_declaration(VALID)[1]
        self.assertEqual(how.stage_for(stages, "skill", "mattpocock-skills:implement"), "Build")
        self.assertEqual(how.stage_for(stages, "command", "/mattpocock-skills:tdd"), "Build")
        self.assertIsNone(how.stage_for(stages, "command", "/clear"))


def fixture(root):
    conn = analyze.init_db(root / "h.db")
    conn.executemany("INSERT INTO sessions (id, project, transcript_path, date,"
                     " status) VALUES (?, ?, 'x', ?, 'done')",
                     [("s1", "proj", "2026-08-01"), ("s2", "proj", "2026-08-03"),
                      ("s3", "other", "2026-08-02")])
    conn.executemany("INSERT INTO audit (session_id, project, date, skip, markdown,"
                     " prompt_version, model) VALUES (?, 'proj', ?, ?, ?, 'v', 'm')",
                     [("s1", "2026-08-01", 0, "### Grilled the plan\n- **Did:** x"),
                      ("s2", "2026-08-03", 1, None)])
    conn.executemany("INSERT INTO command_grains (session_id, command, at) VALUES (?,?,?)",
                     [("s1", "/mattpocock-skills:wayfinder", "2026-08-01T10:00:00Z"),
                      ("s1", "/clear", "2026-08-01T09:00:00Z"),
                      ("s2", "/mattpocock-skills:implement", "2026-08-03T10:00:00Z"),
                      ("s3", "/mattpocock-skills:wayfinder", "2026-08-02T10:00:00Z")])
    p = str(root / "proj")
    conn.executemany("INSERT INTO tool_events (session_id, name, at, file_path,"
                     " consumer_type, consumer) VALUES (?,?,?,?,?,?)", [
        ("s1", "Skill", "2026-08-01T10:05:00Z", None, "skill", "mattpocock-skills:grilling"),
        ("s1", "Write", "2026-08-01T10:10:00Z", f"{p}/docs/adr/0001.md", "builtin", "Write"),
        ("s1", "Edit", "2026-08-01T10:11:00Z", f"{p}/docs/adr/0001.md", "builtin", "Edit"),
        ("s1", "Read", "2026-08-01T10:12:00Z", f"{p}/build/x.py", "builtin", "Read"),
        ("s1", "Edit", "2026-08-01T10:13:00Z", "/elsewhere/notes.md", "builtin", "Edit"),
        ("s2", "Edit", "2026-08-03T10:20:00Z", f"{p}/build/x.py", "builtin", "Edit"),
        ("s2", "Skill", "2026-08-03T10:30:00Z", None, "skill", "ponytail:ponytail-review"),
        ("s2", "Write", "2026-08-03T10:40:00Z", f"{p}/README.md", "builtin", "Write"),
    ])
    conn.commit()
    return conn


class Trail(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.conn = fixture(self.root)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def declare(self, text):
        d = self.root / "proj" / ".claude"
        d.mkdir(parents=True)
        (d / "my-process.md").write_text(text)

    def test_raw_trail_when_absent(self):
        data = how.how_data(self.conn, "proj", self.root)
        self.assertEqual(data["declaration"], {"state": "absent", "error": None, "stages": []})
        self.assertEqual([(e["kind"], e["name"]) for e in data["trail"]], [
            ("command", "/clear"), ("command", "/mattpocock-skills:wayfinder"),
            ("skill", "mattpocock-skills:grilling"), ("write", "docs/adr/0001.md"),
            ("command", "/mattpocock-skills:implement"), ("write", "build/x.py"),
            ("skill", "ponytail:ponytail-review"), ("write", "README.md")])
        self.assertTrue(all(e["stage"] is None for e in data["trail"]))
        self.assertEqual(data["summary"], [])
        self.assertEqual(data["off_script"], [])
        self.assertEqual(data["boundaries"], {})
        self.assertEqual(data["sessions"], {"s1": {"date": "2026-08-01", "title": "Grilled the plan"},
                                            "s2": {"date": "2026-08-03", "title": None}})
        self.assertEqual(data["former"], [])   # never renamed

    def test_writes_under_a_former_root_join_the_trail(self):
        """Ticket #6 / ADR-0018: `proj` was `proj-v0`, then `proj-v1`, before
        its current name — presence history says so, and the sessions were
        re-keyed at analysis time. Writes recorded under either former root
        are trail events of `proj` (first touch per file per session, the
        prefix stripped) and the blob names the former names oldest first."""
        self.conn.execute("UPDATE sessions SET folder_identity = 7 WHERE project = 'proj'")
        self.conn.executemany(
            "INSERT INTO project_presence (folder_identity, name, first_seen,"
            " last_seen, present) VALUES (7, ?, ?, ?, ?)",
            [("proj-v1", "2026-07-20T00:00:00Z", "2026-07-30T00:00:00Z", 0),
             ("proj-v0", "2026-07-01T00:00:00Z", "2026-07-19T00:00:00Z", 0),
             ("proj", "2026-08-01T00:00:00Z", "2026-08-05T00:00:00Z", 1)])
        old = str(self.root / "proj-v0")
        self.conn.executemany("INSERT INTO tool_events (session_id, name, at, file_path,"
                              " consumer_type, consumer) VALUES (?,?,?,?,?,?)", [
            ("s2", "Write", "2026-08-03T10:21:00Z", f"{old}/build/y.py", "builtin", "Write"),
            ("s2", "Edit", "2026-08-03T10:22:00Z", f"{old}/build/y.py", "builtin", "Edit"),
            ("s2", "Edit", "2026-08-03T10:23:00Z", f"{self.root}/proj-v1/CONTEXT.md",
             "builtin", "Edit"),
            # a different project's session under the former root: not ours
            ("s3", "Edit", "2026-08-02T10:23:00Z", f"{old}/build/z.py", "builtin", "Edit"),
        ])
        self.conn.commit()
        self.declare(VALID)
        data = how.how_data(self.conn, "proj", self.root)
        self.assertEqual(data["former"], ["proj-v0", "proj-v1"])
        writes = [(e["name"], e["stage"]) for e in data["trail"] if e["kind"] == "write"]
        self.assertEqual(writes, [("docs/adr/0001.md", "Plan"), ("build/x.py", "Build"),
                                  ("build/y.py", "Build"), ("CONTEXT.md", "Plan"),
                                  ("README.md", None)])

    def test_invalid_is_loud_and_raw(self):
        self.declare("---\nstages:\n  - nam: X\n---\n")
        data = how.how_data(self.conn, "proj", self.root)
        self.assertEqual(data["declaration"]["state"], "invalid")
        self.assertIn("line 3", data["declaration"]["error"])
        self.assertEqual(len(data["trail"]), 8)
        self.assertEqual(data["summary"], [])

    def test_valid_buckets_and_checks(self):
        self.declare(VALID)
        data = how.how_data(self.conn, "proj", self.root)
        self.assertEqual(data["declaration"]["state"], "valid")
        self.assertEqual([e["stage"] for e in data["trail"]],
                         [None, "Plan", "Plan", "Plan", "Build", "Build", None, None])
        self.assertEqual(data["summary"], [
            {"name": "Plan", "count": 3, "first_seen": "2026-08-01T10:00:00Z",
             "last_seen": "2026-08-01T10:10:00Z"},
            {"name": "Build", "count": 2, "first_seen": "2026-08-03T10:00:00Z",
             "last_seen": "2026-08-03T10:20:00Z"},
            {"name": "Release", "count": 0, "first_seen": None, "last_seen": None}])
        # /clear is a session boundary (#70): set aside, stated, not listed;
        # wayfinder is declared under Plan above, so the declaration wins
        self.assertEqual(data["boundaries"], {"/clear": 1})
        self.assertEqual(data["off_script"], [
            {"kind": "skill", "name": "ponytail:ponytail-review", "count": 1,
             "first_seen": "2026-08-03T10:30:00Z", "last_seen": "2026-08-03T10:30:00Z"},
            {"kind": "write", "name": "README.md", "count": 1,
             "first_seen": "2026-08-03T10:40:00Z", "last_seen": "2026-08-03T10:40:00Z"}])

    def test_unknown_project_is_empty_not_error(self):
        data = how.how_data(self.conn, "nope", self.root)
        self.assertEqual(data["trail"], [])
        self.assertEqual(data["declaration"]["state"], "absent")

class RunLedger(unittest.TestCase):
    """Phase runs (ticket #64): ≥3 fold, majority titling, first-appearance
    title order. The five frozen eval fixtures were reproduced byte-for-byte
    by run_ledger over the live DB when this landed (ticket #68) — a claim
    about that moment only: #74 moved run boundaries to the operator's local
    day, so the fixtures no longer re-derive byte-for-byte from live data.
    They are a frozen set, not a live projection, and `eval/` is unaffected."""
    def ev(self, at, sid, stage):
        return {"at": f"2026-08-{at:02d}T10:00:00Z", "session_id": sid, "stage": stage,
                "kind": "skill", "name": "x"}

    def test_short_band_folds_back_and_majority_titles(self):
        trail = ([self.ev(1, "a", "Plan")] * 3 + [self.ev(2, "b", "Build")] * 2
                 + [self.ev(3, "b", "Plan")] * 1 + [self.ev(4, "c", "Build")] * 3
                 + [self.ev(5, "d", None)])
        sessions = {"a": {"date": "2026-08-01", "title": "A"},
                    "b": {"date": "2026-08-02", "title": "B"},
                    "c": {"date": "2026-08-04", "title": None}}
        runs = how.run_ledger(trail, sessions)
        # the 2-event Build band folds into Plan; b's 3 events all sit there
        self.assertEqual([(r["stage"], r["start"], r["end"], r["titles"]) for r in runs],
                         [("Plan", "2026-08-01", "2026-08-03", ["A", "B"]),
                          ("Build", "2026-08-04", "2026-08-04", [])])

    def test_first_band_always_opens_a_run_and_ties_go_newest(self):
        trail = [self.ev(1, "s", "Ideate")] * 2 + [self.ev(2, "s", "Plan")] * 3 \
            + [self.ev(3, "s", "Build")] * 3
        runs = how.run_ledger(trail, {"s": {"date": None, "title": "S"}})
        self.assertEqual([r["stage"] for r in runs], ["Ideate", "Plan", "Build"])
        self.assertEqual([r["titles"] for r in runs], [[], [], ["S"]])

    def test_run_boundaries_follow_the_local_clock(self):
        """Ticket #74 / ADR-0014: a run's dates are the operator's days. An
        evening event stored 2026-08-03T01:00Z closes the run on 08-02."""
        trail = ([self.ev(1, "a", "Plan")] * 3
                 + [{"at": "2026-08-03T01:00:00Z", "session_id": "a",
                     "stage": "Plan", "kind": "skill", "name": "x"}])
        runs = how.run_ledger(trail, {"a": {"date": "2026-08-01", "title": "A"}})
        self.assertEqual((runs[0]["start"], runs[0]["end"]),
                         ("2026-08-01", "2026-08-02"))

    def test_unbucketed_trail_gives_no_runs(self):
        self.assertEqual(how.run_ledger([self.ev(1, "a", None)], {}), [])


class Narrative(unittest.TestCase):
    """how.narrative (ticket #81): the reader beside the writer gate, judged
    stale on the same key triple refresh_narratives writes against."""
    FACTS = '{"Built": ["x"], "Reversed": [], "Now": ["y"]}'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.conn = fixture(self.root)
        d = self.root / "proj" / ".claude"
        d.mkdir(parents=True)
        (d / "my-process.md").write_text(VALID)
        self.d = how.how_data(self.conn, "proj", self.root)
        self.assertTrue(self.d["runs"])   # the fixture must yield runs

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def store(self, h, pv=analyze.STATUS_VERSION, model=analyze.MODEL):
        self.conn.execute(
            "INSERT OR REPLACE INTO status_narrative (project, ledger_hash,"
            " narrative, prompt_version, model, generated_at)"
            " VALUES ('proj', ?, ?, ?, ?, '2026-08-05T12:00:00Z')",
            (h, self.FACTS, pv, model))
        self.conn.commit()

    def test_none_when_nothing_stored(self):
        self.assertIsNone(how.narrative(self.conn, "proj", self.d))

    def test_current_when_all_three_keys_match(self):
        self.store(how.ledger_hash(self.d))
        n = how.narrative(self.conn, "proj", self.d)
        self.assertEqual(n, {"facts": {"Built": ["x"], "Reversed": [], "Now": ["y"]},
                             "written_day": "2026-08-05",
                             "model": analyze.MODEL, "stale": False})

    def test_stale_on_any_of_the_three_keys(self):
        h = how.ledger_hash(self.d)
        for kw in ({"h": "oldhash"}, {"h": h, "pv": "status-v0"},
                   {"h": h, "model": "other-model"}):
            self.store(**kw)
            self.assertTrue(how.narrative(self.conn, "proj", self.d)["stale"], kw)

    def test_never_stale_without_runs(self):
        self.store("oldhash")
        n = how.narrative(self.conn, "proj", {**self.d, "runs": []})
        self.assertFalse(n["stale"])

    def test_ledger_hash_ignores_the_project_name(self):
        """ADR-0018: a rename re-keys the stored row; the hash is over the
        runs, so the narrative is still current under the new name."""
        self.assertEqual(how.ledger_hash(self.d),
                         how.ledger_hash({**self.d, "project": "renamed"}))
        changed = [{**self.d["runs"][0], "titles": ["changed"]}, *self.d["runs"][1:]]
        self.assertNotEqual(how.ledger_hash(self.d),
                            how.ledger_hash({**self.d, "runs": changed}))


if __name__ == "__main__":
    unittest.main()
