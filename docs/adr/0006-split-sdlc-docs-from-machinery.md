# ADR 0006: Split sdlc documents from the plugin's machinery

- **Status:** Accepted, 2026-10-23. Amends [ADR 0001](0001-project-setup-upgrade-eject.md) (where setup writes the user-owned files).
- **Deciders:** Tâm Mai.

## Context

Everything the plugin kept in a repo lived in `.sdlc/`: config and lock, scratch, and also the documents people read and review (constitution, design system, every feature's brainstorm, spec, design, plan and reports). Teams keep their own BA, QA and design artifacts in `docs/` (see [ADR 0005](0005-greenfield-monorepo-layout.md)), so a feature's spec sat in a hidden folder away from the documents it builds on. Some repos also publish `docs/` as a website (Docusaurus, MkDocs, VitePress, Sphinx, Starlight), where internal plans must not appear.

## Decision

- **Machinery and state stay in `.sdlc/`:** `config.json`, the lock, `baseline.md` (the verifier maintains it and the hooks diff it at `Base:`), `ci/`, `lint/`, `.work/`, and one state file per feature at `.sdlc/state/<name>.md`.
- **Documents go to `docs_dir`** (default `docs/sdlc`): `constitution.md`, `design-system.md`, and `intents/<name>/` per feature. `<name>` keeps the `<yyyy-mm-dd>[-<ticket>]-<slug>` convention and is shared by the state file and the folder.
- **The location is recorded** as `docs_dir` in the project's `.sdlc/config.json`, never in the plugin defaults: its presence is what marks a repo as on the new layout. Setup and upgrade look for a docs-site builder first; if one exists they ask where the documents go (`.sdlc` itself is allowed). A value must be a folder inside the repo, not `.`, not `.git`; an invalid one counts as unset, because hooks grant access by it.
- **One resolver** (`hooks/sdlc_layout.py`) knows both layouts; hooks and scripts import it, skills ask `scaffold.py paths <name>`, templates render `{{layout.*}}`.
- **Existing repos move on upgrade:** the `1.7.0-artifact-layout` migration runs `scaffold.py relocate` (a dry run first, then `git mv`; clean tree only; resumable; stops on a name present in both layouts; records `docs_dir` only when nothing is left). Until then every reader accepts the old layout and doctor and status say to upgrade.

### Alternatives considered

| Option | Why not |
|---|---|
| Path conventions written into each skill, a hand-run migration | about 50 places re-derive the paths, and a manual move can miss files or the lock |
| A fixed `docs/sdlc` with a symlink for docs-site repos | symlinks are unreliable on Windows checkouts, and site builders often follow them |
| Moving the baseline too | it behaves like state: written by the verifier, compared by the trust anchor |
| New features in the new layout while old ones stay | a half-moved repo: every reader and every person has to know which feature is where |

## Consequences

- **Good:** specs and reports sit next to the BA, QA and design artifacts they link to; `.sdlc/` is only what the plugin runs on; the next layout change touches one module.
- **Costs:** every hook and script reads two layouts until repos have upgraded; skills say `<intents>`/`<state>` instead of a literal path; the upgrade renames every feature's files, so open feature branches see renames.
- **Guards:** the role guard, the freshness hook and the trust anchor now depend on `docs_dir`, so it is validated on every read and anchored at `Base:` like the commands.
