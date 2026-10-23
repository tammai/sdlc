# Greenfield Polyglot Monorepo Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use sdlc:subagent-driven-development (recommended) or sdlc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Greenfield setup with two or more apps proposes an `apps/` + `packages/` + `docs/` (+ opt-in `infras/`) monorepo with a versioned API contract, and adds team-size-dependent CODEOWNERS and per-app CI.

**Architecture:** The procedure lives in a new `skills/setting-up-projects/references/monorepo.md`, which `greenfield.md` routes to. The deterministic files come from new `scaffold.py` builtins rendered through `render`, so the lock, upgrade and eject handle them unchanged. These are `builtin:ci:<package>`, `builtin:contract-check` and `builtin:codeowners`, plus a seeded `contract-check.sh`. Static READMEs are ordinary templates under `templates/project/monorepo/`.

**Tech Stack:** Python 3.9+ stdlib (`scaffold.py`), bash (`contract-check.sh`), GitHub Actions, oasdiff (CI only), `unittest`.

**Spec:** `docs/sdlc/intents/2026-10-23-monorepo-scaffold/brainstorm.md`. Requirement IDs: `G1`–`G7` are its Goals and `AC-1`–`AC-9` its acceptance criteria.

## Global Constraints

- Stdlib only, Python 3.9+. Any script printing non-ASCII calls `sys.stdout.reconfigure(encoding="utf-8")`. Subprocess output is read with `encoding="utf-8", errors="replace"`.
- Tests start shell scripts with `helpers.BASH`, never a bare `"bash"`.
- Tests stay minimal: one per user-visible behaviour (happy path plus the failure that matters most), and no structural or meta tests.
- Rendered files are written with LF (already true for `render`).
- Generated workflows use the same action pins as `CI_SETUP` (`actions/checkout@v7`, `actions/setup-go@v7`).
- `builtin:ci` with no suffix keeps today's output byte-for-byte, so existing repos see no upgrade diff.
- A published contract version is a `v<N>/` folder containing the spec file on the PR's base branch. A breaking edit fails, with no override. New version folders pass. Removing a published version fails.
- Profiles: `lean` (the default when `project.profile` is absent) and `large`. Nothing in the plugin infers the profile; setup asks for it.
- Skill frontmatter descriptions use no unquoted `: `. Run `claude plugin validate .` after editing skills.

## Public Surface

- template `builtin:ci:<package>`: one workflow per package, path-filtered (AC-7)
- template `builtin:contract-check`: the contract breaking-change workflow (AC-5)
- template `builtin:codeowners`: `.github/CODEOWNERS` from config (AC-7)
- template `templates/project/ci/contract-check.sh`: the diff loop the workflow runs (AC-5)
- template `templates/project/monorepo/docs-README.md`: role folders and the link-don't-copy rule (AC-8, G7)
- template `templates/project/monorepo/api-contract-README.md`: version rules (G3, G4)
- template `templates/project/monorepo/infras-README.md`: what goes in `infras/` (AC-2)
- template `templates/project/monorepo/releasing.md`: per-app tags and release branches, large profile (G6)
- config `project.profile` (`"lean"` | `"large"`): G6
- config `project.owners` (`{pattern: [handles]}`, in CODEOWNERS order): AC-7
- config `api_contract` (`{"path": "packages/api-contract", "spec": "openapi.yaml"}`): AC-5
- config `ci.oasdiff_version` (default: the latest oasdiff release tag at implementation time, e.g. `"1.11.7"`): AC-5
- config default `areas.ci` gains `"infras/**"`: AC-2
- dependency `oasdiff` (installed in CI only, after the user agrees): AC-5

## Review Focus

1. **A PR deletes a published version folder.** It must fail, not pass silently because nothing was diffed. Test in Task 2.
2. **A PR changes only a shared `packages/<lib>`.** Every app's workflow must trigger, because the paths include `packages/**`. Assertion in Task 1.
3. **`builtin:ci:<name>` with a name that isn't in `packages`.** It must error clearly rather than emit an empty workflow. Test in Task 1.
4. **A version-like folder on base with no spec file** (only a README, say). It must be skipped, not crash the loop. This is fixture plus assertion in Task 2's happy test.
5. **Path-filtered workflows don't run, so a branch protection rule that requires them never gets a status.** Instructed in Task 5. `monorepo.md` tells setup to warn: mark only `sdlc contract` and the always-running checks as required, or not use required checks for the per-app workflows. This is not testable in unit tests.

