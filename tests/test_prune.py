"""scripts/prune.py: finished, merged features lose their working files; anything else is left alone."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "prune.py")
OLD = "2026-01-01T12:00:00"


class PruneTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        for name, status in (("2026-01-01-month-filter", "done"), ("2026-01-01-login", "active")):
            self.write(f".sdlc/{name}/state.md", f"# {name}\nStatus: {status}\nRisk: low\n")
            for f in ("spec.md", "plan.md", "test-report.md", "qa-report.md", "review.md", "security.md",
                      "checklists/requirements.md"):
                self.write(f".sdlc/{name}/{f}", "x\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "features", env={"GIT_AUTHOR_DATE": OLD, "GIT_COMMITTER_DATE": OLD})

    def git(self, *args, env=None):
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True,
                       env={**os.environ, **(env or {})})

    def prune(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, *args], capture_output=True, encoding="utf-8", errors="replace")
        return p.returncode, json.loads(p.stdout)

    def left(self, name):
        return sorted(os.path.relpath(os.path.join(d, f), self.path(f".sdlc/{name}")).replace(os.sep, "/")
                      for d, _, files in os.walk(self.path(f".sdlc/{name}")) for f in files)

    def test_done_merged_feature_keeps_only_its_record(self):
        code, listed = self.prune("list")
        self.assertEqual([c["feature"] for c in listed["prune"]], ["2026-01-01-month-filter"])
        code, out = self.prune("apply", "2026-01-01-month-filter")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.left("2026-01-01-month-filter"), ["spec.md", "state.md"])

    def test_a_high_risk_feature_keeps_its_review_with_the_security_section(self):
        name = "2026-01-01-month-filter"
        self.write(f".sdlc/{name}/state.md", f"# {name}\nStatus: done\nRisk: high\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "risk", env={"GIT_AUTHOR_DATE": OLD, "GIT_COMMITTER_DATE": OLD})
        code, out = self.prune("apply", name)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.left(name), ["review.md", "security.md", "spec.md", "state.md"])

    def test_done_feature_in_the_new_layout_keeps_only_its_record(self):
        name = "2026-01-02-PROJ-7-export"
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        self.write(f".sdlc/state/{name}.md", f"# {name}\nStatus: done\nRisk: low\n")
        for f in ("spec.md", "plan.md", "plan-B1.md", "plan-B12.md", "test-report.md", "review.md", "checklists/requirements.md"):
            self.write(f"docs/sdlc/intents/{name}/{f}", "x\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "new layout", env={"GIT_AUTHOR_DATE": OLD, "GIT_COMMITTER_DATE": OLD})
        code, out = self.prune("apply", name)
        self.assertEqual(code, 0, out)
        left = sorted(os.listdir(self.path(f"docs/sdlc/intents/{name}")))
        self.assertEqual(left, ["spec.md"])

    def test_active_feature_is_never_pruned(self):
        code, out = self.prune("apply", "--older-than", "0", "2026-01-01-login")
        self.assertEqual(code, 1)
        self.assertEqual(out["refused"][0]["skip"], "not done on main")
        self.assertIn("plan.md", self.left("2026-01-01-login"))

    def test_uncommitted_work_is_never_pruned(self):
        self.write(".sdlc/2026-01-01-month-filter/plan.md", "edited, not committed\n")
        code, out = self.prune("apply", "2026-01-01-month-filter")
        self.assertEqual(code, 1)
        self.assertIn("uncommitted", out["refused"][0]["skip"])
        self.assertIn("plan.md", self.left("2026-01-01-month-filter"))


if __name__ == "__main__":
    unittest.main()
