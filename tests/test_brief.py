"""scripts/brief.py: everything Define reads before the code, in one call."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "brief.py")


class BriefTest(ProjectTestCase):
    def brief(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_prints_defines_inputs_and_cuts_long_files(self):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc", "commands": {"test": "npm test"}}))
        self.write("knowledge/index.md", "# Knowledge\n- decisions/store.md\n")
        self.write("README.md", "".join(f"line {i}\n" for i in range(250)))
        out = self.brief("2026-10-30-m-x")
        for title in ("paths", ".sdlc/config.json", "knowledge/index.md", "README.md", "change template"):
            self.assertIn(f"===== {title} =====", out)
        self.assertIn('"change": "docs/sdlc/changes/2026-10-30-m-x.md"', out)
        self.assertIn("- decisions/store.md", out)
        self.assertIn("===== docs/sdlc/prd.md =====\n(none)", out)  # missing: said, not skipped
        self.assertIn("line 199\n... (50 more lines: read the file for the rest)", out)
        self.assertNotIn("line 200\n", out)
        self.assertIn("## Acceptance tests", out)  # the plugin's change template


if __name__ == "__main__":
    unittest.main()
