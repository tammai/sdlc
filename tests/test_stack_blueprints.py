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


if __name__ == "__main__":
    unittest.main()
