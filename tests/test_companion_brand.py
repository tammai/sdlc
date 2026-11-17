"""skills/brainstorming/scripts/server.cjs: the visual companion's page is branded sdlc, crediting Superpowers."""
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import unittest
import urllib.request

from helpers import PLUGIN_ROOT

SERVER = os.path.join(PLUGIN_ROOT, "skills", "brainstorming", "scripts", "server.cjs")


@unittest.skipUnless(shutil.which("node"), "node isn't installed")
class CompanionBrandTest(unittest.TestCase):
    def test_the_page_is_branded_sdlc_and_credits_superpowers(self):
        session = tempfile.mkdtemp(prefix="sdlc-companion-")
        self.addCleanup(shutil.rmtree, session, ignore_errors=True)
        with socket.socket() as s:  # a free port: the server puts the port it was given into its URL
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        env = {**os.environ, "BRAINSTORM_DIR": session, "BRAINSTORM_PORT": str(port)}
        env.pop("BRAINSTORM_OWNER_PID", None)
        proc = subprocess.Popen(["node", SERVER], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                encoding="utf-8")
        self.addCleanup(proc.kill)
        info = None
        for line in proc.stdout:
            data = json.loads(line)
            if data.get("type") == "server-started":
                info = data
                break
        self.assertIsNotNone(info)
        with open(os.path.join(info["screen_dir"], "screen.html"), "w", encoding="utf-8") as f:
            f.write("<h2>A screen</h2>\n")  # a fragment: the server wraps it in the branded frame
        # the keyed URL sets the session cookie and redirects to /, which serves the newest screen
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        opener.open(info["url"], timeout=10).read()
        with opener.open(info["url"].split("?")[0], timeout=10) as r:
            page = r.read().decode("utf-8")
        with open(os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            version = json.load(f)["version"]
        title = re.search(r"<title>(.*?)</title>", page, re.S).group(1)
        self.assertIn("sdlc", title)
        self.assertNotIn("Superpowers", title)
        self.assertNotIn("Prime Radiant", page)
        self.assertIn(f"sdlc v{version}", page)
        self.assertRegex(page, r'href="https://github.com/obra/superpowers"[^>]*>[^<]*based on Superpowers')


if __name__ == "__main__":
    unittest.main()
