# Parts (backlog slices)

Only for work too big for one session's context (L is one part by default: each part repeats the red step, build, verify and handoff), so it can pause, `/clear` and resume between parts, or run one fresh session per part (autopilot). Never for S, or for a change confined to 1–2 files. All parts land together: there is one Review and one Ship, after the last part (Feature close).

1. **Backlog.** In Define, write `<work>/backlog.md` from `${CLAUDE_PLUGIN_ROOT}/templates/backlog-template.md`: one row per part (something a test can see working), with its acceptance criteria, dependencies and size; every AC is in some row. The state file's `## Tasks` gives each part an outline. Both are approved with `<change>` in Define's one approval.
2. **Pick the part:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog.py" next <work>/backlog.md` (a part in progress, else the first `todo` whose dependencies are done; `check <backlog> B<n>` for a named one). Nothing ready while rows remain → say which and stop; every row `done` → Feature close. Then `state.py slice <f> start B<n>`; from Define, also `state.py advance <f> 4 --gate pass`. Parts stay at Stage 4.
3. **Each part:**
   - write `<work>/plan-B<n>.md` from `${CLAUDE_PLUGIN_ROOT}/templates/plan-template.md` and the part's outline (its tasks, files and Public Surface; its acceptance tests are rows in `<change>`);
   - build it as `flow.md`'s Build says, ending with `verify.py` passing;
   - `state.py verified …`, then one commit for the part (code, tests, plan, state) naming the record, and `state.py slice <f> done B<n> <commit>`;
   - update the state file's `## Handoff` with what the next part needs, so a fresh session can start from the files;
   - on to the next part (step 2), or, in an autopilot session, end.
4. **Gates.** Parts run back to back without asking, except for a change that adds scope or a hard stop. The user can opt in to stops at `plan` or `commit`: `state.py set <f> "Slice gates" "plan, commit"`.
5. **Backlog changes.** A part that turns out too big: split it and log it (`state.py log`). Anything that adds scope waits for the user (`state.py blocker raise`).
6. **Context.** At a part boundary, if the next part won't fit in what's left of this session, stop with one line: `B<n> done (<commit>). Next: B<m> <title>. Run /clear, then /sdlc:start.` Or the user runs autopilot: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot.py" <feature>` starts one headless session per part, then one for Feature close, and stops on a blocked part, a run that changed nothing, or an open trust-anchor notice.
   **In an autopilot session** (the request ends with `--autopilot`): no one is there to answer. Run the one part named (or Feature close), then end. Anything that would ask runs `state.py slice <f> block B<n> "<reason>"` and ends the session. Review takes its own recommendation (`flow.md`'s Review).
7. **▶ Feature close**, once every row is `done`: `state.py advance <f> 5 --gate pass`, then Review (`flow.md`) over the whole branch (`diff_stats.py --base <Base>` with `--plan` for the state file and each `plan-B*.md`), then Ship.
