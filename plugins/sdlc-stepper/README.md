# sdlc-stepper

A stepper bar above the Claude Code prompt for the sdlc feature in progress, so anyone reading the session can see where it stands without reading the transcript:

```
sdlc ✓ Define ─── ● Build ─── ○ Review ─── ○ Ship   2026-11-03-m-github-look
■□□ 1/3 parts  ·  B2 Title row · failing tests
```

- **Phases** come from the active feature's state file (`.sdlc/state/<feature>.md`, `Current: Stage <n> – <name>`): done phases green, the current one highlighted, later ones dim.
- **Parts** come from the feature's `backlog.md`: one square per part, filled when it's `done`, and the part in progress (else the next one) by ID and title.
- **The step** comes from what the session is doing: `verify.py red` is `failing tests`, editing a test file `tests` and other code `code`, `verify.py` `verify`, `git commit` `commit`, a review agent `reviews`, `ship.py` `checks`, `gh pr create` `PR`, `gh pr checks` `CI`. A step from an earlier phase isn't carried into the next.

It reads the repo the session started in, or, when that folder isn't an sdlc repo, the sdlc repos up to two levels below it (a workbench of several repos and worktrees), showing the one whose active feature changed last. With no active feature, or outside an sdlc repo, the bar shows nothing. It only reads files, and a failure in it never holds a prompt or a tool call.

## Install

It's in the sdlc marketplace and needs the sdlc plugin's files in the repo (`/sdlc:setup`), not the plugin itself:

```
/plugin install sdlc-stepper@sdlc
```

For everyone on a repo, add `"sdlc-stepper@sdlc": true` to `enabledPlugins` in its committed `.claude/settings.json`, beside `sdlc@sdlc`; `/sdlc:setup` names it as an optional companion when it writes those keys.

Claude Code only, in the terminal and the desktop app (the band isn't drawn in VS Code or on mobile). Collapse it with `[-]` or ctrl+x ctrl+a.

## Develop

`claude plugin validate plugins/sdlc-stepper` and `claude plugin test plugins/sdlc-stepper` (CI runs both); `claude --plugin-dir plugins/sdlc-stepper` loads it for one session and reloads it as you edit. `hooks/sdlc.ts` holds the parsing and the step rules, `hooks/register.tsx` the hooks and the drawing.

MIT licensed, like sdlc.
