# Team mode's role guard: the builder's record limits and the objects link

## Why

**Request (verbatim):** three open tickets from `.sdlc/todo.md`, left by the team-mode review (#122):
- "Team mode's builder can still write the reviewers' reports under `.sdlc/.work/findings/` and the state file by hand (role_guard allows it anything but the change file); decide whether to deny them too"
- "role_guard `objects_files()` checks the barred folders (.git, .claude, .sdlc) only on the path config's `objects` names, not where a link leads, and admits an absolute path; apply `objects.target()`'s checks to the resolved path"
- "role_guard computes `team_place()` (config reads, stats) for every sdlc subagent's file call; compute it only for analyst, builder and releaser"

**Proof:**
- With config `team`, `sdlc:builder` writing `.sdlc/.work/findings/login/code-reviewer-r1.md` or `.sdlc/state/login.md` gets no deny.
- With `"objects": "docs/agents/objects.md"` and `docs/agents` a link to `.claude/agents`, the analyst's write is allowed, though objects.py refuses that path.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Deny the builder the reviewers' reports (`.sdlc/.work/findings/`) and a feature's state file (it changes through `state.py`, a shell call) | leave them open | a builder rewriting the review it is fixing, or its gate log, is what team mode's split exists to stop; nothing in Build writes either with a file tool |
| `objects_files()` applies the barred-folder test to the resolved path too, and refuses an absolute path or a drive | importing objects.py | hooks import only sibling modules |
| `team_place()` runs only for analyst, builder and releaser | — | no behaviour change; the reviewers' and the qa-tester's calls skip its config reads |

## Acceptance criteria

- **AC-001** With team mode's role rules, the builder's write to `.sdlc/.work/findings/<f>/<report>` or a feature's state file (either layout) is denied; its writes to code, tests and a feature's work files go through.
- **AC-002** The analyst's write to a config-named objects path is denied when that path leads (through a link) into `.git`, `.claude` or `.sdlc`, or is absolute.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_team_mode.py › TeamModeTest.test_the_builder_leaves_the_review_and_the_state_alone | `python3.10 -m unittest discover -s tests -t tests -p test_team_mode.py -k test_the_builder_leaves_the_review_and_the_state_alone` |
| AC-002 | tests/test_team_mode.py › TeamModeTest.test_an_objects_path_through_a_link_is_judged_where_it_leads | `python3.10 -m unittest discover -s tests -t tests -p test_team_mode.py -k test_an_objects_path_through_a_link_is_judged_where_it_leads` |

## Must never break

- Every existing team-mode, role-guard and qa-tester test.
- A repo without `team` and the reviewers' limits.

## Out of scope

- Team mode in a workbench (the releaser's Learn files in an app repo without its own config): its own ticket.

## Review

No review ran: no trigger fired.
