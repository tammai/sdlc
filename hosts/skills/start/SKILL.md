---
name: start
description: Start or resume a feature through the SDLC pipeline (spec → design → plan → build → test → review → security → ship → learn)
---

Use the `sdlc:orchestrator` skill now and follow it exactly.

Request: <the user's request>

If the request is empty, resume the active feature in `.sdlc/` (on a backlog, its current or next ready slice), or ask what to build if there is none. A request that is `B<n>` runs that slice of the active feature's backlog. A trailing `--autopilot` means `scripts/autopilot.py` started this headless session: follow the orchestrator's autopilot rules (Backlog slices), and ignore the flag when deciding whether the request is empty or `B<n>` (`--autopilot` alone resumes the active feature; every slice done: Feature close).
