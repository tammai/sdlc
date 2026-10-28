"""scripts/diff_stats.py: comment share, new files, export usage, single implementations, new dependencies."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "diff_stats.py")


class DiffStatsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.write("src/existing.ts", "export function old() { return 1 }\n")
        self.write("package.json", json.dumps({"dependencies": {"react": "18"}}))
        self.write("requirements.txt", "requests==2.0\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "feat")

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True)

    def stats(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, *args], capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout) if "--format" not in args else p.stdout

    def file(self, r, path):
        return next(f for f in r["files"] if f["path"] == path)

    def flags(self, r, prefix):
        return [f for f in r["flags"] if f.startswith(prefix)]

    def test_comment_counting_c_like(self):
        self.write("src/a.ts", "// one\n/* two\n   three */\nconst a = 1 // trailing is code\n/**\n * four\n */\n\nf()\n")
        f = self.file(self.stats(), "src/a.ts")
        self.assertEqual((f["added_comments"], f["added_code"]), (6, 2))

    def test_comment_counting_python_docstrings(self):
        self.write("a.py", 'def f():\n    """Doc\n    more\n    """\n    # c\n    return 1\nx = """not a doc"""\n')
        f = self.file(self.stats(), "a.py")
        self.assertEqual((f["added_comments"], f["added_code"]), (4, 3))  # def, return and x = """...""" are code

    def test_modified_file_counts_only_added_lines(self):
        self.write("src/existing.ts", "export function old() { return 1 }\n// why: cache\nconst c = new Map()\n")
        self.git("commit", "-qam", "change")
        f = self.file(self.stats(), "src/existing.ts")
        self.assertEqual((f["added_comments"], f["added_code"], f["new"]), (1, 1, False))

    def test_comment_heavy_flags(self):
        self.write("src/heavy.ts", "// c\n" * 15 + "x()\n" * 10)
        r = self.stats()
        self.assertTrue(self.flags(r, "comment-heavy: src/heavy.ts (60%"))
        self.assertTrue(self.flags(r, "comment-heavy diff"))
        self.write("src/heavy.ts", "// c\n" * 3 + "x()\n" * 30)
        self.assertEqual(self.flags(self.stats(), "comment-heavy"), [])

    def test_test_files_are_excluded_from_ratio_and_exports(self):
        self.write("src/a.test.ts", "// c\n" * 30 + "export const fixture = 1\n")
        r = self.stats()
        self.assertEqual(r["totals"]["test_files"], 1)
        self.assertEqual(r["totals"]["added_comments"], 0)
        self.assertEqual(r["exports"], [])

    def test_export_usage(self):
        self.write("src/lib.ts", "export function used() {}\nexport function once() {}\nexport const never = 1\n"
                                 "export function self() {}\nself()\nexport function tested() {}\n")
        self.write("src/a.ts", "import { used, once } from './lib'\nused(); once()\n")
        self.write("src/b.ts", "import { used } from './lib'\nused()\n")
        self.write("src/lib.test.ts", "import { tested } from './lib'\ntested()\n")
        r = self.stats()
        by = {e["name"]: e for e in r["exports"]}
        self.assertEqual(by["used"]["caller_files"], 2)
        self.assertEqual(by["once"]["caller_files"], 1)
        flags = "\n".join(r["flags"])
        self.assertIn("single-use export: once", flags)
        self.assertIn("unused export: never in src/lib.ts (never used)", flags)
        self.assertIn("needless export: self", flags)
        self.assertIn("unused export: tested in src/lib.ts (only used by 1 test file(s))", flags)
        self.assertNotIn("export: used ", flags)

    def test_python_and_go_exports(self):
        self.write("svc.py", "def public():\n    pass\ndef _private():\n    pass\nclass Thing:\n    def method(self):\n        pass\n")
        self.write("svc.go", "package svc\nfunc Exported() {}\nfunc private() {}\ntype Repo struct{}\nfunc (r Repo) Get() {}\n")
        names = sorted(e["name"] for e in self.stats()["exports"])
        self.assertEqual(names, ["Exported", "Get", "Repo", "Thing", "public"])

    def test_single_implementation_abstraction(self):
        self.write("src/repo.ts", "export interface Repo { get(): string }\n"
                                  "export class SqlRepo implements Repo { get() { return '' } }\n")
        self.write("src/store.ts", "export interface Store {}\nexport class A implements Store {}\nexport class B implements Store {}\n")
        r = self.stats()
        impls = {i["name"]: i["implementations"] for i in r["interfaces"]}
        self.assertEqual(impls, {"Repo": 1, "Store": 2})
        self.assertTrue(self.flags(r, "single-implementation abstraction: Repo"))
        self.assertFalse(self.flags(r, "single-implementation abstraction: Store"))

    def test_new_dependencies(self):
        self.write("package.json", json.dumps({"dependencies": {"react": "18", "zod": "3"}, "devDependencies": {"vitest": "1"}}))
        self.write("requirements.txt", "requests==2.0\nhttpx>=0.27\n")
        names = sorted(d["name"] for d in self.stats()["dependencies"])
        self.assertEqual(names, ["httpx", "vitest", "zod"])

    def test_base_is_merge_base_with_main(self):
        self.write("src/a.ts", "x()\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "feat work")
        r = self.stats()
        self.assertIn("src/a.ts", r["new_files"])
        self.assertEqual(r["totals"]["added_code"], 1)

    def test_base_is_the_active_features_base_even_on_main(self):
        # Work committed straight onto main: the merge-base is HEAD, so only the recorded Base: sees it
        self.git("checkout", "-q", "main")
        base = subprocess.run(["git", "-C", self.root, "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True).stdout.strip()
        self.write(".sdlc/login/state.md", f"# Feature: login\nStatus: active\nProcess: 2\nBase: `{base}`\n")
        self.write("src/a.ts", "x()\n")
        self.write("docs/notes.md", "n\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "feat work on main")
        r = self.stats()
        self.assertTrue(r["base"].startswith(base))
        self.assertIn("src/a.ts", r["changed_files"])
        self.assertIn("docs/notes.md", r["changed_files"])  # non-source too: review-pr picks reviewers from it

    def test_a_state_file_as_the_plan_gives_its_own_base(self):
        # sdlc 2.0 keeps the plan in the state file (.sdlc/state/<feature>.md): its Base: is the diff's base
        self.git("checkout", "-q", "main")
        base = subprocess.run(["git", "-C", self.root, "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True).stdout.strip()
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        state = self.write(".sdlc/state/login.md", f"# login\nStatus: done\nBase: `{base}`\n\n"
                           "## Public Surface\n\n- none\n")
        self.write("src/a.ts", "x()\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "feat work on main")
        self.assertTrue(self.stats("--plan", state)["base"].startswith(base))

    PLAN = """# Login Plan

