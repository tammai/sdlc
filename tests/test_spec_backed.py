"""Spec-backed change files (spec 03 S2) and spec questions (S10): ACs cite criteria from an rspec criteria lock."""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPTS = os.path.join(PLUGIN_ROOT, "scripts")
_spec = importlib.util.spec_from_file_location("contracts_v1", os.path.join(SCRIPTS, "contracts", "v1", "contracts.py"))
contracts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contracts)

LINES = {"F-APP-01.AC1": '- [ ] **F-APP-01.AC1** Given a user, when they sign in, then "Welcome" is shown. `[observed]`',
         "F-APP-01.AC2": '- [ ] **F-APP-01.AC2** Given a user, when they sign out, then "Bye" is shown. `[observed]`'}
# Fails until `done` exists: the feature's code
RUN = "python3 -c \"import os, sys; sys.exit(0 if os.path.exists('done') else 1)\""
BACKLOG = "| ID | Slice | ACs | Deps | Size | Status |\n|---|---|---|---|---|---|\n" \
          "| B1 | Sign in | AC-001 | — | S | done |\n| B2 | Sign out | AC-002 | — | S | in progress |\n"


class SpecBackedTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.write(".gitignore", ".sdlc/.work/\n")
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""}}))
        self.spec_text(LINES)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "spec")
        self.base = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], capture_output=True,
                                   encoding="utf-8").stdout.strip()

    # --- fixtures ---------------------------------------------------------------------------------------------

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True)

    def spec_text(self, lines):
        """The story file and the lock rspec writes from it (C3, contracts 1.1.0 lock paths)."""
        self.write("docs/specs/app/features/F-APP-01.md", "# F-APP-01 Sign in\n\n## Acceptance criteria\n\n" +
                   "\n".join(lines.values()) + "\n")
        self.write("docs/specs/app/criteria.lock.json", json.dumps({
            "contracts": "1.1.0", "spec": "docs/specs/app", "generated": "2026-11-08T10:00:00Z",
            "criteria": [{"id": cid, "feature": "F-APP-01", "file": "features/F-APP-01.md",
                          "text_sha256": contracts.criterion_text_sha256(line), "tag": "observed", "priority": "MVP",
                          "level": 0, "test": None, "departures": []} for cid, line in lines.items()]}, indent=2))

    def amend(self):
        """rspec's amend flow changed F-APP-01.AC1: its text, so its hash in the lock."""
        self.spec_text(dict(LINES, **{"F-APP-01.AC1": LINES["F-APP-01.AC1"].replace('"Welcome"', '"Welcome back"')}))

    def state(self, header="Track: L\nRisk: low\n", extra=""):
        self.write(".sdlc/login/state.md", f"# login\nStatus: active\nProcess: 3\n{header}Base: {self.base}\n"
                   "Current: Stage 2 – Build\n\n## Tasks\n\n1. t `tests/t.py` `done`\n\n## Public Surface\n\n- none\n\n"
                   f"{extra}## Gate log\n-\n\n## Deviations\n\n## Open questions\n-\n")

    def change(self, acs, out_of_scope=""):
        rows = [ac.split("**")[1] for ac in acs]
        table = "| AC | Test | Run |\n|---|---|---|\n" + "".join(f"| {ac} | tests/t.py › ok | `{RUN}` |\n" for ac in rows)
        self.write(".sdlc/login/change.md", "# Change\n\n## Acceptance criteria\n\n" + "\n".join(acs) +
                   "\n\n## Acceptance tests\n\n" + table + (f"\n## Out of scope\n\n{out_of_scope}\n" if out_of_scope else ""))
        self.write("tests/t.py", "")

    def run_script(self, name, *args):
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, name), "--root", self.root, *args],
                           capture_output=True, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr

    def verify(self, *args):
        return self.run_script("verify.py", "--feature", "login", *args)

    def built(self, acs):
        """Red for every AC, then the feature's code."""
        code, out = self.verify("red", *acs)
        self.assertEqual(code, 0, out)
        self.write("done", "")

    def read(self, rel):
        with open(self.path(rel), encoding="utf-8") as f:
            return f.read()

    # --- S2: trace ----------------------------------------------------------------------------------------

    def test_trace_names_an_id_the_lock_does_not_hold(self):
        self.state()
        self.change(["- **AC-001** → F-APP-01.AC1, F-APP-09.AC1"])
        code, out = self.verify("trace")
        self.assertEqual(code, 1, out)
        self.assertIn("F-APP-09.AC1 is not in the lock", out)

    def test_a_changed_criterion_is_stale(self):
        self.state()
        self.change(["- **AC-001** → F-APP-01.AC1"])
        self.assertEqual(self.run_script("state.py", "cite", "login", "F-APP-01.AC1")[0], 0)
        self.built(["AC-001"])
        code, out = self.verify()
        self.assertEqual(code, 0, out)
        self.amend()
        code, out = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("stale criterion: F-APP-01.AC1 changed since Define", out)

    def test_every_slice_criterion_is_cited_or_set_aside(self):
        self.state(header="Track: L\nRisk: low\nSlice criteria: F-APP-01.AC1 F-APP-01.AC2\n")
        self.change(["- **AC-001** → F-APP-01.AC1"])
        self.run_script("state.py", "cite", "login", "F-APP-01.AC1")
        self.built(["AC-001"])
        code, out = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("F-APP-01.AC2 is not covered", out)
        self.change(["- **AC-001** → F-APP-01.AC1"], out_of_scope="- F-APP-01.AC2: sign out comes with B3.")
        code, out = self.verify()
        self.assertEqual(code, 0, out)

    # --- S2: recording ------------------------------------------------------------------------------------------

    def test_cite_records_the_lock_hash(self):
        self.state()
        code, out = self.run_script("state.py", "cite", "login", "F-APP-01.AC1")
        self.assertEqual(code, 0, out)
        sha = contracts.criterion_text_sha256(LINES["F-APP-01.AC1"])
        self.assertIn(f"## Criteria\n- F-APP-01.AC1 sha256:{sha}", self.read(".sdlc/login/state.md").replace("\r\n", "\n"))
        code, out = self.run_script("state.py", "cite", "login", "F-APP-09.AC1")
        self.assertEqual(code, 1, out)

    def test_new_records_the_slice_criteria(self):
        code, out = self.run_script("state.py", "new", "2026-11-08-m-signin", "--track", "M", "--risk", "low",
                                    "--task", "t | AC-001 | a.py", "--criteria", "F-APP-01.AC1", "F-APP-01.AC2")
        self.assertEqual(code, 0, out)
        path = json.loads(out)["event"]["state"]
        self.assertIn("\nSlice criteria: F-APP-01.AC1 F-APP-01.AC2\n", self.read(path))

    def test_brief_prints_the_criteria_text(self):
        code, out = self.run_script("brief.py", "--criteria", "F-APP-01.AC1", "F-APP-09.AC1")
        self.assertEqual(code, 0, out)
        self.assertIn('then "Welcome" is shown.', out)
        self.assertIn("F-APP-09.AC1: not in the lock", out)

    # --- S10: spec questions ------------------------------------------------------------------------------

    def asked(self):
        self.state(extra="")
        self.write(".sdlc/login/backlog.md", BACKLOG)
        state = self.read(".sdlc/login/state.md").replace("Current:", "Slice: B2   Slice base: abc1234   Slice gates: none\nCurrent:", 1)
        self.write(".sdlc/login/state.md", state)
        self.run_script("state.py", "cite", "login", "F-APP-01.AC1")
        code, out = self.run_script("state.py", "question", "login", "F-APP-01.AC1", "Is the greeting localised?")
        self.assertEqual(code, 0, out)
        return ".sdlc/.work/spec-questions/login-SQ-0001.json"

    def test_a_spec_question_is_a_finding_and_blocks_the_part(self):
        found = self.asked()
        # contracts.py prints "→" without setting UTF-8 itself: a cp1252 console would crash it (reported upstream)
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "contracts", "v1", "contracts.py"), "finding",
                            self.path(found)], capture_output=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("SQ-0001", p.stdout)
        self.assertIn("rspec", p.stdout)
        self.assertEqual(json.loads(self.read(found))["question"], "Is the greeting localised?")
        self.assertIn("| B2 | Sign out | AC-002 | — | S | blocked: spec question SQ-0001 on F-APP-01.AC1 |",
                      self.read(".sdlc/login/backlog.md"))
        code, out = self.run_script("state.py", "question", "login", "F-APP-01.AC1", "Again?")
        self.assertEqual(code, 1, out)  # one open question per criterion: one amend answers it

    def test_an_amended_criterion_unblocks_the_part(self):
        found = self.asked()
        code, out = self.run_script("state.py", "questions", "login")
        self.assertEqual(json.loads(out)["open"], ["SQ-0001"])  # the lock hasn't changed yet
        self.amend()
        code, out = self.run_script("state.py", "questions", "login")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["resolved"], ["SQ-0001"])
        self.assertIn("| B2 | Sign out | AC-002 | — | S | todo |", self.read(".sdlc/login/backlog.md"))
        self.assertFalse(os.path.exists(self.path(found)))
        self.assertTrue(os.path.exists(self.path(".sdlc/.work/spec-questions/resolved/login-SQ-0001.json")))
        amended = contracts.criterion_text_sha256(LINES["F-APP-01.AC1"].replace('"Welcome"', '"Welcome back"'))
        self.assertIn(f"- F-APP-01.AC1 sha256:{amended}", self.read(".sdlc/login/state.md"))


if __name__ == "__main__":
    unittest.main()
