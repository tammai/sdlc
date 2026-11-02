---
type: gotcha
title: A stock Mac has bash 3.2 and no timeout binary
description: Why hook-timing logs nothing and the prove_budget wrapped-command tests fail on macOS, and how the suite handles it.
tags: [macos, bash, tests, hooks]
updated: 2026-11-02
---

# A stock Mac has bash 3.2 and no timeout binary

## Symptom
On an Intel Mac, three tests failed: two in `test_prove_budget` and the hook-times test in `test_sg_python`. Separately, `SDLC_HOOK_TIMES=1` logged nothing.

## Cause
- `hooks/sg-python.sh` timestamps with `EPOCHREALTIME`, which needs bash 5. macOS's `/bin/bash` is 3.2.57, so the timing stays off without a message.
- `hooks/prove_budget.py` wraps a command in `timeout` or `gtimeout`. macOS has neither without coreutils, so the hook lowers only the tool timeout. That is the intended fallback.

The 2.3.0 notes blamed all three on `timeout`; only two are.

## Fix
The tests skip with their reason when the machine lacks the binary or the bash. A separate test covers the no-`timeout` path, so the fallback is still checked here. To measure hook time on a Mac, put a newer bash first on `PATH` (`brew install bash`; it compiles on an Intel Mac, so expect a wait).
