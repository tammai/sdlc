# ADR 0032: Opt-in guards in config `guards` (S test lock, dependencies, lint config), turned off only with the user's acceptance

- **Status:** Accepted, 2026-11-24. Records: `.sdlc/2026-11-24-s-gh-92-s-test-lock/change.md`. Issue: #92 (part 2; part 3 adds more guards). Related: [0030](0030-modes-and-skips.md), [0031](0031-approval-policy.md).
- **Deciders:** Tâm Mai.

## Context

S is the most common track and usually gets no review. Since #56 P3, the red step locks the test files only on M and L, so on S a test can be weakened after it was recorded failing and nothing notices. Issue #92 proposed locking S always. The user chose an opt-in lock instead, so that no repo's behaviour changes on upgrade.

## Decision

1. **`"guards": {"s_tests": true}`** in `.sdlc/config.json`, set by `scaffold.py guard s-tests on|off` (`/sdlc:setup guard …`).
   - With it on, an S feature's `verify.py red` locks its test files, as on M and L.
   - A locked test that changes fails `verify.py` until a `test-change` deviation names it and `red --at <Base>` shows it still fails without the feature.
   - An unknown key, or a value other than `true`, counts as off.
2. **A guard is read like `mode`, `skip` and `approval`** (`sdlc_scopes.guards`):
   - turning a guard on counts at once;
   - turning one off counts only once the trust anchor has shown it and the user replied;
   - with no record, HEAD's committed config decides.

   A trust-anchor record without `guards` stays valid.
3. **`guards.dependencies` and `guards.lint_config`** (#92 part 3, `.sdlc/2026-11-24-m-gh-92-guarded-changes/change.md`).
   - **What fails.** `verify.py`'s full run fails on each guarded change since the feature's Base that the user hasn't allowed:
     - a dependency name new in a known manifest (`package.json`, `composer.json`, `pyproject.toml`, `Cargo.toml`, `pubspec.yaml`, `go.mod`, `Gemfile`, `requirements*.txt`);
     - any change to a known lint or type config file, or to its lint sections in `pyproject.toml`, `setup.cfg` or `tox.ini`;
     - a suppression comment (`@ts-ignore`, `eslint-disable`, `# type: ignore`, `# noqa`, …) whose count in a source file grew.
   - **What doesn't.** A version bump, or a removed or moved suppression.
   - **The lists are the plugin's**, never the repo's config. TOML, YAML and `go.mod` are read by a name rule that over-flags rather than misses, since there's no `tomllib` before Python 3.11.
   - **Why verify is the gate.** It runs before every part's commit, Review and Ship, and sees every route: file tools, a package manager in the shell, other hosts. The edit itself isn't prevented, only kept from being built on, reviewed or shipped.
   - **How the user allows an item.** `hooks/guarded_changes.py` records the answer `Allow` to a question headed `Allow change` that names the item's label (or a typed `allow`, which allows every item the last verify listed).
   - **Item ids carry content**: the name, the file's hash, the suppression's count. A later change asks again.
   - **Allowed items are logged.** `ship.py` writes them into the Gate log.
   - **An allowed dependency makes Review run the stack's dependency audit** (instructed).
   - With no guard on, nothing is checked: the only read is the guards lookup itself. Git failing, or no Base, fails verify (`guarded changes not checked`) rather than passing. A workbench feature's branched repos are checked too, their items named from the workbench (`api/package.json`).
4. **`guards.ui_evidence`** (#92 part 4, `.sdlc/2026-11-24-m-gh-92-ui-evidence-profile/change.md`).
   - **What Ship needs.** A change touching `areas.ui` needs at least one screenshot in the feature's `<work>/ui/`, or a `- manual: <reason>` line under `## UI evidence` in its change file. `ship.py` refuses it otherwise.
   - **The PR body.** `ship.py` lists the evidence in the commit message, which `gh pr create --fill` turns into the PR body. `gh` can't attach images, so the images are committed in the work folder.
   - **Who takes the screenshots.** Build takes them with the agent's browser tool, as an instruction (`ui-work.md`).
5. **`scaffold.py checks solo|shared`**, asked in setup with the mode.
   - **Shared** writes `approval: ml` and every guard on.
   - **Solo** takes them out.
   - The name isn't `team`, which already means role agents, nor `profile`, the monorepo's lean/large question.
   - **Shared never lowers a stricter `approval`** (`always` stays `always`).

## Consequences

- A team can make S as tamper-evident as M and L with one config key. Repos without it see no change.
- As with the other config the trust anchor reads, a guard turned off and committed with the anchor's record removed is honoured without a notice (`docs/wiki/Limitations.md`).
