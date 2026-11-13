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


if __name__ == "__main__":
    unittest.main()
