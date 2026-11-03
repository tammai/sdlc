---
type: gotcha
title: A mode the rules name only by its script
description: Why asking for autopilot in a session launched autopilot.py and then asked the user how to go on, and how to word a mode so the session runs it.
tags: [skills, orchestration, autopilot]
updated: 2026-11-03
---

# A mode the rules name only by its script

## Symptom
The user typed "autopilot" mid-backlog. The session ran `scripts/autopilot.py`, whose headless sessions couldn't read the plugin's folder, then asked whether to run the parts here or have the user widen `permissions.additionalDirectories` (2.4.1 smoke test).

## Cause
The rules described autopilot only as `autopilot.py` plus a `--autopilot` flag that the script adds. Given the word and no other rule for it, the agent did the one thing the rules named: it ran the script, and fell back to asking when that failed.

## Fix
For any mode that has a script or flag, also say what the session does when the user asks for it in words (`backlog-slices.md` step 6: autopilot asked for in a session runs in that session), and whether the session may start the script itself (here: never; only the user runs it).

## How to detect early
Grep the skills for each mode's name: every one that appears only next to a script path or a flag needs a sentence for the request typed in words.
