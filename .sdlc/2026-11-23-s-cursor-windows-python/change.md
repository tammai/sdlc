# Cursor's hooks run on Windows

## Why

**Request (verbatim):** from `.sdlc/todo.md`: "Cursor's hooks call a bare `python3` (`hosts/cursor/hooks.json`), but Cursor on Windows runs hook commands through PowerShell, where `python3` may be the Store stub or missing; use a launcher that falls back to `python`/`py -3` as `hooks/sg-python.sh` does"

**Proof:** `tests/test_hosts.py` › `test_on_windows_powershell_the_command_skips_a_python3_that_is_the_store_stub` fails with the old command: the Store stub runs and exits 9009, and hook.py never sees the event. Checked live in cursor-agent 2026.11.22 on Windows: with a stub `python3` first on PATH, no sdlc hook ran.

**Root cause:** Cursor has no per-OS command. On Windows it writes the command into a Windows PowerShell 5.1 script, where a bare `python3` is the first one on PATH. That script gives the hook no stdin: it pipes the event into the command's first statement (`Get-Content payload.json -Raw | & { $input | <command> }`), so a launcher placed before Python takes the event and Python reads nothing.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| One command that reads in sh and PowerShell: `set "\" <# "; python3 … #>; ${\} \| & ".../hosts/cursor/hook.ps1" …` | `python3 … \|\| python …` | PowerShell 5.1 has no `\|\|`; Cursor has no Windows-only field |
| `set` (Set-Variable) keeps Cursor's piped event in `${\}`, which is piped on to `hook.ps1` and then to Python | a nested script reading stdin | Cursor pipes the event into the first statement only; a nested script got 0 bytes live |
| `hook.ps1` tries every `python3`, `python`, `py -3` on PATH, checked with an empty stdin for Python 3.9+ | only the first name found, or `sg-python.sh` | the Store stub sits on PATH as `python3`; there is no sh on a plain Windows machine |
| No `exit` or `exec` in the command | `exit $LASTEXITCODE`, `exec python3` | Cursor's script reads the exit code itself in both shells, and an `exit` or `exec` skips its cleanup (WSL: the shell-state dump after `eval "$1"`) |

## Acceptance criteria

- **AC-001** On Windows, the Cursor hook command run as Cursor's PowerShell script, with a Store stub as the first `python3` on PATH, runs hook.py on a working Python with the event Cursor piped in (non-ASCII intact), its arguments and its exit code.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_hosts.py › CursorHookCommandTest.test_on_windows_powershell_the_command_skips_a_python3_that_is_the_store_stub | `python3 -m unittest discover -s tests -t tests -p test_hosts.py -k test_on_windows_powershell_the_command_skips_a_python3_that_is_the_store_stub` |

## Must never break

- Cursor's hooks on macOS, Linux and WSL: `tests/test_hosts.py` › `test_the_command_runs_the_hook_under_sh` (dash, bash and zsh run it in Cursor's `eval "$1"` form; fish runs it with a harmless `set` error on stderr).
- A launcher failure never denies: no Python found exits 1 with nothing on stdout, and live Cursor still ran the call.

## Out of scope

- Codex's and Antigravity's hook commands (Codex has `commandWindows`; Antigravity falls back with `||` in cmd).
- Cursor started from Git Bash, where its inherited `SHELL` makes it run its PowerShell script through bash (Cursor's bug; noted in `knowledge/gotchas/host-hook-answers.md`).

## Live check (2026-11-23)

- Windows 11, headless cursor-agent 2026.11.22, this branch in `~/.cursor/plugins/local`, a stub `python3.cmd` first on PATH: hook.py ran on `Python310\python.exe` with the full event (594 and 2211 bytes), and the `dangerous-rm` hookify rule denied `rm -rf junk` (the folder stayed). With the old command, the call ran and hook.py never did. With no Python on PATH, the call ran.
- WSL, cursor-agent 2026.10.22: the same rule denied `rm -rf junk` through the new command.
- Not checked: the Cursor desktop app.

## Review

No review ran: no trigger fired.
