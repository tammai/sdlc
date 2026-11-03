"""skills/setting-up-projects/SKILL.md: the `$S` it tells the agent to define works in bash and in zsh (zsh doesn't split a
variable into words, so `S="python3 …/scaffold.py"` failed there) and with a plugin folder that has spaces in its path."""
import os
import re
import shutil
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT

SKILL = os.path.join(PLUGIN_ROOT, "skills", "setting-up-projects", "SKILL.md")


def definition():
    with open(SKILL, encoding="utf-8") as f:
        text = f.read()
    block = next(b for b in re.findall(r"```bash\n(.*?)```", text, re.S) if "S=" in b)
    return block


@unittest.skipIf(sys.platform == "win32", "bash on Windows may be WSL; the zsh problem is a macOS and Linux one")
class SetupSkillShellTest(unittest.TestCase):
    def run_in(self, shell, root):
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=root)
        p = subprocess.run([shell, "-c", definition() + '\n$S --help >/dev/null && echo ok'], capture_output=True,
                           encoding="utf-8", errors="replace", env=env, cwd=PLUGIN_ROOT)
        return p.returncode, p.stdout.strip(), p.stderr.strip()

    def test_s_runs_scaffold_in_every_shell_here(self):
        shells = [s for s in ("bash", "zsh") if shutil.which(s)]
        self.assertTrue(shells)
        for shell in shells:
            with self.subTest(shell=shell):
                self.assertEqual(self.run_in(shell, PLUGIN_ROOT)[:2], (0, "ok"), self.run_in(shell, PLUGIN_ROOT))

    def test_a_plugin_folder_with_spaces_still_works(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "my plugin")
            os.makedirs(root)
            for sub in ("scripts", "hooks"):  # scaffold.py imports its siblings by __file__
                os.symlink(os.path.join(PLUGIN_ROOT, sub), os.path.join(root, sub))
            for shell in [s for s in ("bash", "zsh") if shutil.which(s)]:
                with self.subTest(shell=shell):
                    self.assertEqual(self.run_in(shell, root)[:2], (0, "ok"), self.run_in(shell, root))


if __name__ == "__main__":
    unittest.main()
