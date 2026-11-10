"""Deploy targets: the default migration globs, the runbook template, setup's deploy step, /sdlc:deploy, the Cloud
Run platform reference and the templates that carry deploy and rollback."""
import json
import os
import re
import sys
import unittest

from helpers import PLUGIN_ROOT

sys.path.insert(0, os.path.join(PLUGIN_ROOT, "hooks"))
from sdlc_review_gate import _glob_re  # noqa: E402  (the review gate's own glob matcher, braces included)


def read(rel):
    with open(os.path.join(PLUGIN_ROOT, rel), encoding="utf-8") as f:
        return f.read()


def section(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


class DeployTargetsTest(unittest.TestCase):
    def test_default_migration_globs_cover_drizzle_alembic_flyway(self):
        globs = json.loads(read("templates/project/config.defaults.json"))["areas"]["migrations"]
        for path in ("drizzle/0001_init.sql", "alembic/versions/1a2b_add.py",
                     "src/main/resources/db/migration/V1__init.sql",
                     "prisma/migrations/x/migration.sql", "db/migrate/001.rb"):
            self.assertTrue(any(_glob_re(g).match(path) for g in globs), f"{path} not matched by {globs}")

    def test_runbook_template_has_its_sections(self):
        text = read("templates/knowledge/deploy-runbook.md")
        for heading in ("Environments", "Deploy", "Smoke test", "Rollback", "Logs", "Learnt on deploys"):
            self.assertRegex(text, rf"(?m)^## {heading}$")

    def test_setup_and_upgrade_run_the_deploy_step(self):
        skill = read("skills/setting-up-projects/SKILL.md")
        row = next((line for line in skill.splitlines() if line.startswith("| `deploy` |")), "")
        self.assertIn("$S deploy", row)
        self.assertIn("templates/knowledge/deploy-runbook.md", row)
        hard_stops = section(skill, "Hard stops (always ask)")
        self.assertIn("deploy target", hard_stops)
        migration = read("migrations/3.6.0-deploy-target.md")
        self.assertRegex(migration, r"(?m)^version: 3\.6\.0$")
        self.assertIn("$S deploy", migration.replace('scaffold.py" deploy', "$S deploy"))
        # the runbook is written only where `$S deploy` printed it, never when it's invalid (review r2 M-1)
        for text in (row, migration):
            self.assertIn("printed", text)
            self.assertIn("`invalid`", text)
        # /sdlc:setup deploy reaches the step in a set-up repo (review r2 M1)
        command = read("commands/setup.md")
        self.assertRegex(command, r'argument-hint: ".*\| deploy"')
        self.assertIn("Arguments are `deploy`", command)

    def test_deploy_command_follows_config_and_runbook(self):
        text = read("commands/deploy.md")
        self.assertIn("config.deploy", text)
        self.assertIn("`routine: true`", text)
        self.assertIn("## Learnt on deploys", text)
        # production keeps its go-ahead whatever the repo's config says, and only checked values are used (review r1)
        self.assertIn("whatever `routine` says", text)
        self.assertIn("`invalid`", text)
        for word in ("smoke test", "rollback"):
            self.assertRegex(text.lower(), rf"{word}[^.]*runbook|runbook[^.]*{word}")

    def test_cloud_run_reference_has_define_checks(self):
        checks = section(read("skills/orchestrator/references/platforms/gcp-cloud-run.md"), "Define checks")
        for needle in ("process memory", "--max-instances", "/cloudsql/", "Workload Identity Federation",
                       "printf '%s'", "X-Forwarded-For", "__session", "update-traffic"):
            self.assertIn(needle, checks)

    def test_templates_carry_deploy_and_rollback(self):
        self.assertIn("deploy and rollback", section(read("templates/change-template.md"), "Failure modes"))
        self.assertIn("deploy and rollback", read("skills/orchestrator/references/flow.md"))
        rule = read("templates/project/rules/migrations.md")
        self.assertIn("migrates before it moves traffic", rule)
        self.assertIn("new schema under the old code", rule)
        constitution = read("templates/constitution-template.md")
        self.assertRegex(constitution, r"(?m)^### .*Release")
        for needle in ("deploy script", "go-ahead", "secret"):
            self.assertIn(needle, section(constitution, "Core Principles").split("Release", 1)[-1])

    def test_integrations_hosting_row_names_gcp(self):
        row = next(line for line in read("skills/orchestrator/references/integrations.md").splitlines()
                   if "| Hosting |" in line)
        for needle in ("GCP", "Cloud Run", "Cloud SQL", "Firebase"):
            self.assertIn(needle, row)


if __name__ == "__main__":
    unittest.main()
