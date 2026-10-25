---
description: Start or resume a feature through the SDLC pipeline (spec → design → plan → build → test → review → security → ship → learn)
argument-hint: "[what you want to build or fix | B<n> to run that backlog slice]"
---

Use the `sdlc:orchestrator` skill now and follow it exactly.

Request: $ARGUMENTS

If the request is empty, resume the active feature in `.sdlc/` (on a backlog, its current or next ready slice), or ask what to build if there is none. A request that is `B<n>` runs that slice of the active feature's backlog.
