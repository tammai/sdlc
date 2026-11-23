# Advisory mode and skipped steps

Setup's first question: **full** (the whole workflow with its hooks and gates) or **advisory** (the skills and agents as aids, with no hook, gate or guardrail), for a team whose own workflow would conflict. Recommend full unless the user names such a workflow. Decision: `docs/adr/0030-modes-and-skips.md`.

## Team mode (full mode)

In full mode, ask in the same message whether role agents run each M or L feature's stages (team mode: an analyst for Define, a builder for Build, the reviewers, a releaser for Ship, with this session as their coordinator). Yes → `$S team on` after `init` (it is refused before); `/sdlc:setup team on|off` changes it later.

## Advisory setup

After `detect`, run `$S mode advisory`. Then run only these steps:
- `gitignore`
- `allowlist`
- `enable-plugin`
- `context-diet`, with its question
- `knowledge`

For Claude Code, also render `templates/project/advisory/sdlc.md` to `.claude/rules/sdlc.md`.

Record every other step done with "advisory". That means no guardrails, lint, CI, workflow rules, `agents` block, constitution, PRD, design system, deploy or review rounds, unless the user asks for one. `$S guardrails --render` renders nothing in an advisory repo.

## Changing it later

- `/sdlc:setup mode full|advisory` runs `$S mode …`.
- A full project can skip named steps: `/sdlc:setup skip security-review|code-review|ui-review|pr` runs `$S skip …`, and `--clear` undoes it.
- Advisory in a set-up repo silences the guardrails already installed (CI's own checks still run in CI) but doesn't remove their files; `$S mode` switches `.claude/rules/sdlc.md` to the advisory note and back while it is unedited. Say so; `/sdlc:eject` removes them.
- Either change toward fewer checks is shown to the user by the trust anchor at the turn's end, and their reply accepts it.
