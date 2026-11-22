"""hooks/sdlc_layout.py: where a repo keeps feature state and sdlc documents, in either layout."""
import json
import os
import sys

from helpers import PLUGIN_ROOT, ProjectTestCase

sys.path.insert(0, os.path.join(PLUGIN_ROOT, "hooks"))
import sdlc_layout  # noqa: E402


class LayoutTest(ProjectTestCase):
    def test_legacy_repo_resolves_old_paths_even_for_a_new_feature(self):
        self.write(".sdlc/config.json", "{}")
        p = sdlc_layout.paths(self.root, "2026-10-23-x")
        self.assertEqual((p["layout"], p["state"], p["intents"], p["constitution"]),
                         ("legacy", ".sdlc/2026-10-23-x/state.md", ".sdlc/2026-10-23-x/", ".sdlc/constitution.md"))

    def test_new_layout_uses_docs_dir(self):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        p = sdlc_layout.paths(self.root, "2026-10-23-PROJ-1-x")
        self.assertEqual((p["layout"], p["state"], p["change"], p["work"], p["intents"], p["design_system"]),
                         ("new", ".sdlc/state/2026-10-23-PROJ-1-x.md", "docs/sdlc/changes/2026-10-23-PROJ-1-x.md",
                          ".sdlc/state/2026-10-23-PROJ-1-x/", "docs/sdlc/intents/2026-10-23-PROJ-1-x/",
                          "docs/sdlc/design-system.md"))

    def test_features_reads_both_layouts_and_prefers_the_new_one(self):
        self.write(".sdlc/old/state.md", "Status: done\n")
        self.write(".sdlc/both/state.md", "Status: active\n")
        self.write(".sdlc/state/both.md", "Status: active\n")
        self.write(".sdlc/lint/eslint.sdlc.mjs", "")
        f = sdlc_layout.features(self.root)
        self.assertEqual(sorted(f), ["both", "old"])
        self.assertEqual((f["both"]["layout"], f["old"]["layout"]), ("new", "legacy"))

    def test_an_invalid_recorded_docs_dir_counts_as_legacy(self):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "../outside"}))
        self.assertIsNone(sdlc_layout.docs_dir(self.root))
        self.assertEqual(sdlc_layout.paths(self.root)["layout"], "legacy")

    def test_a_1x_feature_is_not_active_for_the_hooks(self):
        self.write(".sdlc/state/new.md", "Status: active\nProcess: 3\nCurrent: Stage 2 – Build\n")
        self.write(".sdlc/state/old.md", "Status: active\nCurrent: Stage 5 – Prove\n")
        self.assertEqual([name for name, _ in sdlc_layout.active(self.root)], ["new"])

    def test_validate_docs_dir(self):
        self.assertEqual(sdlc_layout.validate_docs_dir("docs\\sdlc/"), "docs/sdlc")
        self.assertEqual(sdlc_layout.validate_docs_dir(".sdlc"), ".sdlc")
        for bad in (".", "..", "../x", "/abs", ".git", ".git/x", ".GIT/x", "docs/.git. /x"):
            with self.assertRaises(ValueError, msg=bad):
                sdlc_layout.validate_docs_dir(bad)


class LinkedConfigTest(ProjectTestCase):
    def test_config_and_manifest_linked_out_of_the_repo_read_as_absent(self):
        # AC-002 (review M2 of 2026-11-22-s-doctor-reads-no-links): no value from a file outside the repo or in .git
        import tempfile, shutil  # noqa: E401
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import objects
        import sdlc_scopes
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        cfg = os.path.join(outside, "config.json")
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({"docs_dir": "docs/sdlc", "prd": "secret.md", "workbench": True, "objects": True}, f)
        man = os.path.join(outside, "workbench.json")
        with open(man, "w", encoding="utf-8") as f:
            json.dump({"repos": [{"name": "app", "url": "https://x/app.git", "role": "app"}]}, f)
        os.makedirs(self.path(".sdlc"))
        try:  # Windows without the symlink privilege can't make one
            os.symlink(cfg, self.path(".sdlc/config.json"))
            os.symlink(man, self.path("workbench.json"))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertIsNone(sdlc_layout.docs_dir(self.root))
        self.assertEqual(sdlc_layout.prd(self.root), ".sdlc/prd.md")
        self.assertFalse(sdlc_scopes.is_workbench(self.root))
        self.assertIsNone(sdlc_scopes.workbench_of(self.root))
        self.assertIsNone(objects.setting(self.root))
        self.assertRaises(ValueError, sdlc_scopes.manifest, self.root)
        os.remove(self.path(".sdlc/config.json"))
        os.makedirs(self.path(".git"))
        self.write(".git/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        os.symlink(os.path.join("..", ".git", "config.json"), self.path(".sdlc/config.json"))
        self.assertIsNone(sdlc_layout.docs_dir(self.root))
        for name in (".GIT", ".g\u200cit"):  # case and the code points HFS+ ignores (git's is_hfs_dotgit)
            os.remove(self.path(".sdlc/config.json"))
            os.makedirs(self.path(name), exist_ok=True)
            self.write(f"{name}/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
            os.symlink(os.path.join("..", name, "config.json"), self.path(".sdlc/config.json"))
            self.assertIsNone(sdlc_layout.docs_dir(self.root), name)
        os.remove(self.path(".sdlc/config.json"))
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))  # a plain file still reads
        self.assertEqual(sdlc_layout.docs_dir(self.root), "docs/sdlc")
