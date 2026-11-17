"""scripts/objects.py, review round 1 of 2026-11-17-l-domain-objects: where a path leads, git's answers, malformed
config, a feature the check can't read, and the Avoid list's spellings."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "objects.py")
BRIEF = os.path.join(PLUGIN_ROOT, "scripts", "brief.py")
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "hooks"))
import objects  # noqa: E402

FILE = "docs/sdlc/objects.md"
GOOD = ("# Objects\n\n## Objects\n\n### Invoice\nA bill.\n- Code: Invoice\n- States: `draft` → `sent`\n\n"
        "## Rules\n- **DR-001** A `sent` Invoice keeps its total.\n\n## Avoid\n- Bill, Receipt → Invoice\n")


def link(src, dst, directory=False):
    try:
        os.symlink(src, dst, target_is_directory=directory)
    except (OSError, NotImplementedError) as e:
        raise unittest.SkipTest(f"can't make a symlink here: {e}")


class ObjectsReviewTest(ProjectTestCase):
    def config(self, **cfg):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc", **cfg}))

    def check(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "check", *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        self.assertNotIn("Traceback", p.stderr)
        return p.returncode, json.loads(p.stdout)

    def codes(self, out, severity=None):
        return sorted(p["code"] for p in out["problems"] if severity in (None, p["severity"]))

    def git(self):
        subprocess.run(["git", "init", "-q", self.root], check=True)
        subprocess.run(["git", "-C", self.root, "add", "-A"], check=True)

    def test_a_path_is_judged_by_where_it_leads(self):
        # H1/S1: both branches resolve links; .git anywhere on the resolved path, and .claude or .sdlc named by a
        # string value, are refused, and nothing of them reaches the brief
        outside = os.path.realpath(self.root) + "-outside.md"
        with open(outside, "w", encoding="utf-8") as f:
            f.write("SECRET outside\n")
        self.addCleanup(os.remove, outside)
        os.makedirs(self.path("docs/sdlc"))
        link(outside, self.path(FILE))
        self.config(objects=True)
        self.assertEqual(self.codes(self.check()[1]), ["objects_path_invalid"])
        p = subprocess.run([sys.executable, BRIEF, "--root", self.root], capture_output=True, encoding="utf-8",
                           errors="replace")
        self.assertNotIn("SECRET", p.stdout)
        os.makedirs(self.path(".git"))
        self.write(".git/config", "[core]\n")
        link(os.path.join(self.root, ".git"), self.path("docs/g"), directory=True)
        self.config(objects="docs/g/config")
        self.assertEqual(self.codes(self.check()[1]), ["objects_path_invalid"])
        # R2-S1: true's file linked into .claude or .sdlc is refused too, and never printed
        for target in (".claude/settings.local.json", ".sdlc/notes.md"):
            with self.subTest(target):
                self.write(target, "SECRET inside\n")
                os.remove(self.path(FILE))
                link(self.path(target), self.path(FILE))
                self.config(objects=True)
                self.assertEqual(self.codes(self.check()[1]), ["objects_path_invalid"])
                p = subprocess.run([sys.executable, BRIEF, "--root", self.root], capture_output=True,
                                   encoding="utf-8", errors="replace")
                self.assertNotIn("SECRET", p.stdout)

    def test_every_path_rule_holds_where_a_link_leads_too(self):
        # R3-S1: one rule set on the written and the resolved path: a link to a non-.md file, or to a name with a
        # format character, is refused like the name itself would be; the old layout's file is allowed in any case
        self.write(".env", "SECRET=1\n")
        self.write("docs/notes​.md", "SECRET format char\n")
        os.makedirs(self.path("docs/sdlc"))
        for target in (".env", "docs/notes​.md"):
            with self.subTest(target):
                if os.path.lexists(self.path(FILE)):
                    os.remove(self.path(FILE))
                link(self.path(target), self.path(FILE))
                self.config(objects=True)
                self.assertEqual(self.codes(self.check()[1]), ["objects_path_invalid"])
                p = subprocess.run([sys.executable, BRIEF, "--root", self.root], capture_output=True,
                                   encoding="utf-8", errors="replace")
                self.assertNotIn("SECRET", p.stdout)

    def test_a_named_path_must_be_a_markdown_file_outside_sdlcs_own_folders(self):
        # R2-L4: these need no symlink, so they run everywhere
        for value in (".claude/objects.md", ".sdlc/objects.md", "docs/objects\n===== x =====.md", ".env",
                      "docs/objects.txt", "docs/objects\u0085.md", "docs/objects‮.md"):
            with self.subTest(value):
                self.config(objects=value)
                self.assertEqual(self.codes(self.check()[1]), ["objects_path_invalid"])
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs\n===== x =====", "objects": True}))
        self.assertEqual(self.codes(self.check()[1]), ["objects_path_invalid"])
        self.config(objects="docs/model.md")
        self.write("docs/model.md", GOOD)
        self.assertEqual(self.check(), (0, {"ok": True, "problems": []}))

    def test_the_objects_file_is_left_out_of_the_code_search_however_config_spells_it(self):
        # R2-L3: another case on Windows, or a link to the real file, still leaves the file's own names out
        self.write("docs/model.md", GOOD.replace("\n## Rules", "\n### Customer\nWho.\n- Code: Customer\n\n## Rules"))
        self.write("src/invoice.py", "class Invoice:\n    pass\n")
        self.git()
        spelled = "Docs/Model.md" if os.path.exists(self.path("Docs/Model.md")) else "docs/model.md"
        self.config(objects=spelled)
        self.assertEqual(objects.unused_code_names(self.root), ["Customer"])

    def test_the_old_layout_keeps_its_file_under_sdlc(self):
        self.write(".sdlc/config.json", json.dumps({"objects": True}))
        self.write(".sdlc/objects.md", GOOD)
        self.assertEqual(self.check(), (0, {"ok": True, "problems": []}))
        if os.path.exists(self.path(".sdlc/OBJECTS.md")):  # a case-insensitive file system: any case is the same file
            self.write(".sdlc/config.json", json.dumps({"objects": True, "docs_dir": ".SDLC"}))
            self.assertEqual(self.check()[0], 0)
            self.write(".sdlc/config.json", json.dumps({"objects": True}))
        # R4-M1/L1: the one place the folder rule is waived still follows a link, and says where it leads
        self.write(".env", "SECRET=1\n")
        os.remove(self.path(".sdlc/objects.md"))
        link(self.path(".env"), self.path(".sdlc/objects.md"))
        code, out = self.check()
        self.assertEqual((code, self.codes(out)), (1, ["objects_path_invalid"]))
        self.assertIn("leads to", out["problems"][0]["message"])

    def test_an_rspec_spec_folder_name_cant_fake_a_brief_section(self):
        # R4-L4: the lock's spec path reaches a section title only when it has no control or format character
        for spec in ("spec\n===== fake =====", "spec"):
            self.write(".sdlc/config.json", json.dumps({"objects": True}))
            self.write("lock/criteria.lock.json", json.dumps({"spec": spec, "criteria": []}))
            if "\n" not in spec:  # a folder name with a newline can't be made on Windows; the check mustn't need it
                self.write(f"{spec}/domain.md", "# Domain rules\n")
            self.git()
            p = subprocess.run([sys.executable, BRIEF, "--root", self.root], capture_output=True, encoding="utf-8",
                               errors="replace")
            self.assertNotIn("===== fake =====", p.stdout)
        self.assertIn("===== domain (rspec, read-only): spec/domain.md =====", p.stdout)

    def test_unused_code_names_read_gits_answer_right(self):
        # M1/S2: a quoted path, no git work tree and a link to elsewhere never make a used name look unused
        self.config(objects=True)
        self.write(FILE, GOOD.replace("\n## Rules", "\n### Customer\nWho.\n- Code: Customer\n\n## Rules"))
        self.write("src/café.py", "class Invoice:\n    pass\n")
        self.assertEqual(objects.unused_code_names(self.root), [])  # not a git work tree: no answer, no warning
        self.git()
        self.assertEqual(objects.unused_code_names(self.root), ["Customer"])

    def test_malformed_areas_and_config_give_json_not_a_traceback(self):
        self.write(FILE, GOOD)
        for areas in (["src"], "src", {"ui": "src/**"}, {"ui": [7]}):
            with self.subTest(areas=areas):
                self.config(objects=True, areas=areas)
                code, out = self.check()
                self.assertEqual(code, 0, out)

    def test_a_feature_the_check_cant_read_fails(self):
        # M3: a misspelled feature, or one whose track can't be read, is an error, never a silent pass
        self.config(objects=True)
        self.write(FILE, GOOD)
        code, out = self.check("no-such-feature")
        self.assertEqual((code, self.codes(out)), (1, ["objects_feature_missing"]))
        self.write("docs/sdlc/changes/c.md", "# c\n\n## Acceptance criteria\n\n- **AC-001** Given a bill, then x.\n")
        self.write(".sdlc/state/c.md", "# c\nStatus: active\nProcess: 3\nCurrent: Stage 1 – Define\n")
        code, out = self.check("c")
        self.assertEqual((code, self.codes(out, "error")), (1, ["objects_avoid_word"]))

    def test_avoid_lines_and_names_are_read_in_every_spelling(self):
        # L1/L2: an ASCII arrow works, a line without one is malformed, names compare in any case, spans stay on a line
        self.config(objects=True)
        self.write(FILE, GOOD.replace("- Bill, Receipt → Invoice", "- Bill -> Invoice"))
        self.write("docs/sdlc/changes/c.md", "# c\n\n## Acceptance criteria\n\n- **AC-001** Given a bill, then x.\n")
        self.write(".sdlc/state/c.md", "# c\nStatus: active\nProcess: 3\nTrack: M\nCurrent: Stage 1 – Define\n")
        self.assertEqual(self.codes(self.check("c")[1]), ["objects_avoid_word"])
        self.write(FILE, GOOD.replace("- Bill, Receipt → Invoice", "- Bill"))
        self.assertEqual(self.codes(self.check()[1], "error"), ["objects_avoid_line"])
        self.write(FILE, GOOD.replace("- Bill, Receipt → Invoice", "- invoice → Invoice"))
        self.assertEqual(self.codes(self.check()[1], "error"), ["objects_avoided_name"])
        self.write(FILE, GOOD + "\nA stray ` here\nand `sent` there.\n")
        msgs = [p["message"] for p in self.check()[1]["problems"]]
        self.assertTrue(all("\n" not in m for m in msgs), msgs)

    def test_an_invalid_path_still_gives_define_an_objects_section(self):
        # L4: the brief's section names objects, so Define adds the check to its gate, which then fails
        self.config(objects="../x.md")
        p = subprocess.run([sys.executable, BRIEF, "--root", self.root], capture_output=True, encoding="utf-8",
                           errors="replace")
        self.assertIn("===== objects: invalid (objects.py check says why) =====", p.stdout)


if __name__ == "__main__":
    unittest.main()
