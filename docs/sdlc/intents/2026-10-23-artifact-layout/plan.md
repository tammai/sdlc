# Artifact Layout Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use sdlc:subagent-driven-development (recommended) or sdlc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In set-up repos, documents move to `<docs_dir>` (default `docs/sdlc`, with `intents/<name>/` per feature), while machinery and per-feature state stay in `.sdlc/` (`state/<name>.md`). Existing repos move on upgrade, and everything in between reads both layouts.

**Architecture:** One resolver module, `hooks/sdlc_layout.py`, knows both layouts. Hooks import it as a sibling, and scripts add `hooks/` to `sys.path`. `scaffold.py` exposes it to skills (`paths`), records `docs_dir` (`init --docs-dir`), detects docs sites (`status`), feeds templates (`{{layout.*}}`), and moves old repos (`relocate`). A migration file drives `relocate` during `/sdlc:upgrade`.

**Tech Stack:** Python 3.9+ stdlib, git, `unittest`, markdown skills.

**Spec:** `docs/sdlc/intents/2026-10-23-artifact-layout/brainstorm.md`. Requirement IDs: `G1`–`G6` are its Goals, `AC-1`–`AC-9` its acceptance criteria, and `BC-*` the "Calls made after the builder check", in order: BC-1 which layout, BC-2 the move, BC-3 in-flight, BC-4 resumable, BC-5 the location input, BC-6 valid values, BC-7 prune, BC-8 freshness.

## Global Constraints

- **The layout signal:** a repo is on the new layout iff the project's own `.sdlc/config.json` (not the defaults) has `docs_dir`. `docs_dir` is never added to `config.defaults.json`.
- **New layout:** state at `.sdlc/state/<name>.md`, documents at `<docs_dir>/intents/<name>/`, constitution at `<docs_dir>/constitution.md`, design system at `<docs_dir>/design-system.md`.
- **Legacy layout:** `.sdlc/<name>/state.md`, `.sdlc/<name>/`, `.sdlc/constitution.md`, `.sdlc/design-system.md`.
- The baseline, config, lock, `ci/`, `lint/` and `.work/` never move.
- **Valid `docs_dir`:** relative, normalised with `/`, inside the repo, not `.`, not `.git` and not under it.
- Paths in JSON output are repo-relative with `/`.
- Scripts that print non-ASCII call `sys.stdout.reconfigure(encoding="utf-8")`. Subprocess output is read with `encoding="utf-8", errors="replace"`. Tests start shell commands with `helpers.BASH`.
- Tests stay minimal: one per user-visible behaviour, plus the failure that matters most. No structural tests.
- No plugin version bump in this plan; the release does that. The migration is versioned `1.7.0`.

## Public Surface

- module `hooks/sdlc_layout.py`: `docs_dir`, `validate_docs_dir`, `paths`, `features`, `DOCS_DEFAULT` (G3)
- CLI `scaffold.py paths [<name>]` (G3, AC-3)
- CLI `scaffold.py init --docs-dir <path>` (G2, AC-1)
- CLI `scaffold.py relocate [--docs-dir <path>] [--apply]` (G4, AC-5)
- output field `docs_site` in `scaffold.py status` (G2, AC-2)
- template context `{{layout.docs_dir}}`, `{{layout.constitution}}`, `{{layout.design_system}}`, `{{layout.intents_root}}` (G3)
- config `docs_dir` (G2)
- migration `migrations/1.7.0-artifact-layout.md` (G4)

## Review Focus

1. **An old-layout repo whose `.sdlc/` also has a folder without `state.md`** (`ci/`, `lint/`, `.work/`, `state/`). `relocate` and `features` must leave it alone. Fixture plus assertion in Task 3.
2. **The same feature in both layouts after an interrupted relocate.** Reads prefer the new one, and `relocate` stops on the name without overwriting. Test in Task 3.
3. **`docs_dir` given as `docs\sdlc` on Windows, or with a trailing `/`.** It must be normalised, not rejected or double-slashed. Assertion in Task 1.
4. **A new feature in a legacy repo.** `paths` must return legacy paths, so the repo isn't half-moved. Test in Task 1.
5. **The upgrade regenerates rules before migrations run** (upgrade.md step 1 before step 8). After `relocate`, the rules must be re-rendered so they name the new paths. Instructed in Task 6's migration file, with no unit test.

