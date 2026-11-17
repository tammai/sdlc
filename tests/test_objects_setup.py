"""scripts/scaffold.py objects: the domain model's setup step (spec 13, B4): report, inputs, switch on, eject keeps it."""
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


class ObjectsSetupTest(ProjectTestCase):
    def sc(self, *args, expect=0):
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace", env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT})
        self.assertNotIn("Traceback", p.stderr)
        self.assertEqual(p.returncode, expect, p.stdout + p.stderr)
        return json.loads(p.stdout)

    def set_up_repo(self):
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.sc("init", "--kind", "brownfield", "--docs-dir", "docs/sdlc", "--host", "claude-code")
        self.sc("step-done", "finalize", "--complete")
        cfg = self.config()
        cfg["commands"] = {"test": "npm test"}
        self.write(".sdlc/config.json", json.dumps(cfg))

    def config(self):
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            return json.load(f)

    def git_add(self):
        subprocess.run(["git", "-C", self.root, "add", "-A"], check=True)

    def test_enable_turns_the_switch_on_and_keeps_the_config(self):
        self.set_up_repo()
        os.makedirs(self.path("docs/sdlc"), exist_ok=True)
        shutil.copy(TEMPLATE, self.path(FILE))
        before = self.sc("objects")
        self.assertEqual((before["path"], before["exists"], before["on"]), (FILE, True, False))
        self.sc("objects", "--enable")
        cfg = self.config()
        self.assertIs(cfg.get("objects"), True)
        self.assertEqual(cfg["commands"], {"test": "npm test"})
        after = self.sc("objects")
        self.assertEqual((after["path"], after["exists"], after["on"]), (FILE, True, True))

    def test_enable_is_refused_and_changes_nothing(self):
        out = self.sc("objects", "--enable", expect=1)  # not set up
        self.assertIn("set up", json.dumps(out))
        self.set_up_repo()
        before = self.config()
        out = self.sc("objects", "--enable", expect=2)  # no file yet
        self.assertIn(FILE, json.dumps(out))
        self.write(FILE, "# Objects\n\n`stray`\n")  # a file the check fails
        out = self.sc("objects", "--enable", expect=2)
        self.assertIn("objects_state_undeclared", json.dumps(out))
        self.assertEqual(self.config(), before)
        shutil.copy(TEMPLATE, self.path(FILE))
        self.write("spec/criteria.lock.json", json.dumps({"spec": "spec", "criteria": []}))
        self.git_add()
        out = self.sc("objects", "--enable", expect=2)  # spec-backed: rspec's domain.md is the model there
        self.assertIn("domain.md", json.dumps(out))
        self.assertEqual(self.config(), before)

    def test_inputs_name_the_prd_and_schema_like_files_only(self):
        self.set_up_repo()
        self.write("docs/sdlc/prd.md", "# PRD\n")
        wanted = ["prisma/schema.prisma", "db/migrations/001_init.sql", "src/models/invoice.py", "src/types.ts",
                  "src/api.d.ts", "src/enums.py", "src/routes/invoices.ts", "app/api/invoices/route.ts"]
        for rel in wanted + ["src/util.ts", "README.md", "src/components/Button.tsx"]:
            self.write(rel, "x\n")
        for k in range(60):
            self.write(f"db/migrations/{k:03d}_more.sql", "x\n")
        self.git_add()
        inputs = self.sc("objects")["inputs"]
        self.assertEqual(inputs["prd"], "docs/sdlc/prd.md")
        files = inputs["files"]
        self.assertLessEqual(len(files), 40)
        for rel in wanted[2:] + wanted[:1]:
            self.assertIn(rel, files)
        for rel in ("src/util.ts", "README.md", "src/components/Button.tsx"):
            self.assertNotIn(rel, files)

    def test_eject_keeps_the_objects_file(self):
        self.set_up_repo()
        os.makedirs(self.path("docs/sdlc"), exist_ok=True)
        shutil.copy(TEMPLATE, self.path(FILE))
        plan = self.sc("eject")
        self.assertIn(FILE, plan["keep"])
        self.assertNotIn(FILE, plan["delete"])


if __name__ == "__main__":
    unittest.main()
