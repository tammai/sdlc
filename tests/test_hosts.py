"""scripts/hosts.py: Codex, Cursor and Antigravity files built from the Claude Code sources."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "hosts.py")


class HostsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write(".claude-plugin/plugin.json", json.dumps({"name": "sdlc", "version": "2.0.0", "description": "d"}))
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "sdlc", "plugins": []}))
        self.write("agents/reviewer.md", "---\nname: reviewer\ntools: Glob, Grep, Read, Bash\ndescription: Reviews.\n"
                                         "model: opus\n---\nReview it.\n")
        # Its Write is only for its findings report, which Cursor's flow doesn't read
        self.write("agents/code-reviewer.md", "---\nname: code-reviewer\ntools: Read, Write\ndescription: Checks.\n"
                                              "model: inherit\n---\nCheck it.\n")
        self.write("agents/qa-tester.md", "---\nname: qa-tester\ntools: Read, Bash, Write\ndescription: Tests.\n"
                                          "model: inherit\n---\nTest it.\n")

    def hosts(self, cmd):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, cmd], capture_output=True, encoding="utf-8")
        return p.returncode, json.loads(p.stdout)

    def read(self, rel):
        with open(self.path(rel), encoding="utf-8") as f:
            return f.read()

    def test_build_writes_every_host_and_check_catches_drift(self):
        self.assertEqual(self.hosts("build")[0], 0)
        self.assertEqual(self.hosts("check"), (0, {"stale": []}))
        for manifest in (".codex-plugin/plugin.json", ".cursor-plugin/plugin.json", "plugin.json"):
            self.assertEqual(json.loads(self.read(manifest))["version"], "2.0.0", manifest)
        self.assertEqual(self.read("hosts/cursor/agents/reviewer.md"),
                         "---\nname: reviewer\ndescription: Reviews.\nmodel: inherit\nreadonly: true\n---\nReview it.\n")
        self.assertNotIn("readonly", self.read("hosts/cursor/agents/qa-tester.md"))  # it writes its report
        self.assertIn("readonly: true", self.read("hosts/cursor/agents/code-reviewer.md"))
        self.write(".claude-plugin/plugin.json", json.dumps({"name": "sdlc", "version": "2.1.0", "description": "d"}))
        code, out = self.hosts("check")
        self.assertEqual(code, 1)
        self.assertIn(".codex-plugin/plugin.json", out["stale"])

    def test_commands_become_skills_for_codex_and_antigravity(self):
        # Neither loads a command that takes $ARGUMENTS; the hook-driven ones can't work without hooks
        self.write("commands/start.md", "---\ndescription: Start a feature.\nargument-hint: \"[what]\"\n---\n"
                                        "Status: !`git status`\n\nRequest: $ARGUMENTS\n")
        self.write("commands/ralph-loop.md", "---\ndescription: Loop.\n---\nLoop.\n")
        self.assertEqual(self.hosts("build")[0], 0)
        self.assertEqual(self.read("hosts/skills/start/SKILL.md"),
                         "---\nname: start\ndescription: Start a feature.\n---\n"
                         "Status: run `git status`\n\nRequest: <the user's request>\n")
        self.assertFalse(os.path.exists(self.path("hosts/skills/ralph-loop")))
        codex = json.loads(self.read(".codex-plugin/plugin.json"))
        self.assertIn("./hosts/skills/", codex["skills"])
        self.assertNotEqual(codex["commands"], "./commands/")  # else Codex adds its own copies of some
        self.assertEqual(json.loads(self.read("plugin.json"))["skills"], "./hosts/skills/")

    def test_stray_file_in_hosts_skills_is_ignored(self):
        # macOS writes .DS_Store into any folder Finder opens
        self.assertEqual(self.hosts("build")[0], 0)
        self.write("hosts/skills/.DS_Store", "x")
        self.assertEqual(self.hosts("check"), (0, {"stale": []}))
        self.assertEqual(self.hosts("build"), (0, {"written": []}))
        self.assertTrue(os.path.isfile(self.path("hosts/skills/.DS_Store")))

    def test_folder_without_skill_md_in_hosts_skills_is_ignored(self):
        self.assertEqual(self.hosts("build")[0], 0)
        self.write("hosts/skills/notes/README.md", "x")
        self.assertEqual(self.hosts("check"), (0, {"stale": []}))
        self.assertEqual(self.hosts("build"), (0, {"written": []}))
        self.assertTrue(os.path.isfile(self.path("hosts/skills/notes/README.md")))

    def test_stray_entries_in_cursor_agents_are_ignored(self):
        self.assertEqual(self.hosts("build")[0], 0)
        self.write("hosts/cursor/agents/.DS_Store", "x")
        self.write("hosts/cursor/agents/drafts.md/note.txt", "x")  # a folder, even one named like an agent
        self.assertEqual(self.hosts("check"), (0, {"stale": []}))
        self.assertEqual(self.hosts("build"), (0, {"written": []}))
        self.assertTrue(os.path.isfile(self.path("hosts/cursor/agents/.DS_Store")))

    def test_removed_command_and_agent_are_still_deleted(self):
        self.write("commands/old.md", "---\ndescription: Old.\n---\nOld.\n")
        self.assertEqual(self.hosts("build")[0], 0)
        os.remove(self.path("commands/old.md"))
        os.remove(self.path("agents/reviewer.md"))
        code, out = self.hosts("check")
        self.assertEqual(code, 1)
        self.assertEqual(sorted(out["stale"]), ["hosts/cursor/agents/reviewer.md", "hosts/skills/old/SKILL.md"])
        self.assertEqual(self.hosts("build")[0], 0)
        self.assertFalse(os.path.exists(self.path("hosts/skills/old")))
        self.assertFalse(os.path.exists(self.path("hosts/cursor/agents/reviewer.md")))

    def test_antigravity_dist_converts_the_agents_it_would_skip(self):
        out = os.path.join(self.root, "dist")
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "dist", "antigravity", out],
                           capture_output=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        with open(os.path.join(out, "agents", "reviewer.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "---\nname: reviewer\ndescription: Reviews.\nmodel: inherit\n"
                                       "tools: [\"Glob\", \"Grep\", \"Read\", \"Bash\"]\n---\nReview it.\n")
        self.assertTrue(os.path.exists(os.path.join(out, "plugin.json")))
        with open(self.path("agents/reviewer.md"), encoding="utf-8") as f:
            self.assertIn("model: opus", f.read())  # the Claude Code source is untouched


# Stands in for hosts/hook.py: reports what reached it, and exits 3 so the test sees the exit code come back
FAKE_HOOK = ("import json, sys\n"
             "print(json.dumps({'argv': sys.argv[1:], 'stdin': json.loads(sys.stdin.buffer.read().decode('utf-8'))}))\n"
             "sys.exit(3)\n")
EVENT = '{"tool_name": "Shell", "command": "echo café"}'
# The part of cursor-agent 2026.11.22's hook script that runs the command: the event is piped into the command's
# first statement, and the exit code is $LASTEXITCODE afterwards
CURSOR_WRAPPER = ("$OutputEncoding = [System.Text.UTF8Encoding]::new($false)\n"
                  "$__cursorCommand = {{\nGet-Content -LiteralPath '{payload}' -Raw -Encoding UTF8 | & {{ $input | "
                  "{command} }}\n}}\n. $__cursorCommand | Out-Default\nexit $LASTEXITCODE\n")


class CursorHookCommandTest(ProjectTestCase):
    """The Cursor hook command, run the way Cursor runs it: under sh, and on Windows as a Windows PowerShell 5.1
    script file (cursor-agent 2026.11.22), with ${CURSOR_PLUGIN_ROOT} replaced by the plugin's folder."""

    def setUp(self):
        super().setUp()
        self.write(".claude-plugin/plugin.json", json.dumps({"name": "sdlc", "version": "2.0.0", "description": "d"}))
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "sdlc", "plugins": []}))
        os.makedirs(self.path("agents"))
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "build"], capture_output=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.write("hosts/hook.py", FAKE_HOOK)
        launcher = os.path.join(PLUGIN_ROOT, "hosts", "cursor", "hook.ps1")
        if os.path.exists(launcher):
            with open(launcher, encoding="utf-8") as f:
                self.write("hosts/cursor/hook.ps1", f.read())
        with open(self.path("hosts/cursor/hooks.json"), encoding="utf-8") as f:
            command = json.load(f)["hooks"]["preToolUse"][0]["command"]
        self.command = command.replace("${CURSOR_PLUGIN_ROOT}", self.root)

    def check(self, p):
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout), {"argv": ["cursor", "PreToolUse"], "stdin": json.loads(EVENT)})

    def test_the_command_runs_the_hook_under_sh(self):
        from helpers import BASH
        p = subprocess.run([BASH, "-c", self.command], input=EVENT, capture_output=True, encoding="utf-8")
        self.check(p)

    @unittest.skipUnless(os.name == "nt", "Cursor runs hooks through Windows PowerShell only on Windows")
    def test_on_windows_powershell_the_command_skips_a_python3_that_is_the_store_stub(self):
        # The Microsoft Store stub: on PATH as python3, prints where to get Python and exits 9009
        self.write("stub/python3.cmd", "@echo Python was not found; run without arguments to install from the "
                                       "Microsoft Store. 1>&2\r\n@exit /b 9009\r\n")
        system = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
        env = dict(os.environ, PATH=os.pathsep.join([self.path("stub"), os.path.dirname(sys.executable), system,
                                                     os.path.join(system, "WindowsPowerShell", "v1.0")]))
        self.write("payload.json", EVENT)
        with open(self.path("cursor-hook.ps1"), "w", encoding="utf-8-sig") as f:  # Cursor writes a BOM
            f.write(CURSOR_WRAPPER.format(payload=self.path("payload.json"), command=self.command))
        p = subprocess.run([os.path.join(system, "WindowsPowerShell", "v1.0", "powershell.exe"), "-ExecutionPolicy",
                            "Bypass", "-NonInteractive", "-File", self.path("cursor-hook.ps1")],
                           stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", env=env)
        self.check(p)


if __name__ == "__main__":
    unittest.main()
