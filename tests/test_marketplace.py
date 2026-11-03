"""The sdlc marketplace: every plugin it ships from this repo exists, and carries sdlc's version."""
import json
import os
import unittest

from helpers import PLUGIN_ROOT


def load(*path):
    with open(os.path.join(PLUGIN_ROOT, *path), encoding="utf-8") as f:
        return json.load(f)


class MarketplaceTest(unittest.TestCase):
    def test_every_local_plugin_has_sdlcs_version(self):
        # The companions release with sdlc: one bumped without the others ships a mismatched set
        version = load(".claude-plugin", "plugin.json")["version"]
        local = [p for p in load(".claude-plugin", "marketplace.json")["plugins"] if isinstance(p["source"], str)]
        self.assertIn("sdlc-stepper", [p["name"] for p in local])
        for p in local:
            manifest = load(p["source"], ".claude-plugin", "plugin.json")
            self.assertEqual(manifest["name"], p["name"])
            self.assertEqual(manifest["version"], version, p["name"])

    def test_every_marketplace_companion_setup_names_is_in_the_marketplace(self):
        names = {p["name"] for p in load(".claude-plugin", "marketplace.json")["plugins"]}
        for c in load("templates", "project", "config.defaults.json")["companions"]:
            if c.get("marketplace") == "sdlc":
                self.assertIn(c["id"].split("@")[0], names)


if __name__ == "__main__":
    unittest.main()
