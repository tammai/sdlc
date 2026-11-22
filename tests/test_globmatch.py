"""hooks/globmatch.py: committed globs (security areas, rule paths) matched in bounded time."""
import os
import subprocess
import sys
import unittest

from helpers import HOOKS

sys.path.insert(0, HOOKS)
import globmatch  # noqa: E402


class GlobMatchTest(unittest.TestCase):
    def test_glob_semantics(self):
        cases = [("src/**/*.ts", "src/a/b.ts", True), ("src/**/*.ts", "src/b.ts", True),
                 ("**/migrations/**", "db/migrations/1.sql", True), ("*.ts", "a/b.ts", False),
                 ("app/[id].ts", "app/[id].ts", True), ("app/[id].ts", "app/i.ts", False),
                 ("src/{api,web}/**/*.{ts,tsx}", "src/web/x/y.tsx", True), ("db/migrate/**", "db/migrate/x.rb", True),
                 ("**/.env*", "a/.env.local", True), ("auth/**", "auth.py", False), ("a?c", "abc", True)]
        for pattern, path, want in cases:
            self.assertIs(globmatch.glob_match(pattern, path), want, (pattern, path))

    def test_a_hostile_security_area_cannot_stall_the_commit_review(self):
        # .sdlc/2026-11-22-s-gate-glob-stall AC-001: areas come from a committed config; the old regex took > 10 s
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import sdlc_review_gate as g, re\n"
                "rx = (g._glob_re(sys.argv[2]) if hasattr(g, '_glob_re') else g.globmatch.Glob(sys.argv[2]))\n"
                "rx.match('a' * 4000)\n")
        for glob in ("*" * 60 + "z", "*a" * 20 + "z", "{a,b}" * 30 + "x"):
            try:
                subprocess.run([sys.executable, "-c", code, HOOKS, glob], check=True, timeout=10, capture_output=True)
            except subprocess.TimeoutExpired:
                self.fail(f"the commit review's area match stalled on {glob[:12]}…")
        self.assertTrue(globmatch.glob_match("{a,b}" * 30 + "x", "anything"))  # too big to judge: counts as touched


if __name__ == "__main__":
    unittest.main()
