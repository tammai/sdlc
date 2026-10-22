"""hooks/verify_freshness.py: Stage 5 blocks finishing on stale test results."""
import json
import os
import subprocess
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "verify_freshness.py")]

STATE = """# Feature: {feature}
Status: {status}
Current: Stage {stage}
Track: M

## Commands
{test_line}
"""


class VerifyFreshnessTest(ProjectTestCase):
    def set_state(self, feature="login", status="active", stage=5, test_cmd=None):
        test_line = f"- test: `{test_cmd}`" if test_cmd else ""
        self.write(f".sdlc/{feature}/state.md",
                   STATE.format(feature=feature, status=status, stage=stage, test_line=test_line))

    def post(self, tool, **tool_input):
        payload = {"hook_event_name": "PostToolUse", "cwd": self.root, "tool_name": tool,
                   "tool_input": tool_input, "tool_response": tool_input.pop("_response", {})}
        return run_hook(HOOK, payload, self.root)

    def bash(self, command, **resp):
        return self.post("Bash", command=command, _response=resp)

    def edit(self, rel, tool="Edit"):
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        return self.post(tool, **{key: self.path(rel)})

    def stop(self, stop_hook_active=False):
        code, out, raw, err = run_hook(
            HOOK, {"hook_event_name": "Stop", "cwd": self.root, "stop_hook_active": stop_hook_active}, self.root)
        self.assertEqual(code, 0, err)
        return out

    def assertBlocks(self, out=None):
        out = out if out is not None else self.stop()
        self.assertIsNotNone(out, "expected Stop to block, got no output")
        self.assertEqual(out.get("decision"), "block")
        return out

    def assertAllows(self):
        self.assertIsNone(self.stop(), "expected Stop to pass silently")

    def state_file(self):
        with open(self.path(".sdlc/.work/verify-freshness.json"), encoding="utf-8") as f:
            return json.load(f)

    # --- when the hook is inactive -------------------------------------------------

    def test_no_sdlc_dir_is_noop(self):
        self.write("src/a.ts", "")
        self.edit("src/a.ts")
        self.assertAllows()
        self.assertFalse(os.path.exists(self.path(".sdlc")))

    def test_other_stage_is_noop(self):
        self.set_state(stage=4)
        self.edit("src/a.ts")
        self.assertAllows()
        self.assertFalse(os.path.exists(self.path(".sdlc/.work/verify-freshness.json")))

    def test_stage_5_but_not_active_is_noop(self):
        self.set_state(status="done")
        self.assertAllows()

    def test_stage_50_is_not_stage_5(self):
        self.set_state(stage=50)
        self.assertAllows()

    # --- stale / fresh ---------------------------------------------------------

    def test_entering_stage_5_without_a_test_run_blocks(self):
        self.set_state()
        out = self.assertBlocks()
        self.assertIn("no full test run", out["reason"])

    def test_full_test_run_makes_fresh(self):
        self.set_state()
        self.bash("npm test")
        self.assertAllows()
        st = self.state_file()
        self.assertFalse(st["stale"])
        self.assertEqual(st["last_test_cmd"], "npm test")

    def test_code_edit_after_test_run_makes_stale(self):
        self.set_state()
        self.bash("npm test")
        self.edit("src/login.ts")
        out = self.assertBlocks()
        self.assertIn("src/login.ts", out["reason"])

    def test_rerun_after_edit_makes_fresh_again(self):
        self.set_state()
        self.bash("npm test")
        self.edit("src/login.ts")
        self.bash("npm test")
        self.assertAllows()

    def test_all_edit_tools_mark_stale(self):
        for tool, rel in [("Edit", "src/a.ts"), ("Write", "src/b.ts"),
                          ("MultiEdit", "src/c.ts"), ("NotebookEdit", "nb/d.ipynb")]:
            with self.subTest(tool=tool):
                self.set_state()
                self.bash("npm test")
                self.edit(rel, tool=tool)
                self.assertBlocks()

    def test_non_code_edits_keep_results_fresh(self):
        self.set_state()
        self.bash("npm test")
        for rel in ["README.md", "src/notes.MD", "CHANGELOG.txt", "docs/api.ts", "knowledge/index.md",
                    ".claude/rules/api.md", ".sdlc/login/test-report.md", ".sdlc/login/notes.json"]:
            with self.subTest(rel=rel):
                self.edit(rel)
                self.assertAllows()

    def test_edit_outside_project_is_ignored(self):
        self.set_state()
        self.bash("npm test")
        self.post("Edit", file_path=os.path.join(os.path.dirname(self.root), "elsewhere.ts"))
        self.assertAllows()

    def test_non_test_bash_does_not_make_fresh(self):
        self.set_state()
        for cmd in ["npm run build", "npx tsc --noEmit", "git status", "cat test.log"]:
            with self.subTest(cmd=cmd):
                self.bash(cmd)
                self.assertBlocks()

    def test_generic_test_commands_count(self):
        for cmd in ["npm test", "npm run test", "pnpm test", "yarn test", "bun test", "npx vitest run",
                    "npx jest", "pytest", "python -m pytest -q", "go test ./...", "cargo test",
                    "dotnet test", "make test", "CI=1 npm test 2>&1 | tail -50"]:
            with self.subTest(cmd=cmd):
                self.set_state()
                self.bash("npm run build")  # reset nothing, just make sure state exists
                self.edit("src/a.ts")
                self.bash(cmd)
                self.assertAllows()

    def test_filtered_runs_do_not_count(self):
        for cmd in ["npx jest -t login", "npx vitest run --testNamePattern login", "pytest -k login",
                    "npx playwright test --grep login", "go test -run TestLogin ./...",
                    "pnpm test --filter api", "npx jest --bail"]:
            with self.subTest(cmd=cmd):
                self.set_state()
                self.edit("src/a.ts")
                self.bash(cmd)
                self.assertBlocks()

    def test_interrupted_test_run_does_not_count(self):
        self.set_state()
        self.bash("npm test", interrupted=True)
        self.assertBlocks()

    # --- `test:` command from state.md ------------------------------------------

    def test_state_test_command_is_required_when_set(self):
        self.set_state(test_cmd="pnpm test:all")
        self.bash("npx vitest run")  # generic pattern, but not the project's command
        self.assertBlocks()
        self.bash("pnpm test:all")
        self.assertAllows()

    def test_state_test_command_still_rejects_filters(self):
        self.set_state(test_cmd="pnpm test:all")
        self.bash("pnpm test:all -t login")
        self.assertBlocks()

    def test_block_message_names_the_test_command(self):
        self.set_state(test_cmd="pnpm test:all")
        self.assertIn("`pnpm test:all`", self.assertBlocks()["reason"])

    # --- loop guard, feature switch, git -----------------------------------------

    def test_second_consecutive_stop_only_warns(self):
        self.set_state()
        out = self.stop(stop_hook_active=True)
        self.assertIsNotNone(out)
        self.assertNotIn("decision", out)
        self.assertIn("stale", out["systemMessage"])

    def test_switching_feature_resets_freshness(self):
        self.set_state(feature="login")
        self.bash("npm test")
        self.assertAllows()
        os.remove(self.path(".sdlc/login/state.md"))
        self.set_state(feature="signup")
        self.assertBlocks()
        self.assertEqual(self.state_file()["feature"], "signup")

    def test_records_git_head_on_fresh_run(self):
        git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "init"], check=True)
        head = subprocess.run(git + ["rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.set_state()
        self.bash("npm test")
        self.assertEqual(self.state_file()["head"], head)

    def test_found_from_subdirectory_cwd(self):
        self.set_state()
        os.makedirs(self.path("packages/api"))
        payload = {"hook_event_name": "Stop", "cwd": self.path("packages/api")}
        code, out, _, _ = run_hook(HOOK, payload, self.path("packages/api"),
                                   env_extra={"CLAUDE_PROJECT_DIR": self.path("packages/api")})
        self.assertEqual(out.get("decision"), "block")

    # --- never breaks the session -------------------------------------------------

    def test_bad_input_exits_zero_silently(self):
        self.set_state()
        for stdin in ["", "not json", "[]", '{"hook_event_name": "PostToolUse", "tool_input": null}']:
            with self.subTest(stdin=stdin):
                code, out, raw, _ = run_hook(HOOK, stdin, self.root)
                self.assertEqual(code, 0)
                self.assertEqual(raw, "")

    def test_corrupt_state_file_is_recovered(self):
        self.set_state()
        self.write(".sdlc/.work/verify-freshness.json", "{oops")
        self.bash("npm test")
        self.assertAllows()


if __name__ == "__main__":
    unittest.main()
