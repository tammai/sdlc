# Stage 3 · Plan (full flow)

- `sdlc:writing-plans` → `<intents>/plan.md` (bite-sized TDD tasks). More than about one session of work (~8–10 tasks, or several distinct parts): a backlog instead (`backlog-slices.md`), with each slice's plan written as it starts.
- `sdlc:analyzing-consistency` (L track; M when the plan has > ~8 tasks)
- **Gate:** no CRITICAL or HIGH scope findings; every requirement has a task and every task cites a requirement; Public Surface declared; the user picks the execution method: subagent-driven, native, or one implementer subagent for the whole plan (`Build: subagent`, the core's rule; record it with `state.py set <f> Build …`). On L with a backlog, the backlog's approval replaces this question.
