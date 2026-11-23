---
type: gotcha
title: The turn-end review's session state and how to test it
description: touched_paths is cleared at every Stop (a rewake sees only new edits; turn_touched spans the turn); only the first repo's baseline moves; a fake API needs hasVulnerabilities.
tags: [hooks, security-review, workbench]
updated: 2026-11-23
---

# The turn-end review's session state and how to test it

## Symptom
- Code that reads `snap["touched_paths"]` in `handle_stop_hook` sees only what was edited since the last Stop: `consume_stop_state` clears it on every Stop, so on a rewake (a Stop after findings) a repo the turn edited earlier is gone. Three review rounds of 2026-11-23-m-stop-review-every-repo went into fixes built on it.
- Skipping already-reviewed files on a rewake by time (`other_reviewed_at`) kept losing files: the file cap and the prompt's byte cap (`llm._cap_files_for_prompt`) cut files after the hook decided what was "sent".
- A finding's `filePath` is the dedup key everywhere ((filePath, category) in `_record_fire`, `_dedup_against_state`, the commit review): one file named two ways repeats a finding, two files named one way hide one.

## Fix
- For the whole turn, read `snap["turn_touched"]`: kept across rewakes, reset by the next prompt (`security_reminder_hook.py` UserPromptSubmit), last 200 paths with a re-touched path counted as recent.
- Only the first repo has a baseline that moves past reviewed code; anything else is diffed again from the turn's start (`hooks/stop_repos.py`). Prefer that (more tokens, nothing lost) over remembering what was sent.
- Name files by their path from the session's cwd: real paths the agent can open, distinct per repo in one review.

## How to detect early
Drive the real Stop path: `ANTHROPIC_API_KEY=test`, `ANTHROPIC_BASE_URL` at a local `http.server` that records the POST body, the prompt hook, a Write's PostToolUse, then Stop, all through `run_hook` with `SECURITY_WARNINGS_STATE_DIR` (`tests/test_workbench.py` `StopReviewEveryRepo`). The reply's text must be JSON with `hasVulnerabilities` (and `vulnerabilities`), or the review counts as failed (`review_failed`, exit 0). A second Stop with no new edits is the rewake.

## Related
- [Hooks that judge a Bash command by its text](hooks-read-command-text.md)
