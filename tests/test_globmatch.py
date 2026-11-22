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

    def test_whatever_the_old_area_matcher_matched_still_matches(self):
        # end-of-push review r1 H1: a `**` inside a segment crossed `/` in the old matcher; an area may only grow
        import re

        def old(pattern):  # sdlc_review_gate._glob_re before c9e318b
            out, i = "", 0
            while i < len(pattern):
                c = pattern[i]
                if pattern.startswith("**/", i):
                    out, i = out + "(?:.*/)?", i + 3
                    continue
                if pattern.startswith("**", i):
                    out, i = out + ".*", i + 2
                    continue
                if c == "{":
                    end = pattern.find("}", i)
                    if end > i:
                        out += "(?:" + "|".join(re.escape(p) for p in pattern[i + 1:end].split(",")) + ")"
                        i = end + 1
                        continue
                out += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
                i += 1
            return re.compile(out + r"\Z")

        patterns = ["**.pem", "secrets**", "**secret**", "a**/b", "src/**", "**/auth/**", "{a,{b}", "x**y/z",
                    "**/*{secret,token}*", "db/**/migrate*", "*.key", "a/**b"]
        paths = ["a.pem", "x/y/k.pem", "secrets", "secrets/a/b", "x/my-secret-file", "a/b", "a1/z/b", "a/x/y/b",
                 "src/a", "auth/x", "p/auth/q/r", "a", "{b", "a}", "xay/z", "x/q/y/z", "db/1/migrate_x", "k.key",
                 "a/b/c", "a/xb", "a/x/yb"]
        for pattern in patterns:
            for path in paths:
                if old(pattern).match(path):
                    self.assertTrue(globmatch.glob_match(pattern, path), (pattern, path))

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
        import time  # end-of-push review r1 SH-H7: many `**` against a deep path
        t = time.monotonic()
        globmatch.glob_match("**/a/" * 60 + "z", "a/" * 1500 + "b")
        self.assertLess(time.monotonic() - t, 5)


if __name__ == "__main__":
    unittest.main()
