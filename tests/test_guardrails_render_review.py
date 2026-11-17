"""guardrails --render and doctor's row, review round 1: every written file recorded even when one fails, a deleted
or linked guardrail left alone, only for Claude Code, and doctor's row not fooled by a repo behind the plugin."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
DOCTOR = os.path.join(PLUGIN_ROOT, "scripts", "doctor.py")


class GuardrailsRenderReviewTest(ProjectTestCase):
    def run_py(self, script, *args):
        p = subprocess.run([sys.executable, script, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace", env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT})
        self.assertNotIn("Traceback", p.stderr)
        return p.returncode, json.loads(p.stdout)

    def set_up(self, host="claude-code", complete=True):
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.run_py(SCAFFOLD, "init", "--kind", "greenfield", "--docs-dir", "docs/sdlc", "--host", host)
        if complete:
            self.run_py(SCAFFOLD, "step-done", "finalize", "--complete")

    def lock(self):
        with open(self.path(".sdlc/scaffold.lock.json"), encoding="utf-8") as f:
            return json.load(f)

    def listed(self):
        return [g["dest"] for g in self.run_py(SCAFFOLD, "guardrails")[1]["guardrails"]]

    def test_a_failing_guardrail_leaves_the_others_written_and_recorded(self):
        # F1: a write error part-way (a disk error, a file locked by an editor) doesn't lose what was written before
        self.set_up(complete=False)
        dests = self.listed()
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        real, calls = scaffold.cmd_render, []

        def flaky(p, a):
            calls.append(a.dest)
            if len(calls) == 4:
                raise PermissionError(13, "Permission denied")
            return real(p, a)

        scaffold.cmd_render = flaky
        self.addCleanup(setattr, scaffold, "cmd_render", real)
        self.addCleanup(sys.path.remove, os.path.join(PLUGIN_ROOT, "scripts"))
        old = os.environ.get("CLAUDE_PLUGIN_ROOT")
        os.environ["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT
        self.addCleanup(lambda: os.environ.__setitem__("CLAUDE_PLUGIN_ROOT", old) if old is not None
                        else os.environ.pop("CLAUDE_PLUGIN_ROOT", None))
        # R2-3: a write failure keeps the whole result (every group) and isn't a refusal
        with self.assertRaises(scaffold.CommandsFailed) as failed:
            scaffold.cmd_guardrails(scaffold.Project(self.root), scaffold.argparse.Namespace(render=True))
        result = failed.exception.args[0]
        self.assertIn(dests[3], " ".join(result["failed"]))
        self.assertEqual(len(result["rendered"]), len(dests) - 1)
        lock = self.lock()
        for d in dests[:3] + dests[4:]:
            self.assertIn(d, lock["files"], d)
        # R2-2: any other error from one guardrail is reported the same way, and the rest are still tried
        calls.clear()
        scaffold.cmd_render = lambda p, a: (_ for _ in ()).throw(ValueError("no value for {{x}}")) \
            if a.dest == dests[5] else real(p, a)
        with self.assertRaises(scaffold.CommandsFailed) as failed:
            scaffold.cmd_guardrails(scaffold.Project(self.root), scaffold.argparse.Namespace(render=True))
        self.assertIn(dests[5], " ".join(failed.exception.args[0]["failed"]))
        scaffold.cmd_render = real
        # F2: a guardrail linked out of the project is left and listed; the rest go on
        outside = os.path.realpath(self.root) + "-shared.md"
        with open(outside, "w") as f:
            f.write("shared\n")
        self.addCleanup(os.remove, outside)
        os.remove(self.path(dests[1]))
        try:
            os.symlink(outside, self.path(dests[1]))
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"can't make a symlink here for the outside case: {e}")
        code, out = self.run_py(SCAFFOLD, "guardrails", "--render")
        self.assertEqual(code, 0, out)
        self.assertIn(dests[1], out["outside"])

    def test_a_deleted_guardrail_stays_deleted(self):
        # F5: the user deleted one the plugin wrote; --render doesn't bring it back
        self.set_up(complete=False)
        dests = self.listed()
        self.run_py(SCAFFOLD, "guardrails", "--render")
        os.remove(self.path(dests[0]))
        code, out = self.run_py(SCAFFOLD, "guardrails", "--render")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(self.path(dests[0])))
        self.assertIn(dests[0], out["deleted"])

    def test_a_path_with_a_trailing_carriage_return_still_renders(self):
        # R2-7: the root cause, for every loop that calls render (setup's rules, upgrade's add)
        self.set_up(complete=False)
        code, out = self.run_py(SCAFFOLD, "render", "templates/project/rules/sdlc.md\r", ".claude/rules/sdlc.md\r")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(self.path(".claude/rules/sdlc.md")))
        self.assertIn(".claude/rules/sdlc.md", self.lock()["files"])

    def test_render_on_a_scaffold_behind_the_plugin_points_at_upgrade(self):
        # R2-8: replacing guardrails outside the upgrade flow is refused
        self.set_up()
        lock = self.lock()
        lock["scaffold_version"] = "3.0.0"
        self.write(".sdlc/scaffold.lock.json", json.dumps(lock))
        code, out = self.run_py(SCAFFOLD, "guardrails", "--render")
        self.assertEqual(code, 2, out)
        self.assertIn("/sdlc:upgrade", out["refused"])

    def test_only_for_claude_code(self):
        # F8: a repo set up for another agent gets no .claude/hookify files
        self.set_up(host="codex", complete=False)
        code, out = self.run_py(SCAFFOLD, "guardrails", "--render")
        self.assertEqual(code, 2, out)
        self.assertFalse(os.path.isdir(self.path(".claude/hookify")))

    def test_doctor_points_a_repo_behind_the_plugin_at_upgrade_and_sees_unwritten_rules(self):
        # F3/F7: behind the plugin, unwritten files are upgrade's to add; current, rules count too
        self.set_up()
        self.run_py(SCAFFOLD, "guardrails", "--render")
        lock = self.lock()
        lock["scaffold_version"] = "3.0.0"
        self.write(".sdlc/scaffold.lock.json", json.dumps(lock))
        checks = {c["check"]: c for c in self.run_py(DOCTOR)[1]["checks"]}
        self.assertNotEqual(checks.get("guardrails", {}).get("status"), "warn", checks.get("guardrails"))
        lock["scaffold_version"] = self.run_py(SCAFFOLD, "status")[1]["plugin_version"]
        self.write(".sdlc/scaffold.lock.json", json.dumps(lock))
        checks = {c["check"]: c for c in self.run_py(DOCTOR)[1]["checks"]}
        row = checks["guardrails"]
        self.assertEqual(row["status"], "warn")
        self.assertIn(".claude/rules/sdlc.md", row["detail"])
        # R2-5: only rules missing: the fix names the render commands that write them, not --render or setup
        self.assertIn("scaffold.py render templates/project/rules/sdlc.md .claude/rules/sdlc.md", row["fix"])
        self.assertNotIn("guardrails --render", row["fix"])


if __name__ == "__main__":
    unittest.main()
