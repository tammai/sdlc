"""scripts/doctor.py: read-only health check of environment, plugin and repo."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

DOCTOR = os.path.join(PLUGIN_ROOT, "scripts", "doctor.py")
SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
COMMANDS = {k: "git --version" for k in ("install", "test", "lint", "typecheck", "build")}


class DoctorTest(ProjectTestCase):
    def doctor(self, expect=None):
        p = subprocess.run([sys.executable, DOCTOR, "--root", self.root], capture_output=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT})
        report = json.loads(p.stdout)
        if expect is not None:
            self.assertEqual(p.returncode, expect, p.stdout)
        return {(c["group"], c["check"]): c for c in report["checks"]}, p.returncode

    def check(self, name, group="repo"):
        return self.doctor()[0].get((group, name))

    def setup_repo(self, kind="greenfield"):
        subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, "init", "--kind", kind],
                       check=True, capture_output=True)
        subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, "step-done", "finalize", "--complete"],
                       check=True, capture_output=True)
        self.configure(commands=COMMANDS)
        self.write(".gitignore", ".sdlc/.work/\n")

    def configure(self, **config):
        path = self.path(".sdlc/config.json")
        with open(path) as f:
            data = json.load(f)
        data.update(config)
        self.write(".sdlc/config.json", json.dumps(data))

    def lock(self, **changes):
        path = self.path(".sdlc/scaffold.lock.json")
        with open(path) as f:
            data = json.load(f)
        data.update(changes)
        self.write(".sdlc/scaffold.lock.json", json.dumps(data))

    def test_environment_and_plugin_checks_always_run(self):
        checks, _ = self.doctor()
        for key in [("environment", "python"), ("environment", "python3"), ("environment", "git"),
                    ("environment", "gh"), ("environment", "jq"), ("environment", "security reviewer env"),
                    ("plugin", "version"), ("plugin", "hook scripts")]:
            self.assertIn(key, checks)
        self.assertEqual(checks[("plugin", "hook scripts")]["status"], "ok")

    # Windows looks in the running interpreter's folder before PATH, so an empty PATH can't hide a python3.exe there
    @unittest.skipIf(os.path.exists(os.path.join(os.path.dirname(sys.executable), "python3.exe")),
                     "python3.exe sits next to the interpreter; Windows finds it even with an empty PATH")
    def test_missing_python3_fails(self):
        p = subprocess.run([sys.executable, DOCTOR, "--root", self.root], capture_output=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT, "PATH": ""})
        checks = {(c["group"], c["check"]): c for c in json.loads(p.stdout)["checks"]}
        self.assertEqual(checks[("environment", "python3")]["status"], "fail")
        self.assertEqual(p.returncode, 1)

    def test_repo_not_set_up_is_a_warning_not_a_failure(self):
        checks, code = self.doctor(expect=0)
        self.assertEqual((checks[("repo", "setup")]["status"], checks[("repo", "setup")]["fix"]),
                         ("warn", "/sdlc:setup"))

    def test_healthy_set_up_repo(self):
        self.setup_repo()
        checks, code = self.doctor(expect=0)
        for name in ("setup", "version", "plugin files", "commands", ".gitignore"):
            self.assertEqual(checks[("repo", name)]["status"], "ok", checks[("repo", name)])

    def test_commands_never_run_warn_until_run_commands(self):
        self.setup_repo()
        self.assertEqual(self.check("commands run")["status"], "warn")
        subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, "run-commands"], check=True,
                       capture_output=True, env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT})
        self.assertIsNone(self.check("commands run"))

    def test_old_layout_after_setup_warns_to_upgrade(self):
        self.setup_repo()
        self.assertIsNone(self.check("layout"))
        data = json.load(open(self.path(".sdlc/config.json")))
        del data["docs_dir"]
        self.write(".sdlc/config.json", json.dumps(data))
        found = self.check("layout")
        self.assertEqual(found["status"], "warn")
        self.assertIn("/sdlc:upgrade", found["fix"])

    def test_setup_in_progress(self):
        subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, "init", "--kind", "greenfield"],
                       check=True, capture_output=True)
        self.assertIn("in progress", self.check("setup")["detail"])

    def test_missing_commands_fail(self):
        self.setup_repo()
        self.configure(commands={"test": "git --version"})
        c = self.doctor(expect=1)[0][("repo", "commands")]
        self.assertEqual((c["status"], c["detail"]), ("fail", "no install, lint, typecheck, build command"))

    def test_command_tools_not_installed_warn(self):
        self.setup_repo()
        self.configure(commands={**COMMANDS, "lint": "nosuchlinter-xyz ."})
        c = self.check("command tools")
        self.assertEqual((c["status"], c["detail"]), ("warn", "not found on PATH: lint needs `nosuchlinter-xyz`"))

    def test_monorepo_commands_per_package(self):
        self.setup_repo()
        os.makedirs(self.path("services/api"))
        self.configure(commands={}, packages=[{"name": "api", "path": "services/api", "commands": COMMANDS},
                                              {"name": "web", "path": "apps/web", "commands": COMMANDS}])
        c = self.check("commands")
        self.assertEqual((c["status"], c["detail"]), ("fail", "web: path 'apps/web' does not exist"))
        os.makedirs(self.path("apps/web"))
        self.assertEqual(self.check("commands")["detail"], "defined for 2 packages")

    def test_version_drift(self):
        self.setup_repo()
        self.lock(scaffold_version="1.0.0")
        self.assertEqual(self.check("version")["fix"], "/sdlc:upgrade")
        self.write(".sdlc/config.json", json.dumps({"min_plugin_version": "99.0.0"}))
        checks, code = self.doctor(expect=1)
        self.assertEqual(checks[("repo", "version")]["status"], "fail")

    def test_corrupt_lock_fails(self):
        self.setup_repo()
        self.write(".sdlc/scaffold.lock.json", "{nope")
        self.assertEqual(self.doctor(expect=1)[0][("repo", "config and lock")]["status"], "fail")

    def test_missing_and_hand_edited_plugin_files(self):
        self.setup_repo()
        self.write(".claude/rules/sdlc.md", "x")
        self.write(".claude/hookify/sdlc-a.md", "y")
        subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, "record", "generated", ".claude/rules/sdlc.md"],
                       check=True, capture_output=True)
        subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, "record", "seeded", ".claude/hookify/sdlc-a.md"],
                       check=True, capture_output=True)
        self.write(".claude/rules/sdlc.md", "edited")
        os.remove(self.path(".claude/hookify/sdlc-a.md"))
        c = self.check("plugin files")
        self.assertEqual(c["status"], "warn")
        self.assertIn("missing: .claude/hookify/sdlc-a.md", c["detail"])
        self.assertIn("hand-edited", c["detail"])

    def test_brownfield_without_baseline(self):
        self.setup_repo("brownfield")
        self.assertEqual(self.check("baseline")["status"], "warn")
        self.write(".sdlc/baseline.md", "# baseline\n")
        self.assertEqual(self.check("baseline")["status"], "ok")

    def test_ui_without_design_system_warns(self):
        self.setup_repo()
        self.write("src/App.tsx", "export const App = () => null\n")
        self.assertEqual(self.check("design system")["status"], "warn")
        self.write("docs/sdlc/design-system.md", "# Design system\n")  # setup records docs_dir
        self.assertEqual(self.check("design system")["status"], "ok")

    def test_gitignore(self):
        self.setup_repo()
        self.write(".gitignore", "node_modules/\n")
        self.assertEqual(self.check(".gitignore")["status"], "warn")

    def test_rules_whose_paths_match_nothing(self):
        self.write("src/api/a.ts", "")
        self.write(".claude/rules/api.md", '---\npaths:\n  - "src/api/**/*.{ts,js}"\n---\n# API\n')
        self.write(".claude/rules/db.md", '---\npaths:\n  - "db/migrate/**"\n---\n# DB\n')
        self.write(".claude/rules/always.md", "# no paths: always loads\n")
        self.write(".claude/rules/sdlc-migrations.md", '---\npaths:\n  - "**/migrations/**"\n---\n# plugin policy\n')
        c = self.check("rules paths")  # plugin policy rules waiting for files to exist aren't reported
        self.assertEqual(c["status"], "warn")
        self.assertEqual(c["detail"], "match no files (never load): db.md")

    def test_hookify_rules_parse(self):
        self.write(".claude/hookify/ok.md", "---\nname: ok\nenabled: true\nevent: bash\npattern: rm\\s+-rf\naction: warn\n---\nmsg\n")
        self.assertEqual(self.check("hookify rules")["status"], "ok")
        self.write(".claude/hookify.bad.local.md", "---\nname: bad\nenabled: true\nevent: bash\npattern: (unclosed\naction: warn\n---\nmsg\n")
        c, code = self.doctor(expect=1)
        self.assertIn("hookify.bad.local.md", c[("repo", "hookify rules")]["detail"])

    def test_hookify_rules_that_would_never_fire_are_flagged(self):
        rule = "---\nname: r\nenabled: true\nevent: bash\naction: block\nconditions:\n  - field: command\n    operator: {op}\n    pattern: x\n---\nmsg\n"
        self.write(".claude/hookify/r.md", rule.format(op="regex_matc"))
        c, code = self.doctor(expect=1)
        self.assertIn("unknown operator", c[("repo", "hookify rules")]["detail"])

    def test_claude_md_budget(self):
        self.write("CLAUDE.md", "line\n" * 61)
        self.assertEqual(self.check("CLAUDE.md size")["fix"], "/sdlc:knowledge-audit")
        self.write("CLAUDE.md", "line\n" * 60)
        self.assertEqual(self.check("CLAUDE.md size")["status"], "ok")

    def test_agents_md_out_of_date_warns(self):
        self.setup_repo()
        self.configure(tools={"targets": ["codex"]})
        subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, "agents"], check=True, capture_output=True)
        self.assertEqual(self.check("AGENTS.md")["status"], "ok")
        self.write("CLAUDE.md", "Use pnpm.\n")
        self.assertEqual(self.check("AGENTS.md")["status"], "warn")

    def test_knowledge_index_links(self):
        self.write("knowledge/conventions/naming.md", "x")
        self.assertIn("no index.md", self.check("knowledge index")["detail"])
        self.write("knowledge/index.md", "- [Naming](conventions/naming.md)\n- [Gone](gotchas/gone.md)\n- [Site](https://x.dev)\n")
        self.assertEqual(self.check("knowledge index")["detail"], "broken links: gotchas/gone.md")

    def test_feature_state(self):
        self.write(".sdlc/a/state.md", "Status: active\nCurrent: Stage 4 – Implement\n")
        self.assertEqual(self.check("features")["status"], "ok")
        self.write(".sdlc/b/state.md", "Status: active\nCurrent: Stage 2 – Design\n")
        self.write(".sdlc/c/state.md", "# c\n")
        c = self.check("features")
        self.assertEqual(c["status"], "warn")
        self.assertIn("active: a, b", c["detail"])
        self.assertIn("missing Status/Current: c", c["detail"])

    def test_freshness_state(self):
        self.write(".sdlc/.work/verify-freshness.json", json.dumps({"feature": "a", "stale": True, "reason": "x edited"}))
        self.assertEqual(self.check("verify freshness")["detail"], "a: stale: x edited")
        self.write(".sdlc/.work/verify-freshness.json", "{bad")
        self.assertEqual(self.check("verify freshness")["status"], "warn")

    def test_freshness_hook_error_warns(self):
        self.write(".sdlc/.work/verify-freshness.error", "2026-10-23T00:00:00Z AttributeError: boom\n")
        c = self.check("verify freshness hook")
        self.assertEqual(c["status"], "warn")
        self.assertIn("AttributeError: boom", c["detail"])

    def test_doctor_changes_nothing(self):
        self.setup_repo("brownfield")
        before = sorted(os.path.relpath(os.path.join(d, f), self.root) for d, _, fs in os.walk(self.root) for f in fs)
        self.doctor()
        after = sorted(os.path.relpath(os.path.join(d, f), self.root) for d, _, fs in os.walk(self.root) for f in fs)
        self.assertEqual(before, after)

    def test_markdown_output(self):
        # A non-UTF-8 pipe, as on Windows (cp1252), must not crash on the status emoji
        p = subprocess.run([sys.executable, DOCTOR, "--root", self.root, "--format", "md"], capture_output=True,
                           text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "cp1252"})
        self.assertIn("| | Check | Detail | Fix |", p.stdout)
        self.assertIn("failing", p.stdout)


if __name__ == "__main__":
    unittest.main()
