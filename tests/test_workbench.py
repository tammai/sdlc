"""The workbench (one repo per app under a parent workbench repo) and the scope parsing it builds on.

Record: .sdlc/2026-11-13-l-workbench/change.md (AC-001 onward)."""
import json
import os
import sys
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase

sys.path.insert(0, HOOKS)
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
import scaffold  # noqa: E402
import verify_freshness as vf  # noqa: E402

MONOREPO = {
    "commands": {"install": "pnpm install", "test": "pnpm -r test"},
    "packages": [
        {"name": "web", "path": "apps/web/", "stack": "node", "commands": {"test": "pnpm test", "lint": "pnpm lint"}},
        {"path": "./apps/api", "stack": "go", "commands": {"test": "go test ./..."}},
        {"name": "lib", "path": "packages/lib", "commands": {"test": "pnpm test"}},
    ],
}


class ScopeParsing(ProjectTestCase):
    def write_config(self, config):
        os.makedirs(self.path(".sdlc"), exist_ok=True)
        with open(self.path(".sdlc/config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f)

    def test_one_scope_parser_for_scripts_and_hooks(self):
        self.write_config(MONOREPO)
        script = [(sc["name"], sc["path"]) for sc in scaffold.scopes(MONOREPO)]
        hook = [(sc["name"], sc["path"]) for sc in vf.load_scopes(self.root, None)[0]]
        self.assertEqual(script, hook)
        self.assertEqual(script, [("web", "apps/web"), ("apps/api", "apps/api"), ("lib", "packages/lib")])
        # A package without a name is still reported by the contract check
        os.makedirs(self.path("apps/web")), os.makedirs(self.path("apps/api")), os.makedirs(self.path("packages/lib"))
        out = scaffold.cmd_contract(scaffold.Project(self.root), None)
        self.assertIn("package without a name", out["scopes"]["apps/api"]["problems"])
        # Malformed packages are named, never guessed at or a traceback
        for bad, msg in (({"packages": [1]}, r"packages\[0\]"),({"packages": {"web": {}}}, "not a list")):
            with self.assertRaisesRegex(ValueError, msg):
                scaffold.scopes(bad)

    def test_root_test_beside_packages_runs_and_covers_every_package(self):
        self.write_config(MONOREPO)
        plan = scaffold.verify_plan(MONOREPO)
        root_steps = [(s["step"], s["cwd"], s["run"]) for s in plan["install"] + plan["verify"]
                      if s["scope"] == scaffold.ROOT_SCOPE]
        self.assertEqual(root_steps, [("install", ".", "pnpm install"), ("test", ".", "pnpm -r test")])
        self.assertIn("pnpm -r test", scaffold.generate_ci(scaffold.Project(self.root)))
        # A package's own workflow leaves the root steps out
        self.assertNotIn("pnpm -r test", scaffold.generate_ci(scaffold.Project(self.root), "web"))
        scopes, root_tests = vf.load_scopes(self.root, None)
        self.assertEqual(vf.fresh_scopes("pnpm -r test", scopes, root_tests, self.root, self.root, True),
                         ["web", "apps/api", "lib"])

    def test_brownfield_reference_records_top_level_packages(self):
        path = os.path.join(PLUGIN_ROOT, "skills", "setting-up-projects", "references", "brownfield.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("→ `project` (`stack`, and `packages`", text)
        self.assertIn("top-level `packages`", text)


def git(cwd, *args):
    import subprocess
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args], cwd=cwd, check=True,
                   capture_output=True)


class WorkbenchTestCase(ProjectTestCase):
    """A workbench at self.root: a git repo whose config says `"workbench": true`."""

    def setUp(self):
        super().setUp()
        git(self.root, "init", "-q")
        self.write_json(".sdlc/config.json", {"workbench": True})

    def write_json(self, rel, data):
        os.makedirs(os.path.dirname(self.path(rel)) or self.root, exist_ok=True)
        with open(self.path(rel), "w", encoding="utf-8") as f:
            json.dump(data, f)

    def origin(self, name, config=None):
        """A bare-able source repo outside the workbench to clone from; returns its file URL."""
        import tempfile
        src = os.path.realpath(tempfile.mkdtemp(prefix=f"sdlc-origin-{name}-"))
        self.addCleanup(__import__("shutil").rmtree, src, ignore_errors=True)
        git(src, "init", "-q")
        if config is not None:
            os.makedirs(os.path.join(src, ".sdlc"))
            with open(os.path.join(src, ".sdlc", "config.json"), "w", encoding="utf-8") as f:
                json.dump(config, f)
        with open(os.path.join(src, "README.md"), "w", encoding="utf-8") as f:
            f.write(name)
        git(src, "add", "-A")
        git(src, "commit", "-q", "-m", "init")
        return src

    def gitignore(self):
        try:
            with open(self.path(".gitignore"), encoding="utf-8") as f:
                return f.read().splitlines()
        except FileNotFoundError:
            return []


class WorkbenchManifest(WorkbenchTestCase):
    def test_workbench_scopes_and_detection(self):
        import sdlc_scopes
        self.write_json("workbench.json", {"repos": [
            {"name": "api", "url": "u1", "role": "app", "write": True, "contract": {"provides": "v1"}},
            {"name": "web", "url": "u2", "role": "app", "write": True, "contract": {"consumes": "v1"}},
            {"name": "specs", "url": "u3", "role": "specs", "owner": "@org/ba"},
        ]})
        self.write_json("api/.sdlc/config.json", {"commands": {"test": "go test ./..."}, "project": {"stack": "go"}})
        self.assertTrue(sdlc_scopes.is_workbench(self.root))
        got = [(s["name"], s["path"], s["commands"].get("test")) for s in sdlc_scopes.workbench_scopes(self.root)]
        self.assertEqual(got, [("api", "api", "go test ./..."), ("web", "web", None),
                               (sdlc_scopes.WORKBENCH_SCOPE, ".", None)])
        # product-rebuild's repos.yaml alone, or no workbench key: not a workbench
        os.remove(self.path("workbench.json"))
        with open(self.path("repos.yaml"), "w", encoding="utf-8") as f:
            f.write("repos:\n  - name: api\n    path: ../api\n")
        self.assertFalse(sdlc_scopes.is_workbench(self.root))
        self.write_json(".sdlc/config.json", {"workbench": "yes"})
        self.write_json("workbench.json", {"repos": []})
        self.assertFalse(sdlc_scopes.is_workbench(self.root))
        # Malformed manifests are named, never a traceback
        self.write_json(".sdlc/config.json", {"workbench": True})
        for bad in ([], {"repos": None}, {"repos": [1]}, {"repos": [{"name": "api", "url": None, "role": "app"}]},
                    {"repos": [{"name": "api", "url": "u", "role": "boss"}]},
                    {"repos": [{"name": "api", "url": "u", "role": "specs", "write": True}]},
                    {"repos": [{"name": "api", "url": "u", "role": "app", "write": "yes"}]},
                    {"repos": [{"name": "a", "url": "u", "role": "app"}, {"name": "a", "url": "v", "role": "app"}]}):
            self.write_json("workbench.json", bad)
            with self.assertRaisesRegex(ValueError, "^not run: workbench.json"):
                sdlc_scopes.manifest(self.root)

    def run_scaffold(self, *args):
        import subprocess
        p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py"), "--root", self.root,
                            *args], capture_output=True, encoding="utf-8", errors="replace")
        return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout), p.stderr

    def test_workbench_add_and_remove(self):
        import sdlc_scopes
        url = self.origin("api", {"commands": {"test": "true"}})
        code, out, err = self.run_scaffold("workbench", "add", url, "--name", "api", "--role", "app", "--write",
                                           "--owner", "@org/backend")
        self.assertEqual(code, 0, (out, err))
        self.assertTrue(os.path.isfile(self.path("api/README.md")))
        self.assertIn("/api/", self.gitignore())
        [entry] = sdlc_scopes.manifest(self.root)
        self.assertEqual((entry["name"], entry["url"], entry["role"], entry["write"], entry["owner"]),
                         ("api", url, "app", True, "@org/backend"))
        # A read-only repo, named from its URL
        specs = self.origin("specs")
        code, out, err = self.run_scaffold("workbench", "add", specs, "--role", "specs")
        self.assertEqual(code, 0, (out, err))
        name = os.path.basename(specs)
        self.assertFalse(sdlc_scopes.manifest(self.root)[1]["write"])
        # remove: entry and gitignore line go, the folder stays
        code, out, err = self.run_scaffold("workbench", "remove", "api")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual([r["name"] for r in sdlc_scopes.manifest(self.root)], [name])
        self.assertNotIn("/api/", self.gitignore())
        self.assertTrue(os.path.isdir(self.path("api")))
        # Names that aren't plain folder names are refused and nothing is written
        def snapshot():
            with open(self.path("workbench.json"), encoding="utf-8") as f:
                return f.read(), self.gitignore()
        before = snapshot()
        for bad in ("@org/web", "a/b", "..", "a\\b", ".git", ".sdlc", ".claude", "C:x", "-x", ""):
            code, out, err = self.run_scaffold("workbench", "add", url, f"--name={bad}", "--role", "app")
            self.assertNotEqual(code, 0, bad)
            self.assertIn("not a plain folder name", json.dumps(out) + err, bad)
        self.assertEqual(before, snapshot())
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.root), "web")))
        # Outside a workbench: refused
        self.write_json(".sdlc/config.json", {})
        code, out, err = self.run_scaffold("workbench", "add", url, "--name", "web", "--role", "app")
        self.assertNotEqual(code, 0)
        self.assertIn("not a workbench", json.dumps(out) + err)

    def test_doctor_reports_workbench_drift(self):
        import doctor
        self.write_json("workbench.json", {"repos": [
            {"name": "api", "url": "u1", "role": "app", "write": True},
            {"name": "web", "url": "u2", "role": "app", "write": True},
            {"name": "specs", "url": "u3", "role": "specs"},
        ]})
        os.makedirs(self.path("api/.git")), os.makedirs(self.path("web/.git")), os.makedirs(self.path("stray/.git"))
        self.write_json("web/.sdlc/config.json", {"commands": {}})
        with open(self.path(".gitignore"), "w", encoding="utf-8") as f:
            f.write("/web/\nspecs\n")
        r = doctor.Report()
        doctor.check_workbench(r, self.root)
        rows = {c["check"]: c for c in r.checks}
        self.assertIn("specs", rows["workbench repos"]["detail"])  # listed, not cloned
        self.assertIn("stray", rows["workbench unlisted"]["detail"])
        self.assertIn("api", rows["workbench gitignore"]["detail"])
        self.assertNotIn("web", rows["workbench gitignore"]["detail"])
        self.assertIn("api", rows["workbench app setup"]["detail"])
        self.assertNotIn("web", rows["workbench app setup"]["detail"])
        # A malformed manifest is a failed row, not a crash; outside a workbench, no rows
        self.write_json("workbench.json", {"repos": [1]})
        r = doctor.Report()
        doctor.check_workbench(r, self.root)
        self.assertEqual([c["status"] for c in r.checks], ["fail"])
        self.write_json(".sdlc/config.json", {})
        r = doctor.Report()
        doctor.check_workbench(r, self.root)
        self.assertEqual(r.checks, [])


