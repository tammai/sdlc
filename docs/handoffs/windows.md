# Handoff: verify the guardrail audit fixes on Windows

**Temporary file. Delete it when you finish (last step). It is untracked; do not commit it.**

## Context

A security audit of the plugin's guardrails (hookify engine, seeded `sdlc-*.md` rules, ralph-loop, doctor) found 5 high, 4 medium and 4 low issues. Everything except **H5** is fixed in the working tree and passes the suite on macOS (167 tests). **H5 is the reason for this run, and it can only be confirmed on Windows.**

**H5 (unverified):** `hooks/hooks.json` runs `pretooluse.py`, `stop.py`, `userpromptsubmit.py` and `verify_freshness.py` with bare `python3`. `hooks/sg-python.sh` documents that on Windows `python3` is often the Microsoft Store stub, which exits 49 silently. Claude Code treats any exit other than 2 as non-blocking, so every hookify guardrail would fail open with no message. Only the security hook goes through the launcher.

## Safety rule

**Never test a destructive command live** (`rm -rf /*`, force-push). If H5 is real, the guardrail is inert and the command would run. Pipe test input to the hook script on stdin, as below. The only live test is Step 6, which is harmless.

## Prerequisites

- Git for Windows (Git Bash, which also provides `perl`), `jq` on PATH, Python 3.10+ from python.org.
- This checkout with the fixes (copy the working tree, or `git fetch && git checkout <branch>` if it was pushed).
- Run everything in **Git Bash** from the repo root unless it says PowerShell.

## Step 1: Is `python3` a real interpreter? (H5)

```bash
command -v python3
python3 -c "print('ok')"; echo "exit=$?"
python -c "print('ok')"; echo "exit=$?"
```

Real: `ok`, exit 0. **Store stub: no `ok`, exit 49, or the Store opens. That confirms the precondition for H5.**

## Step 2: Run a hook exactly as Claude Code does

```bash
export CLAUDE_PLUGIN_ROOT="$PWD"
mkdir -p /tmp/h5 && cd /tmp/h5 && mkdir -p .claude/hookify && cp "$CLAUDE_PLUGIN_ROOT"/templates/project/hookify/sdlc-*.md .claude/hookify/
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf /*"}}' \
  | CLAUDE_PROJECT_DIR="$PWD" python3 "$CLAUDE_PLUGIN_ROOT/hooks/pretooluse.py"; echo "exit=$?"
```

- Expected: JSON containing `"permissionDecision": "deny"`, exit 0.
- **H5 confirmed if:** no output and exit 49 (or any non-zero), meaning the guardrails are off on this machine.
- Repeat with `python` and with `bash "$CLAUDE_PLUGIN_ROOT/hooks/sg-python.sh" "$CLAUDE_PLUGIN_ROOT/hooks/pretooluse.py"` in place of `python3`. If the launcher works and bare `python3` doesn't, the fix below is right.

## Step 3: Run the test suite

```bash
cd "$CLAUDE_PLUGIN_ROOT"
python -W ignore -m unittest discover -s tests 2>&1 | tail -40
```

The tests spawn `python3` and `bash` by name, so on a Store-stub machine most hook tests fail. That is H5 again, not a new bug. To get a clean run, put a real `python3.exe` on PATH (PowerShell):

```powershell
$py = (Get-Command python).Source
mkdir $HOME\pybin -Force; Copy-Item $py $HOME\pybin\python3.exe
$env:PATH = "$HOME\pybin;$env:PATH"
python3 -c "print('ok')"
```

Then re-run the suite from that shell. **Record what still fails.** Expected to be skipped on Windows: `test_catastrophic_regex_is_skipped` (no SIGALRM). Ralph tests need `bash`, `jq` and `perl` on PATH.

## Step 4: Windows path separators

Claude Code passes `C:\proj\.claude\hookify\sdlc-x.md` (backslashes). The new `sdlc-protect-guardrails-*` rules accept both separators and have tests. Check the older rules:

```bash
cd /tmp/h5
for p in 'C:\proj\.env' 'C:\proj\certs\server.pem' 'C:\proj\.claude\hookify\sdlc-reset-hard.md'; do
  printf '%s -> ' "$p"
  python3 - "$p" <<'EOF'
import json, os, subprocess, sys
env = dict(os.environ, CLAUDE_PLUGIN_ROOT=os.environ["CLAUDE_PLUGIN_ROOT"], CLAUDE_PROJECT_DIR=os.getcwd())
payload = {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": sys.argv[1], "content": "x"}}
r = subprocess.run(["python3", os.path.join(env["CLAUDE_PLUGIN_ROOT"], "hooks", "pretooluse.py")], input=json.dumps(payload), capture_output=True, text=True, env=env)
print(r.returncode, (r.stdout.split('"systemMessage"')[-1][:90] if r.stdout.strip() else "(no output)"))
EOF
done
```

Expected: `.claude\hookify\sdlc-*.md` blocked. **Known suspect, not fixed:** `sdlc-sensitive-files` uses `(^|/)\.env` and `id_rsa`, so `C:\proj\.env` probably won't warn. If it doesn't, the fix is `(^|[\\/])` in that pattern (and add a backslash case to `tests/test_guardrails.py`).

## Step 5: The doctor and ralph scripts

```bash
python scripts/doctor.py --root /tmp/h5 --format md | head -40
bash scripts/setup-ralph-loop.sh "demo" --max-iterations 2 && cat .claude/ralph-loop.local.md && rm -f .claude/ralph-loop.local.md
```

Expected: doctor reports the python/jq situation and 14 hookify rules parse; the ralph setup writes the state file.

## Step 6: One harmless live check (optional)

In a scratch project with `.claude/hookify/sdlc-*.md` copied in and this plugin installed, ask Claude to append a blank line to `.claude/hookify/sdlc-reset-hard.md`. Expected: **blocked** by `sdlc-protect-guardrails-file`. If the edit goes through, the hooks are not running (H5) or are not matching Windows paths. The worst outcome is one blank line.

## If H5 is confirmed: proposed fix (not applied)

Route the four hooks through the launcher that already handles the Store stub, in `hooks/hooks.json`:

```json
"command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/sg-python.sh\" \"${CLAUDE_PLUGIN_ROOT}/hooks/pretooluse.py\""
```

Do the same for `stop.py`, `userpromptsubmit.py` and `verify_freshness.py` (two entries). Keep `"timeout": 10`. Also make `/sdlc:doctor` fail when `python3` is missing or exits non-zero. The tests should then call the launcher too. Cost: one extra `bash` spawn per tool call.

## Report back

Paste: Step 1 and 2 output, the failing test names from Step 3 (before and after the `python3.exe` shim), the Step 4 lines, and the Step 6 result.

## Cleanup (do this last)

```bash
rm -rf /tmp/h5
rm -f docs/handoffs/windows.md
```

PowerShell: `Remove-Item -Recurse -Force $HOME\pybin` if you created the shim and no longer need it.