---

### Task 1: Per-package CI workflow (`builtin:ci:<package>`)

**Requirements:** AC-7, G6

**Files:**
- Modify: `scripts/scaffold.py` (`generate_ci`, `project_stacks`, `render_source`, and the `render` help text)
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Produces: `generate_ci(p, package=None) -> str`. `render_source("builtin:ci:<name>", p)` calls `generate_ci(p, package="<name>")`. `template_exists` already accepts any `builtin:` prefix, so `upgrade-plan` re-renders these with no change.
- Produces: `project_stacks(config, package=None) -> list[str]`, the stacks of that package only when `package` is given.

- [ ] **Step 1: Write the failing tests** in `ScaffoldTest`:

```python
def test_builtin_ci_per_package(self):
    self.commands_config(packages=[
        {"name": "web", "path": "apps/web", "stack": "typescript", "commands": {"install": "pnpm i", "test": "pnpm test"}},
        {"name": "api", "path": "apps/api", "stack": "go", "commands": {"test": "go test ./..."}}])
    self.write("apps/api/go.mod", "module x\n")
    out = self.sc("render", "builtin:ci:web", ".github/workflows/sdlc-verify-web.yml", "--class", "seeded")
    text = self.read(".github/workflows/sdlc-verify-web.yml")
    for want in ("name: \"sdlc verify web\"", "\"apps/web/**\"", "\"packages/**\"",
                 "\".github/workflows/sdlc-verify-web.yml\"", "actions/setup-node@v7",
                 "working-directory: apps/web", "group: sdlc-verify-web-${{ github.ref }}"):
        self.assertIn(want, text)
    self.assertNotIn("go test", text)
    self.assertNotIn("setup-go", text)
    self.assertEqual(self.lock()["files"][".github/workflows/sdlc-verify-web.yml"]["template"], "builtin:ci:web")

def test_builtin_ci_unknown_package_is_an_error(self):
    self.commands_config(packages=[{"name": "web", "path": "apps/web", "commands": {"test": "pnpm test"}}])
    self.assertIn("no package named 'mobile'", self.sc("preview", "builtin:ci:mobile", expect=1)["error"])
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m unittest discover -s tests -t tests -k builtin_ci_per_package -k builtin_ci_unknown`
Expected: FAIL (unknown template `builtin:ci:web`, or a file-not-found error from `render_source`).

- [ ] **Step 3: Implement `generate_ci(p, package=None)`**

With `package` set:
- Keep only the plan steps and stacks whose scope is that package.
- Set `name: "sdlc verify <name>"` (via `json.dumps`).
- Use `group: sdlc-verify-<name>-${{ github.ref }}`.
- Add a `paths:` list under both `pull_request` and `push`: `"<path>/**"`, `"packages/**"`, `".github/workflows/sdlc-verify-<name>.yml"`. Each is quoted with `json.dumps`.
- Raise `ValueError(f"no package named {package!r} in .sdlc/config.json")` when the name doesn't match.

With `package=None`, the output stays unchanged.

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `python3 -m unittest discover -s tests -t tests`
Expected: all pass, including the existing `test_builtin_ci_*`, which proves the unsuffixed output is unchanged.

- [ ] **Step 5: Commit** with message `feat(scaffold): per-package CI workflow builtin`.

### Task 2: Contract breaking-change check

**Requirements:** AC-5, G4

**Files:**
- Create: `templates/project/ci/contract-check.sh`
- Modify: `scripts/scaffold.py` (add `generate_contract_check(p) -> str` and route `builtin:contract-check` to it in `render_source`)
- Modify: `templates/project/config.defaults.json` (add `"oasdiff_version"` under `ci`)
- Test: `tests/test_contract_check.py` (new; uses `helpers.BASH` and `ProjectTestCase`), plus one test in `tests/test_scaffold.py`

**Interfaces:**
- Produces: `contract-check.sh BASE_REF CONTRACT_PATH SPEC_FILE`, exit 0 or 1. It is rendered by setup to `.sdlc/ci/contract-check.sh` (seeded).
- Produces: `builtin:contract-check`, rendered to `.github/workflows/sdlc-contract.yml`. It needs `api_contract.path` and `api_contract.spec` in config. Missing either gives `ValueError("no api_contract in .sdlc/config.json ...")`.

- [ ] **Step 1: Write the failing script tests**

Fixture: a temp git repo where `main` holds:
- `packages/api-contract/v1/openapi.yaml`
- `packages/api-contract/drafts/README.md`, a folder with no spec, which must be ignored

