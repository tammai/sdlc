"""hooks/gitutil.py: the path list the turn's security-review diff is limited to."""
import os
import sys
import unittest

from helpers import HOOKS, ProjectTestCase

sys.path.insert(0, HOOKS)
import gitutil  # noqa: E402


class DiffPathspecTest(ProjectTestCase):
    def test_a_folder_named_dotdot_something_stays_in_the_path_list(self):
        inside = self.path("..hidden/x.py")
        outside = os.path.join(os.path.dirname(self.root), "elsewhere.py")
        self.assertEqual(gitutil._diff_pathspec(self.root, [inside, outside]), ["--", os.path.join("..hidden", "x.py")])
        self.assertEqual(gitutil._diff_pathspec(self.root, [outside]), [])  # only outside: never an unrestricted diff


if __name__ == "__main__":
    unittest.main()
