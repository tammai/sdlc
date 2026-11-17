"""scripts/objects.py: the opt-in domain model (objects.md), its file rules and the Avoid check on a change's ACs."""
import json
import os
import shutil
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "objects.py")
BRIEF = os.path.join(PLUGIN_ROOT, "scripts", "brief.py")
TEMPLATE = os.path.join(PLUGIN_ROOT, "templates", "objects-template.md")
FILE = "docs/sdlc/objects.md"
GOOD = """# Objects

## Objects

### Invoice
A request for payment sent to one Customer.
- UI name: Invoice, Invoices
- Code: Invoice (table invoices)
- States: `draft` → `sent` → `paid`; `sent` → `void`
- Actions: send (draft), void (sent)
- Shown as: InvoiceRow (list)

## Rules
- **DR-001** An Invoice in `paid` never changes its total.

## Avoid
- Bill, Receipt → Invoice
"""
CHANGE = "# c\n\n## Acceptance criteria\n\n- **AC-001** Given a bill, when it is sent, then it is `sent`.\n"
STATE = "# c\nStatus: active\nProcess: 3\nTrack: {track}\nCurrent: Stage 1 – Define\n"


class ObjectsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.config(objects=True)

    def config(self, **cfg):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc", **cfg}))

    def check(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "check", *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, json.loads(p.stdout)

    def codes(self, out, severity=None):
        return sorted(p["code"] for p in out["problems"] if severity in (None, p["severity"]))

    def test_the_template_passes_and_the_switch_off_reads_nothing(self):
        os.makedirs(os.path.dirname(self.path(FILE)))
        shutil.copy(TEMPLATE, self.path(FILE))
        self.assertEqual(self.check(), (0, {"ok": True, "problems": []}))
        self.config()  # no key: nothing is read, so even a broken file isn't seen
        self.write(FILE, "`undeclared`\n")
        self.assertEqual(self.check(), (0, {"ok": True, "problems": []}))

    def test_each_file_error_has_its_code_and_fails(self):
        code, out = self.check()
        self.assertEqual((code, self.codes(out)), (1, ["objects_missing"]))
        cases = {
            "objects_state_undeclared": GOOD.replace("void (sent)", "void (`sent`, `closed`)"),
            "objects_duplicate": GOOD + "\n## Objects\n\n### Invoice\nAgain.\n",
            "objects_avoided_name": GOOD.replace("- Bill, Receipt → Invoice", "- Invoice, Bill → Invoice"),
            "objects_rule_id": GOOD.replace("- **DR-001** An Invoice", "- **DR-001** One.\n- **DR-001** Two.\n"
                                            "- **DR-1** An Invoice"),
        }
        for expected, text in cases.items():
            with self.subTest(expected):
                self.write(FILE, text)
                code, out = self.check()
                self.assertEqual(code, 1, out)
                self.assertIn(expected, self.codes(out, "error"))
        self.write(FILE, GOOD.replace("- **DR-001** An Invoice", "- An Invoice"))  # a rule with no id is malformed
        self.assertIn("objects_rule_id", self.codes(self.check()[1], "error"))
        for value in ("../outside.md", ".git/objects.md", 7):  # repo config naming a file: refused, never read
            with self.subTest(value):
                self.config(objects=value)
                code, out = self.check()
                self.assertEqual((code, self.codes(out)), (1, ["objects_path_invalid"]))
        self.config(objects=True)
        with open(self.path(FILE), "wb") as f:
            f.write(b"\xff\xfe not utf-8")
        code, out = self.check()
        self.assertEqual((code, self.codes(out)), (1, ["objects_unreadable"]))

    def test_a_long_file_and_missing_ui_fields_warn(self):
        self.write(FILE, GOOD + "\nA note.\n" * 100)  # trailing blank lines don't count: brief.py drops them too
        code, out = self.check()
        self.assertEqual((code, self.codes(out, "warning")), (0, ["objects_too_long"]))
        self.write("src/components/InvoiceRow.tsx", "export {}\n")  # matches the default areas.ui
        subprocess.run(["git", "init", "-q", self.root], check=True)
        subprocess.run(["git", "-C", self.root, "add", "-A"], check=True)
        self.write(FILE, GOOD.replace("- Shown as: InvoiceRow (list)\n", ""))
        code, out = self.check()
        self.assertEqual((code, self.codes(out, "warning")), (0, ["objects_ui_fields"]))
        self.assertIn("Invoice", out["problems"][0]["message"])

    def test_an_avoid_word_in_the_criteria_warns_on_m_and_fails_on_l(self):
        self.write(FILE, GOOD)
        self.write("docs/sdlc/changes/c.md", CHANGE)
        self.write(".sdlc/state/c.md", STATE.format(track="M"))
        code, out = self.check("c")
        self.assertEqual((code, self.codes(out, "warning")), (0, ["objects_avoid_word"]))
        self.assertIn("Bill", out["problems"][0]["message"])
        self.write(".sdlc/state/c.md", STATE.format(track="L"))
        code, out = self.check("c")
        self.assertEqual((code, self.codes(out, "error")), (1, ["objects_avoid_word"]))
        self.write("docs/sdlc/changes/c.md", CHANGE.replace("a bill", "a billing run"))  # whole words only
        self.assertEqual(self.check("c"), (0, {"ok": True, "problems": []}))

    def test_a_spec_backed_repo_reads_rspecs_domain_file_instead(self):
        self.write("spec/criteria.lock.json", json.dumps({"spec": "spec", "criteria": []}))
        self.write("spec/domain.md", "# Domain rules\n\n`Operations` are not states here.\n")
        subprocess.run(["git", "init", "-q", self.root], check=True)
        subprocess.run(["git", "-C", self.root, "add", "-A"], check=True)
        self.assertEqual(self.check(), (0, {"ok": True, "problems": []}))
        p = subprocess.run([sys.executable, BRIEF, "--root", self.root], capture_output=True, encoding="utf-8",
                           errors="replace")
        self.assertIn("===== domain (rspec, read-only): spec/domain.md =====", p.stdout)
        self.assertNotIn("===== objects:", p.stdout)


if __name__ == "__main__":
    unittest.main()
