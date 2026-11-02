"""The plugin's own files: checks on the shipped tree, not on a fixture."""
import glob
import os
import unittest

from helpers import PLUGIN_ROOT

# Claude Code truncates a skill at 20,000 characters after compaction, so one that long loses its tail (Superpowers
# fails CI at the same size)
SKILL_LIMIT = 20000


class SkillSizeTest(unittest.TestCase):
    def test_no_skill_reaches_the_truncation_limit(self):
        skills = glob.glob(os.path.join(PLUGIN_ROOT, "**", "SKILL.md"), recursive=True)
        self.assertTrue(skills)
        for path in skills:
            with open(path, encoding="utf-8") as f:  # universal newlines: a CRLF checkout counts one per line break
                size = len(f.read())
            self.assertLess(size, SKILL_LIMIT, f"{os.path.relpath(path, PLUGIN_ROOT)} is {size} characters")


if __name__ == "__main__":
    unittest.main()
