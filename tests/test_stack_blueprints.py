"""Stack blueprints folded into setup: how a stack is chosen, the sections, conventions and platforms."""
import os
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase, run_hook

sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))

REFS = ("skills", "setting-up-projects", "references")


def read_doc(*parts):
    with open(os.path.join(PLUGIN_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def section(text, heading):
    """The text under `heading` up to the next heading of the same or a higher level."""
    level = heading.split(" ", 1)[0]
    start = text.index(heading + "\n")
    rest = text[start + len(heading) + 1:]
    ends = [i for i in (rest.find("\n" + "#" * n + " ") for n in range(1, len(level) + 1)) if i >= 0]
    return rest[:min(ends)] if ends else rest


class Selection(unittest.TestCase):
    def test_choosing_a_stack_table(self):
        stacks = read_doc(*REFS, "stacks.md")
        self.assertLess(stacks.index("\n## Choosing a stack\n"), stacks.index("\n## Nuxt"))
        choosing = section(stacks, "## Choosing a stack").lower()
        for term in ("one deployable", "standalone api", "one web client", "no mobile app", "internal", "small",
                     "crud", "cpu-heavy", "realtime", "high load", "go", "typescript", "python", "nuxt",
                     "next.js", "flutter", "the user names"):
            self.assertIn(term, choosing, term)
        self.assertIn("|", choosing)  # a table, not prose

    def test_warnings(self):
        warnings = section(read_doc(*REFS, "stacks.md"), "### Warnings").lower()
        for term in ("typescript", "python", "small crud", "no web or mobile", "two native", "macos",
                     "cloudflare workers", "background", "vercel", "commercial", "vps", "backups"):
            self.assertIn(term, warnings, term)

    def test_stack_interview_applies_the_table(self):
        step = section(read_doc(*REFS, "greenfield.md"), "## `stack` – interview, then propose (hard stop)")
        low = step.lower()
        for term in ("outside", "heaviest", "workload", "scale", "choosing a stack", "reason", "warning",
                     "approves"):
            self.assertIn(term, low, term)
        for ref in ("monorepo.md", "workbench.md"):
            stack_step = section(read_doc(*REFS, ref), "## `stack` – interview, then propose (hard stop)")
            self.assertIn("Choosing a stack", stack_step, ref)


def stack_sections():
    """`stacks.md`'s `## ` sections, keyed by heading line."""
    return {s.split("\n", 1)[0].strip(): s for s in read_doc(*REFS, "stacks.md").split("\n## ")[1:]}


def stack_section(prefix):
    return next(v for k, v in stack_sections().items() if k.startswith(prefix))


class StackSections(unittest.TestCase):
    def test_new_sections(self):
        expected = {
            "Vue": ["Vite", "Vue Router", "Pinia", "create vue"],
            "Next.js": ["App Router", "create next-app"],
            "Flutter": ["Riverpod", "go_router", "flutter create"],
            "iOS": ["SwiftUI", "Swift OpenAPI Generator", "xcodebuild"],
            "Android": ["Jetpack Compose", "Hilt", "gradlew"],
            "FastAPI": ["Pydantic", "uv", "SQLAlchemy", "Alembic"],
        }
        for stack, pieces in expected.items():
            section = stack_section(stack)
            for piece in pieces:
                self.assertIn(piece, section, (stack, piece))
            self.assertIn("**Generator:**", section, stack)
            for command in ("install", "test", "lint", "typecheck", "build"):
                self.assertRegex(section, rf"\|\s*`{command}`\s*\|", (stack, command))

    def test_reconciled_sections(self):
        node = stack_section("Node")
        for term in ("@hono/zod-openapi", "@hono/zod-validator", "consumer", "contract"):
            self.assertIn(term, node, term)
        for web in ("Nuxt", "Next.js"):
            section = stack_section(web).lower()
            self.assertIn("one deployable", section, web)
            self.assertIn("bridge", section, web)
        stacks = read_doc(*REFS, "stacks.md").lower()
        for auth in ("better-auth", "better auth", "next-auth", "auth.js", "lucia", "clerk", "supabase auth",
                     "firebase auth", "auth0", "passport"):
            self.assertNotIn(auth, stacks, auth)


class CiToolchains(unittest.TestCase):
    def test_ci_sets_up_mobile_toolchains(self):
        import json
        import shutil
        import tempfile

        import scaffold  # noqa: E402
        root = tempfile.mkdtemp(prefix="sdlc-test-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, ".sdlc"))
        packages = [
            {"name": "mobile", "path": "apps/mobile", "stack": "flutter", "commands": {"test": "flutter test"}},
            {"name": "ios", "path": "apps/ios", "stack": "swift", "commands": {"test": "xcodebuild test"}},
            {"name": "android", "path": "apps/android", "stack": "kotlin",
             "commands": {"test": "./gradlew testDebugUnitTest"}},
        ]
        with open(os.path.join(root, ".sdlc", "config.json"), "w", encoding="utf-8") as f:
            json.dump({"packages": packages}, f)
        p = scaffold.Project(root)
        whole = scaffold.generate_ci(p)
        self.assertNotIn("# TODO", whole)
        for want in ("subosito/flutter-action", "actions/setup-java", "setup-xcode"):
            self.assertIn(want, whole, want)
        # Swift runs on macOS; a package without Swift keeps the default runner
        self.assertIn("macos-", scaffold.generate_ci(p, "ios"))
        self.assertNotIn("macos-", scaffold.generate_ci(p, "android"))
        self.assertIn("ubuntu-latest", scaffold.generate_ci(p, "android"))

    def test_swift_gets_its_own_macos_job(self):
        """A monorepo with an iOS app: only the Swift package runs on macOS, whatever ci.os the repo names."""
        import json
        import shutil
        import tempfile

        import scaffold  # noqa: E402
        root = tempfile.mkdtemp(prefix="sdlc-test-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, ".sdlc"))
        packages = [
            {"name": "ios", "path": "apps/ios", "stack": "swift", "commands": {"test": "xcodebuild test"}},
            {"name": "tools", "path": "tools", "stack": "shell", "commands": {"test": "bats tests"}},
        ]
        with open(os.path.join(root, ".sdlc", "config.json"), "w", encoding="utf-8") as f:
            json.dump({"packages": packages, "ci": {"os": ["windows-latest"]}}, f)
        ci = scaffold.generate_ci(scaffold.Project(root))
        jobs = ci.split("\n  verify")
        main = next(j for j in jobs if j.startswith(":"))
        mac = next(j for j in jobs if j.startswith("-macos:"))
        self.assertIn("windows-latest", main)
        self.assertNotIn("setup-xcode", main)
        self.assertNotIn("xcodebuild", main)
        self.assertIn("bats tests", main)
        self.assertIn('os: ["macos-latest"]', mac)
        self.assertIn("setup-xcode", mac)
        self.assertIn("xcodebuild test", mac)
        self.assertNotIn("bats tests", mac)
        self.assertNotIn("apt-get", mac)

    def test_packages_without_a_stack_use_the_project_stack(self):
        import json
        import shutil
        import tempfile

        import scaffold  # noqa: E402
        root = tempfile.mkdtemp(prefix="sdlc-test-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, ".sdlc"))
        packages = [{"name": "web", "path": "apps/web", "commands": {"test": "pnpm test"}},
                    {"name": "api", "path": "apps/api", "commands": {"test": "pnpm test"}}]
        for stack, want in ((["typescript"], "actions/setup-node"), (["swift"], "setup-xcode")):
            with open(os.path.join(root, ".sdlc", "config.json"), "w", encoding="utf-8") as f:
                json.dump({"packages": packages, "project": {"stack": stack}}, f)
            ci = scaffold.generate_ci(scaffold.Project(root))
            self.assertIn(want, ci, stack)
        self.assertIn('os: ["macos-latest"]', ci)


class Conventions(ProjectTestCase):
    def sc(self, *args, expect=0):
        code, out, raw, err = run_hook([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py"),
                                        "--root", self.root, *args], "", self.root)
        self.assertEqual(code, expect, f"{args}: {raw}{err}")
        return out

    def lock(self):
        import json
        with open(self.path(".sdlc/scaffold.lock.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_render_one_area(self):
        import json
        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        self.write(".sdlc/config.json", json.dumps({"packages": [
            {"name": "web", "path": "apps/web", "stack": "typescript"},
            {"name": "api", "path": "apps/api", "stack": "typescript"}]}))
        out = self.sc("conventions", "node", "layers", "--package", "api")
        dest = ".claude/rules/node-layers.md"
        self.assertEqual(out["rendered"], dest)
        with open(self.path(dest), encoding="utf-8") as f:
            text = f.read()
        globs = scaffold.rule_scope(text)
        self.assertTrue(globs and all(g.startswith("apps/api/") for g in globs), globs)
        self.assertNotIn("{{", text)
        lock = self.lock()
        self.assertNotIn(dest, lock.get("files", {}))  # user-owned: eject keeps it, upgrade never replaces it
        self.assertIn(dest, lock["declined"])
        entry = lock["conventions"][dest]
        self.assertEqual((entry["stack"], entry["area"], entry["package"]), ("node", "layers", "api"))
        self.assertEqual(entry["template"], "templates/project/conventions/node/layers.md")
        self.assertTrue(entry["version"] and entry["sha256"])
        # a second stack's same area gets its own file
        self.sc("conventions", "nuxt", "layers", "--package", "web")
        self.assertTrue(os.path.exists(self.path(".claude/rules/nuxt-layers.md")))

        def refused(*args):
            before = sorted(os.listdir(self.path(".claude/rules")))
            out = self.sc("conventions", *args, expect=2)
            self.assertEqual(sorted(os.listdir(self.path(".claude/rules"))), before, args)
            return out["refused"]

        self.assertIn("data-access", refused("node", "bogus", "--package", "api"))  # names the allowed areas
        self.assertIn("fastapi", refused("../evil", "layers", "--package", "api"))  # names the allowed stacks
        self.assertIn("ui", refused("nuxt", "schema", "--package", "web"))  # the areas nuxt has
        self.assertIn("api", refused("node", "schema", "--package", "nope"))  # the packages config has
        self.assertIn("exists", refused("node", "layers", "--package", "api"))  # never overwrites
        self.write(".claude/rules/go-auth.md", "mine\n")
        refused("go", "auth", "--package", "api")
        with open(self.path(".claude/rules/go-auth.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "mine\n")

    def test_deleted_convention_renders_again(self):
        self.sc("init", "--kind", "greenfield")
        self.sc("conventions", "go", "auth")
        os.remove(self.path(".claude/rules/go-auth.md"))
        self.assertEqual(self.sc("conventions", "go", "auth")["rendered"], ".claude/rules/go-auth.md")
        self.assertTrue(os.path.exists(self.path(".claude/rules/go-auth.md")))

    def test_malformed_lock_is_refused_before_any_write(self):
        import json

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        for field, bad in (("conventions", []), ("conventions", "x"), ("declined", {})):
            lock = dict(self.lock(), conventions={}, declined=[])
            lock[field] = bad
            with open(self.path(".sdlc/scaffold.lock.json"), "w", encoding="utf-8") as f:
                json.dump(lock, f)
            out = self.sc("conventions", "go", "auth", expect=2 if field == "conventions" else 1)
            self.assertIn(field, out.get("refused") or out["error"], field)  # declined: require_lock's error
            self.assertFalse(os.path.exists(self.path(".claude/rules/go-auth.md")), field)
            # upgrade's list reports the bad lock instead of crashing the whole plan
            if field == "conventions":  # a bad declined fails the lock check itself (LockSafety)
                items = scaffold.convention_updates(scaffold.Project(self.root))
                self.assertTrue(items and "error" in items[0], items)

    def test_upgrade_reports_an_unreadable_rule_per_item(self):
        import shutil
        from unittest import mock

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        self.sc("conventions", "go", "auth")
        self.sc("conventions", "go", "layers")
        with open(self.path(".claude/rules/go-auth.md"), "wb") as f:
            f.write(b"\xff\xfe not utf-8\n")
        plugin = os.path.join(self.root, "plugin-copy")
        shutil.copytree(os.path.join(PLUGIN_ROOT, "templates", "project", "conventions"),
                        os.path.join(plugin, "templates", "project", "conventions"))
        for area in ("auth", "layers"):
            with open(os.path.join(plugin, f"templates/project/conventions/go/{area}.md"), "a", encoding="utf-8") as f:
                f.write("- A new line.\n")
        with mock.patch.object(scaffold, "PLUGIN_ROOT", plugin):
            items = {i["path"]: i for i in scaffold.convention_updates(scaffold.Project(self.root))}
        self.assertIn("error", items[".claude/rules/go-auth.md"])
        self.assertIn("+- A new line.", items[".claude/rules/go-layers.md"]["diff"])

    def test_upgrade_offers_only_a_changed_template(self):
        import argparse
        import json
        import shutil
        from unittest import mock

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        self.sc("conventions", "go", "auth")
        plugin = os.path.join(self.root, "plugin-copy")
        shutil.copytree(os.path.join(PLUGIN_ROOT, "templates", "project", "conventions"),
                        os.path.join(plugin, "templates", "project", "conventions"))
        p = scaffold.Project(self.root)
        with mock.patch.object(scaffold, "PLUGIN_ROOT", plugin), \
                mock.patch.object(scaffold, "plugin_version", lambda: "99.0.0"):
            self.assertEqual(scaffold.convention_updates(p), [])  # a new release alone offers nothing
            with open(os.path.join(plugin, "templates/project/conventions/go/auth.md"), "a", encoding="utf-8") as f:
                f.write("- A new line.\n")
            [item] = scaffold.convention_updates(p)
            self.assertEqual(item["path"], ".claude/rules/go-auth.md")
            self.assertIn("+- A new line.", item["diff"])
            scaffold.cmd_conventions(p, argparse.Namespace(seen=".claude/rules/go-auth.md", stack=None, area=None,
                                                           package=None))
            self.assertEqual(scaffold.convention_updates(scaffold.Project(self.root)), [])
            # a lock entry whose path isn't its own stack-area name is never read
            lock = self.lock()
            lock["conventions"]["../outside.md"] = dict(lock["conventions"][".claude/rules/go-auth.md"], sha256="x")
            with open(self.path(".sdlc/scaffold.lock.json"), "w", encoding="utf-8") as f:
                json.dump(lock, f)
            self.assertEqual(scaffold.convention_updates(scaffold.Project(self.root)), [])

    def test_rendered_on_first_touch_not_at_setup(self):
        for parts in (REFS + ("greenfield.md",), REFS + ("monorepo.md",), REFS + ("workbench.md",),
                      ("skills", "setting-up-projects", "SKILL.md")):
            self.assertNotIn("scaffold.py conventions", read_doc(*parts), parts)
            self.assertNotIn("$S conventions", read_doc(*parts), parts)
        self.assertIn("no convention", read_doc(*REFS, "greenfield.md").lower())
        flow = section(read_doc("skills", "orchestrator", "references", "flow.md"), "## Define (Stage 1)")
        s_track = read_doc("skills", "orchestrator", "references", "s-track.md")
        for text in (flow, s_track):
            self.assertIn("scaffold.py\" conventions", text)
            self.assertIn("first touch", text.lower())


class Hardening(ProjectTestCase):
    """The conventions command against links, races, kills and a lock of the wrong shape."""
    sc, lock = Conventions.sc, Conventions.lock

    def write_lock(self, lock):
        import json
        with open(self.path(".sdlc/scaffold.lock.json"), "w", encoding="utf-8") as f:
            json.dump(lock, f)

    def test_rules_folder_linked_outside_is_refused(self):
        import shutil
        import tempfile
        self.sc("init", "--kind", "greenfield")
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        os.makedirs(self.path(".claude"), exist_ok=True)
        if os.path.isdir(self.path(".claude/rules")):
            shutil.rmtree(self.path(".claude/rules"))
        try:
            os.symlink(outside, self.path(".claude/rules"), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks here")
        self.assertIn("outside", self.sc("conventions", "go", "auth", expect=2)["refused"])
        self.assertEqual(os.listdir(outside), [])

    def test_rules_folder_on_another_drive_is_refused(self):
        import argparse
        from unittest import mock

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        with mock.patch.object(scaffold.os.path, "commonpath", side_effect=ValueError("Paths don't have the same drive")):
            with self.assertRaises(scaffold.Refused):
                scaffold.cmd_conventions(scaffold.Project(self.root), argparse.Namespace(
                    seen=None, stack="go", area="auth", package=None, one_deployable=False))
        self.assertFalse(os.path.exists(self.path(".claude/rules/go-auth.md")))

    def test_file_appearing_mid_render_is_kept(self):
        import argparse
        from unittest import mock

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        self.sc("conventions", "go", "auth")  # rendered once, then deleted by the user: its entry stays
        dest = self.path(".claude/rules/go-auth.md")
        os.remove(dest)
        before = self.lock()["conventions"][".claude/rules/go-auth.md"]
        real = scaffold.convention_text

        def racing(*args):  # another writer lands the file after the exists check
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write("mine\n")
            return real(*args)

        with mock.patch.object(scaffold, "convention_text", racing):
            with self.assertRaises(scaffold.Refused):
                scaffold.cmd_conventions(scaffold.Project(self.root), argparse.Namespace(
                    seen=None, stack="go", area="auth", package=None, one_deployable=False))
        with open(dest, encoding="utf-8") as f:
            self.assertEqual(f.read(), "mine\n")
        self.assertEqual(self.lock()["conventions"][".claude/rules/go-auth.md"], before)  # the lock as it was

    def test_render_killed_before_the_write_reruns(self):
        import argparse
        from unittest import mock

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        real = scaffold.Project.save

        def save_then_die(project):
            real(project)
            raise SystemExit("killed")

        with mock.patch.object(scaffold.Project, "save", save_then_die), self.assertRaises(SystemExit):
            scaffold.cmd_conventions(scaffold.Project(self.root), argparse.Namespace(
                seen=None, stack="go", area="auth", package=None, one_deployable=False))
        self.assertFalse(os.path.exists(self.path(".claude/rules/go-auth.md")))
        self.assertEqual(self.sc("conventions", "go", "auth")["rendered"], ".claude/rules/go-auth.md")

    def test_failed_write_without_hard_links_leaves_no_file(self):
        import argparse
        from unittest import mock

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        real_replace = os.replace

        def replace_fails_on_the_rule(src, dst):  # the lock's own saves go through
            if dst.endswith("go-auth.md"):
                raise OSError("disk full")
            return real_replace(src, dst)

        with mock.patch.object(scaffold.os, "link", side_effect=PermissionError("no hard links")), \
                mock.patch.object(scaffold.os, "replace", side_effect=replace_fails_on_the_rule), \
                self.assertRaises(OSError):
            scaffold.cmd_conventions(scaffold.Project(self.root), argparse.Namespace(
                seen=None, stack="go", area="auth", package=None, one_deployable=False))
        self.assertFalse(os.path.exists(self.path(".claude/rules/go-auth.md")))
        self.assertNotIn(".claude/rules/go-auth.md", self.lock()["conventions"])  # a failed write leaves no entry
        self.assertEqual(self.sc("conventions", "go", "auth")["rendered"], ".claude/rules/go-auth.md")

    def test_lock_of_the_wrong_shape_is_an_error(self):
        self.sc("init", "--kind", "greenfield")
        good = self.lock()
        for bad in ([], dict(good, files=[]), dict(good, declined=5)):
            self.write_lock(bad)
            for args in (("conventions", "go", "auth"), ("upgrade-plan",)):
                out = self.sc(*args, expect=1)
                self.assertIn("scaffold.lock.json", out["error"], (bad, args))
            self.assertFalse(os.path.exists(self.path(".claude/rules/go-auth.md")))

    def test_lock_root_is_checked_on_read(self):
        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        self.sc("conventions", "go", "auth")
        good = self.lock()
        for root in ("..", None):
            lock = dict(good)
            lock["conventions"] = {".claude/rules/go-auth.md": dict(good["conventions"][".claude/rules/go-auth.md"],
                                                                    root=root, sha256="stale")}
            self.write_lock(lock)
            self.assertEqual(scaffold.convention_updates(scaffold.Project(self.root)), [], root)
            self.sc("conventions", "--seen", ".claude/rules/go-auth.md", expect=2)

    def test_one_deployable_keeps_backend_globs(self):
        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        self.sc("conventions", "node", "layers", "--one-deployable")
        with open(self.path(".claude/rules/node-layers.md"), encoding="utf-8") as f:
            globs = scaffold.rule_scope(f.read())
        self.assertTrue(globs and all(g.startswith("backend/") for g in globs), globs)
        self.sc("conventions", "node", "schema", "--one-deployable")
        with open(self.path(".claude/rules/node-schema.md"), encoding="utf-8") as f:
            globs = scaffold.rule_scope(f.read())
        self.assertIn("drizzle.config.ts", globs)  # root-level config isn't the web app's
        self.assertFalse([g for g in globs if g.startswith("src/")], globs)
        self.assertIn("backend", self.sc("conventions", "nuxt", "ui", "--one-deployable", expect=2)["refused"])
        self.assertFalse(os.path.exists(self.path(".claude/rules/nuxt-ui.md")))
        # a lock entry marked one-deployable on a template with no backend/ paths: that item's error, not the plan's
        self.sc("conventions", "nuxt", "ui")
        lock = self.lock()
        lock["conventions"][".claude/rules/nuxt-ui.md"].update(one_deployable=True, sha256="stale")
        self.write_lock(lock)
        items = {i.get("path"): i for i in scaffold.convention_updates(scaffold.Project(self.root))}
        self.assertIn("error", items[".claude/rules/nuxt-ui.md"])


class LockSafety(ProjectTestCase):
    """run-commands keeps a concurrent change, no partial rule file, and every reader of the lock checks its shape."""
    sc, lock = Conventions.sc, Conventions.lock
    write_lock = Hardening.write_lock

    def test_run_commands_keeps_a_concurrent_change(self):
        import json
        self.sc("init", "--kind", "greenfield")
        self.write("edit_lock.py", "import json\n"
                   "p = '.sdlc/scaffold.lock.json'\n"
                   "lock = json.load(open(p, encoding='utf-8'))\n"
                   "lock.setdefault('declined', []).append('during.md')\n"
                   "json.dump(lock, open(p, 'w', encoding='utf-8'))\n"
                   "c = '.sdlc/config.json'\n"  # and the config, edited while the run goes on
                   "config = json.load(open(c, encoding='utf-8'))\n"
                   "config['design'] = 'builtin'\n"
                   "json.dump(config, open(c, 'w', encoding='utf-8'))\n")
        python = sys.executable.replace("\\", "/")
        if " " in python:
            self.skipTest("a Python path with a space can't be a bare shell command here")
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": f"{python} edit_lock.py"}}))
        self.sc("run-commands")
        lock = self.lock()
        self.assertIn("during.md", lock["declined"])
        self.assertTrue(lock["command_runs"])
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f).get("design"), "builtin")

    def test_killed_fallback_write_leaves_no_partial_file(self):
        import argparse
        from unittest import mock

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        real_fdopen, writes = os.fdopen, []

        class Dying:  # the second write of rule text is cut off halfway by a kill: no cleanup runs
            def __init__(self, f):
                self.f = f

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.f.close()

            def write(self, data):
                text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
                if not text.startswith("---"):  # the lock's own save
                    return self.f.write(data)
                writes.append(data)
                if len(writes) == 2:
                    self.f.write(data[:len(data) // 2])
                    self.f.flush()
                    raise SystemExit("killed")
                return self.f.write(data)

            def __getattr__(self, name):
                return getattr(self.f, name)

        with mock.patch.object(scaffold.os, "link", side_effect=PermissionError("no hard links")), \
                mock.patch.object(scaffold.os, "fdopen", lambda *a, **k: Dying(real_fdopen(*a, **k))), \
                mock.patch.object(scaffold.os, "remove", lambda *a: None):
            try:
                scaffold.cmd_conventions(scaffold.Project(self.root), argparse.Namespace(
                    seen=None, stack="go", area="auth", package=None, one_deployable=False))
            except SystemExit:
                pass
        # the only write is the temp file's, so the cut never lands on the rule: it arrives whole
        self.assertEqual(len(writes), 1, "the rule text should be written once, to the temp file")
        with open(self.path(".claude/rules/go-auth.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), scaffold.convention_text("templates/project/conventions/go/auth.md", "."))

    def test_every_reader_checks_the_lock(self):
        import json
        self.sc("init", "--kind", "greenfield")
        good = self.lock()
        self.write_lock([])
        for args in (("status",), ("design", "builtin")):
            self.assertIn("scaffold.lock.json", self.sc(*args, expect=1)["error"], args)
        self.write_lock(dict(good, files={".claude/rules/sdlc.md": 5}))
        self.assertIn("scaffold.lock.json", self.sc("upgrade-plan", expect=1)["error"])
        out = run_hook([sys.executable, os.path.join(PLUGIN_ROOT, "hooks", "session_status.py")],
                       json.dumps({"cwd": self.root}), self.root)[1]  # the session hook says so, not silence
        self.assertIn("unreadable", out["hookSpecificOutput"]["additionalContext"])
        self.sc("init", "--kind", "greenfield", "--force")
        self.sc("status")


class LockMerge(ProjectTestCase):
    """Concurrent saves merge, eject stays inside the repo, and the smaller lock tickets."""
    sc, lock = Conventions.sc, Conventions.lock
    write_lock = Hardening.write_lock

    def test_concurrent_saves_merge(self):
        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        a, b = scaffold.Project(self.root), scaffold.Project(self.root)  # both read the lock first
        a.require_lock()["declined"].append("a.md")
        a.save()
        b.require_lock()["declined"].append("b.md")
        b.require_lock()["files"]["b.txt"] = {"class": "seeded", "sha256": None, "template": None}
        b.save()
        lock = self.lock()
        self.assertIn("a.md", lock["declined"])
        self.assertIn("b.md", lock["declined"])
        self.assertIn("b.txt", lock["files"])
        # both add the same key the lock didn't have: each one's entries are kept
        c, d = scaffold.Project(self.root), scaffold.Project(self.root)
        c.require_lock().setdefault("conventions", {})["c.md"] = {"x": 1}
        c.save()
        d.require_lock().setdefault("conventions", {})["d.md"] = {"x": 2}
        d.save()
        self.assertEqual(set(self.lock()["conventions"]), {"c.md", "d.md"})
        # a list a command holds stays the one it saves, merge or not
        e, f = scaffold.Project(self.root), scaffold.Project(self.root)
        declined = f.require_lock()["declined"]
        e.require_lock()["declined"].append("e.md")
        e.save()
        declined.append("f.md")
        f.save()
        declined.remove("f.md")  # a rollback through the reference it held
        f.save()
        lock = self.lock()
        self.assertIn("e.md", lock["declined"])
        self.assertNotIn("f.md", lock["declined"])
        # a command that never reads the lock never rewrites it
        g, h = scaffold.Project(self.root), scaffold.Project(self.root)
        g.config["design"] = "builtin"
        h.require_lock()["declined"].append("h.md")
        h.save()
        g.save()
        self.assertIn("h.md", self.lock()["declined"])
        # one entry changed by both: the last writer's whole entry, never a mix
        i, j = scaffold.Project(self.root), scaffold.Project(self.root)
        i.require_lock()["files"]["b.txt"] = {"class": "generated", "sha256": "i", "template": "t1"}
        i.save()
        j.require_lock()["files"]["b.txt"] = {"class": "seeded", "sha256": "j", "template": None}
        j.save()
        self.assertEqual(self.lock()["files"]["b.txt"], {"class": "seeded", "sha256": "j", "template": None})
        # a collection below a section (setup.pending) merges key by key: two step-done runs both land
        k = scaffold.Project(self.root)
        k.require_lock()["setup"]["pending"] = {"x": "wait", "y": "wait"}
        k.save()
        m, n = scaffold.Project(self.root), scaffold.Project(self.root)
        del m.require_lock()["setup"]["pending"]["x"]
        m.save()
        del n.require_lock()["setup"]["pending"]["y"]
        n.save()
        self.assertEqual(self.lock()["setup"]["pending"], {})

    def test_removed_lock_is_not_recreated(self):
        import json

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        p = scaffold.Project(self.root)
        p.require_lock()["declined"].append("x.md")
        os.remove(self.path(".sdlc/scaffold.lock.json"))  # eject ran meanwhile
        with self.assertRaises(ValueError):
            p.save()
        self.assertFalse(os.path.exists(self.path(".sdlc/scaffold.lock.json")))
        # a lock broken meanwhile isn't overwritten with this command's older copy
        self.sc("init", "--kind", "greenfield", "--force")
        p = scaffold.Project(self.root)
        p.require_lock()["declined"].append("x.md")
        self.write(".sdlc/scaffold.lock.json", '{"files": [], "edited": "by hand"}')
        with self.assertRaises(ValueError):
            p.save()
        with open(self.path(".sdlc/scaffold.lock.json"), encoding="utf-8") as f:
            self.assertIn("by hand", f.read())
        # a write that fails, then a save that works: nothing this command did is dropped
        from unittest import mock
        self.sc("init", "--kind", "greenfield", "--force")
        p = scaffold.Project(self.root)
        p.require_lock()["declined"].append("first.md")
        with mock.patch.object(scaffold, "write_json", side_effect=OSError("disk full")), self.assertRaises(OSError):
            p.save()
        p.require_lock()["declined"].append("second.md")
        p.save()
        self.assertTrue({"first.md", "second.md"} <= set(self.lock()["declined"]))
        # run-commands keeps its results whatever the save raises
        import argparse
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "true"}}))
        with mock.patch.object(scaffold.Project, "save", side_effect=OSError("held open")), \
                mock.patch.object(scaffold, "resolves", lambda *a: False), \
                self.assertRaises(scaffold.CommandsFailed) as failed:
            scaffold.cmd_run_commands(scaffold.Project(self.root), argparse.Namespace(timeout=30))
        self.assertIn("held open", failed.exception.args[0]["lock_error"])
        # run-commands still prints what ran
        self.sc("init", "--kind", "greenfield", "--force")
        self.write("drop_lock.py", "import os\nos.remove('.sdlc/scaffold.lock.json')\n")
        python = sys.executable.replace("\\", "/")
        if " " in python:
            self.skipTest("a Python path with a space can't be a bare shell command here")
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": f"{python} drop_lock.py"}}))
        out = self.sc("run-commands", expect=1)
        self.assertTrue(out["scopes"])
        self.assertIn("scaffold.lock.json", out["lock_error"])

    def test_eject_stays_inside_the_repo(self):
        import shutil
        import tempfile
        self.sc("init", "--kind", "greenfield")
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        with open(os.path.join(outside, "keep.txt"), "w", encoding="utf-8") as f:
            f.write("not the plugin's\n")
        rel_out = os.path.relpath(os.path.join(outside, "keep.txt"), self.root).replace("\\", "/")
        good = self.lock()
        self.write_lock(dict(good, files=dict(good["files"], **{rel_out: {"class": "generated", "sha256": None}})))
        self.assertIn("scaffold.lock.json", self.sc("eject", "--apply", expect=1)["error"])
        self.assertTrue(os.path.exists(os.path.join(outside, "keep.txt")))
        try:  # a link out of the repo, named by a path that looks inside
            os.symlink(outside, self.path("linked"), target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        self.write_lock(dict(good, files=dict(good["files"], **{"linked/keep.txt": {"class": "generated",
                                                                                   "sha256": None}})))
        import scaffold  # noqa: E402
        from unittest import mock
        real_sha = scaffold.sha256

        def never_outside(path):  # the plan doesn't even read a file outside the repo
            self.assertNotIn(outside, os.path.realpath(path))
            return real_sha(path)

        with mock.patch.object(scaffold, "sha256", never_outside):
            self.assertIn("linked/keep.txt", scaffold.eject_plan(scaffold.Project(self.root))["outside"])
        out = self.sc("eject", "--apply")
        self.assertIn("linked/keep.txt", out["outside"])
        self.assertTrue(os.path.exists(os.path.join(outside, "keep.txt")))

    def test_empty_placeholder_renders_again(self):
        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        self.sc("conventions", "go", "auth")
        open(self.path(".claude/rules/go-auth.md"), "w").close()  # the interrupted render's empty placeholder
        self.assertEqual(self.sc("conventions", "go", "auth")["rendered"], ".claude/rules/go-auth.md")
        with open(self.path(".claude/rules/go-auth.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), scaffold.convention_text("templates/project/conventions/go/auth.md", "."))

    def test_config_and_null_lock_are_errors(self):
        import json
        self.sc("init", "--kind", "greenfield")
        config = self.path(".sdlc/config.json")
        with open(config, encoding="utf-8") as f:
            good = f.read()
        self.write(".sdlc/config.json", "[]")
        self.assertIn("config.json", self.sc("status", expect=1)["error"])
        lock_text = open(self.path(".sdlc/scaffold.lock.json"), encoding="utf-8").read()
        os.remove(self.path(".sdlc/scaffold.lock.json"))  # no lock: plain init must still not replace that config
        self.assertIn("config.json", self.sc("init", "--kind", "greenfield", expect=1)["error"])
        with open(config, encoding="utf-8") as f:
            self.assertEqual(f.read(), "[]")
        self.write(".sdlc/scaffold.lock.json", lock_text)
        out = run_hook([sys.executable, os.path.join(PLUGIN_ROOT, "hooks", "session_status.py")],
                       json.dumps({"cwd": self.root}), self.root)[1]
        self.assertIn("unreadable", out["hookSpecificOutput"]["additionalContext"])
        self.sc("init", "--kind", "greenfield", "--force")  # --force restarts over it
        with open(config, encoding="utf-8") as f:
            self.assertIsInstance(json.load(f), dict)
        self.write(".sdlc/config.json", good)
        self.write(".sdlc/scaffold.lock.json", "null")
        self.assertIn("scaffold.lock.json", self.sc("status", expect=1)["error"])
        self.sc("init", "--kind", "greenfield", expect=1)  # it exists: only --force restarts over it

    def test_stale_temp_files_are_swept(self):
        import time
        self.sc("init", "--kind", "greenfield")
        os.makedirs(self.path(".claude/rules"), exist_ok=True)
        self.write(".claude/rules/.sdlc-tmp-old", "left by a kill\n")
        self.write(".claude/rules/.sdlc-tmp-new", "another writer, mid-write\n")
        self.write(".claude/rules/.tmp-notes", "the user's own file\n")
        old = time.time() - 7200
        for name in (".sdlc-tmp-old", ".tmp-notes"):
            os.utime(self.path(".claude/rules/" + name), (old, old))
        self.sc("conventions", "go", "auth")
        self.assertFalse(os.path.exists(self.path(".claude/rules/.sdlc-tmp-old")))
        self.assertTrue(os.path.exists(self.path(".claude/rules/.sdlc-tmp-new")))
        self.assertTrue(os.path.exists(self.path(".claude/rules/.tmp-notes")))  # not ours: never swept

    def test_save_keeps_the_files_mode_and_links(self):
        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        lock = self.path(".sdlc/scaffold.lock.json")
        if os.name != "nt":
            os.chmod(lock, 0o644)
        p = scaffold.Project(self.root)
        p.require_lock()["declined"].append("x.md")
        p.save()
        if os.name != "nt":
            self.assertEqual(os.stat(lock).st_mode & 0o777, 0o644)
        import glob
        import stat
        os.chmod(lock, stat.S_IREAD)  # read-only: refused, not replaced, and no temp file left behind
        self.addCleanup(os.chmod, lock, stat.S_IREAD | stat.S_IWRITE)
        p = scaffold.Project(self.root)
        p.require_lock()["declined"].append("y.md")
        with self.assertRaises(OSError):
            p.save()
        os.chmod(lock, stat.S_IREAD | stat.S_IWRITE)
        self.assertNotIn("y.md", self.lock()["declined"])
        self.assertEqual(glob.glob(self.path(".sdlc/.sdlc-tmp-*")), [])
        real = self.path("shared-config.json")  # a config kept elsewhere, linked in
        os.replace(self.path(".sdlc/config.json"), real)
        try:
            os.symlink(real, self.path(".sdlc/config.json"))
        except (OSError, NotImplementedError):
            return
        p = scaffold.Project(self.root)
        p.config["design"] = "builtin"
        p.save()
        self.assertTrue(os.path.islink(self.path(".sdlc/config.json")))
        with open(real, encoding="utf-8") as f:
            self.assertIn("builtin", f.read())


class ConfigAndContainment(ProjectTestCase):
    """config.json merges like the lock, save temps stay in scratch, and links out of the repo aren't followed."""
    sc, lock = Conventions.sc, Conventions.lock
    write_lock = Hardening.write_lock

    def config(self):
        import json
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_config_saves_merge(self):
        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        a, b = scaffold.Project(self.root), scaffold.Project(self.root)
        a.config["design"] = "builtin"
        a.config["packages"] = [{"name": "web", "path": "apps/web"}]
        a.save()
        b.config["deploy"] = {"target": "vercel"}
        b.config["packages"] = [{"name": "web", "path": "apps/site"}]
        b.save()
        config = self.config()
        self.assertEqual(config["design"], "builtin")
        self.assertEqual(config["deploy"], {"target": "vercel"})
        self.assertEqual(config["packages"], [{"name": "web", "path": "apps/site"}])  # one whole list
        # a config removed meanwhile isn't recreated, and a config broken meanwhile stops the save before the lock
        c = scaffold.Project(self.root)
        c.config["design"] = "impeccable"
        os.remove(self.path(".sdlc/config.json"))
        with self.assertRaises(ValueError):
            c.save()
        self.assertFalse(os.path.exists(self.path(".sdlc/config.json")))
        self.write(".sdlc/config.json", '{"design": "builtin"}')
        d = scaffold.Project(self.root)
        d.config["design"] = "impeccable"
        d.require_lock()["declined"].append("d.md")
        self.write(".sdlc/config.json", "{not json")
        with self.assertRaises(ValueError):
            d.save()
        self.assertNotIn("d.md", self.lock()["declined"])
        # a read-only config refuses before the lock is written, too
        import stat
        self.write(".sdlc/config.json", '{"design": "builtin", "packages": [{"name": "web"}]}')
        e = scaffold.Project(self.root)
        e.config["design"] = "impeccable"
        e.require_lock()["declined"].append("e.md")
        os.chmod(self.path(".sdlc/config.json"), stat.S_IREAD)
        self.addCleanup(os.chmod, self.path(".sdlc/config.json"), stat.S_IREAD | stat.S_IWRITE)
        with self.assertRaises(OSError):
            e.save()
        os.chmod(self.path(".sdlc/config.json"), stat.S_IREAD | stat.S_IWRITE)
        self.assertNotIn("e.md", self.lock()["declined"])
        # a list this command holds stays the one it saves, even when another command replaced it
        f, g = scaffold.Project(self.root), scaffold.Project(self.root)
        pkgs = f.config["packages"]
        g.config["packages"] = [{"name": "api"}]
        g.save()
        f.config["design"] = "impeccable"
        f.save()
        pkgs.append({"name": "docs"})
        f.save()
        self.assertEqual(self.config()["packages"], [{"name": "api"}, {"name": "docs"}])

    def test_init_creates_no_scratch(self):
        self.sc("init", "--kind", "greenfield")
        self.assertTrue(os.path.exists(self.path(".sdlc/scaffold.lock.json")))
        self.assertFalse(os.path.exists(self.path(".sdlc/.work")))  # setup's gitignore step comes first

    def test_save_temp_stays_in_scratch(self):
        import glob
        from unittest import mock

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        os.makedirs(self.path(".sdlc/.work"), exist_ok=True)  # scratch is used once it exists
        p = scaffold.Project(self.root)
        p.require_lock()["declined"].append("x.md")
        real_replace = os.replace

        def killed(src, dst):  # the kill lands before the rename; no cleanup runs
            if dst.endswith("scaffold.lock.json"):
                raise SystemExit("killed")
            return real_replace(src, dst)

        with mock.patch.object(scaffold.os, "replace", killed), \
                mock.patch.object(scaffold.os, "remove", lambda *a: None), self.assertRaises(SystemExit):
            p.save()
        self.assertEqual(glob.glob(self.path(".sdlc/.sdlc-tmp-*")), [])
        self.assertTrue(glob.glob(self.path(".sdlc/.work/.sdlc-tmp-*")))
        # an old temp copy beside the lock (an earlier version's kill) is swept by the next save
        import errno
        import time
        self.write(".sdlc/.sdlc-tmp-old", "{}")
        old = time.time() - 7200
        os.utime(self.path(".sdlc/.sdlc-tmp-old"), (old, old))
        # and a scratch folder on another device falls back to a temp beside the file
        def cross_device(src, dst):
            if ".work" in src.replace("\\", "/"):
                raise OSError(errno.EXDEV, "Invalid cross-device link")
            return real_replace(src, dst)

        p = scaffold.Project(self.root)
        p.require_lock()["declined"].append("z.md")
        with mock.patch.object(scaffold.os, "replace", cross_device):
            p.save()
        self.assertIn("z.md", self.lock()["declined"])
        self.assertFalse(os.path.exists(self.path(".sdlc/.sdlc-tmp-old")))
        # a scratch folder that can't be used (here a file in its place) falls back beside the file
        import shutil
        shutil.rmtree(self.path(".sdlc/.work"))
        self.write(".sdlc/.work", "not a folder\n")
        p = scaffold.Project(self.root)
        p.require_lock()["declined"].append("w.md")
        p.save()
        self.assertIn("w.md", self.lock()["declined"])

    def test_links_out_are_not_followed(self):
        import shutil
        import tempfile
        from unittest import mock

        import scaffold  # noqa: E402
        self.sc("init", "--kind", "greenfield")
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        self.write("keep.txt", "")
        shutil.copy(self.path("keep.txt"), os.path.join(outside, "keep.txt"))
        try:
            os.symlink(outside, self.path("linked"), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("no symlinks here")
        lock = self.lock()
        lock["files"]["linked/keep.txt"] = {"class": "seeded", "sha256": "x",
                                            "template": "templates/project/rules/sdlc.md"}
        lock["files"]["linked/gone.md"] = {"class": "seeded", "sha256": "x", "template": "templates/no-such.md"}
        self.write_lock(lock)
        # .claude/rules linked out too: the tracked AGENTS mirror and new shipped rules there are outside
        rules_out = os.path.join(outside, "rules")
        os.makedirs(rules_out)
        with open(os.path.join(rules_out, "sdlc-agents-md.md"), "w", encoding="utf-8") as f:
            f.write("mirror\n")
        if os.path.isdir(self.path(".claude/rules")):
            shutil.rmtree(self.path(".claude/rules"))
        os.makedirs(self.path(".claude"), exist_ok=True)
        os.symlink(rules_out, self.path(".claude/rules"), target_is_directory=True)
        lock = self.lock()
        lock["files"][scaffold.AGENTS_MIRROR] = {"class": "generated", "sha256": "x", "template": "builtin:agents-mirror"}
        self.write_lock(lock)
        real_sha = scaffold.sha256

        def never_outside(path):
            self.assertNotIn(os.path.realpath(outside), os.path.realpath(path))
            return real_sha(path)

        with mock.patch.object(scaffold, "sha256", never_outside):
            p = scaffold.Project(self.root)
            status = scaffold.cmd_status(p, None)
            plan = scaffold.cmd_upgrade_plan(scaffold.Project(self.root), None)
        self.assertEqual(status["files"]["linked/keep.txt"]["state"], "outside")
        self.assertIn("linked/keep.txt", plan["outside"])
        self.assertIn("linked/gone.md", plan["outside"])  # never offered for deletion as template_gone
        self.assertNotIn("linked/gone.md", plan["template_gone"])
        self.assertFalse([i for i in plan["add"] if i["path"].startswith(".claude/rules/")], plan["add"])
        shutil.rmtree(self.path(".claude/rules")) if not os.path.islink(self.path(".claude/rules")) \
            else os.remove(self.path(".claude/rules")) if os.name != "nt" else os.rmdir(self.path(".claude/rules"))
        lock = self.lock()
        del lock["files"][scaffold.AGENTS_MIRROR], lock["files"]["linked/gone.md"]
        self.write_lock(lock)

        def outside_text():
            with open(os.path.join(outside, "keep.txt"), encoding="utf-8") as f:
                return f.read()

        before = outside_text()
        self.sc("render", "templates/project/rules/sdlc.md", "linked/keep.txt", expect=2)
        self.sc("record", "linked/keep.txt", expect=2)  # nor recorded (read) through the link
        self.assertEqual(outside_text(), before)
        # an edited guardrail reached through a link out is never deleted by a design swap
        os.makedirs(self.path(".claude"), exist_ok=True)
        hook_dir = os.path.join(outside, "hookify")
        os.makedirs(hook_dir)
        guard = os.path.join(hook_dir, scaffold.IMPECCABLE_REPLACES)
        with open(guard, "w", encoding="utf-8") as f:
            f.write("edited by the user\n")
        if os.path.isdir(self.path(".claude/hookify")):
            shutil.rmtree(self.path(".claude/hookify"))
        os.symlink(hook_dir, self.path(".claude/hookify"), target_is_directory=True)
        lock = self.lock()
        lock["files"][".claude/hookify/" + scaffold.IMPECCABLE_REPLACES] = {"class": "seeded", "sha256": "x",
                                                                         "template": None}
        self.write_lock(lock)
        with mock.patch.object(scaffold, "design_mode", lambda p: "impeccable"), \
                mock.patch.object(scaffold, "impeccable_status", lambda root: {"hook": True}):
            scaffold.swap_ui_guardrail(scaffold.Project(self.root))
        self.assertTrue(os.path.exists(guard))
        # upgrade-plan always lists outside, empty when nothing is
        hook_link = self.path(".claude/hookify")
        os.rmdir(hook_link) if os.name == "nt" else os.remove(hook_link)
        lock = self.lock()
        for key in [k for k in lock["files"] if k.startswith(("linked/", ".claude/hookify/"))]:
            del lock["files"][key]
        self.write_lock(lock)
        self.assertEqual(scaffold.cmd_upgrade_plan(scaffold.Project(self.root), None)["outside"], [])


class Platforms(ProjectTestCase):
    def test_define_checks_per_target(self):
        import json
        import subprocess
        needles = {"cloudflare": ("CPU", "Cron Triggers", "Hyperdrive", "interactive transactions"),
                   "vercel": ("Hobby", "maxDuration", "attachDatabasePool", "preview"),
                   "docker-compose": ("ufw", "backups", "restore", "previous image")}
        for target, words in needles.items():
            self.write(".sdlc/config.json", json.dumps({"deploy": {"target": target}}))
            p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "brief.py"), "--root", self.root],
                               capture_output=True, encoding="utf-8", errors="replace")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn(f"===== platform: {target}", p.stdout, target)
            self.assertIn(f"references/platforms/{target}.md", p.stdout, target)
            checks = p.stdout.split(f"===== platform: {target}", 1)[1].split(chr(10) + "===== ", 1)[0]
            for word in words:
                self.assertIn(word, checks, f"{target}: {word}")


class Constitution(unittest.TestCase):
    def test_stack_principles_and_roadmap(self):
        import re
        from scaffold import CONVENTION_STACKS
        principles = read_doc("skills", "project-constitution", "references", "stack-principles.md")
        for stack in ("Every stack",) + CONVENTION_STACKS:
            m = re.search(r"^## " + re.escape(stack) + r"\b.*?$(.*?)(?=^## |\Z)", principles, re.M | re.S)
            self.assertTrue(m, stack)
            self.assertIn("MUST", m.group(1), stack)
        self.assertIn("references/stack-principles.md", read_doc("skills", "project-constitution", "SKILL.md"))
        roadmap = read_doc("templates", "knowledge", "scaling-roadmap.md")
        for term in ("| Step | Trigger |", "Split the API", "Move hot paths to Go", "Extract a worker", "Add a BFF",
                     "Change hosting", "managed", "multi-tenancy", "sized L"):
            self.assertIn(term, roadmap, term)
        setup = read_doc("skills", "setting-up-projects", "SKILL.md")
        knowledge_step = next(line for line in setup.splitlines() if line.startswith("| `knowledge` |"))
        for term in ("templates/knowledge/scaling-roadmap.md", "knowledge/index.md", "greenfield.md"):
            self.assertIn(term, knowledge_step, term)
        self.assertIn("scaling-roadmap.md", read_doc(*REFS, "greenfield.md"))


if __name__ == "__main__":
    unittest.main()
