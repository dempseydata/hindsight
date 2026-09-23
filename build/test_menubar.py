"""Menu bar plugin (issue #37): the menu is a pure function of the probe and
the open breakage rows; the reader never mistakes an unreadable table for a
clean one."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

import menubar


class RenderTest(unittest.TestCase):
    def test_icon_states(self):
        both = dict(serve_up=True)
        self.assertTrue(menubar.render(False, [], **both).startswith("⚪\n"))
        self.assertTrue(menubar.render(True, [], serve_up=False).startswith("⚪\n"))
        self.assertTrue(menubar.render(True, [], **both).startswith("🔵\n"))
        info = [(1, "informational", 2, "assistant.slug", "2.1.274")]
        self.assertTrue(menubar.render(True, info, **both).startswith("🔵 1\n"))
        self.assertTrue(menubar.render(True, info, serve_up=False).startswith("⚪\n"))
        prob = info + [(2, "problem", 1, "message.usage", "2.1.275")]
        self.assertTrue(menubar.render(True, prob, serve_up=False).startswith("🔴 2\n"))

    def test_menu_lines(self):
        rows = [(7, "problem", 3, None, None)]
        out = menubar.render(True, rows)
        self.assertIn("Stop listener | bash=", out)
        self.assertIn("problem: skipped-record spike under ? | color=red", out)
        self.assertIn("--Acknowledge #7 | bash=", out)
        self.assertIn("param2=acknowledge-breakage param3=7", out)
        self.assertIn("Start listener", menubar.render(False, []))
        self.assertIn("Listener not installed", menubar.render(False, [], plist_installed=False))
        self.assertIn("No open breakages", menubar.render(True, []))
        up = menubar.render(True, [], serve_up=True)
        self.assertIn("Stop views server | bash=", up)
        down = menubar.render(True, [], serve_up=False)
        self.assertIn("Start views server | bash=", down)
        for out in (up, down):   # always there; starts the server itself if needed
            self.assertEqual(out.splitlines()[2].split(" | ")[0], "Open dashboard")
            self.assertIn("param2=open", out)

    def test_unreadable_table_is_shown_not_clean(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "x.db"
            sqlite3.connect(db).execute("CREATE TABLE nope (id)").close()
            rows = menubar.open_breakages(db)
            self.assertIsInstance(rows, str)
            self.assertIn("Breakage rows unreadable", menubar.render(True, rows))
            self.assertEqual(menubar.open_breakages(Path(d) / "absent.db"), [])


if __name__ == "__main__":
    unittest.main()
