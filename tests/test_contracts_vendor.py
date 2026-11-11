"""scripts/contracts/v1: the vendored shared contracts stay byte-identical to their MANIFEST (spec 01, Distribution)."""
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT

VENDORED = os.path.join(PLUGIN_ROOT, "scripts", "contracts", "v1")


class VendoredContractsTest(unittest.TestCase):
    def test_vendored_copy_matches_its_manifest(self):
        p = subprocess.run([sys.executable, os.path.join(VENDORED, "contracts.py"), "vendor-check", VENDORED],
                           capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("matches MANIFEST (contracts 1.", p.stdout)

    def test_vendored_version_is_1_2_0(self):
        p = subprocess.run([sys.executable, os.path.join(VENDORED, "contracts.py"), "vendor-check", VENDORED],
                           capture_output=True, encoding="utf-8", errors="replace")
        self.assertIn("matches MANIFEST (contracts 1.2.0)", p.stdout, p.stdout + p.stderr)

    def test_the_finding_check_prints_on_a_console_that_is_not_utf8(self):
        fixture = os.path.join(VENDORED, "fixtures", "finding", "valid", "SQ-0001-spec-question.json")
        p = subprocess.run([sys.executable, os.path.join(VENDORED, "contracts.py"), "finding", fixture],
                           capture_output=True, encoding="cp1252", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="cp1252"))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("SQ-0001", p.stdout)


if __name__ == "__main__":
    unittest.main()