Check out a branch, make the edit, and commit. A fake `oasdiff` goes first on `PATH`: a bash script that appends `$3` to `calls.txt` and exits 1 if `$3` contains `BREAKING`. Run it with `[helpers.BASH, script, "main", "packages/api-contract", "openapi.yaml"]`.

```python
def test_additive_edit_and_new_version_pass(self):
    # branch: append a field to v1/openapi.yaml, add v2/openapi.yaml
    code, out = self.check()
    self.assertEqual(code, 0, out)
    self.assertEqual(self.calls(), ["packages/api-contract/v1/openapi.yaml"])  # v2 is new, drafts has no spec

def test_breaking_edit_to_published_version_fails(self):
    # branch: write "BREAKING" into v1/openapi.yaml
    code, out = self.check()
    self.assertEqual(code, 1)
    self.assertIn("packages/api-contract/v1", out)

def test_removed_published_version_fails(self):
    # branch: git rm -r packages/api-contract/v1
    code, out = self.check()
    self.assertEqual(code, 1)
    self.assertIn("v1 was removed", out)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m unittest discover -s tests -t tests -k contract_check`
Expected: FAIL (the script doesn't exist).

- [ ] **Step 3: Implement `templates/project/ci/contract-check.sh`**

Start with `set -euo pipefail`. Then:
1. List folders matching `v[0-9]+` under `CONTRACT_PATH` on `BASE_REF` (`git ls-tree -d --name-only "$BASE_REF" "$CONTRACT_PATH/"`).
2. Keep only those where `git cat-file -e "$BASE_REF:$dir/$SPEC"` succeeds.
3. For each, if the head file is missing, print `published version $dir was removed` and mark the run failed. Otherwise write the base file to a `mktemp` file and run `oasdiff breaking --fail-on ERR "$base" "$dir/$SPEC"`, marking failure on a non-zero exit.
4. Exit 1 if anything failed.

Add one header comment saying what it checks.

- [ ] **Step 4: Run the script tests to verify they pass.** Same command; expected PASS.

- [ ] **Step 5: Write the failing workflow test** in `test_scaffold.py`:

```python
def test_builtin_contract_check(self):
    self.commands_config(commands={"test": "make test"},
                         api_contract={"path": "packages/api-contract", "spec": "openapi.yaml"},
                         ci={"oasdiff_version": "1.11.7"})
    text = self.sc("preview", "builtin:contract-check")["text"]
    for want in ("\"packages/api-contract/**\"", "fetch-depth: 0", "github.com/oasdiff/oasdiff@v1.11.7",
                 "bash .sdlc/ci/contract-check.sh \"origin/${{ github.base_ref }}\" packages/api-contract openapi.yaml"):
        self.assertIn(want, text)
```

- [ ] **Step 6: Implement `generate_contract_check(p) -> str`**

The workflow is `name: sdlc contract` and runs on `pull_request` with `paths: ["<path>/**"]`. It runs on `ubuntu-latest` with `permissions: contents: read`, and its steps are:
1. `checkout@v7` with `fetch-depth: 0`
2. `setup-go@v7` with `go-version: stable`
3. `go install github.com/oasdiff/oasdiff@v<ci.oasdiff_version>`
4. The `bash .sdlc/ci/contract-check.sh …` line from the test

It opens with the same managed-by header comment as `generate_ci`.

- [ ] **Step 7: Run the full suite to verify it passes.** Expected: all pass, including `test_every_template_renders_without_leftover_placeholders`, which now also walks `ci/contract-check.sh`.

- [ ] **Step 8: Commit** with message `feat(scaffold): contract breaking-change check`.

### Task 3: CODEOWNERS from config (`builtin:codeowners`)

**Requirements:** AC-7, G6

**Files:**
- Modify: `scripts/scaffold.py` (add `generate_codeowners(p) -> str` and route it in `render_source`)
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Produces: `builtin:codeowners`, rendered to `.github/CODEOWNERS` (seeded). It reads `project.owners`, and raises `ValueError("no project.owners in .sdlc/config.json")` when that is empty or missing.

- [ ] **Step 1: Write the failing test**

```python
def test_builtin_codeowners(self):
    self.commands_config(commands={"test": "make test"}, project={"profile": "large", "owners": {
        "/apps/web/": ["@acme/web"], "/packages/api-contract/": ["@acme/backend", "@acme/leads"]}})
    lines = [l for l in self.sc("preview", "builtin:codeowners")["text"].splitlines() if not l.startswith("#")]
    self.assertEqual(lines, ["/apps/web/ @acme/web", "/packages/api-contract/ @acme/backend @acme/leads"])
    self.write(".sdlc/config.json", json.dumps({"min_plugin_version": "1.3.0", "commands": {"test": "make test"}}))
    self.assertIn("no project.owners", self.sc("preview", "builtin:codeowners", expect=1)["error"])
```

- [ ] **Step 2: Run it to verify it fails.** Expected: FAIL.
- [ ] **Step 3: Implement `generate_codeowners(p)`.** Write a managed-by header comment, then one line per entry in config order (CODEOWNERS is last-match-wins, so order is the user's).
- [ ] **Step 4: Run the full suite.** Expected: all pass.
- [ ] **Step 5: Commit** with message `feat(scaffold): CODEOWNERS builtin`.

### Task 4: Monorepo static templates and the infra area

**Requirements:** AC-2, AC-8, G3, G4, G6, G7

**Files:**
- Create: `templates/project/monorepo/docs-README.md`, `api-contract-README.md`, `infras-README.md`, `releasing.md`
- Modify: `templates/project/config.defaults.json` (`areas.ci` gains `"infras/**"`)
- Test: none new. `test_every_template_renders_without_leftover_placeholders` already walks `templates/project/**`.

**Interfaces:**
- Produces: four templates with no `{{config…}}` placeholders. Task 5 renders them with `--class seeded`.

- [ ] **Step 1: Write the four templates.** Each stays short (≤40 lines) and in plain words:
  - `docs-README.md`: folders `specs/` (BA), `test-cases/` (QA), `designs/` (design), `runbooks/`. These are produced in each role's own workflow and synced here. Feature work in `.sdlc/<feature>/` **links** to them and never copies them. `knowledge/` is for codebase gotchas and conventions, not these.
  - `api-contract-README.md`: one folder per version (`v1/openapi.yaml`, `v2/…`). Merging to `main` publishes a version. Published versions take non-breaking additions only, and a breaking change means a new folder. CI (`sdlc contract`) enforces this. Each app generates its client from the version it uses, with its `generate:api` script, and doesn't commit the generated code. Backend owns this folder.
  - `infras-README.md`: Dockerfiles, compose files, deploy playbooks and IaC, grouped per app (`infras/<app>/`) or shared.
  - `releasing.md`: per-app tags `<app>@<semver>`, release branches `release/<app>-v<major>` when an older major needs fixes, and each app's CI running only on its own paths. This is the large profile only.
- [ ] **Step 2: Add `"infras/**"` to `areas.ci`** in `config.defaults.json`.
- [ ] **Step 3: Run the full suite.** Expected: all pass.
- [ ] **Step 4: Commit** with message `feat(templates): monorepo READMEs and infras area`.

### Task 5: The setup procedure (`references/monorepo.md`)

**Requirements:** AC-1, AC-2, AC-3, AC-4, AC-6, AC-7, AC-9, G1, G2, G5, G6, G7

**Files:**
- Create: `skills/setting-up-projects/references/monorepo.md`
- Modify: `skills/setting-up-projects/references/greenfield.md` (route to it from `stack`, `skeleton`, `commands` and `ci`)
- Modify: `skills/setting-up-projects/SKILL.md` (Hard stops list)
- Modify: `templates/spec-template.md` (add a `**References**` line under the header)
- Test: none. This is instructed behaviour, and review covers it.

**Interfaces:**
- Consumes: `builtin:ci`, `builtin:ci:<name>`, `builtin:contract-check`, `builtin:codeowners`, `templates/project/ci/contract-check.sh` and `templates/project/monorepo/*.md` from Tasks 1–4, plus the config keys in Public Surface.

- [ ] **Step 1: Write `monorepo.md`**, in the voice and density of `greenfield.md`. Its sections:
  1. **When.** Two or more apps. One app is today's flow, unchanged (AC-9). The contract applies when one app serves an API that another consumes.
  2. **Interview** (hard stops). Ask, with a suggested answer each:
     - the apps and the stack for each
     - "Who will work in this repo?", which sets `lean` or `large`
     - for `large`, the team handles per area
     - "Add `infras/`?"
     - the contract format (default OpenAPI)
     - whether to add the oasdiff check to CI
  3. **Propose** (one approval). Cover the tree (`apps/<name>`, `packages/api-contract` and other `packages/<name>`, `docs/`, plus `infras/` if yes), the generator per app, the workspace manifest per ecosystem, and the five commands per package.
  4. **Skeleton.**
     - Generate each app into `apps/<name>` with its official tool.
     - Create `packages/api-contract/v1/openapi.yaml` as a minimal valid spec.
     - Give each consuming app a `generate:api` script (or the stack's equivalent) that runs before build and test, with the generated output gitignored through `$S gitignore`.
     - A generator that needs another toolchain (such as Java) is a hard stop.
     - For `large`, create `docs/{specs,test-cases,designs,runbooks}/`; for `lean`, only `docs/`.
  5. **Config.**
     - Add one `packages` entry for each `apps/*` and `packages/*`.
     - Set `project.profile`.
     - For `large`, set `project.owners`, with backend on `/packages/api-contract/`. Also for `large`, don't set root `commands.test`.
     - Set `api_contract` only if OpenAPI was chosen and the check was accepted.
  6. **Renders** (all `--class seeded`):
     - The READMEs go to `docs/README.md`, `packages/api-contract/README.md` and, if chosen, `infras/README.md`.
     - CI: for `lean`, `builtin:ci` → `.github/workflows/sdlc-verify.yml`. For `large`, `builtin:ci:<name>` → `.github/workflows/sdlc-verify-<name>.yml` per package.
     - If `api_contract` is set, render `ci/contract-check.sh` → `.sdlc/ci/contract-check.sh` and `builtin:contract-check` → `.github/workflows/sdlc-contract.yml`.
     - For `large`, render `builtin:codeowners` → `.github/CODEOWNERS` and `releasing.md` → `docs/runbooks/releasing.md`.
  7. **Warn about required checks** (Review Focus 5).
  8. **Report** what was skipped and why: a declined or missing contract check, or no infras.
- [ ] **Step 2: In `greenfield.md`,** change the "several of these (→ monorepo)" bullet so that two or more apps means following `monorepo.md` for the `stack`, `skeleton`, `commands` and `ci` steps. The step names stay the same, so resume still works.
- [ ] **Step 3: In `SKILL.md` Hard stops,** add: team size, team handles, `infras/`, and the contract check.
- [ ] **Step 4: In `templates/spec-template.md`,** add `**References**: links to docs/ artifacts this feature builds on (BA specs, QA test cases, designs). Link, never copy.`
- [ ] **Step 5: Run** `claude plugin validate .` and the full suite. Expected: valid, and all pass.
- [ ] **Step 6: Commit** with message `feat(setup): greenfield monorepo procedure`.

### Task 6: Decision record, spec and stale-docs audit

**Requirements:** supports AC-1 to AC-9 (documents them)

**Files:**
- Create: `docs/adr/0005-greenfield-monorepo-layout.md`, in the shape of 0002: Status, Context, Decision, Consequences. Decision: one monorepo for every team size, no subtrees, folder-versioned contract, profile asked and never inferred. Add its row to `docs/adr/README.md`.
- Modify: `docs/specs/01-setup-upgrade-eject.md`:
  - Add the ADR to Decisions.
  - Add a scenario: "New multi-app repo".
  - Add requirements `SET-FR-0xx` (next free IDs) for the per-package CI, the contract check and CODEOWNERS, each `[enforced]` with its test names. Add one `[instructed]` row for the monorepo procedure (monorepo.md).
- Modify: `CHANGELOG.md`, adding under `## Unreleased` → `### Added` a plain-words entry for the user.
- Modify: `README.md` line 18, adding "a greenfield multi-app repo becomes an apps/packages monorepo with a versioned API contract".

- [ ] **Step 1:** Write the ADR and its README row.
- [ ] **Step 2:** Update spec 01 and the CHANGELOG.
- [ ] **Step 3: Run the stale-docs audit** (`CONTRIBUTING.md` → Stale-docs audit). Grep `monorepo`, `builtin:ci`, `CODEOWNERS`, `api-contract`, `infras` and `profile` across README, CONTRIBUTING, CHANGELOG, `knowledge/`, `.claude/rules/`, `docs/` and the `docs/diagrams/*.svg` `<desc>`. Fix what's stale, and name in the report anything left (e.g. an SVG needing relayout).
- [ ] **Step 4: Run** the full suite and `claude plugin validate .`. Expected: all pass, and valid.
- [ ] **Step 5: Commit** with message `docs: ADR 0005 and setup spec for the monorepo scaffold`.
