"""scaffold.py guardrails --render and doctor's guardrails row: setup writes every guardrail itself (3.12.0 smoke C3)."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
DOCTOR = os.path.join(PLUGIN_ROOT, "scripts", "doctor.py")


class GuardrailsRenderTest(ProjectTestCase):
    def run_py(self, script, *args):
        p = subprocess.run([sys.executable, script, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace", env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT})
        self.assertNotIn("Traceback", p.stderr)
        return p.returncode, json.loads(p.stdout)

    def set_up(self, complete=True):
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.run_py(SCAFFOLD, "init", "--kind", "greenfield", "--docs-dir", "docs/sdlc", "--host", "claude-code")
        if complete:
            self.run_py(SCAFFOLD, "step-done", "finalize", "--complete")

    def listed(self):
        return [g["dest"] for g in self.run_py(SCAFFOLD, "guardrails")[1]["guardrails"]]

    def test_render_writes_every_guardrail_and_keeps_edited_ones(self):
        self.set_up(complete=False)
        dests = self.listed()
        self.assertGreater(len(dests), 5)
        code, out = self.run_py(SCAFFOLD, "guardrails", "--render")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(out["rendered"]), sorted(dests))
        with open(self.path(".sdlc/scaffold.lock.json"), encoding="utf-8") as f:
            lock = json.load(f)
        for d in dests:
            self.assertTrue(os.path.isfile(self.path(d)), d)
            self.assertEqual(lock["files"][d]["class"], "seeded")
        with open(self.path(dests[0]), "a", encoding="utf-8") as f:
            f.write("\nTeam note.\n")
        code, out = self.run_py(SCAFFOLD, "guardrails", "--render")
        self.assertIn(dests[0], out["kept"])
        with open(self.path(dests[0]), encoding="utf-8") as f:
            self.assertIn("Team note.", f.read())
        self.assertEqual(self.run_py(SCAFFOLD, "guardrails")[1].get("rendered"), None)  # plain: writes nothing

    def test_doctor_warns_when_guardrails_were_never_written(self):
        self.set_up()
        checks = {c["check"]: c for c in self.run_py(DOCTOR)[1]["checks"]}
        row = checks.get("guardrails")
        self.assertIsNotNone(row, sorted(checks))
        self.assertEqual(row["status"], "warn")
        self.assertIn(str(len(self.listed())), row["detail"])
        self.assertIn("guardrails --render", row["fix"])
        self.run_py(SCAFFOLD, "guardrails", "--render")
        for x in ("sdlc", "sdlc-code-style", "sdlc-tests", "sdlc-migrations", "sdlc-sensitive", "sdlc-ci", "sdlc-ui"):
            self.run_py(SCAFFOLD, "render", f"templates/project/rules/{x[5:] or 'sdlc'}.md", f".claude/rules/{x}.md")
        checks = {c["check"]: c for c in self.run_py(DOCTOR)[1]["checks"]}
        self.assertEqual(checks["guardrails"]["status"], "ok", checks["guardrails"])


if __name__ == "__main__":
    unittest.main()
