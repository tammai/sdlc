"""scripts/scaffold.py objects, review round 1 of 2026-11-17-l-objects-ui-and-setup: one path rule whether the switch
is on or off, an invalid value reported, and drafting inputs that never follow a link, never misread a name, and keep
the schema when they're cut."""
import json
import os
import shutil
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
TEMPLATE = os.path.join(PLUGIN_ROOT, "templates", "objects-template.md")
FILE = "docs/sdlc/objects.md"


def link(src, dst, directory=False):
    try:
        os.symlink(src, dst, target_is_directory=directory)
    except (OSError, NotImplementedError) as e:
        raise unittest.SkipTest(f"can't make a symlink here: {e}")


class ObjectsSetupReviewTest(ProjectTestCase):
    def sc(self, *args, expect=0):
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace", env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT})
        self.assertNotIn("Traceback", p.stderr)
        self.assertEqual(p.returncode, expect, p.stdout + p.stderr)
        return json.loads(p.stdout)

    def set_up_repo(self, **extra):
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.sc("init", "--kind", "brownfield", "--docs-dir", "docs/sdlc", "--host", "claude-code")
        self.sc("step-done", "finalize", "--complete")
        self.write_config(**extra)

    def write_config(self, **extra):
        cfg = self.config()
        cfg.update({"commands": {"test": "npm test"}, **extra})
        self.write(".sdlc/config.json", json.dumps(cfg))

    def config(self):
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            return json.load(f)

    def snapshot(self):
        out = {}
        for d, _, files in os.walk(self.root):
            if ".git" in d.split(os.sep):
                continue
            for f in files:
                with open(os.path.join(d, f), "rb") as fh:
                    out[os.path.relpath(os.path.join(d, f), self.root)] = fh.read()
        return out

    def git_add(self):
        subprocess.run(["git", "-C", self.root, "add", "-A"], check=True)

    def test_the_off_switch_path_follows_the_same_rule(self):
        # SEC-1/F1: with no objects key, a docs/sdlc/objects.md that links out of the repo is reported, never used
        self.set_up_repo()
        outside = os.path.realpath(self.root) + "-outside.md"
        shutil.copy(TEMPLATE, outside)
        self.addCleanup(os.remove, outside)
        os.makedirs(self.path("docs/sdlc"), exist_ok=True)
        link(outside, self.path(FILE))
        before = self.config()
        report = self.sc("objects")
        self.assertIsNone(report["path"])
        self.assertIn("outside the repo", report["invalid"])
        self.assertFalse(report["on"])
        out = self.sc("objects", "--enable", expect=2)
        self.assertIn("outside the repo", out["refused"])
        self.assertEqual(self.config(), before)

    def test_an_invalid_value_is_reported_and_a_plain_run_writes_nothing(self):
        # F6/F10: the report names the bad value and says off; without --enable nothing changes on disk
        self.set_up_repo(objects="../x.md")
        os.makedirs(self.path("docs/sdlc"), exist_ok=True)
        shutil.copy(TEMPLATE, self.path(FILE))
        before = self.snapshot()
        report = self.sc("objects")
        self.assertFalse(report["on"])
        self.assertIn("../x.md", report["invalid"])
        self.assertEqual(self.snapshot(), before)
        for bad in (0, 0.0, 1, "yes"):  # R2-2: only a missing key and false are off; anything else is judged
            with self.subTest(bad=bad):
                self.write_config(objects=bad)
                report = self.sc("objects")
                self.assertFalse(report["on"])
                self.assertIn("invalid", report)
                self.sc("objects", "--enable", expect=2)
        self.write_config(objects=False)
        self.assertNotIn("invalid", self.sc("objects"))
        self.write_config(objects="docs/sdlc/objects.md")  # a valid path value is kept by --enable
        self.sc("objects", "--enable")
        self.assertEqual(self.config()["objects"], "docs/sdlc/objects.md")
        self.write(".sdlc/config.json", "[1, 2]")  # config that isn't a JSON object: refused by name
        out = self.sc("objects", "--enable", expect=1)
        self.assertIn("config.json", json.dumps(out))

    def test_the_old_layouts_place_is_never_reached_through_a_link(self):
        # security R2-6: the new layout's docs/sdlc/objects.md linking to .sdlc/objects.md is refused
        self.set_up_repo()
        shutil.copy(TEMPLATE, self.path(".sdlc/objects.md"))
        os.makedirs(self.path("docs/sdlc"), exist_ok=True)
        link(self.path(".sdlc/objects.md"), self.path(FILE))
        report = self.sc("objects")
        self.assertIsNone(report["path"])
        self.assertIn(".sdlc", report["invalid"])

    def test_setup_still_in_progress_is_refused(self):
        # F9: --enable only in a set-up repo, not one whose setup is half done
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.sc("init", "--kind", "brownfield", "--docs-dir", "docs/sdlc", "--host", "claude-code")
        os.makedirs(self.path("docs/sdlc"), exist_ok=True)
        shutil.copy(TEMPLATE, self.path(FILE))
        out = self.sc("objects", "--enable", expect=2)
        self.assertIn("setup", out["refused"])

    def test_inputs_never_follow_a_link_or_misread_a_name(self):
        # SEC-2/F4/SEC-4: a tracked link, a name with a format character, and a non-ASCII name
        self.set_up_repo()
        self.write("models/données.py", "class Facture: pass\n")
        self.write("models/plain.py", "class Customer: pass\n")
        self.write("models/odd‮.py", "x\n")
        outside = os.path.realpath(self.root) + "-secret.env"
        with open(outside, "w") as f:
            f.write("SECRET=1\n")
        self.addCleanup(os.remove, outside)
        link(outside, self.path("models/user.py"))
        self.git_add()
        files = self.sc("objects")["inputs"]["files"]
        self.assertIn("models/données.py", files)
        self.assertIn("models/plain.py", files)
        self.assertNotIn("models/user.py", files)
        self.assertFalse(any("‮" in f for f in files), files)

    def test_inputs_keep_the_schema_and_say_what_was_cut(self):
        # F3/F5: ranked by kind, schema first; tests, docs and non-code files are left out; the cut is counted
        self.set_up_repo()
        for k in range(50):
            self.write(f"app/api/r{k:02d}/route.ts", "x\n")
        for rel in ("prisma/schema.prisma", "src/models.py", "src/user.entity.ts", "tests/api/test_x.py",
                    "docs/api/index.md", "assets/schema.png", "PRODUCT.md", "db/seeds.sql", "web/queries.graphql"):
            self.write(rel, "x\n")
        self.git_add()
        inputs = self.sc("objects")["inputs"]
        files = inputs["files"]
        self.assertEqual(files[0], "prisma/schema.prisma")
        self.assertIn("src/models.py", files)
        self.assertIn("src/user.entity.ts", files)
        self.write("app/schema.py", "x\n")  # R3-3/R3-4: a schema module and a model named like a seed stay inputs
        self.write("src/models/seedling.py", "x\n")
        self.git_add()
        inputs = self.sc("objects")["inputs"]
        files = inputs["files"]
        self.assertIn("app/schema.py", files)
        self.assertIn("src/models/seedling.py", files)
        # R2-3: a seed file or a query document never outranks the models
        for rel in ("db/seeds.sql", "web/queries.graphql"):
            if rel in files:
                self.assertGreater(files.index(rel), files.index("src/models.py"))
        for rel in ("tests/api/test_x.py", "docs/api/index.md", "assets/schema.png"):
            self.assertNotIn(rel, files)
        self.assertEqual(len(files), 40)
        self.assertEqual(inputs["more"], 56 - 40)  # seeds are left out; the query document is an input
        self.assertEqual(inputs["product"], "PRODUCT.md")


if __name__ == "__main__":
    unittest.main()
