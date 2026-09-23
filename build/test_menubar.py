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
        self.assertTrue(menubar.render(False, []).startswith("⚪\n"))
        self.assertTrue(menubar.render(True, []).startswith("🔵\n"))
        info = [(1, "informational", 2, "assistant.slug", "2.1.274")]
        self.assertTrue(menubar.render(True, info).startswith("🔵 1\n"))
        prob = info + [(2, "problem", 1, "message.usage", "2.1.275")]
        self.assertTrue(menubar.render(True, prob).startswith("🔴 2\n"))

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