## Global Constraints

- export `notTheSurface` — mentioned outside the section, must be ignored

## Public Surface

- export `createSession` (src/auth/session.ts) — FR-002
- export `planned` — FR-003
- dependency `zod` — FR-004
- endpoint `POST /api/sessions` — FR-001
- config `SESSION_TTL_SECONDS` — FR-003

## Review Focus

- nothing
"""

    def plan(self, text=PLAN):
        return self.write(".sdlc/login/plan.md", text)

    def test_plan_surface_flags_undeclared_and_unbuilt(self):
        self.write("src/auth/session.ts", "export function createSession() {}\nexport function sneaky() {}\n")
        self.write("package.json", json.dumps({"dependencies": {"react": "18", "zod": "3", "lodash": "4"}}))
        r = self.stats("--plan", self.plan())
        s = r["surface"]
        self.assertEqual(s["undeclared_exports"], ["sneaky"])
        self.assertEqual(s["undeclared_dependencies"], ["lodash"])
        self.assertEqual(s["declared_not_built"], ["planned"])
        self.assertEqual(s["check_by_hand"], {"endpoint": ["POST /api/sessions"], "config": ["SESSION_TTL_SECONDS"]})
        flags = "\n".join(r["flags"])
        self.assertIn("undeclared export: sneaky", flags)
        self.assertIn("undeclared dependency: lodash", flags)
        self.assertIn("declared but not built: planned", flags)
        self.assertNotIn("undeclared export: createSession", flags)

    def test_plan_surface_none_declared(self):
        self.plan("# P\n\n## Public Surface\n\n- none\n")
        self.write("src/a.ts", "export const extra = 1\n")
        self.assertEqual(self.stats("--plan", self.path(".sdlc/login/plan.md"))["surface"]["undeclared_exports"], ["extra"])

    def test_plan_without_surface_section_is_flagged(self):
        self.plan("# P\n\n## Tasks\n")
        r = self.stats("--plan", self.path(".sdlc/login/plan.md"))
        self.assertIsNone(r["surface"])
        self.assertTrue(self.flags(r, "plan has no '## Public Surface' section"))

    def test_feature_close_checks_the_union_of_every_slice_plans_surface(self):
        one = self.write(".sdlc/login/plan-B1.md", "# B1\n\n## Public Surface\n\n- export `createSession` — FR-001\n")
        two = self.write(".sdlc/login/plan-B2.md", "# B2\n\n## Public Surface\n\n- export `endSession` — FR-002\n")
        self.write("src/auth/session.ts", "export function createSession() {}\nexport function endSession() {}\n"
                                          "export function sneaky() {}\n")
        self.assertEqual(self.stats("--plan", one, "--plan", two)["surface"]["undeclared_exports"], ["sneaky"])

    def test_plan_surface_in_markdown(self):
        self.write("src/auth/session.ts", "export function createSession() {}\n")
        md = self.stats("--plan", self.plan(), "--format", "md")
        self.assertIn("- endpoint `POST /api/sessions`", md)

    def test_markdown_output(self):
        self.write("src/a.ts", "export const never = 1\n")
        md = self.stats("--format", "md")
        self.assertIn("### Diff stats", md)
        self.assertIn("- unused export: never", md)

    def test_non_ascii_diff_survives_a_non_utf8_locale(self):
        # U+FF10 is EF BC 90 in UTF-8; 0x90 has no cp1252 mapping, which crashed the git read on Windows
        self.write("src/a.ts", "export const total０ = 1\n")
        env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "--format", "md"], capture_output=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        self.assertIn("- unused export: total０", p.stdout.decode("utf-8"))

    def test_no_changes(self):
        r = self.stats()
        self.assertEqual((r["flags"], r["totals"]["new_files"]), ([], 0))

    def test_not_a_git_repo(self):
        p = subprocess.run([sys.executable, SCRIPT, "--root", os.path.dirname(self.root)], capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 1)
        self.assertIn("error", json.loads(p.stdout))


if __name__ == "__main__":
    unittest.main()
