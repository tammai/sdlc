# sdlc-stepper

A mini stepper above the Claude Code prompt for the sdlc feature in progress, so anyone reading the session can see where it stands without reading the transcript. It is one row: the title `SDLC`, the four stages as marks joined by short lines, then where the session is now, with the feature at the right.

In the terminal, in a rounded outline and the terminal's theme colors:

```
╭─────────────────────────────────────────────────────────────────────────────────╮
│ SDLC ✓─●─○─○ · Build · B2 Title row · failing tests    2026-11-03-m-github-look │
╰─────────────────────────────────────────────────────────────────────────────────╯
```

The desktop app draws the same row, the title in semibold, with small icons: a green check when a stage is done, a green dot when it is current (the one thing that pulses: a ring spreads out from it) and a gray ring after, joined by 1px lines that are green once passed. A mod can't read the app's theme, so the icons use a green and a gray that read on both light and dark.

- **Phases** come from the active feature's state file (`.sdlc/state/<feature>.md`, `Current: Stage <n> – <name>`, and `Process: 2` or `3`, which number the stages differently, so the name is read first): done phases checked, the current one highlighted, later ones dim.
- **The words** after the stepper are the agent's latest update when it has made one: sdlc has it begin every update `<Phase> · <part> · <step>`, and the bar shows the last such line of what the model said, so it says what the transcript says. Otherwise they are built from the phase, the part in progress (else the next one) from the feature's `backlog.md`, by ID and title, and the step from what the session is doing: `verify.py red` is `failing tests`, editing a test file `tests` and other code `code`, `verify.py` `verify`, `git commit` `commit`, a review agent `reviews`, `ship.py` `checks`, `gh pr create` `PR`, `gh pr checks` `CI`, `gh pr merge` `done`. A tool the bar knows replaces an older update line, being newer. A step or line from an earlier phase isn't carried into the next.
- **Define:** sdlc writes a feature's state file at the end of Define, so before then there is nothing to read. The bar shows Define at once when you submit `/sdlc:start` in an sdlc repo with no feature on disk, then follows the agent's `Define · …` lines, and hands over to the feature's state file as soon as it exists (named, at Build). A start that turns out trivial, which never writes a state file or says a Define line, leaves nothing behind: a Define band nobody spoke for goes when its turn ends. A feature the model starts itself, without `/sdlc:start`, shows from its first `Define · …` line.
- **Ship:** Ship marks the feature's record done as it starts (`ship.py` advances to Stage 4 and sets `Status: done` in one run, so the commit carries the finished record). The bar keeps showing that feature at Ship through the commit, the PR and CI, as long as it's the feature the bar was already showing and this session ran its `ship.py`; in a workbench, a parallel session's ship of it gives way to the older active feature here. A feature that was shipped before the session started isn't shown, and neither is one after `/clear`, a restart or `--resume` partway through Ship. `/sdlc:start` or a `Define · …` line replaces it: the bar shows the next feature's Define, or an older active feature if one is being resumed. A `Build · …` line while fixing a red CI run doesn't, since that's still part of Ship. Once `gh pr checks` passes at Ship, the bar checks all four stages and reads `Ship · CI passed` (on the desktop nothing pulses), since only the merge is left. When the session merges the PR (a `gh pr merge` that succeeds; one that fails, on a red check or a conflict, reads `Ship · merge failed` at Ship), the bar checks all four stages and reads `Ship · done` for the rest of that turn, and the next prompt clears it. A PR merged outside the session (on GitHub) isn't seen: the bar then stays at Ship until `/clear`, a restart or the next start.
- **A short window:** the engine gives the band only the rows left above the prompt and hides a band that doesn't fit. The terminal band is 3 rows with its outline; given fewer than 3 it drops the outline and is one line, and with none to spare nothing can be shown. A taller window or a shorter prompt area brings it back.

It reads the repo the session started in, or, when that folder isn't an sdlc repo, the sdlc repos up to two levels below it (a workbench of several repos and worktrees), showing the one whose active feature changed last. With no active feature, no start in progress and no feature being shipped in this session, or outside an sdlc repo, the bar shows nothing. It only reads files, and a failure in it never holds a prompt or a tool call.

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
