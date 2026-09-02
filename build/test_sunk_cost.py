"""Seam tests for the sunk-cost scan (ticket #24 — build/sunk_cost.py),
driven through the analysis-run entrypoint: CLAUDE.md chain / skills / MCP
itemised per project, plugin registry keyed by install path, idempotent
rescan.
"""
import json
import tempfile
import unittest
from pathlib import Path

from analyze import run_analysis
from test_helpers import DbHelpers, StubRunner


class SunkCostTest(DbHelpers, unittest.TestCase):
    """Session-start sunk-cost scan (ticket #24), driven through the
    analysis-run entrypoint: CLAUDE.md chain / skills / MCP itemised per
    project, plugin registry keyed by install path, idempotent rescan."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.root.mkdir()
        self.db = base / "hindsight.db"
        self.work = base / "analysis"
        self.claude = base / "claude"
        self.claude.mkdir()
        self.repos = base / "repos"
        self.repos.mkdir()

    def run_pipeline(self):
        run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                      model_runner=StubRunner([]),
                      claude_dir=self.claude, projects_dir=self.repos)

    def sunk_rows(self, where="", params=()):
        return self.rows("SELECT project, category, plugin, name, path, tokens"
                         f" FROM sunk_cost {where} ORDER BY category, name", params)

    def write_skill(self, root, name, desc):
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {desc}\n---\n\nSkill body here.\n")
        return desc

    def install_plugin(self, key, skills, records=1):
        """One plugin in the registry: an install path holding `skills`,
        listed under `records` identical install records (the ccwhere
        double-count shape)."""
        install = Path(self.tmp.name) / "cache" / key.split("@")[0] / "1.0.0"
        for name, desc in skills.items():
            self.write_skill(install / "skills", name, desc)
        pf = self.claude / "plugins" / "installed_plugins.json"
        plugins = (json.loads(pf.read_text())["plugins"] if pf.exists() else {})
        plugins[key] = [{"scope": "user", "installPath": str(install),
                         "version": "1.0.0"}] * records
        pf.parent.mkdir(exist_ok=True)
        pf.write_text(json.dumps({"version": 2, "plugins": plugins}))

    def enable_plugins(self, settings_path, keys):
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(
            {"enabledPlugins": {k: True for k in keys}}))

    def test_scan_itemises_chain_skills_and_mcp_per_project(self):
        (self.claude / "CLAUDE.md").write_text("user instructions here")
        (self.repos / "CLAUDE.md").write_text("workspace instructions")
        proj = self.repos / "proj"
        proj.mkdir()
        (proj / "CLAUDE.md").write_text("project instructions, longer text")
        (proj / ".mcp.json").write_text('{"mcpServers": {"srv": {}}}')
        desc = self.write_skill(proj / ".claude" / "skills", "deploy",
                                "Deploys the thing when asked to deploy.")
        self.enable_plugins(self.claude / "settings.json", [])
        self.run_pipeline()

        # a project's full bill: its own rows plus the user-scope floor
        bill = self.sunk_rows("WHERE project=? OR project IS NULL", ("proj",))
        chain = [r for r in bill if r["category"] == "claude-md"]
        self.assertEqual([(r["project"], r["name"]) for r in chain],
                         [(None, "CLAUDE.md"), (None, "CLAUDE.md"),
                          ("proj", "CLAUDE.md")])
        for r in chain:
            self.assertEqual(r["tokens"], Path(r["path"]).stat().st_size // 4)

        mcp = [r for r in bill if r["category"] == "mcp"]
        self.assertEqual([(r["project"], r["name"], r["tokens"]) for r in mcp],
                         [("proj", ".mcp.json",
                           (proj / ".mcp.json").stat().st_size // 4)])

        skills = [r for r in bill if r["category"] == "skill"]
        self.assertEqual([(r["project"], r["name"], r["tokens"]) for r in skills],
                         [("proj", "deploy", (len(desc) + 40) // 4)])

    def test_skill_via_two_install_records_counted_once(self):
        self.install_plugin("pm@skills", {"write-prd": "Writes a PRD."},
                            records=2)
        self.enable_plugins(self.claude / "settings.json", ["pm@skills"])
        self.run_pipeline()

        skills = self.sunk_rows("WHERE category='skill'")
        self.assertEqual([(r["name"], r["plugin"], r["project"]) for r in skills],
                         [("write-prd", "pm@skills", None)])

    def test_plugins_are_a_grouping_level_per_scope(self):
        self.install_plugin("user-plug@a", {"alpha": "Does alpha."})
        self.install_plugin("proj-plug@b", {"beta": "Does beta."})
        self.enable_plugins(self.claude / "settings.json", ["user-plug@a"])
        proj = self.repos / "proj"
        self.enable_plugins(proj / ".claude" / "settings.json", ["proj-plug@b"])
        self.write_skill(self.claude / "skills", "bare", "A plugin-less skill.")
        self.run_pipeline()

        by_plugin = {r["plugin"]: r for r in self.sunk_rows("WHERE category='skill'")}
        self.assertEqual(set(by_plugin), {None, "user-plug@a", "proj-plug@b"})
        self.assertIsNone(by_plugin["user-plug@a"]["project"])  # user scope
        self.assertEqual(by_plugin["proj-plug@b"]["project"], "proj")
        self.assertIsNone(by_plugin[None]["plugin"])

    def test_claude_md_imports_expand_into_rows(self):
        proj = self.repos / "proj"
        (proj / ".claude").mkdir(parents=True)
        (proj / "CLAUDE.md").write_text("# proj\n@.claude/my-process.md\n")
        (proj / ".claude" / "my-process.md").write_text("process " * 100)
        self.run_pipeline()

        chain = self.sunk_rows("WHERE category='claude-md' AND project=?",
                               ("proj",))
        self.assertEqual({r["name"] for r in chain},
                         {"CLAUDE.md", "my-process.md"})
        imported = next(r for r in chain if r["name"] == "my-process.md")
        self.assertEqual(imported["tokens"],
                         (proj / ".claude" / "my-process.md").stat().st_size // 4)

    def test_agents_md_imported_by_claude_md_counted_once(self):
        proj = self.repos / "proj"
        proj.mkdir()
        (proj / "CLAUDE.md").write_text("@AGENTS.md\n")
        (proj / "AGENTS.md").write_text("agent instructions")
        self.run_pipeline()
        chain = self.sunk_rows("WHERE category='claude-md' AND project=?",
                               ("proj",))
        self.assertEqual(sorted(r["name"] for r in chain),
                         ["AGENTS.md", "CLAUDE.md"])

    def test_commands_counted_like_skills(self):
        install = Path(self.tmp.name) / "cache" / "pm" / "1.0.0"
        (install / "commands").mkdir(parents=True)
        (install / "commands" / "write-prd.md").write_text(
            "---\ndescription: Writes a PRD.\n---\n\nDo the thing.\n")
        self.install_plugin("pm@skills", {})  # registers install path
        self.enable_plugins(self.claude / "settings.json", ["pm@skills"])
        proj = self.repos / "proj"
        (proj / ".claude" / "commands").mkdir(parents=True)
        (proj / ".claude" / "commands" / "ship.md").write_text(
            "---\ndescription: Ships it.\n---\n")
        self.run_pipeline()

        cmds = {r["name"]: r for r in self.sunk_rows("WHERE category='command'")}
        self.assertEqual(set(cmds), {"write-prd", "ship"})
        self.assertEqual(cmds["write-prd"]["plugin"], "pm@skills")
        self.assertEqual(cmds["write-prd"]["tokens"],
                         (len("Writes a PRD.") + 40) // 4)
        self.assertEqual(cmds["ship"]["project"], "proj")

    def test_plugin_skills_outside_skills_dir_not_counted(self):
        # a vendored mirror (.openclaw/skills/...) must not double the count
        self.install_plugin("pm@skills", {"write-prd": "Writes a PRD."})
        install = Path(self.tmp.name) / "cache" / "pm" / "1.0.0"
        mirror = install / ".openclaw" / "skills" / "write-prd"
        mirror.mkdir(parents=True)
        (mirror / "SKILL.md").write_text(
            "---\nname: write-prd\ndescription: Writes a PRD.\n---\n")
        self.enable_plugins(self.claude / "settings.json", ["pm@skills"])
        self.run_pipeline()
        self.assertEqual(len(self.sunk_rows("WHERE category='skill'")), 1)

    def test_user_mcp_read_from_claude_json(self):
        servers = {"tavily": {"command": "npx", "args": ["tavily-mcp"]}}
        (Path(self.tmp.name) / "claude.json").write_text(json.dumps(
            {"mcpServers": servers,
             "projects": {str(self.repos / "proj"):
                          {"mcpServers": {"local-srv": {}}}}}))
        (self.repos / "proj").mkdir()
        self.run_pipeline()

        mcp = self.sunk_rows("WHERE category='mcp'")
        by_scope = {r["project"]: r for r in mcp}
        self.assertEqual(set(by_scope), {None, "proj"})
        self.assertEqual(by_scope[None]["tokens"],
                         len(json.dumps(servers)) // 4)

    def test_install_path_shared_across_scopes_billed_once(self):
        # user-enabled key and project-enabled key pointing at one path:
        # the project bill (project rows + user floor) must not pay twice
        self.install_plugin("dual@a", {"alpha": "Does alpha."})
        install = str(Path(self.tmp.name) / "cache" / "dual" / "1.0.0")
        pf = self.claude / "plugins" / "installed_plugins.json"
        plugins = json.loads(pf.read_text())["plugins"]
        plugins["dual@b"] = [{"scope": "project", "installPath": install,
                              "version": "1.0.0"}]
        pf.write_text(json.dumps({"version": 2, "plugins": plugins}))
        self.enable_plugins(self.claude / "settings.json", ["dual@a"])
        proj = self.repos / "proj"
        self.enable_plugins(proj / ".claude" / "settings.json", ["dual@b"])
        self.run_pipeline()

        skills = self.sunk_rows("WHERE category='skill' AND (project=?"
                                " OR project IS NULL)", ("proj",))
        self.assertEqual([(r["name"], r["project"]) for r in skills],
                         [("alpha", None)])

    def test_corrupt_settings_does_not_flip_all_plugins_to_user_scope(self):
        self.install_plugin("pm@skills", {"write-prd": "Writes a PRD."})
        (self.claude / "settings.json").write_text('{"enabledPlugins": {,}')
        self.run_pipeline()
        self.assertEqual(self.sunk_rows("WHERE category='skill'"), [])

    def test_rescan_is_idempotent(self):
        (self.claude / "CLAUDE.md").write_text("user instructions")
        self.install_plugin("pm@skills", {"write-prd": "Writes a PRD."})
        self.enable_plugins(self.claude / "settings.json", ["pm@skills"])
        self.run_pipeline()
        first = self.sunk_rows()
        self.assertTrue(first)
        self.run_pipeline()
        self.assertEqual(self.sunk_rows(), first)


if __name__ == "__main__":
    unittest.main()
