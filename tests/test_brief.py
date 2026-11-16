"""scripts/brief.py: everything Define reads before the code, in one call."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "brief.py")


class BriefTest(ProjectTestCase):
    def brief(self, *args, env=None):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace", env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_prints_defines_inputs_and_cuts_long_files(self):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc", "commands": {"test": "npm test"}}))
        self.write("knowledge/index.md", "# Knowledge\n- decisions/store.md\n")
        self.write("README.md", "".join(f"line {i}\n" for i in range(250)))
        out = self.brief("2026-10-30-m-x")
        for title in ("paths", ".sdlc/config.json", "knowledge/index.md", "README.md", "change template"):
            self.assertIn(f"===== {title} =====", out)
        self.assertIn('"change": "docs/sdlc/changes/2026-10-30-m-x.md"', out)
        self.assertIn("- decisions/store.md", out)
        self.assertIn("===== docs/sdlc/prd.md =====\n(none)", out)  # missing: said, not skipped
        self.assertIn("line 199\n... (50 more lines: read the file for the rest)", out)
        self.assertNotIn("line 200\n", out)
        self.assertIn("## Acceptance tests", out)  # the plugin's change template
        # the builder gets the plugin's defect list too, not only the reviewer
        self.assertIn("===== plugin recurring defects =====\n# Recurring defects", out)

    def test_prints_platform_checks_only_for_a_known_target(self):
        self.write(".sdlc/config.json", json.dumps({"deploy": {"target": "gcp-cloud-run"}}))
        out = self.brief()
        self.assertIn("===== platform: gcp-cloud-run", out)
        self.assertIn("references/platforms/gcp-cloud-run.md", out)
        self.assertIn("--max-instances", out)  # the Define checks themselves
        for target in ("none", "heroku", "../platforms/gcp-cloud-run", "GCP-Cloud-Run"):
            self.write(".sdlc/config.json", json.dumps({"deploy": {"target": target}}))
            self.assertNotIn("===== platform", self.brief(), target)
        self.write(".sdlc/config.json", json.dumps({"deploy": "gcp-cloud-run"}))  # malformed: no crash, no section
        self.assertNotIn("===== platform", self.brief())

    def test_points_define_at_a_graphify_graph_only_when_the_repo_has_one(self):
        self.assertNotIn("graphify", self.brief())  # none: nothing said, nothing run
        self.write("graphify-out/graph.json", "{}")
        bin_dir = os.path.join(self.root, "bin")  # outside the brief's file reads: only PATH points at it
        tool = self.write("bin/graphify.bat" if os.name == "nt" else "bin/graphify", "exit 0\n")
        os.chmod(tool, 0o755)
        out = self.brief(env={**os.environ, "PATH": bin_dir + os.pathsep + os.environ.get("PATH", "")})
        self.assertIn("===== graphify graph: graphify-out/graph.json", out)
        self.assertIn('graphify query "<the request in a few words>"', out)
        self.assertIn("the code wins", out)
        out = self.brief(env={**os.environ, "PATH": os.path.join(self.root, "empty")})  # no graphify command
        self.assertIn("graphify-out/GRAPH_REPORT.md summarizes the graph", out)

    def test_prints_the_projects_rules_for_each_document(self):
        # #75: config's `rules`, keyed by the document they shape, printed beside the change template
        self.write(".sdlc/config.json", json.dumps({"rules": {
            "plan": ["Every task touching file paths adds a Windows check."], "review": ["No raw SQL."],
            "change": "not a list", "other": ["ignored"]}}))
        out = self.brief()
        self.assertIn("===== project rules (.sdlc/config.json `rules`) =====\n"
                      "plan:\n- Every task touching file paths adds a Windows check.\nreview:\n- No raw SQL.\n", out)
        self.assertNotIn("- ignored", out.split("===== project rules")[1])
        self.write(".sdlc/config.json", json.dumps({"rules": ["not", "a", "dict"]}))  # malformed: no section
        self.assertNotIn("===== project rules", self.brief())


if __name__ == "__main__":
    unittest.main()
