"""A session moved into a linked git worktree inside its project (`git worktree add`, Claude Code's worktrees under
.claude/worktrees/) keeps CLAUDE_PROJECT_DIR on the main checkout: the hooks follow the call into the worktree, so
the main checkout's active feature doesn't gate it. A separate repo inside the project (a workbench's app repo, a
nested repo) resolves as before."""
import json
import os
import subprocess
import unittest

from helpers import HOOKS, ProjectTestCase, rmtree, run_hook

STATUS = ["python3", os.path.join(HOOKS, "session_status.py")]
BUDGET = ["python3", os.path.join(HOOKS, "prove_budget.py")]
IN_REVIEW = "# Feature: login\nStatus: active\nProcess: 3\nCurrent: Stage 3 – Review\n"
POLL = "until grep -q done log; do sleep 3; done"  # denied in Review


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args], cwd=cwd, check=True,
                   capture_output=True)


class WorktreeRootTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(rmtree, self.root)  # git's read-only objects (the base cleanup ignores the error)
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "npm test"}}))
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")

    def status(self, cwd):
        code, out, _, err = run_hook(STATUS, {"hook_event_name": "SessionStart", "cwd": cwd}, self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {}).get("additionalContext") or ""

    def poll(self, cwd):
        payload = {"hook_event_name": "PreToolUse", "cwd": cwd, "tool_name": "Bash", "tool_input": {"command": POLL}}
        code, out, _, err = run_hook(BUDGET, payload, self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def test_a_worktree_inside_the_project_is_gated_by_its_own_features(self):
        worktree = self.path(".claude/worktrees/w")
        git(self.root, "worktree", "add", "-q", "-b", "w", worktree)
        self.write(".sdlc/login/state.md", IN_REVIEW)  # active in the main checkout only
        self.assertIn("active: login", self.status(self.root))
        self.assertEqual(self.poll(self.root), "deny")
        self.assertIn("active: none", self.status(worktree))
        self.assertIsNone(self.poll(worktree))
        self.assertIsNone(self.poll(os.path.join(worktree, ".sdlc")))  # a folder inside the worktree too
        # A hand-made .git file naming a worktree git never registered doesn't escape the main checkout's gate
        self.write("fake/.git", f"gitdir: {self.path('.git/worktrees/fake')}\n")
        self.assertEqual(self.poll(self.path("fake")), "deny")

    def test_a_separate_repo_inside_the_project_still_follows_the_project(self):
        nested = self.path("app")
        os.makedirs(nested)
        git(nested, "init", "-q")
        self.write(".sdlc/login/state.md", IN_REVIEW)
        self.assertIn("active: login", self.status(nested))
        self.assertEqual(self.poll(nested), "deny")


if __name__ == "__main__":
    unittest.main()
