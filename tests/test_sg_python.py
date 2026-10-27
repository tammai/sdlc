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


if __name__ == "__main__":
    unittest.main()
