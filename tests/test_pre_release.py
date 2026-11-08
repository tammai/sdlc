"""A pre-release (3.5.0-rc.N) sorts before its release, and the release's migrations apply from its first
candidate (ported from 3.5.0-rc.1, 5ecc109)."""
import json
import unittest

import test_scaffold


class PreReleaseTest(test_scaffold.ScaffoldTest):
    def test_a_pre_release_orders_before_its_release_and_its_migrations_stay_pending(self):
        self.migration("3.5.0-keys")
        self.init()
        lock = self.lock()
        lock.update(scaffold_version="3.5.0-rc.1", migrations={"applied": ["3.5.0-keys"], "skipped": {}})
        self.write(".sdlc/scaffold.lock.json", json.dumps(lock))
        self.migration("3.5.0-lock")  # a later candidate's migration, same release
        self.set_plugin_version("3.5.0-rc.2")
        out = self.sc("status")
        self.assertEqual(out["drift"], "behind")
        self.assertEqual(out["pending_migrations"], ["3.5.0-lock"])


def load_tests(loader, tests, pattern):
    """Only the tests this file defines: the fixture class it extends runs in its own file."""
    return unittest.TestSuite(PreReleaseTest(n) for n in loader.getTestCaseNames(PreReleaseTest) if n in vars(PreReleaseTest))


if __name__ == "__main__":
    unittest.main()