---

### Task 1: The layout resolver

**Requirements:** G3, G5, BC-1, BC-6, AC-3

**Files:**
- Create: `hooks/sdlc_layout.py`
- Test: `tests/test_sdlc_layout.py`

**Interfaces:**
- Produces:
  - `DOCS_DEFAULT = "docs/sdlc"`
  - `docs_dir(root: str) -> str | None`: the project config's value, or None (legacy). A missing or corrupt config gives None.
  - `validate_docs_dir(value: str) -> str`: the normalised value, or `ValueError` with the reason.
  - `paths(root: str, name: str | None = None) -> dict` with keys `layout` (`"new"`|`"legacy"`), `docs_dir`, `constitution`, `design_system`, `intents_root`, `state_root`. With `name`, it also has `state` and `intents`. All values are relative paths.
  - `features(root: str) -> dict[str, dict]`: `{name: {"state": rel, "intents": rel, "layout": "new"|"legacy"}}` from both `.sdlc/state/*.md` and `.sdlc/*/state.md`. The new layout wins on a name in both.

- [ ] **Step 1: Write the failing tests**

```python
def test_legacy_repo_resolves_old_paths_even_for_a_new_feature(self):
    self.write(".sdlc/config.json", "{}")
    p = sdlc_layout.paths(self.root, "2026-10-23-x")
    self.assertEqual((p["layout"], p["state"], p["intents"], p["constitution"]),
                     ("legacy", ".sdlc/2026-10-23-x/state.md", ".sdlc/2026-10-23-x/", ".sdlc/constitution.md"))

def test_new_layout_uses_docs_dir(self):
    self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
    p = sdlc_layout.paths(self.root, "2026-10-23-PROJ-1-x")
    self.assertEqual((p["layout"], p["state"], p["intents"], p["design_system"]),
                     ("new", ".sdlc/state/2026-10-23-PROJ-1-x.md", "docs/sdlc/intents/2026-10-23-PROJ-1-x/",
                      "docs/sdlc/design-system.md"))

def test_features_reads_both_layouts_and_prefers_the_new_one(self):
    self.write(".sdlc/old/state.md", "Status: done\n")
    self.write(".sdlc/both/state.md", "Status: active\n")
    self.write(".sdlc/state/both.md", "Status: active\n")
    self.write(".sdlc/lint/eslint.sdlc.mjs", "")
    f = sdlc_layout.features(self.root)
    self.assertEqual(sorted(f), ["both", "old"])
    self.assertEqual((f["both"]["layout"], f["old"]["layout"]), ("new", "legacy"))

def test_validate_docs_dir(self):
    self.assertEqual(sdlc_layout.validate_docs_dir("docs\\sdlc/"), "docs/sdlc")
    self.assertEqual(sdlc_layout.validate_docs_dir(".sdlc"), ".sdlc")
    for bad in (".", "..", "../x", "/abs", ".git", ".git/x"):
        with self.assertRaises(ValueError):
            sdlc_layout.validate_docs_dir(bad)
```

Import the module via `sys.path.insert(0, os.path.join(PLUGIN_ROOT, "hooks"))`.

- [ ] **Step 2: Run them to verify they fail.** Run `python3 -m unittest discover -s tests -t tests -k sdlc_layout`. Expected: an error, because the module doesn't exist.
- [ ] **Step 3: Implement `hooks/sdlc_layout.py`** with the signatures above. Read config with `json.load` (UTF-8) and treat any error as legacy. `features` with the new layout but a legacy `intents` entry: a legacy feature's intents is `.sdlc/<name>/`.
- [ ] **Step 4: Run the tests to verify they pass.** Same command. Expected: PASS.
- [ ] **Step 5: Commit** with message `feat: layout resolver for sdlc state and docs`.

### Task 2: `scaffold.py` paths, init, docs-site detection, template context, eject

**Requirements:** G2, G3, AC-1, AC-2, AC-3, AC-9

