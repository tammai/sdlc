# sdlc-stepper

A mini stepper above the Claude Code prompt for the sdlc feature in progress, so anyone reading the session can see where it stands without reading the transcript. It is one row: the four stages as marks joined by short lines, where a title would be, then where the session is now, with the feature at the right.

In the terminal, in a rounded outline and the terminal's theme colors:

```
╭────────────────────────────────────────────────────────────────────────────╮
│ ✓─●─○─○ · Build · B2 Title row · failing tests    2026-11-03-m-github-look │
╰────────────────────────────────────────────────────────────────────────────╯
```

The desktop app draws the same row with small icons: a green check when a stage is done, a green dot when it is current (the one thing that pulses: a ring spreads out from it) and a gray ring after, joined by 1px lines that are green once passed. A mod can't read the app's theme, so the icons use a green and a gray that read on both light and dark.

- **Phases** come from the active feature's state file (`.sdlc/state/<feature>.md`, `Current: Stage <n> – <name>`, and `Process: 2` or `3`, which number the stages differently, so the name is read first): done phases checked, the current one highlighted, later ones dim.
- **The words** after the stepper are the agent's latest update when it has made one: sdlc has it begin every update `<Phase> · <part> · <step>`, and the bar shows the last such line of what the model said, so it says what the transcript says. Otherwise they are built from the phase, the part in progress (else the next one) from the feature's `backlog.md`, by ID and title, and the step from what the session is doing: `verify.py red` is `failing tests`, editing a test file `tests` and other code `code`, `verify.py` `verify`, `git commit` `commit`, a review agent `reviews`, `ship.py` `checks`, `gh pr create` `PR`, `gh pr checks` `CI`. A tool the bar knows replaces an older update line, being newer. A step or line from an earlier phase isn't carried into the next.
- **Define:** sdlc writes a feature's state file at the end of Define, so before then there is nothing to read. The bar shows Define at once when you submit `/sdlc:start` in an sdlc repo with no feature on disk, then follows the agent's `Define · …` lines, and hands over to the feature's state file as soon as it exists (named, at Build). A start that turns out trivial, which never writes a state file or says a Define line, leaves nothing behind: a Define band nobody spoke for goes when its turn ends. A feature the model starts itself, without `/sdlc:start`, shows from its first `Define · …` line.
- **A short window:** the engine gives the band only the rows left above the prompt and hides a band that doesn't fit. The terminal band is 3 rows with its outline; given fewer than 3 it drops the outline and is one line, and with none to spare nothing can be shown. A taller window or a shorter prompt area brings it back.

It reads the repo the session started in, or, when that folder isn't an sdlc repo, the sdlc repos up to two levels below it (a workbench of several repos and worktrees), showing the one whose active feature changed last. With no active feature and no start in progress, or outside an sdlc repo, the bar shows nothing. It only reads files, and a failure in it never holds a prompt or a tool call.

## Install

It's in the sdlc marketplace and needs the sdlc plugin's files in the repo (`/sdlc:setup`), not the plugin itself:

```
/plugin install sdlc-stepper@sdlc
```

`/sdlc:setup` turns it on beside `sdlc@sdlc` when it writes the plugin keys (this machine's `.claude/settings.local.json`, or the committed `.claude/settings.json` for everyone on the repo); set it to `false` there to leave it off.

Claude Code only, in the terminal and the desktop app (the band isn't drawn in VS Code or on mobile). Collapse it with `[-]` or ctrl+x ctrl+a.

## Develop

`claude plugin validate plugins/sdlc-stepper` and `claude plugin test plugins/sdlc-stepper` (CI runs both); `claude --plugin-dir plugins/sdlc-stepper` loads it for one session and reloads it as you edit. `hooks/sdlc.ts` holds the parsing, the step rules and the update-line reader, `hooks/desktop.ts` the desktop stepper's SVG, `hooks/register.tsx` the hooks and both drawings.

MIT licensed, like sdlc.
