"""wiki_sync.py: the wiki's links resolve, and a build turns repo-style links into wiki links."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import PLUGIN_ROOT

SCRIPT = os.path.join(PLUGIN_ROOT, ".github", "scripts", "wiki_sync.py")


def run(*args):
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, encoding="utf-8",
                          cwd=PLUGIN_ROOT, timeout=60)


class WikiSyncTest(unittest.TestCase):

    def test_every_wiki_link_resolves(self):
        p = run("check")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_build_rewrites_links_and_leaves_code_alone(self):
        out = tempfile.mkdtemp(prefix="sdlc-wiki-")
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        with open(os.path.join(out, "Stale-page.md"), "w", encoding="utf-8") as f:
            f.write("gone from the source")
        p = run("build", out, "--repo", "o/r")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        pages = os.listdir(out)
        self.assertNotIn("Stale-page.md", pages)
        self.assertNotIn("README.md", pages)
        self.assertIn("_Sidebar.md", pages)

        def page(name):
            with open(os.path.join(out, name), encoding="utf-8") as f:
                return f.read()

        home = page("Home.md")
        self.assertIn("](Install)", home)
        self.assertIn("](https://github.com/o/r/raw/main/docs/assets/banner.svg)", home)
        self.assertIn("](https://github.com/o/r/blob/main/docs/adr/README.md)", home)
        self.assertNotIn(".md)", home.replace("README.md)", "").replace("CHANGELOG.md)", ""))
        self.assertIn("](Troubleshooting#r4-blocked-at-stop-with-re-run-tests)", page("Everyday-work.md"))
        # inside a code fence the text is shown as written
        self.assertIn("/sdlc:doctor ", page("Quick-start.md"))


if __name__ == "__main__":
    unittest.main()