def block_rule(name, word, event="bash", field="command"):
    return (f"---\nname: {name}\nenabled: true\nevent: {event}\naction: block\nconditions:\n"
            f"  - field: {field}\n    operator: regex_match\n    pattern: {word}\n---\n{name} says no\n")


class WorkbenchGuards(WorkbenchTestCase):
    """A session started in the workbench (which has its own .sdlc/): api/ is a writable app repo with its own
    guardrails, specs/ another team's read-only repo."""

    def setUp(self):
        super().setUp()
        self.write_json("workbench.json", {"repos": [
            {"name": "api", "url": "u1", "role": "app", "write": True},
            {"name": "specs", "url": "u2", "role": "specs", "owner": "@org/ba"},
        ]})
        self.write_json("api/.sdlc/config.json", {"workbench": "shop-workbench", "commands": {}})
        self.write("api/.claude/hookify/no-x.md", block_rule("no-x", "forbidden"))
        self.write("api/.claude/hookify/no-secret.md", block_rule("no-secret", "SECRET", "file", "new_text"))
        self.write("specs/a.md", "spec\n")

    def pre(self, tool, cwd=None, **tool_input):
        from helpers import run_hook
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input,
                   "cwd": cwd or self.root}
        code, out, raw, err = run_hook(["python3", os.path.join(HOOKS, "pretooluse.py")], payload, self.root)
        self.assertEqual(code, 0, err)
        hso = (out or {}).get("hookSpecificOutput", {})
        return hso.get("permissionDecisionReason", "") if hso.get("permissionDecision") == "deny" else None

    def guard(self, path, agent):
        from helpers import run_hook
        payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Write",
                   "tool_input": {"file_path": path}, "agent_type": agent}
        code, out, raw, err = run_hook(["python3", os.path.join(HOOKS, "role_guard.py")], payload, self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def test_guards_route_into_an_app_repo_from_a_workbench(self):
        api = self.path("api")
        self.assertIn("no-x", self.pre("Bash", command="cd api && echo forbidden") or "")
        self.assertIn("no-x", self.pre("Bash", cwd=api, command="echo forbidden") or "")
        self.assertIn("no-secret", self.pre("Write", file_path=self.path("api/src/a.ts"), content="SECRET=1") or "")
        self.assertIsNone(self.pre("Write", file_path=self.path("docs/a.md"), content="SECRET=1"))
        # The role guard judges api's files against api, and the workbench's own findings folder stays open
        self.assertEqual(self.guard(self.path("api/src/a.ts"), "sdlc:code-reviewer"), "deny")
        self.assertIsNone(self.guard(self.path(".sdlc/.work/findings/f/r.md"), "sdlc:code-reviewer"))
        # A repo that isn't a workbench (no key, or the key without a manifest) behaves as before
        for config, manifest in (({}, True), ({"workbench": True}, False), ({"workbench": "yes"}, True)):
            self.write_json(".sdlc/config.json", config)
            if not manifest:
                os.remove(self.path("workbench.json"))
            self.assertIsNone(self.pre("Bash", command="cd api && echo forbidden"), config)
            self.assertIsNone(self.pre("Write", file_path=self.path("api/src/a.ts"), content="SECRET=1"), config)

    def test_writes_into_a_read_only_repo_are_denied(self):
        specs = self.path("specs")
        denied = [("Write", {"file_path": self.path("specs/b.md"), "content": "x"}),
                  ("Edit", {"file_path": "specs/a.md", "old_string": "spec", "new_string": "x"}),
                  ("Write", {"file_path": self.path("specs/deep/c.md"), "content": "x"}),
                  ("Bash", {"command": "echo hi > specs/a.md"}),
                  ("Bash", {"command": "cd specs && rm a.md"}),
                  ("Bash", {"command": "sed -i s/a/b/ specs/a.md"}),
                  ("Bash", {"command": "cp README.md specs/"}),
                  ("Bash", {"command": "mv specs/a.md ."}),
                  ("Bash", {"command": "touch specs/new.md"}),
                  ("Bash", {"command": "bash -c 'mkdir specs/x'"}),
                  ("Bash", {"command": f"git -C {specs} commit -am x"}),
                  ("Bash", {"command": "cd specs && git push origin main"}),
                  ("Bash", {"command": "rm -rf ./specs"}),
                  ("PowerShell", {"command": "Set-Content specs\\a.md x"})]
        if os.path.normcase("A") == "a" or sys.platform == "darwin":
            denied.append(("Write", {"file_path": self.path("SPECS/b.md"), "content": "x"}))
        for tool, tin in denied:
            reason = self.pre(tool, **tin)
            self.assertIsNotNone(reason, (tool, tin))
            self.assertIn("specs", reason)
            self.assertIn("@org/ba", reason)
        # Writes from inside the repo, and through a link to it
        self.assertIsNotNone(self.pre("Bash", cwd=specs, command="echo x > b.md"))
        os.symlink(specs, self.path("s2"))
        self.assertIsNotNone(self.pre("Write", file_path=self.path("s2/b.md"), content="x"))
        # Reads, and writes elsewhere, stay open
        for tool, tin in [("Bash", {"command": "cat specs/a.md"}), ("Bash", {"command": f"git -C {specs} log"}),
                          ("Bash", {"command": "cd specs && git pull"}),
                          ("Bash", {"command": "cp specs/a.md docs/a.md"}),
                          ("Write", {"file_path": self.path("api/a.ts"), "content": "x"}),
                          ("Write", {"file_path": self.path("specsx/a.md"), "content": "x"})]:
            self.assertIsNone(self.pre(tool, **tin), (tool, tin))
        # Not a workbench: no read-only repos
        self.write_json(".sdlc/config.json", {})
        self.assertIsNone(self.pre("Write", file_path=self.path("specs/b.md"), content="x"))

    def test_no_feature_starts_in_an_app_repo(self):
        import subprocess
        def new(root):
            p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "state.py"), "--root", root,
                                "new", "feat", "--track", "S", "--risk", "low", "--task", "x | AC-001 | a.py"],
                               capture_output=True, encoding="utf-8", errors="replace")
            return p.returncode, p.stdout
        api = self.path("api")
        before = sorted(os.listdir(os.path.join(api, ".sdlc")))
        code, out = new(api)
        self.assertEqual(code, 1, out)
        self.assertIn("shop-workbench", out)
        self.assertIn(self.root, json.loads(out)["error"])
        self.assertEqual(sorted(os.listdir(os.path.join(api, ".sdlc"))), before)
        # The workbench itself starts features
        code, out = new(self.root)
        self.assertEqual(code, 0, out)


