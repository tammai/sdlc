# Install

In Claude Code:

```
/plugin marketplace add tammai/sdlc
/plugin install sdlc@sdlc
```

**Restart the session** so the commands and hooks load. `/plugin` shows whether sdlc is enabled.

Optional companions (setup offers them):

- `sdlc-extras@sdlc`: the Ralph loop, hookify commands, extra review agents.
- `sdlc-stepper@sdlc`: a bar above the prompt showing the active feature's phase ([README](../../plugins/sdlc-stepper/README.md)).

Using Claude Code on the web or a routine? See [Cloud sessions](Cloud-sessions.md).

## Requirements

Your project needs nothing extra. Your machine needs:

| Need | For |
|---|---|
| `git` | Worktrees, the freshness hook, commit and PR commands |
| `gh` | `/sdlc:code-review` and PR commands |
| Python 3.9+ | All hooks and `scripts/` (stdlib only; macOS system 3.9 works). Found via `hooks/sg-python.sh` (`python3`, `python` or `py -3`) |
| `jq` | Ralph loop stop hook (`sdlc-extras`) |
| Node | Brainstorming visual companion |
| `typescript-language-server`, `typescript` | TypeScript code intelligence (`npm i -g typescript-language-server typescript`) |

## Other coding agents (experimental)

| Agent | Install |
|---|---|
| Codex | `codex plugin marketplace add tammai/sdlc`, then `codex plugin add sdlc@sdlc` |
| Cursor | Customize → Import from Repo → `https://github.com/tammai/sdlc` |
| Antigravity | In a clone: `python3 scripts/hosts.py dist antigravity <folder>`, then `agy plugin install <folder>` |

What works there: [Limitations](Limitations.md).

## Check the install

In a scratch repo:

1. `/sdlc:doctor`: no ❌. Expected warnings: the repo isn't set up, and (until the first session finishes) the reviewer environment.
2. `/sdlc:setup` with a one-line description: it proposes a stack, and after your OK it writes `.sdlc/config.json` and the rest on `sdlc/setup`. Run `/sdlc:doctor` again: the repo checks should be ✅.
3. `/sdlc:start` with a tiny request: it creates `.sdlc/state/<feature>.md` and announces the track, risk and top model.

Something wrong? [Health check](Health-check.md) → [Troubleshooting](Troubleshooting.md).

## Update and uninstall

- **Update:** update the marketplace and plugin from `/plugin`, restart, then run `/sdlc:upgrade` in each repo ([16](Setup-and-upgrade.md#16-upgrade-after-a-plugin-update)).
- **Uninstall:** run `/sdlc:eject` in each repo ([17](Setup-and-upgrade.md#17-remove-sdlc-from-a-repo)), then `/plugin uninstall sdlc`.

Working on the plugin itself: [CONTRIBUTING](../../CONTRIBUTING.md).
