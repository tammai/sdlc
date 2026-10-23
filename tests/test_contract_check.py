"""templates/project/ci/contract-check.sh: published contract versions take additions only."""
import os
import subprocess

from helpers import BASH, PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "templates", "project", "ci", "contract-check.sh")
SPEC = "packages/api-contract/v1/openapi.yaml"
# Stands in for oasdiff: logs the revision it was asked about and fails when it holds a breaking change
FAKE_OASDIFF = '#!/usr/bin/env bash\nhead=${@: -1}\necho "$head" >> "$CALLS"\n! grep -q BREAKING "$head"\n'


class ContractCheckTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.write(SPEC, "openapi: 3.1.0\n")
        self.write("packages/api-contract/drafts/README.md", "not a version\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "change")
        self.bin = self.path("_bin")
        self.write("_bin/oasdiff", FAKE_OASDIFF)
        os.chmod(self.path("_bin/oasdiff"), 0o755)

    def git(self, *args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=self.root, check=True,
                       capture_output=True)

    def commit(self, msg):
        self.git("add", "-A", "packages")
        self.git("commit", "-q", "-m", msg)

    def check(self):
        env = dict(os.environ, CALLS=self.path("calls.txt"), PATH=self.bin + os.pathsep + os.environ["PATH"])
        p = subprocess.run([BASH, SCRIPT, "main", "packages/api-contract", "openapi.yaml"], cwd=self.root, env=env,
                           capture_output=True, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr

    def calls(self):
        with open(self.path("calls.txt"), encoding="utf-8") as f:
            return f.read().split()

    def test_additive_edit_and_new_version_pass(self):
        self.write(SPEC, "openapi: 3.1.0\n# new optional field\n")
        self.write("packages/api-contract/v2/openapi.yaml", "openapi: 3.1.0\nBREAKING but new\n")
        self.commit("add")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.calls(), [SPEC])

    def test_breaking_edit_to_published_version_fails(self):
        self.write(SPEC, "openapi: 3.1.0\nBREAKING\n")
        self.commit("break")
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn("packages/api-contract/v1", out)

    def test_removed_published_version_fails(self):
        self.git("rm", "-q", "-r", "packages/api-contract/v1")
        self.git("commit", "-q", "-m", "drop")
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn("v1 was removed", out)
