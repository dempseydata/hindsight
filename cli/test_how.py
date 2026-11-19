"""Tests for the how-view data pipeline (ticket #63, ADR-0010/0011):
declaration parsing with its three states, process resolution (#94,
ADR-0032), marker matching, trail assembly and the dumb checker — over a
fixture DB built from the real schema."""
import os
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

import analyze
import how
import test_helpers  # noqa: F401 — the house-master guard (#94)

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


    def test_unreadable_file_is_invalid_not_absent(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "local-process.md").mkdir()  # a dir: exists, unreadable
            state, _, err, _ = how.resolve_declaration(d)
            self.assertEqual(state, "invalid")
            self.assertIn("cannot read", err)


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
    conn.executemany("INSERT INTO audit (session_id, project, skip, markdown,"
                     " prompt_version, model) VALUES (?, 'proj', ?, ?, 'v', 'm')",
                     [("s1", 0, "### Grilled the plan\n- **Did:** x"),
                      ("s2", 1, None)])
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
        d = self.root / "proj"
        d.mkdir(parents=True, exist_ok=True)
        (d / "local-process.md").write_text(text)

    def test_raw_trail_when_absent(self):
        self.declare("none\n")
        data = how.how_data(self.conn, "proj", self.root)
        self.assertEqual(data["declaration"], {"state": "absent", "error": None, "stages": [],
                                               "source": "local-process.md"})
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
        # the two trailing off-script events fold into Build (#17); the
        # stated-process summary above is untouched by them
        self.assertEqual([(r["stage"], r["end"]) for r in data["runs"]], [("Plan", "2026-08-03")])
        self.assertEqual(data["run_detail"][0]["minor"], {"Build": 2, how.OFF_SCRIPT: 2})
        self.assertEqual(data["off_script"], [
            {"kind": "skill", "name": "ponytail:ponytail-review", "count": 1,
             "first_seen": "2026-08-03T10:30:00Z", "last_seen": "2026-08-03T10:30:00Z"},
            {"kind": "write", "name": "README.md", "count": 1,
             "first_seen": "2026-08-03T10:40:00Z", "last_seen": "2026-08-03T10:40:00Z"}])

    def test_unknown_project_is_empty_not_error(self):
        data = how.how_data(self.conn, "nope", self.root)
        self.assertEqual(data["trail"], [])
        # no folder, so no local file: the (here unresolvable) master decides
        self.assertEqual(data["declaration"]["state"], "invalid")


