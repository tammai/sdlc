# Recurring defects

One line per defect: what it looks like, then the severity.

- **A hook's command matcher misses another spelling:** a guard on file writes catches `cp`/`Set-Content` but not `mv`/`Move-Item`, a backslash or `..` path, another drive, or an abbreviated PowerShell parameter, so a protected file is written anyway; or it widens and denies ordinary commands. High (a guard that fails open). Fix with one path-normalising check on every route, not one spelling.
- **A fix for one shell breaks another:** quoting, paths or exit codes fixed for bash regress under cmd.exe or PowerShell, or the reverse. High when a hook or verify step is affected. Test each shell the fix touches.
- **Two report families share one counter or key:** a new report written into a folder or JSON that another gate counts (review rounds, waivers, grants) changes what that gate sees. High.
- **Malformed state or config crashes a script:** a lock, manifest or config value that is `null`, the wrong type or not a JSON object gives a traceback instead of `not run: <path> …`. Medium.
- **Repo config relaxes a safety stop or names a file:** a committed `.sdlc/config.json` value turns off a go-ahead (an environment marked routine skips production's stop) or becomes a path the agent reads or writes (a runbook, a reference file), checked only when a flag sets it, not when it's read back, and matched by exact name only (`prod` but not `prod-eu`). High when a stop is skipped. Fix with one check on every read: an allowlist or a plain-name pattern, the stop kept whatever the config says, paths kept inside the repo after symlinks and away from `.git/`, `.claude/` and `.sdlc/`.
- **A changed rule is still restated in the old words:** CHANGELOG, wiki, agent prompt or flow.md still describes the old behaviour. Medium (fix in passing when wording only).
