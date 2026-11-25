"""Guarded changes hardening (.sdlc/2026-11-25-m-guarded-changes-hardening): dependency sources, more suppressions and
manifests, a plain move, an unreadable Base manifest, what an Allow covers, and errors reported as not checked."""
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

sys.path.insert(0, HOOKS)
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
import guarded_changes  # noqa: E402

HOOK = lambda name: [sys.executable, os.path.join(HOOKS, name)]  # noqa: E731  (as hooks.json runs them)
UTF8 = {"PYTHONUTF8": "1"}
GUARDS = ["dependencies", "lint_config"]


class GuardedHardeningTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q")

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True,
                       capture_output=True)

    def base(self, files):
        for rel, text in files.items():
            self.write(rel, text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")

    def labels(self):
        return [label for _, label in guarded_changes.items(self.root, "HEAD", GUARDS)]

    # AC-001
    def test_a_changed_dependency_source_is_an_item(self):
        self.base({"requirements.txt": "requests\n", "package.json": json.dumps({"dependencies": {"a": "1"}}),
                   "go.mod": "module x\n\ngo 1.21\n\nrequire a v1.0.0\n",
                   "Cargo.toml": '[package]\nname = "x"\n\n[dependencies]\nserde = "1"\n'})
        self.assertEqual(self.labels(), [])
        self.write("requirements.txt", "--index-url https://example.invalid/simple\n-e ../lib\nrequests\n")
        self.write("package.json", json.dumps({"dependencies": {"a": "1"}, "overrides": {"a": "2"}}))
        self.write("go.mod", "module x\n\ngo 1.21\n\nrequire a v1.0.0\n\nreplace a => ../a\n")
        self.write("Cargo.toml", '[package]\nname = "x"\n\n[dependencies]\nserde = "1"\n\n'
                                 '[patch.crates-io]\nserde = { path = "../serde" }\n')
        self.write(".npmrc", "registry=https://example.invalid/\n")
        found = self.labels()
        for name in ("requirements.txt", "package.json", "go.mod", "Cargo.toml", ".npmrc"):
            self.assertTrue(any(l.startswith(f"dependency source {name} (") for l in found), (name, found))
        self.assertFalse(any(l.startswith("dependency ../") or "dependency lib" in l for l in found), found)

    # AC-002
    def test_more_suppressions_are_counted(self):
        self.base({"src/p.py": "x = 1\n", "src/e.js": "const a = 1\n"})
        self.write("src/p.py", "# ruff: noqa\n# flake8: noqa\n# mypy: ignore-errors\n# pyright: basic\nx = 1\n")
        self.write("src/e.js", '/* eslint no-console: "off" */\n// oxlint-disable\n// deno-lint-ignore\nconst a = 1\n')
        found = " | ".join(self.labels())
        for name in ("# ruff: noqa", "# flake8: noqa", "# mypy: ignore-errors", "# pyright: config",
                     "/* eslint rule */", "oxlint-disable", "deno-lint-ignore"):
            self.assertIn(f"suppression {name} in", found, name)

    # AC-003
    def test_more_manifests_are_read(self):
        self.base({"dev-requirements.txt": "pytest\n", "requirements.in": "flask\n",
                   "pyproject.toml": '[project]\nname = "x"\noptional-dependencies = { dev = ["pytest"] }\n'})
        self.write("dev-requirements.txt", "pytest\nblack\n")
        self.write("requirements.in", "flask\nhttpx\n")
        self.write("pyproject.toml", '[project]\nname = "x"\noptional-dependencies = { dev = ["pytest", "ruff"] }\n')
        found = self.labels()
        for label in ("dependency black (dev-requirements.txt)", "dependency httpx (requirements.in)",
                      "dependency ruff (pyproject.toml)"):
            self.assertIn(label, found)

    # AC-004
    def test_a_plain_move_keeps_its_suppressions(self):
        self.base({"src/old.py": "x = 1  # noqa\n"})
        os.makedirs(self.path("lib"))
        os.replace(self.path("src/old.py"), self.path("lib/old.py"))  # `mv`, not staged
        self.assertEqual(self.labels(), [])
        self.write("lib/old.py", "x = 1  # noqa\ny = 2  # noqa\n")  # one more is still one more
        self.assertIn("suppression # noqa in lib/old.py (now +1)", self.labels())

    # AC-005
    def test_an_unreadable_base_manifest_flags_each_dependency(self):
        self.base({"package.json": "{oops"})
        self.write("package.json", json.dumps({"dependencies": {"left-pad": "1"}}))
        found = self.labels()
        self.assertIn("dependency left-pad (package.json)", found)
        self.assertFalse(any("unreadable" in l for l in found), found)


class GuardedAllowTest(ProjectTestCase):
    LABEL = "dependency x (package.json)"

    def setUp(self):
        super().setUp()
        self.write(".sdlc/config.json", json.dumps({"guards": {"dependencies": True}}))
        for name in ("login", "signup"):
            self.write(f".sdlc/{name}/state.md", f"# {name}\nStatus: active\nProcess: 3\nCurrent: Stage 2 – Build\n")

    def pending(self, *features):
        self.write(".sdlc/.work/guarded.json", json.dumps(
            {"pending": {f: {"dependency:package.json:x": self.LABEL} for f in features}, "allowed": {}}))

    def allowed(self):
        with open(self.path(".sdlc/.work/guarded.json"), encoding="utf-8") as f:
            return {f: ids for f, ids in json.load(f)["allowed"].items() if ids}

    def answer(self, question, use_id, label="Allow"):
        q = {"question": question, "header": "Allow change", "options": [{"label": "Allow"}, {"label": "Undo it"}]}
        run_hook(HOOK("user_answer.py"), {"hook_event_name": "PreToolUse", "cwd": self.root,
                                          "tool_name": "AskUserQuestion", "tool_use_id": use_id,
                                          "tool_input": {"questions": [q]}}, self.root, UTF8)
        given = {question: label}
        run_hook(HOOK("guarded_changes.py"), {"hook_event_name": "PostToolUse", "cwd": self.root,
                                              "tool_name": "AskUserQuestion", "tool_use_id": use_id,
                                              "tool_input": {"questions": [q], "answers": given},
                                              "tool_response": {"questions": [q], "answers": given}}, self.root, UTF8)

    # AC-006
    def test_an_allow_covers_only_what_its_question_allows(self):
        self.pending("login", "signup")
        self.answer(f"Allow every change except {self.LABEL}?", "toolu_1")
        self.assertEqual(self.allowed(), {})
        self.answer(f"Allow {self.LABEL}?", "toolu_2")  # names no feature, two have it pending
        self.assertEqual(self.allowed(), {})
        self.answer(f"Allow {self.LABEL} for login?", "toolu_3")
        self.assertEqual(list(self.allowed()), ["login"])

    # AC-007
    def test_an_error_in_the_check_is_not_checked(self):
        import verify
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nProcess: 3\nBase: abc1234\nCurrent: Stage 2 – Build\n")
        with mock.patch.object(verify, "branched_repos", side_effect=RuntimeError("boom")):
            found = verify.guarded_failures(self.root, "login")
        self.assertEqual([p.code for p in found], ["guarded_not_checked"])


if __name__ == "__main__":
    unittest.main()