def git_out(cwd, *args):
    import subprocess
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, encoding="utf-8",
                          errors="replace").stdout.strip()


CHECK = "import os, sys; sys.exit(1 if os.path.exists('broken') else 0)\n"


class WorkbenchFeature(WorkbenchTestCase):
    """A workbench on branch feat-x with a feature `feat`; api/ and web/ are writable app repos on main, specs/ a
    read-only repo."""

    def setUp(self):
        super().setUp()
        self.write_json("workbench.json", {"repos": [
            {"name": "api", "url": "u1", "role": "app", "write": True},
            {"name": "web", "url": "u2", "role": "app", "write": True},
            {"name": "specs", "url": "u3", "role": "specs"},
        ]})
        self.write(".gitignore", "/api/\n/web/\n/specs/\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "workbench")
        git(self.root, "checkout", "-q", "-b", "feat-x")
        for name in ("api", "web", "specs"):
            d = self.path(name)
            git(self.root, "init", "-q", "-b", "main", name)
            if name != "specs":
                self.write_json(f"{name}/.sdlc/config.json",
                                {"workbench": "shop-workbench", "commands": {"test": "python3 check.py"}})
                self.write(f"{name}/check.py", CHECK)
                self.write(f"{name}/.gitignore", ".sdlc/.work/\n")
            self.write(f"{name}/README.md", name)
            git(d, "add", "-A")
            git(d, "commit", "-q", "-m", "init")
        code, out = self.state("new", "feat", "--track", "M", "--risk", "low", "--task", "x | AC-001 | api/a.py")
        self.assertEqual(code, 0, out)

    def state(self, *args):
        import subprocess
        p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "state.py"), "--root", self.root,
                            *args], capture_output=True, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout

    def state_text(self):
        with open(self.path(".sdlc/feat/state.md"), encoding="utf-8") as f:
            return f.read()

    def test_build_branches_and_verifies_each_touched_repo(self):
        import sdlc_scopes
        import verify
        api_main = git_out(self.path("api"), "rev-parse", "HEAD")
        code, out = self.state("repo", "feat", "api")
        self.assertEqual(code, 0, out)
        self.assertEqual(git_out(self.path("api"), "rev-parse", "--abbrev-ref", "HEAD"), "feat-x")
        self.assertEqual(sdlc_scopes.feature_repos(self.state_text())["api"],
                         {"branch": "feat-x", "base": api_main})
        # Again: already recorded, nothing changes
        before = self.state_text()
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.assertEqual(self.state_text(), before)
        # A dirty repo is refused, naming it; no branch, nothing recorded
        self.write("web/wip.txt", "x")
        code, out = self.state("repo", "feat", "web")
        self.assertEqual(code, 1, out)
        self.assertIn("web", json.loads(out)["error"])
        self.assertIn("uncommitted", json.loads(out)["error"])
        self.assertEqual(git_out(self.path("web"), "rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertNotIn("web", sdlc_scopes.feature_repos(self.state_text()))
        # A read-only repo records the commit read; an unlisted name or a bad one is refused
        code, out = self.state("repo", "feat", "specs")
        self.assertEqual(code, 0, out)
        self.assertEqual(sdlc_scopes.feature_repos(self.state_text())["specs"],
                         {"read": git_out(self.path("specs"), "rev-parse", "HEAD")})
        for bad in ("nope", "../x", ".sdlc"):
            self.assertEqual(self.state("repo", "feat", bad)[0], 1, bad)
        # verify runs each touched repo's plan in its folder; a failure names the repo
        self.assertEqual(verify.repo_failures(self.root, "feat", 60), [])
        self.write("api/broken", "")
        failures = verify.repo_failures(self.root, "feat", 60)
        self.assertEqual(len(failures), 1, failures)
        self.assertTrue(failures[0].startswith("api: "), failures)

    def hook(self, event, tool=None, cwd=None, **tool_input):
        from helpers import run_hook
        payload = {"hook_event_name": event, "cwd": cwd or self.root}
        if tool:
            payload.update(tool_name=tool, tool_input=tool_input, tool_response={})
        code, out, raw, err = run_hook(["python3", os.path.join(HOOKS, "verify_freshness.py")], payload, self.root)
        self.assertEqual(code, 0, err)
        self.assertFalse(os.path.exists(self.path(".sdlc/.work/verify-freshness.error")),
                         open(self.path(".sdlc/.work/verify-freshness.error")).read()
                         if os.path.exists(self.path(".sdlc/.work/verify-freshness.error")) else "")
        return out

    def scopes(self):
        with open(self.path(".sdlc/.work/verify-freshness.json"), encoding="utf-8") as f:
            return json.load(f)["scopes"]

    def test_freshness_is_per_app_repo(self):
        for name in ("api", "web"):
            self.assertEqual(self.state("repo", "feat", name)[0], 0)
            self.write(f"{name}/a.py", "x = 1\n")
        self.assertEqual(self.state("advance", "feat", "3")[0], 0)
        self.hook("PostToolUse", "Edit", file_path=self.path("api/a.py"))
        st = self.scopes()
        self.assertTrue(st["api"]["stale"])
        self.assertIn("api/a.py", st["api"]["reason"])
        self.assertNotIn("api/a.py", st["web"].get("reason", ""))
        # A full test run in api/ makes only api fresh
        self.hook("PostToolUse", "Bash", command="cd api && python3 check.py")
        st = self.scopes()
        self.assertFalse(st["api"]["stale"])
        self.assertTrue(st["web"]["stale"])
        out = self.hook("Stop")
        self.assertIn("web:", out["reason"])
        self.assertNotIn("api:", out["reason"])
        # A change in api/ that no edit tool made is seen at the next stop, in api only
        self.write("api/a.py", "x = 2\n")
        out = self.hook("Stop")
        self.assertIn("api: api/a.py", out["reason"])
        # web's own run clears web, from its folder only
        self.hook("PostToolUse", "Bash", command="python3 check.py", cwd=self.path("web"))
        self.assertFalse(self.scopes()["web"]["stale"])

    def test_moved_read_only_repo_is_reported(self):
        import subprocess
        specs = self.path("specs")
        self.write("specs/b.md", "b")
        git(specs, "add", "-A")
        git(specs, "commit", "-q", "-m", "b")
        recorded = git_out(specs, "rev-parse", "HEAD")
        self.assertEqual(self.state("repo", "feat", "specs")[0], 0)

        def stats():
            p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "diff_stats.py"), "--root",
                                self.root, "--plan", self.path(".sdlc/feat/state.md")], capture_output=True,
                               encoding="utf-8", errors="replace")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            return json.loads(p.stdout)
        self.assertEqual(stats()["read_only"], [])
        self.write("specs/c.md", "c")
        git(specs, "add", "-A")
        git(specs, "commit", "-q", "-m", "c")
        current = git_out(specs, "rev-parse", "HEAD")
        r = stats()
        self.assertEqual(r["read_only"], [{"repo": "specs", "recorded": recorded, "current": current,
                                           "files": ["c.md"], "gone": False}])
        self.assertTrue(any("specs" in f and "moved" in f for f in r["flags"]), r["flags"])
        # Force-pushed: the recorded commit is gone
        git(specs, "reset", "-q", "--hard", "HEAD~2")
        git(specs, "reflog", "expire", "--expire=now", "--all")
        git(specs, "gc", "-q", "--prune=now")
        [moved] = stats()["read_only"]
        self.assertTrue(moved["gone"], moved)
        self.assertTrue(any("no longer exists" in f for f in stats()["flags"]))


if __name__ == "__main__":
    unittest.main()