**Files:**
- Modify: `scripts/scaffold.py`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: `sdlc_layout` (Task 1), imported after `sys.path.insert(0, os.path.join(PLUGIN_ROOT, "hooks"))`.
- Produces:
  - `cmd_paths` → `{"layout", "docs_dir", ...}` as `sdlc_layout.paths`.
  - `init --docs-dir` (default `DOCS_DEFAULT`, validated) writes `config["docs_dir"]`.
  - `status` gains `"docs_site": "<marker path>" | None` (first match of `docusaurus.config.*`, `mkdocs.yml`, `docs/.vitepress`, `docs/conf.py`, `astro.config.*` when `src/content/docs` exists).
  - `render_text` context gains `"layout": sdlc_layout.paths(p.root)`.
  - The eject `keep` list uses the resolved `constitution`, `design_system`, `state_root` and `intents_root`, plus `CONFIG` and the baseline.

- [ ] **Step 1: Write the failing tests**

```python
def test_init_records_docs_dir_and_paths_resolve(self):
    self.sc("init", "--kind", "greenfield", "--docs-dir", "handbook/sdlc/")
    self.assertEqual(self.config()["docs_dir"], "handbook/sdlc")
    self.assertEqual(self.sc("paths", "2026-10-23-x")["intents"], "handbook/sdlc/intents/2026-10-23-x/")
    self.assertIn("not inside the repo", self.sc("init", "--kind", "greenfield", "--force", "--docs-dir", "../x",
                                                 expect=1)["error"])

def test_status_names_a_docs_site(self):
    self.write("mkdocs.yml", "site_name: x\n")
    self.assertEqual(self.sc("status")["docs_site"], "mkdocs.yml")

def test_templates_name_the_repos_layout_paths(self):
    self.init()
    self.template("templates/project/l.md", "{{layout.constitution}}")
    self.write(".sdlc/config.json", "{}")  # legacy: no docs_dir
    self.assertEqual(self.sc("preview", "templates/project/l.md")["text"], ".sdlc/constitution.md")
    self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
    self.assertEqual(self.sc("preview", "templates/project/l.md")["text"], "docs/sdlc/constitution.md")
```

`validate_docs_dir`'s `ValueError` text contains "not inside the repo" for `..` and absolute paths.

- [ ] **Step 2: Run them to verify they fail.** Run `python3 -m unittest discover -s tests -t tests -k docs_dir -k docs_site -k layout_paths`. Expected: FAIL.
- [ ] **Step 3: Implement** the `paths` subcommand (optional positional `name`), `init --docs-dir`, `status.docs_site`, the `layout` render context and the eject keep-list.
- [ ] **Step 4: Run the full suite.** Expected: all pass. The existing init tests still pass, because `init` without the flag writes the default.
- [ ] **Step 5: Commit** with message `feat(scaffold): paths, docs_dir on init, docs-site detection`.

### Task 3: `scaffold.py relocate`

**Requirements:** G4, AC-5, BC-2, BC-4, BC-5

**Files:**
- Modify: `scripts/scaffold.py`
- Test: `tests/test_scaffold.py` (git fixture as in `test_prune.py`)

**Interfaces:**
- Produces: `relocate [--docs-dir P] [--apply]`, which returns `{"docs_dir", "moves": [[from, to], …], "conflicts": [name…], "applied": bool}`.
  - `--docs-dir` defaults to the recorded value, else `DOCS_DEFAULT`.
  - It refuses with exit 1 when `git status --porcelain` is non-empty and `--apply` is set.
  - With `--apply`, it moves with `git mv` (creating parent dirs), then updates any lock `files` key that moved, and then writes `docs_dir` to config **only if there are no conflicts**.

- [ ] **Step 1: Write the failing tests**

