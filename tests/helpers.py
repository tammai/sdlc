"""Shared helpers: run a plugin hook the way Claude Code does (JSON on stdin, in the project dir)."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(PLUGIN_ROOT, "hooks")
# Bare "bash" on Windows resolves to System32\bash.exe (WSL) before PATH; shutil.which follows PATH, so it finds Git Bash.
BASH = shutil.which("bash") or "bash"


def run_hook(argv, payload, cwd, env_extra=None):
    """Run a hook command with `payload` on stdin. Returns (exit_code, parsed_stdout_or_None, raw_stdout, stderr)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
    env.update(CLAUDE_PLUGIN_ROOT=PLUGIN_ROOT, CLAUDE_PROJECT_DIR=cwd)
    env.update(env_extra or {})
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    p = subprocess.run(argv, input=stdin, capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=env,
                       timeout=30)
    out = p.stdout.strip()
    try:
        parsed = json.loads(out) if out else None
    except json.JSONDecodeError:
        parsed = None
    return p.returncode, parsed, out, p.stderr


class ProjectTestCase(unittest.TestCase):
    """Gives each test a fresh, empty project directory at self.root."""

    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def path(self, rel):
        return os.path.join(self.root, rel)

    def write(self, rel, text):
        full = self.path(rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
        return full