class Resolution(unittest.TestCase):
    """Process resolution (#94, ADR-0032), through how_data: a root
    local-process.md decides; otherwise the house master, found through the
    pointer under `## Process` in an injected user-level CLAUDE.md."""
    MASTER = VALID.replace("build/", "cli/")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.conn = fixture(self.root)
        (self.root / "proj").mkdir()
        self.claude_md = self.root / "home" / ".claude" / "CLAUDE.md"
        self.claude_md.parent.mkdir(parents=True)
        self.master = self.root / "standards" / "my-process.md"
        self.master.parent.mkdir()

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def point(self, pointer=None, master=MASTER):
        pointer = pointer or f"`{self.master}`"
        # a my-process.md token outside `## Process` is never the pointer
        self.claude_md.write_text(
            "# Me\n\n## Notes\nSee `elsewhere/my-process.md`.\n\n"
            f"## Process\nThe master is {pointer}; also `.claude/my-process.md`.\n\n"
            "## Constraints\n- none\n")
        if master is not None:
            self.master.write_text(master)

    def dec(self):
        return how.how_data(self.conn, "proj", self.root, claude_md=self.claude_md)["declaration"]

    def local(self, text):
        (self.root / "proj" / "local-process.md").write_text(text)

    def test_local_file_states(self):
        self.point()   # a valid master, which a local file always overrides
        for text, state in (("  none\n", "absent"), (VALID, "valid"),
                            ("", "invalid"), ("# prose, no fence\n", "invalid"),
                            ("---\nstages:\n  - nam: X\n---\n", "invalid")):
            self.local(text)
            d = self.dec()
            self.assertEqual((d["state"], d["source"]), (state, "local-process.md"), text)
            self.assertEqual(d["error"] is None, state != "invalid", text)

    def test_master_resolves_through_the_pointer(self):
        self.point()
        d = self.dec()
        self.assertEqual((d["state"], d["error"]), ("valid", None))
        self.assertEqual(d["source"], f"house master {self.master}")
        self.assertEqual(d["stages"][1]["paths"], ["cli/"])

    def test_pointer_expands_home(self):
        self.point(pointer="`~/standards/my-process.md`")
        with unittest.mock.patch.dict(os.environ, {"HOME": str(self.root)}):
            d = self.dec()
        self.assertEqual((d["state"], d["source"]), ("valid", f"house master {self.master}"))

    def test_claude_my_process_is_never_read(self):
        (self.root / "proj" / ".claude").mkdir()
        (self.root / "proj" / ".claude" / "my-process.md").write_text(VALID)
        self.assertEqual(self.dec()["state"], "invalid")   # no CLAUDE.md: master unresolvable

    def test_unresolvable_master_is_invalid_with_path_and_reason(self):
        cases = [
            (lambda: None, str(self.claude_md), "cannot read"),
            (lambda: self.claude_md.write_text("# Me\n## Work\n`x/my-process.md`\n"),
             str(self.claude_md), "no `## Process` heading"),
            (lambda: self.claude_md.write_text("# Me\n## Process\nno pointer\n## Next\n"
                                               "`x/my-process.md`\n"),
             str(self.claude_md), "pointer"),
            (lambda: self.point(master=None), str(self.master), "cannot read"),
            (lambda: self.point(master="# prose only\n"), str(self.master), "fence"),
            (lambda: self.point(master="---\nstages:\n  - nam: X\n---\n"),
             str(self.master), "line 3"),
        ]
        for i, (arrange, path, reason) in enumerate(cases):
            arrange()
            d = self.dec()
            self.assertEqual((d["state"], d["stages"]), ("invalid", []), i)
            self.assertIn(path, d["error"], i)
            self.assertIn(reason, d["error"], i)
            self.assertTrue(d["source"].startswith("house master"), i)
            self.claude_md.unlink(missing_ok=True)
            self.master.unlink(missing_ok=True)

    def test_three_layout_marker_matches_only_the_existing_path(self):
        """One master serves every house layout (ADR-0032): its Ideate paths
        list all three; this project's writes sit under the born-public one,
        and an unanchored look-alike never matches."""
        self.point(master="---\nstages:\n  - name: Ideate\n"
                          "    paths: [ideation/, background/ideation/, docs/ideation/]\n---\n")
        p = self.root / "proj"
        self.conn.executemany(
            "INSERT INTO tool_events (session_id, name, at, file_path, consumer_type,"
            " consumer) VALUES ('s1', 'Write', ?, ?, 'builtin', 'Write')",
            [("2026-08-01T11:00:00Z", f"{p}/background/ideation/framing.md"),
             ("2026-08-01T11:01:00Z", f"{p}/notes/ideation/x.md")])
        data = how.how_data(self.conn, "proj", self.root, claude_md=self.claude_md)
        stages = {e["name"]: e["stage"] for e in data["trail"] if e["kind"] == "write"}
        self.assertEqual(stages["background/ideation/framing.md"], "Ideate")
        self.assertIsNone(stages["notes/ideation/x.md"])


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
        # the 2-event Build band folds into Plan; b's 3 events all sit there;
        # the lone off-script event folds into Build like any short band (#17)
        self.assertEqual([(r["stage"], r["start"], r["end"], r["titles"]) for r in runs],
                         [("Plan", "2026-08-01", "2026-08-03", ["A", "B"]),
                          ("Build", "2026-08-04", "2026-08-05", [])])

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

    def test_unbucketed_trail_forms_an_off_script_run(self):
        runs = how.run_ledger([self.ev(1, "a", None)], {})
        self.assertEqual([(r["stage"], r["start"]) for r in runs], [(how.OFF_SCRIPT, "2026-08-01")])

    def test_off_script_events_form_runs_of_their_own(self):
        """Issue #17: three consecutive off-script writes under .claude/ are a
        run — the off-script label, the right span, the used names — and a
        short off-script band between staged runs still folds back."""
        def w(at, name):
            return {**self.ev(at, "u", None), "kind": "write", "name": name}
        upkeep = [w(8, ".claude/skills/a/SKILL.md"), w(9, ".claude/agents/b.md"),
                  w(10, ".claude/my-process.md")]
        trail = ([self.ev(1, "a", "Plan")] * 3
                 + [w(2, "README.md"), w(2, "CLAUDE.md")]        # 2: folds into Plan
                 + [self.ev(4, "c", "Build")] * 3
                 + upkeep + [{**self.ev(10, "u", None), "name": "/ponytail"}])
        runs, detail = how.run_ledger(trail, {"u": {"date": None, "title": "Upkeep"}},
                                      detail=True)
        self.assertEqual([(r["stage"], r["start"], r["end"], r["titles"]) for r in runs],
                         [("Plan", "2026-08-01", "2026-08-02", []),
                          ("Build", "2026-08-04", "2026-08-04", []),
                          (how.OFF_SCRIPT, "2026-08-08", "2026-08-10", ["Upkeep"])])
        self.assertEqual(detail[0]["minor"], {how.OFF_SCRIPT: 2})
        self.assertEqual(detail[2]["names"], ["ponytail"])
        self.assertEqual(detail[2]["events"], 4)

    def test_compact_is_a_boundary_never_a_run_event(self):
        """/compact opens a session as /clear does (#17): with it, an
        off-script band of three would form a run; set aside, the two left
        fold into the run before them."""
        trail = ([self.ev(1, "a", "Plan")] * 3
                 + [{**self.ev(2, "a", None), "kind": "command", "name": "/compact"},
                    self.ev(3, "a", None), self.ev(3, "a", None)])
        runs = how.run_ledger(trail, {})
        self.assertEqual([(r["stage"], r["end"]) for r in runs], [("Plan", "2026-08-03")])
        self.assertTrue(how.is_boundary({"kind": "command", "name": "/compact"}))


