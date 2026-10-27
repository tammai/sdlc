"""hooks/sg-python.sh: the launcher every hook starts through finds a working Python 3 once and remembers it."""
import os
import subprocess
import unittest

from helpers import BASH, HOOKS, ProjectTestCase

LAUNCHER = os.path.join(HOOKS, "sg-python.sh")


class LauncherTest(ProjectTestCase):
    def launch(self):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=self.root)
        return subprocess.run([BASH, LAUNCHER, "-c", "print(7*6)"], capture_output=True, encoding="utf-8",
                              errors="replace", env=env)

    def test_remembers_the_interpreter_and_recovers_from_a_stale_one(self):
        p = self.launch()
        self.assertEqual(p.stdout.strip(), "42", p.stderr)
        with open(self.path("sdlc-hook-python"), encoding="utf-8") as f:
            remembered = f.read().strip()
        self.assertIn("\t", remembered)  # the name and where it resolved: later hooks skip the probes
        name = remembered.split("\t")[0]
        self.write("sdlc-hook-python", f"{name}\t/elsewhere/{name}\n")  # PATH now finds another program by that name
        p = self.launch()
        self.assertEqual(p.stdout.strip(), "42", p.stderr)
        with open(self.path("sdlc-hook-python"), encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), remembered)  # probed again, not trusted
        self.write("sdlc-hook-python", "python3.0-not-installed\n")  # e.g. that Python was uninstalled
        p = self.launch()
        self.assertEqual(p.stdout.strip(), "42", p.stderr)
        with open(self.path("sdlc-hook-python"), encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), remembered)


    def test_without_a_plugin_data_folder_it_remembers_per_user_never_in_shared_temp(self):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_DATA"}
        env.update(HOME=self.root, XDG_CACHE_HOME="", TMPDIR=self.path("shared-tmp"))
        os.makedirs(self.path("shared-tmp"))
        p = subprocess.run([BASH, LAUNCHER, "-c", "print(7*6)"], capture_output=True, encoding="utf-8",
                           errors="replace", env=env)
        self.assertEqual(p.stdout.strip(), "42", p.stderr)
        self.assertTrue(os.path.exists(self.path(".cache/sdlc/sdlc-hook-python")))
        self.assertEqual(os.listdir(self.path("shared-tmp")), [])  # another user could plant or redirect it there


if __name__ == "__main__":
    unittest.main()
