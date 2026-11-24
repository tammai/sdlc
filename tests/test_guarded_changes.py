"""Guarded changes (.sdlc/2026-11-24-m-gh-92-guarded-changes, issue #92 part 3): with config `guards.dependencies` or
`guards.lint_config` on, verify fails on a new dependency, a changed lint or type config, or an added suppression
comment until the user allows it (hooks/guarded_changes.py records the answer)."""
import json
import os
import subprocess
import sys
import unittest

from helpers import HOOKS, run_hook

sys.path.insert(0, HOOKS)
import test_verify

HOOK = lambda name: [sys.executable, os.path.join(HOOKS, name)]  # noqa: E731  (as hooks.json runs them)
UTF8 = {"PYTHONUTF8": "1"}
RUN = "python3 -c \"import os, sys; sys.exit(0 if os.path.exists('done') else 1)\""
FILES = ["package.json", "pyproject.toml", "pubspec.yaml", "setup.cfg", "tsconfig.json", "src/a.ts", "src/b.py", "src/c.ts",
         "done", "tests/t.py"]


class GuardedChangesTest(test_verify.VerifyTest):
    GUARDS = {"dependencies": True, "lint_config": True}

    def setUp(self):
        super().setUp()
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""},
                                                    **({"guards": self.GUARDS} if self.GUARDS else {})}))
        self.write("package.json", json.dumps({"dependencies": {"a": "1.0.0"}}))
        self.write("pyproject.toml", '[project]\nname = "x"\ndependencies = [\n  "requests>=2",\n]\n\n'
                                     '[tool.other]\nx = 1\n\n[tool.mypy]  # type checking\nstrict = true\n')
        self.write("pubspec.yaml", "name: app\ndependencies:\n    http: ^1.0.0\n")
        self.write("setup.cfg", "[metadata]\nname = x\n\n[tool:pytest]\naddopts = -q\n")
        self.write("src/b.py", "x = 1\n")
        self.write("tsconfig.json", json.dumps({"compilerOptions": {"strict": True}}))
        self.write("src/a.ts", "// @ts-ignore\nconst a: number = 'x'\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "manifests")
        base = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], capture_output=True,
                              encoding="utf-8").stdout.strip()
        self.state = test_verify.STATE.format(base=base)
        self.spec("AC-001")
        self.plan([("AC-001", "tests/t.py › ok", RUN)], tasks=["1. t " + " ".join(f"`{f}`" for f in FILES)],
                  deviations=[f"- {d} What: a dependency. Why: the test. Effect: none."
                              for d in ("b", "c", "flask", "uvicorn")])
        self.write("tests/t.py", "ok\n")
        code, out, _ = self.verify("red", "AC-001")
        self.assertEqual(code, 0, out)
        self.write("done", "")

    def deps(self, **names):
        self.write("package.json", json.dumps({"dependencies": names}))

    def answer(self, label, question, use_id, *more):
        """One AskUserQuestion call: (question, answer) pairs, the first given as label and question."""
        pairs = [(question, label)] + list(more)
        qs = [{"question": q, "header": "Allow change", "options": [{"label": "Allow"}, {"label": "Undo it"}]}
              for q, _ in pairs]
        run_hook(HOOK("user_answer.py"), {"hook_event_name": "PreToolUse", "cwd": self.root,
                                          "tool_name": "AskUserQuestion", "tool_use_id": use_id,
                                          "tool_input": {"questions": qs}}, self.root, UTF8)
        given = {q: a for q, a in pairs}
        run_hook(HOOK("guarded_changes.py"), {"hook_event_name": "PostToolUse", "cwd": self.root,
                                              "tool_name": "AskUserQuestion", "tool_use_id": use_id,
                                              "tool_input": {"questions": qs, "answers": given},
                                              "tool_response": {"questions": qs, "answers": given}}, self.root, UTF8)

    # AC-001
    def test_a_new_dependency_fails_verify_and_a_version_bump_does_not(self):
        self.assertEqual(self.verify()[0], 0)
        self.deps(a="2.0.0")  # a version bump
        self.assertEqual(self.verify()[0], 0)
        self.deps(a="2.0.0", b="1.0.0")
        self.write("pyproject.toml", '[project]\nname = "x"\ndependencies = [\n  "requests>=3",\n  "uvicorn[standard]",\n'
                                     '  "flask",\n]\n\n[tool.other]\nx = 1\n\n[tool.mypy]  # type checking\nstrict = true\n')
        self.write("pubspec.yaml", "name: app\ndependencies:\n    http: ^1.0.0\n    dio: ^5.0.0\n")
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("dependency b (package.json)", out)
        self.assertIn("dependency flask (pyproject.toml)", out)
        self.assertIn("dependency uvicorn (pyproject.toml)", out)
        self.assertIn("dependency dio (pubspec.yaml)", out)
        self.assertNotIn("dependency a ", out)
        self.assertNotIn("dependency requests", out)
        self.assertNotIn("dependency http", out)
        with open(self.path("package.json"), "w", encoding="utf-8-sig") as f:  # PowerShell 5 writes a BOM
            f.write(json.dumps({"dependencies": {"a": "1", "c": "1", "x\n## Gate log": "1"}}))
        code, out, _ = self.verify()
        self.assertIn("dependency c (package.json)", out)
        self.assertNotIn("\n## Gate log", out)  # a name that isn't one never reaches the output raw

    # AC-002
    def test_the_users_allow_for_the_named_item_lets_verify_pass(self):
        self.deps(a="1.0.0", b="1.0.0")
        self.assertEqual(self.verify()[0], 1)
        self.answer("Undo it", "Allow dependency b (package.json)?", "toolu_1")
        self.answer("Allow", "Allow the new dependency?", "toolu_2")  # names no item
        self.assertEqual(self.verify()[0], 1)
        self.deps(a="1.0.0", b="1.0.0", c="1.0.0")
        self.verify()
        self.answer("Allow (Recommended)", "Allow dependency b (package.json)?", "toolu_3",
                    ("Allow dependency c (package.json)?", "Undo it"))  # one call, each question its own answer
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("dependency c (package.json)", out)
        self.assertNotIn("dependency b (package.json)", out)
        import guarded_changes  # another feature's verify doesn't take this one's pending items away
        guarded_changes.unallowed(self.root, "HEAD", ["dependencies"], feature="other")
        self.answer("Allow", "Allow dependency c (package.json)?", "toolu_4")
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)
        self.deps(a="1.0.0", b="1.0.0", c="1.0.0", d="1.0.0")
        self.assertEqual(self.verify()[0], 1)
        run_hook(HOOK("guarded_changes.py"), {"hook_event_name": "UserPromptSubmit", "cwd": self.root,
                                              "prompt": "Allow"}, self.root, UTF8)
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)
        ship = subprocess.run([sys.executable, os.path.join(test_verify.PLUGIN_ROOT, "scripts", "ship.py"), "--root",
                               self.root, "login", "--review", "No review ran."], capture_output=True, encoding="utf-8")
        self.assertEqual(ship.returncode, 0, ship.stdout + ship.stderr)
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            self.assertIn("guarded changes allowed by the user: dependency b (package.json); dependency c "
                          "(package.json); dependency d (package.json)", f.read())

    # AC-003
    def test_a_changed_lint_config_or_an_added_suppression_fails_verify(self):
        self.write("tsconfig.json", json.dumps({"compilerOptions": {"strict": False}}))
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("lint config tsconfig.json", out)
        self.write("tsconfig.json", json.dumps({"compilerOptions": {"strict": True}}))
        self.write("src/a.ts", "const a: number = 1\n")  # a suppression removed: free
        self.assertEqual(self.verify()[0], 0)
        self.write("src/a.ts", "// @ts-ignore\n// @ts-ignore\n// @ts-ignore\nconst a: number = 'x'\n")
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("suppression @ts-ignore in src/a.ts", out)
        run_hook(HOOK("guarded_changes.py"), {"hook_event_name": "UserPromptSubmit", "cwd": self.root,
                                              "prompt": "allow"}, self.root, UTF8)
        self.write("src/a.ts", "// @ts-ignore\n// @ts-ignore\nconst a: number = 'x'\n")  # one of those taken back
        self.assertEqual(self.verify()[0], 0)
        import guarded_changes  # an allow is this feature's: another feature adding as many asks again
        base = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], capture_output=True,
                              encoding="utf-8").stdout.strip()
        self.assertTrue(guarded_changes.unallowed(self.root, base, ["lint_config"], feature="other"))
        self.write("src/b.py", "x = 1\n\x0c\ny = 2  # noqa\n")  # a form feed line, then a suppression
        self.git("config", "diff.noprefix", "true")  # git's diff headers as some users have them
        code, out, _ = self.verify()
        self.assertNotIn("Traceback", out)
        self.assertIn("suppression # noqa in src/b.py", out)
        self.write("src/b.py", "x = 1\n++ y\nz = 1  # noqa\n")  # an added line that looks like a diff header
        code, out, _ = self.verify()
        self.assertIn("suppression # noqa in src/b.py", out)
        self.write("src/b.py", "x = 1\n")
        self.write("src/a.ts", "// @ts-ignore\nconst a: number = 'x'\n")
        self.git("mv", "src/a.ts", "src/c.ts")  # a file moved as it is: its suppressions stay free
        code, out, _ = self.verify()
        self.assertNotIn("src/c.ts", out)
        self.git("mv", "src/c.ts", "src/a.ts")
        self.write("setup.cfg", "[metadata]\nname = x\n\n[tool:pytest]\naddopts = -q\n\n[mypy-x.*]\nignore_errors = True\n")
        code, out, _ = self.verify()
        self.assertIn("lint config setup.cfg", out)
        self.write("setup.cfg", "[metadata]\nname = x\n\n[tool:pytest]\naddopts = -q\n")
        self.write("pyproject.toml", '[project]\nname = "x"\ndependencies = [\n  "requests>=2",\n]\n\n'
                                     '[tool.other]\nx = 1\n\n[tool.mypy]  # type checking\nstrict = false\n')
        code, out, _ = self.verify()
        self.assertIn("lint config pyproject.toml", out)


class UnguardedTest(GuardedChangesTest):
    GUARDS = None

    def test_without_the_guards_nothing_is_checked(self):
        self.deps(a="1.0.0", b="1.0.0")
        self.write("tsconfig.json", json.dumps({"compilerOptions": {"strict": False}}))
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)


def load_tests(loader, tests, pattern):
    """Only this file's tests: the fixture it extends runs in test_verify.py."""
    suite = unittest.TestSuite()
    for name in loader.getTestCaseNames(GuardedChangesTest):
        if name.startswith("test_") and name in GuardedChangesTest.__dict__:
            suite.addTest(GuardedChangesTest(name))
    suite.addTest(UnguardedTest("test_without_the_guards_nothing_is_checked"))
    return suite


if __name__ == "__main__":
    unittest.main()
