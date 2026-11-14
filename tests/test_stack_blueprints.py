"""Stack blueprints folded into setup: how a stack is chosen, the sections, conventions and platforms."""
import os
import sys
import unittest

from helpers import PLUGIN_ROOT

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


if __name__ == "__main__":
    unittest.main()
