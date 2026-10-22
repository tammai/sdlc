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

    def scope_state(self, name="(root)"):
        return self.state_file()["scopes"][name]

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
        st = self.scope_state()
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
                    "pnpm test --filter api", "npx jest --bail",
                    "npm test 2>/dev/null -t login", "pytest > out.txt -k login", "npx jest &>log src/a.test.ts"]:
            with self.subTest(cmd=cmd):
                self.set_state()
                self.edit("src/a.ts")
                self.bash(cmd)
                self.assertBlocks()

    def test_single_test_file_runs_do_not_count(self):
        for cmd in ["npx vitest run src/login.test.ts", "npx jest src/login.spec.tsx", "npm test -- src/a.test.mjs",
                    "pytest tests/test_login.py", "pytest tests/api_test.py", "pytest tests/x.py::test_ok",
                    "go test ./internal/auth", "go test ./internal/auth/login_test.go", "bundle exec rspec spec/a_spec.rb",
                    "mvn test -Dtest=x LoginTest.java"]:
            with self.subTest(cmd=cmd):
                self.set_state()
                self.edit("src/a.ts")
                self.bash(cmd)
                self.assertBlocks()

    def test_whole_suite_arguments_still_count(self):
        for cmd in ["go test ./...", "go test -race ./...", "go test ./... 2>&1 | tail -20", "pytest tests/", "npx vitest run --coverage",
                    "npm test -- --reporter=dot", "npm test && echo src/a.test.ts", "npx jest 2>&1 | grep a_test.go"]:
            with self.subTest(cmd=cmd):
                self.set_state()
                self.edit("src/a.ts")
                self.bash(cmd)
                self.assertAllows()

    def test_state_test_command_with_a_test_file_does_not_count(self):
        self.set_state(test_cmd="pnpm test:all")
        self.bash("pnpm test:all src/login.test.ts")
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

    def test_flags_inside_the_test_command_are_not_filters(self):
        # unittest's -t is the top-level directory, not jest's name filter
        self.set_state(test_cmd="python3 -m unittest discover -s tests -t .")
        self.bash("python3 -m unittest discover -s tests -t .")
        self.assertAllows()

    def test_block_message_names_the_test_command(self):
        self.set_state(test_cmd="pnpm test:all")
        self.assertIn("`pnpm test:all`", self.assertBlocks()["reason"])

    # --- .sdlc/config.json (after /sdlc:setup) ---------------------------------------

    def configure(self, **config):
        self.write(".sdlc/config.json", json.dumps({"min_plugin_version": "1.3.0", **config}))

    def test_config_test_command_counts_and_generic_runners_do_not(self):
        self.set_state()
        self.configure(commands={"test": "pnpm test", "lint": "pnpm lint"})
        for cmd, full in [("pnpm test", True), ("CI=1 pnpm test 2>&1 | tail", True), ("pnpm lint && pnpm test", True),
                          ("npx vitest run", False), ("pnpm test src/a.test.ts", False), ("pnpm test -t login", False),
                          ("pnpm test:unit", False)]:
            with self.subTest(cmd=cmd):
                self.edit("src/a.ts")
                self.bash(cmd)
                (self.assertAllows if full else self.assertBlocks)()

    def test_config_command_only_counts_in_its_own_directory(self):
        self.set_state()
        self.configure(commands={"test": "pnpm test"})
        self.write("apps/web/x.ts", "")
        self.bash("cd apps/web && pnpm test")
        self.assertBlocks()
        self.bash("cd apps/web && cd ../.. && pnpm test")
        self.assertAllows()

    def test_block_message_names_the_config_command(self):
        self.set_state()
        self.configure(commands={"test": "make check"})
        self.assertIn("`make check`", self.assertBlocks()["reason"])

    def test_state_test_command_still_counts_with_config(self):
        self.set_state(test_cmd="pnpm test:all")
        self.configure(commands={"test": "pnpm test"})
        self.bash("pnpm test:all")
        self.assertAllows()

    def test_command_must_match_whole_words(self):
        self.set_state(test_cmd="pnpm test")
        self.bash("pnpm test:unit")
        self.assertBlocks()

    # --- monorepo: freshness per package ----------------------------------------------

    PACKAGES = [{"name": "api", "path": "services/api", "stack": "go", "commands": {"test": "go test ./..."}},
                {"name": "web", "path": "apps/web", "stack": "node", "commands": {"test": "pnpm test"}}]

    def monorepo(self, root_test=None):
        self.set_state()
        config = {"packages": self.PACKAGES}
        if root_test:
            config["commands"] = {"test": root_test}
        self.configure(**config)
        for d in ("services/api", "apps/web"):
            os.makedirs(self.path(d), exist_ok=True)

    def monorepo_git(self, base_line=True):
        git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        self.write(".gitignore", ".sdlc/.work/\n")
        self.write("services/api/main.go", "package main\n")
        self.write("apps/web/a.ts", "export const a = 1\n")
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "base"], check=True)
        base = subprocess.run(git + ["rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.monorepo()
        if base_line:
            path = self.path(".sdlc/login/state.md")
            with open(path) as f:
                text = f.read()
            self.write(".sdlc/login/state.md", text.replace("Current:", f"Base: {base}\nCurrent:"))
        return git

    def test_only_packages_changed_since_the_feature_base_start_stale(self):
        git = self.monorepo_git()
        self.write("services/api/handler.go", "package main\n")  # uncommitted feature work
        self.write("services/api/main.go", "package main // changed\n")
        subprocess.run(git + ["commit", "-q", "-am", "feature commit"], check=True)  # committed work counts too
        reason = self.assertBlocks()["reason"]
        self.assertIn("api:", reason)
        self.assertNotIn("web:", reason)
        self.bash("cd services/api && go test ./...")
        self.assertAllows()

    def test_untouched_package_still_goes_stale_when_it_changes_later(self):
        self.monorepo_git()
        self.write("services/api/handler.go", "package main\n")
        self.bash("cd services/api && go test ./...")
        self.write("apps/web/a.ts", "export const a = 2\n")  # e.g. a formatter, after Stage 5 began
        self.assertIn("web: apps/web/a.ts changed", self.assertBlocks()["reason"])

    def test_without_a_base_every_package_starts_stale(self):
        self.monorepo_git(base_line=False)
        self.write("services/api/handler.go", "package main\n")
        reason = self.assertBlocks()["reason"]
        self.assertIn("api:", reason)
        self.assertIn("web:", reason)

    def test_no_changes_since_base_keeps_everything_stale(self):
        self.monorepo_git()
        reason = self.assertBlocks()["reason"]
        self.assertIn("api:", reason)
        self.assertIn("web:", reason)

    def test_every_package_starts_stale(self):
        self.monorepo()
        reason = self.assertBlocks()["reason"]
        self.assertIn("api: no full test run", reason)
        self.assertIn("→ run `cd services/api && go test ./...`", reason)
        self.assertIn("→ run `cd apps/web && pnpm test`", reason)

    def test_each_package_goes_fresh_in_its_own_directory(self):
        self.monorepo()
        self.bash("cd services/api && go test ./...")
        reason = self.assertBlocks()["reason"]
        self.assertNotIn("api:", reason)
        self.assertIn("web:", reason)
        self.bash("pnpm test")  # right command, wrong directory (repo root)
        self.assertBlocks()
        self.bash("cd 'apps/web' && pnpm test")
        self.assertAllows()

    def test_session_cwd_counts_as_the_run_directory(self):
        self.monorepo()
        self.bash("cd services/api && go test ./...")
        payload = {"hook_event_name": "PostToolUse", "cwd": self.path("apps/web"), "tool_name": "Bash",
                   "tool_input": {"command": "pnpm test"}, "tool_response": {}}
        run_hook(HOOK, payload, self.path("apps/web"), env_extra={"CLAUDE_PROJECT_DIR": self.root})
        self.assertAllows()

    def test_edit_only_makes_its_own_package_stale(self):
        self.monorepo()
        self.bash("cd services/api && go test ./...")
        self.bash("cd apps/web && pnpm test")
        self.edit("services/api/handler.go")
        reason = self.assertBlocks()["reason"]
        self.assertIn("api: services/api/handler.go edited", reason)
        self.assertNotIn("web:", reason)

    def test_shared_root_file_makes_every_package_stale(self):
        self.monorepo()
        self.bash("cd services/api && go test ./...")
        self.bash("cd apps/web && pnpm test")
        self.edit("tsconfig.base.json")
        reason = self.assertBlocks()["reason"]
        self.assertIn("api:", reason)
        self.assertIn("web:", reason)

    def test_package_filters_still_partial(self):
        self.monorepo()
        self.bash("cd services/api && go test ./internal/auth")
        self.assertIn("api:", self.assertBlocks()["reason"])

    def test_root_test_command_covers_every_package(self):
        self.monorepo(root_test="pnpm turbo run test")
        self.bash("pnpm turbo run test")
        self.assertAllows()
        self.bash("cd apps/web && pnpm turbo run test")  # from inside a package it's not the root run
        self.edit("apps/web/a.ts")
        self.bash("cd apps/web && pnpm turbo run test")
        self.assertBlocks()

    def test_worktree_changes_are_attributed_per_package(self):
        git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        self.write(".gitignore", ".sdlc/.work/\n")
        self.write("services/api/main.go", "package main\n")
        self.write("apps/web/a.ts", "export const a = 1\n")
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "init"], check=True)
        self.monorepo()
        self.bash("cd services/api && go test ./...")
        self.bash("cd apps/web && pnpm test")
        self.write("apps/web/a.ts", "export const a = 2\n")  # e.g. a formatter, no Edit tool involved
        reason = self.assertBlocks()["reason"]
        self.assertIn("web: apps/web/a.ts changed", reason)
        self.assertNotIn("api:", reason)
        self.write("apps/web/a.ts", "export const a = 1\n")
        self.assertAllows()

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
        self.assertEqual(self.scope_state()["head"], head)

    # --- worktree fingerprint (git repos): catches edits made outside Edit/Write --------

    def git_repo(self):
        git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        self.write(".gitignore", ".sdlc/.work/\nnode_modules/\n")
        self.write("src/login.ts", "export const a = 1\n")
        self.write("README.md", "# app\n")
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "init"], check=True)
        return git

    def test_bash_edit_after_test_run_makes_stale(self):
        self.git_repo()
        self.set_state()
        self.bash("npm test")
        self.write("src/login.ts", "export const a = 2\n")  # e.g. sed -i, a formatter, or a subagent
        self.bash("sed -i '' s/1/2/ src/login.ts")
        out = self.assertBlocks()
        self.assertIn("src/login.ts", out["reason"])

    def test_new_and_deleted_files_make_stale(self):
        self.git_repo()
        self.set_state()
        self.bash("npm test")
        self.write("src/new.ts", "x")
        self.assertIn("src/new.ts", self.assertBlocks()["reason"])
        os.remove(self.path("src/new.ts"))
        self.assertAllows()
        os.remove(self.path("src/login.ts"))
        self.assertIn("src/login.ts", self.assertBlocks()["reason"])

    def test_reverting_an_edit_makes_fresh_again(self):
        self.git_repo()
        self.set_state()
        self.bash("npm test")
        self.write("src/login.ts", "export const a = 2\n")
        self.edit("src/login.ts")
        self.assertBlocks()
        self.write("src/login.ts", "export const a = 1\n")
        self.assertAllows()

    def test_non_code_and_ignored_changes_keep_fresh(self):
        self.git_repo()
        self.set_state()
        self.bash("npm test")
        self.write("README.md", "# changed\n")
        self.write("docs/x.ts", "x")
        self.write("node_modules/pkg/index.js", "x")
        self.assertAllows()

    def test_committing_tested_code_keeps_fresh(self):
        git = self.git_repo()
        self.write("src/login.ts", "export const a = 2\n")
        self.set_state()
        self.bash("npm test")
        subprocess.run(git + ["commit", "-q", "-am", "wip"], check=True)
        self.assertAllows()

    def test_real_git_index_is_untouched(self):
        git = self.git_repo()
        self.set_state()
        self.write("src/login.ts", "export const a = 2\n")
        self.write("src/new.ts", "x")
        self.bash("npm test")
        self.stop()
        staged = subprocess.run(git + ["diff", "--cached", "--name-only"], capture_output=True, text=True).stdout
        self.assertEqual(staged, "")

    def test_lists_at_most_five_changed_files(self):
        self.git_repo()
        self.set_state()
        self.bash("npm test")
        for i in range(8):
            self.write(f"src/f{i}.ts", "x")
        self.assertIn("and 3 more", self.assertBlocks()["reason"])

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