class Narrative(unittest.TestCase):
    """how.narrative (ticket #81): the reader beside the writer gate, judged
    stale on the same key triple refresh_narratives writes against."""
    FACTS = '{"Built": ["x"], "Reversed": [], "Now": ["y"]}'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.conn = fixture(self.root)
        d = self.root / "proj"
        d.mkdir(parents=True)
        (d / "local-process.md").write_text(VALID)
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
                             "model": analyze.MODEL,
                             "prompt_version": analyze.STATUS_VERSION, "stale": False})

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

    def test_adr_status_edit_rekeys_the_narrative(self):
        """#96, ADR-0035 §3: the ADR headers are the narrative's second input,
        so editing a status line makes the stored card stale."""
        adr = self.root / "proj" / "docs" / "adr" / "0001-x.md"
        adr.parent.mkdir(parents=True)
        adr.write_text("# ADR-0001: X\n\n**Date:** 2026-08-01 · **Status:** accepted\n")
        d = how.how_data(self.conn, "proj", self.root)
        self.assertEqual([a["number"] for a in how.ledger(d)["adrs"]], ["ADR-0001"])
        self.store(how.ledger_hash(d))
        adr.write_text("# ADR-0001: X\n\n**Date:** 2026-08-01 · **Status:** superseded by ADR-0002\n")
        self.assertTrue(how.narrative(self.conn, "proj",
                                      how.how_data(self.conn, "proj", self.root))["stale"])




HINDSIGHT_ADR = """# ADR-0033: Capture runs on `Stop`

**Date:** 2026-11-15 · **Status:** accepted, amended by [ADR-0039](0039-x.md) · **Supersedes:** ADR-0005 · **Amends:** ADR-0001, ADR-0020 · **Decides:** issue #68

## Context
"""
FRONTMATTER_ADR = """---
status: accepted, superseded in part by ADR-0011
---

# The skills install by symlink or plugin

Body.
"""