```python
def test_relocate_moves_old_layout_and_is_idempotent(self):
    # git repo; .sdlc/config.json {}, lock via init then config rewritten to {} ;
    # .sdlc/f1/{state.md,spec.md,checklists/r.md}, .sdlc/constitution.md, .sdlc/baseline.md, .sdlc/lint/x.mjs; commit
    dry = self.sc("relocate")
    self.assertFalse(dry["applied"])
    self.assertIn([".sdlc/f1/state.md", ".sdlc/state/f1.md"], dry["moves"])
    self.assertFalse(os.path.exists(self.path(".sdlc/state/f1.md")))
    out = self.sc("relocate", "--apply")
    for path in (".sdlc/state/f1.md", "docs/sdlc/intents/f1/spec.md", "docs/sdlc/intents/f1/checklists/r.md",
                 "docs/sdlc/constitution.md", ".sdlc/baseline.md", ".sdlc/lint/x.mjs"):
        self.assertTrue(os.path.exists(self.path(path)), path)
    self.assertEqual(self.config()["docs_dir"], "docs/sdlc")
    self.git("commit", "-q", "-m", "moved")
    self.assertEqual(self.sc("relocate", "--apply")["moves"], [])

def test_relocate_stops_on_a_name_in_both_layouts(self):
    # .sdlc/f1/state.md and .sdlc/state/f1.md both committed
    out = self.sc("relocate", "--apply")
    self.assertEqual(out["conflicts"], ["f1"])
    self.assertNotIn("docs_dir", self.config())

def test_relocate_refuses_a_dirty_tree(self):
    # uncommitted .sdlc/f1/spec.md edit
    self.assertIn("uncommitted", self.sc("relocate", "--apply", expect=1)["error"])
```

- [ ] **Step 2: Run them to verify they fail.** Run `python3 -m unittest discover -s tests -t tests -k relocate`. Expected: FAIL.
- [ ] **Step 3: Implement `cmd_relocate`.**
  - Moves:
    - each legacy feature (from `sdlc_layout.features`, layout `legacy`, not in conflicts): `state.md` → `.sdlc/state/<name>.md`, each other entry of the folder → `<docs>/intents/<name>/<entry>`
    - `.sdlc/constitution.md` and `.sdlc/design-system.md` → `<docs>/`, if present
    - a target that already exists is a conflict for that name
  - Run git through the same `encoding="utf-8", errors="replace"` pattern used elsewhere in the file.
- [ ] **Step 4: Run the full suite.** Expected: all pass.
- [ ] **Step 5: Commit** with message `feat(scaffold): relocate old-layout repos`.

### Task 4: Hooks read the layout

**Requirements:** G5, G6, AC-6, AC-8, BC-8

**Files:**
- Modify: `hooks/model_router.py` (`active_states`), `hooks/trust_anchor.py` (the feature glob, and `spec.md` reads via `features()[name]["intents"]`), `hooks/verify_freshness.py` (`feature_base`, `active_verify_feature`, and `is_code_file` also treats `<docs_dir>/` as non-code), `hooks/role_guard.py` (the verifier may write `test-report.md` and the qa-tester `qa-report.md` under `.sdlc/` **or** `docs_dir`; the qa-tester may read `docs_dir`)
- Update module docstrings that name `.sdlc/<feature>/` paths.
- Test: `tests/test_model_router.py`, `tests/test_role_guard.py`

**Interfaces:**
- Consumes: `sdlc_layout.features`, `sdlc_layout.docs_dir` (Task 1).

- [ ] **Step 1: Write the failing tests**

```python
# test_model_router.py
def test_active_feature_in_the_new_layout_is_seen(self):
    # write .sdlc/config.json {"docs_dir": "docs/sdlc"} and .sdlc/state/f.md with "Status: active"
    # a dispatch without a model is denied (same assertion as test_dispatch_without_a_model_is_denied)

# test_role_guard.py
def test_verifier_writes_its_report_in_the_docs_folder(self):
    # config {"docs_dir": "docs/sdlc"}
    # Write docs/sdlc/intents/f/test-report.md as sdlc:verifier → no output
    # Write src/app.py as sdlc:verifier → denied (unchanged)
```

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL. The router sees no active feature (silent), and the guard denies the report.
- [ ] **Step 3: Implement** the four hook changes. `trust_anchor`'s removed-state notice keys on the names from `features()`, so a relocate (state moved, name unchanged) doesn't read as a removal.
- [ ] **Step 4: Run the full suite.** Expected: all pass, including the existing legacy-layout tests of each hook, which proves both layouts are read.
- [ ] **Step 5: Commit** with message `feat(hooks): read state and docs from either layout`.

