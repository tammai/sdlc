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


class LinkedConfigReadersTest(ProjectTestCase):
    def test_no_config_reader_follows_a_link_to_a_fifo(self):
        # end-of-push review r1 M1: every reader of .sdlc/config.json goes through sdlc_scopes' guarded reader
        import subprocess
        import tempfile, shutil  # noqa: E401
        if not hasattr(os, "mkfifo"):
            self.skipTest("no FIFOs here")
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        fifo = os.path.join(outside, "config.json")
        os.mkfifo(fifo)
        os.makedirs(self.path(".sdlc"))
        os.symlink(fifo, self.path(".sdlc/config.json"))
        code = ("import sys; sys.path[:0] = [sys.argv[1] + '/hooks', sys.argv[1] + '/scripts']; r = sys.argv[2]\n"
                "import review_rounds, sdlc_review_gate, verify_freshness, capabilities, state, brief, spec_lock\n"
                "review_rounds.read_config(r); sdlc_review_gate._security_areas(r); verify_freshness.load_scopes(r, '')\n"
                "capabilities.config(r); state.test_command(r); brief.config_text(r); spec_lock.lock_paths(r)\n"
                "brief.read(r, '.sdlc/config.json'); assert review_rounds.record_in_config(r, 3) is False\n"
                "import verify; rec, _ = verify.full(r, 'x', timeout=5); assert rec['result'] == 'fail', rec\n"
                "assert verify.accept_target(r)[0] is None\n")
        try:
            p = subprocess.run([sys.executable, "-c", code, PLUGIN_ROOT, self.root], capture_output=True, timeout=20,
                               encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            self.fail("a config reader opened the linked FIFO")
        self.assertEqual(p.returncode, 0, p.stderr)


class GitSegmentTest(ProjectTestCase):
    """One `.git` segment rule (sdlc_scopes.git_segment) in every check: case, trailing dots and spaces, the NTFS
    stream suffix, the code points HFS+ ignores and the 8.3 short name `git~1` all open a git dir somewhere."""
    SPELLINGS = (".GIT", ".git. ", "GIT~1", "git~1", ".git::$INDEX_ALLOCATION", ".g‌it", "﻿.git", ".gi⁪t")

    def test_the_shared_helper_names_every_spelling(self):
        import sdlc_scopes
        for seg in self.SPELLINGS + (".git",):
            self.assertTrue(sdlc_scopes.git_segment(seg), seg)
        for seg in (".github", ".gitignore", "git", "gitx~1", "x"):
            self.assertFalse(sdlc_scopes.git_segment(seg), seg)

    def test_no_check_keeps_its_own_copy(self):
        # the HFS+ code point table lives once, so the checks can't drift apart
        hits = []
        for folder in ("hooks", "scripts"):
            for name in sorted(os.listdir(os.path.join(PLUGIN_ROOT, folder))):
                if name.endswith(".py"):
                    with open(os.path.join(PLUGIN_ROOT, folder, name), encoding="utf-8") as f:
                        if "0x200C" in f.read():
                            hits.append(f"{folder}/{name}")
        self.assertEqual(hits, ["hooks/sdlc_scopes.py"])

    def test_validate_docs_dir_refuses_every_spelling(self):
        for seg in self.SPELLINGS:
            for value in (seg, f"{seg}/x", f"docs/{seg}/x"):
                with self.assertRaises(ValueError, msg=value):
                    sdlc_layout.validate_docs_dir(value)

    def test_runbook_path_refuses_every_spelling_at_any_depth(self):
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        self.assertEqual(scaffold.runbook_path(self.root, "knowledge/deploy.md"), "knowledge/deploy.md")
        for seg in self.SPELLINGS + (".git",):
            for value in (f"{seg}/x.md", f"sub/{seg}/x.md"):
                self.assertIsNone(scaffold.runbook_path(self.root, value), value)

    def test_objects_path_refuses_a_link_into_a_short_named_git_dir(self):
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import objects
        for value in ("GIT~1/objects.md", ".git::$DATA/objects.md"):
            with self.assertRaises(ValueError, msg=value):
                objects.target(self.root, value)
        os.makedirs(self.path("git~1"))
        try:  # Windows without the symlink privilege can't make one
            os.symlink("git~1", self.path("docs"), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):  # the path written is fine; where it leads isn't
            objects.target(self.root, "docs/objects.md")


class SdlcFolderSpellingTest(ProjectTestCase):
    """end review SP-L1 of 2026-11-22-todo-lanes: `.claude` and `.sdlc` are barred by the same spelling rule as `.git`
    (sdlc_scopes.dot_segment): case, trailing dots and spaces, NTFS stream suffix, HFS+ code points, 8.3 short name."""

    @staticmethod
    def spellings(name):
        short = name.lstrip(".")[:6]
        out = (name.upper(), name + ". ", short.upper() + "~1", short + "~1", name + "::$INDEX_ALLOCATION",
               name[:2] + "\u200c" + name[2:], "\ufeff" + name, name.replace("s", "\u017f"), name.replace("i", "\u0131"))
        # security-r1 S-3: a folder sorting before it (`.claude-a`) gives it `~2`; git bars `~1`-`~4` past `.git`
        return out + ((short.upper() + "~2", short + "~4") if name != ".git" else ())

    def test_the_shared_helper_names_every_spelling(self):
        import sdlc_scopes
        for name in (".git", ".claude", ".sdlc"):
            for seg in self.spellings(name) + (name,):
                self.assertTrue(sdlc_scopes.dot_segment(seg, name), (seg, name))
        for seg in (".claudex", "claude", ".sdlcrc", "sdlc~5", "git~2", ".github"):
            self.assertFalse(any(sdlc_scopes.dot_segment(seg, n) for n in (".git", ".claude", ".sdlc")), seg)

    def test_runbook_path_refuses_every_spelling(self):
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        for name in (".claude", ".sdlc"):
            for seg in self.spellings(name):
                self.assertIsNone(scaffold.runbook_path(self.root, f"{seg}/x.md"), seg)

    def test_runbook_path_refuses_instruction_files_and_odd_names(self):
        # security review L-2, L-3 of 2026-11-23-s-runbook-nested-sdlc-folders: /sdlc:deploy appends to the runbook,
        # so never an agent's instruction file; and no control or format character, as the objects path refuses
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        for value in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", "pkg/claude.md", "api/AGENTS.MD",
                      "docs/a\nb.md", "docs/a\u202eb.md", "docs/\u200bdeploy.md"):
            self.assertIsNone(scaffold.runbook_path(self.root, value), repr(value))
        self.assertEqual(scaffold.runbook_path(self.root, "docs/claude-deploy.md"), "docs/claude-deploy.md")
        self.write("CLAUDE.md", "x")
        os.makedirs(self.path("ops"), exist_ok=True)
        try:  # a link to an instruction file counts like the file (security review L-4)
            os.symlink(os.path.join("..", "CLAUDE.md"), self.path("ops/deploy.md"))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertIsNone(scaffold.runbook_path(self.root, "ops/deploy.md"))

    def test_runbook_path_refuses_them_at_any_depth(self):
        # security review S-4 of 2026-11-23-todo-fixes: a nested package's .claude or an app repo's .sdlc in a
        # workbench is sdlc's or Claude Code's own folder too
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        for value in ("pkg/.claude/skills/x/SKILL.md", "api/.sdlc/todo.md", "a/b/.SDLC/x.md", "pkg/CLAUDE~1/x.md"):
            self.assertIsNone(scaffold.runbook_path(self.root, value), value)
        for value in ("knowledge/runbooks/deploy.md", "docs/claude/deploy.md", "pkg/.claudex/deploy.md"):
            self.assertEqual(scaffold.runbook_path(self.root, value), value)
        for name in (".claude", ".sdlc"):
            for seg in self.spellings(name):
                self.assertIsNone(scaffold.runbook_path(self.root, f"sub/{seg}/x.md"), seg)
        os.makedirs(self.path("pkg/.claude"))
        try:  # where a path leads counts at any depth too (security review L-1)
            os.symlink(os.path.join("pkg", ".claude"), self.path("docs"), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertIsNone(scaffold.runbook_path(self.root, "docs/deploy.md"))

    def test_objects_path_refuses_every_spelling(self):
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import objects
        for name in (".claude", ".sdlc"):
            for seg in self.spellings(name):
                for value in (f"{seg}/objects.md", f"docs/{seg}/objects.md"):
                    with self.assertRaises(ValueError, msg=value):
                        objects.target(self.root, value)


class GitPrefixedNamesPassTest(ProjectTestCase):
    def test_names_that_only_start_with_git_are_accepted(self):
        # end review SP-L2: the shared .git rule must not widen to `.git*`
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        for name in (".github/docs", ".gitignore-docs", "docs/.git-notes", "a.git/docs"):
            self.assertEqual(sdlc_layout.validate_docs_dir(name), name)
        self.write(".github/runbooks/deploy.md", "x")
        self.assertIsNotNone(scaffold.runbook_path(self.root, ".github/runbooks/deploy.md"))