class AdrHeaders(unittest.TestCase):
    """ADR-0035 §3: the status-v2 input's second half, read mechanically —
    number, date (header, else the commit that added the file), title,
    status line and touches/amends, from <root>/docs/adr only (#95)."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "docs" / "adr").mkdir(parents=True)

    def write(self, name, text):
        (self.root / "docs" / "adr" / name).write_text(text)

    def git(self, *args):
        import subprocess
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t",
                        *args], check=True, capture_output=True,
                       env={**os.environ, "GIT_AUTHOR_DATE": "2026-09-26T12:00:00",
                            "GIT_COMMITTER_DATE": "2026-09-26T12:00:00"})

    def test_bold_header_line(self):
        self.write("0033-capture-on-stop.md", HINDSIGHT_ADR)
        self.assertEqual(how.adr_headers(self.root), [{
            "number": "ADR-0033", "date": "2026-11-15", "title": "Capture runs on `Stop`",
            "status": "accepted, amended by ADR-0039",
            "touches": "Supersedes: ADR-0005 · Amends: ADR-0001, ADR-0020"}])

    def test_frontmatter_status_and_date_from_the_adding_commit(self):
        self.write("0010-the-skills-install.md", FRONTMATTER_ADR)
        self.git("init", "-q"); self.git("add", "."); self.git("commit", "-qm", "add")
        self.assertEqual(how.adr_headers(self.root), [{
            "number": "ADR-0010", "date": "2026-09-26",
            "title": "The skills install by symlink or plugin",
            "status": "accepted, superseded in part by ADR-0011", "touches": ""}])

    def test_ordered_by_number_other_files_and_folders_ignored(self):
        self.write("0002-b.md", "# ADR-0002: B\n\n**Date:** 2026-08-02 · **Status:** accepted\n")
        self.write("0001-a.md", "# ADR-0001: A\n\n**Date:** 2026-08-01 · **Status:** accepted\n")
        self.write("README.md", "# not an ADR\n")
        self.assertEqual([a["number"] for a in how.adr_headers(self.root)], ["ADR-0001", "ADR-0002"])
        other = Path(tempfile.mkdtemp())  # thisisme's shape: ADRs only under build/
        (other / "build" / "docs" / "adr").mkdir(parents=True)
        (other / "build" / "docs" / "adr" / "0001-a.md").write_text("# A\n")
        self.assertEqual(how.adr_headers(other), [])


class StatusV2Cases(unittest.TestCase):
    """The frozen status-v2 set (#73, #95): five cases, the dated cut leaks
    nothing later, and a stub card fails the floors before any prompt."""

    def setUp(self):
        import json
        import score
        self.score = score
        self.cases = json.loads((Path(__file__).resolve().parent.parent / "eval"
                                 / "status_v2_cases.json").read_text())["cases"]

    def test_the_five_cases(self):
        self.assertEqual(sorted(self.cases), sorted([
            "hindsight@live", "hindsight@2026-09-15", "explainer@live",
            "thisisme@live", "skills-playground@live"]))
        self.assertEqual([c for c, v in self.cases.items() if not v["adrs"]],
                         ["thisisme@live", "skills-playground@live"])

    def test_the_cut_leaks_no_later_adr(self):
        import json
        c = self.cases["hindsight@2026-09-15"]
        sent = json.dumps({k: c[k] for k in ("runs", "adrs")})
        self.assertNotIn("0026", sent)
        self.assertTrue(all(a["date"] <= c["as_of"] for a in c["adrs"]))
        self.assertTrue(all(r["end"] <= c["as_of"] for r in c["runs"]))
        self.assertEqual(c["adrs"][-1]["number"], "ADR-0025")

    def test_a_stub_card_fails_every_case(self):
        for cid, c in self.cases.items():
            for stub in ({"Standing": [], "Superseded": [], "Now": []},
                         {"Standing": ["x"] * 3, "Superseded": [], "Now": ["x"]}):
                with self.subTest(cid):
                    self.assertFalse(self.score.score_v2(c, stub)[0]["pass"])

if __name__ == "__main__":
    unittest.main()