### Task 5: prune, diff_stats and doctor read the layout

**Requirements:** G5, AC-7, BC-1, BC-7

**Files:**
- Modify: `scripts/prune.py`, `scripts/diff_stats.py` (`feature_base`: the plan's folder name → `paths(root, name)["state"]`, else active features from `features()`), `scripts/doctor.py` (the features check and design-system path from the layout; a new warn "old layout: run /sdlc:upgrade to move features to `<docs>`" when setup is complete and `docs_dir(root)` is None)
- Test: `tests/test_prune.py`, `tests/test_doctor.py`

**Interfaces:**
- Consumes: `sdlc_layout` (Task 1), with `hooks/` added to `sys.path` as in `doctor.py`'s existing insert.
- Produces: prune's `candidate` reads state on the ref at the new path, else the legacy one. Age comes from `git log -1 --follow --format=%ct <ref> -- <path>`. `status --porcelain` checks both the state file and the intents folder. Deletes come from the intents folder.

- [ ] **Step 1: Write the failing tests**

```python
# test_prune.py — a second fixture class or a helper that builds the new layout:
def test_done_feature_in_the_new_layout_keeps_only_its_record(self):
    # config {"docs_dir": "docs/sdlc"}; .sdlc/state/<done>.md; docs/sdlc/intents/<done>/{spec,plan,test-report,...}; old commit
    # prune --apply <done> → plan.md, test-report.md, qa-report.md, review.md, checklists gone; spec.md kept

# test_doctor.py
def test_old_layout_after_setup_warns_to_upgrade(self):
    # complete setup lock, config without docs_dir → a warn row naming /sdlc:upgrade
```

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Implement** the three script changes.
- [ ] **Step 4: Run the full suite.** Expected: all pass, including the existing legacy prune tests.
- [ ] **Step 5: Commit** with message `feat(scripts): prune, diff_stats and doctor follow the layout`.

### Task 6: Templates and the migration

**Requirements:** G1, G3, G4, BC-3, BC-5

**Files:**
- Modify: `templates/project/rules/sdlc.md`:
  - features: "state in `.sdlc/state/`, documents in `{{layout.intents_root}}`"
  - "Project principles: `{{layout.constitution}}`"
- Modify: `templates/project/rules/ui.md` and `templates/project/hookify/sdlc-ui-hardcoded-values.md` to use `{{layout.design_system}}`.
- Modify: `templates/knowledge/doc.md` to say "links to the feature's spec.md, design.md, retro.md (`scaffold.py paths <name>`)".
- Create: `migrations/1.7.0-artifact-layout.md` (frontmatter `version: 1.7.0`, `summary: Move sdlc documents to docs/sdlc (or a location you choose); state stays in .sdlc`). Its steps:
  1. `$S status` → if `docs_site`, explain it and ask for the location (`.sdlc`, a path, or `docs/sdlc`). Otherwise use `docs/sdlc`.
  2. `$S relocate --docs-dir <d>` (dry run): show the moves. List active features (`Status: active`) and warn that their open branches will see renames. The user confirms.
  3. `$S relocate --docs-dir <d> --apply`. Any `conflicts` → show both copies, the user picks, and the run is repeated until there are none.
  4. Re-render every generated file (`$S upgrade-plan` → `regenerate`), because they were rendered before the move.
  5. Commit `chore(sdlc): move sdlc documents to <d>`.
- Test: none new. `test_every_template_renders_without_leftover_placeholders` covers the templates (`layout` always resolves).

- [ ] **Step 1:** Edit the templates and write the migration.
- [ ] **Step 2: Run** the full suite. Expected: all pass.
- [ ] **Step 3: Commit** with message `feat: templates follow the layout; 1.7.0 migration`.

### Task 7: Skills, agents and commands use resolved paths

**Requirements:** G1, G2, G3, AC-1, AC-2, AC-4

**Files:**
- Modify: every file under `skills/`, `agents/` and `commands/` that names `.sdlc/<feature>/`, `.sdlc/<name>/`, `.sdlc/<slug>/`, `.sdlc/*/state.md`, `.sdlc/constitution.md` or `.sdlc/design-system.md`. Find them with `grep -rlE "\.sdlc/(<feature>|<name>|<slug>|\*|constitution|design-system)" skills agents commands`.
- Modify: `skills/setting-up-projects/SKILL.md`:
  - **Before `init`:** `$S status` → `docs_site`. If one is found, explain and ask for the location (new hard stop). Then `$S init --kind … --docs-dir <d>`.
  - The ownership table and the `constitution` and `design-system` steps name `<docs_dir>/…`.
- Modify: `skills/setting-up-projects/references/upgrade.md`, where the mid-stage check reads features via `$S paths`/doctor instead of `.sdlc/*/state.md`.
- Modify: `skills/setting-up-projects/references/eject.md` to keep the docs folder and `.sdlc/state/`.
- Test: none. This is instructed behaviour, and review covers it.

**Interfaces:**
- Consumes: `scaffold.py paths [<name>]` (Task 2).

- [ ] **Step 1: In `skills/orchestrator/SKILL.md` §0,** a new feature runs `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py paths <name>` once. It writes state to `state` and documents to `intents`, and records both paths at the top of the state file (`Docs: <intents>`). Define the two placeholders once: `<state>` and `<intents>`.
- [ ] **Step 2: Everywhere else,** use the same mechanical rewrite:
  - `.sdlc/<feature>/state.md` → `<state>`
  - `.sdlc/<feature>/<doc>` → `<intents>/<doc>`
  - `.sdlc/constitution.md` → `<docs>/constitution.md`
  - `.sdlc/design-system.md` → `<docs>/design-system.md`

  Each file gets one line on first use: "(paths from `scaffold.py paths <name>`; the feature's state file records them)". Frontmatter descriptions use plain wording, and no `: `.
- [ ] **Step 3: Run** `claude plugin validate .` and the full suite. Expected: valid, and all pass. A grep with the pattern above lists no files under `skills/`, `agents/` or `commands/`, except deliberate mentions of the legacy layout in `upgrade.md` and the migration.
- [ ] **Step 4: Commit** with message `docs(skills): resolve sdlc paths instead of hard-coding .sdlc`.

### Task 8: Decision record, specs and stale-docs audit

**Requirements:** supports G1 to G6 (documents them)

**Files:**
- Create: `docs/adr/0006-split-sdlc-docs-from-machinery.md`, amending 0001, with Status, Context, Decision, Consequences and Alternatives (B and C from the spec). Add its row to `docs/adr/README.md`.
- Modify:
  - spec 01 (setup and upgrade: `docs_dir`, docs-site question, relocate; new `[enforced]` rows with test names)
  - spec 02 (ORC-FR-016: where the feature lives)
  - specs 05, 07 and 10 (paths)
  - `docs/guidebook.md` "Where things live" and the Configuration table (`docs_dir`)
  - `docs/runbook.md` (the `scaffold.py` table: `paths`, `relocate`, `init --docs-dir`)
  - `docs/playbook.md`
  - `README.md`
  - `CHANGELOG.md` under Unreleased: Changed, plus a "Migration: 1.7.0-artifact-layout" line
- [ ] **Step 1:** Write the ADR and its index row.
- [ ] **Step 2:** Update the specs, guidebook, runbook, playbook, README and CHANGELOG.
- [ ] **Step 3: Run the stale-docs audit** (`CONTRIBUTING.md`). Grep `.sdlc/<`, `.sdlc/*/state.md`, `.sdlc/constitution`, `.sdlc/design-system`, `docs_dir`, `relocate` and `intents` across the listed places, including `docs/diagrams/*.svg` `<desc>`. Fix them, or name in the report what's left (e.g. an SVG needing relayout).
- [ ] **Step 4: Run** the full suite and `claude plugin validate .`. Expected: all pass, and valid.
- [ ] **Step 5: Commit** with message `docs: ADR 0006 and specs for the sdlc docs/machinery split`.
