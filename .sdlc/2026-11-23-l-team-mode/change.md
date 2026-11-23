# Team mode: role agents drive the sdlc stages

## Why

**Request (verbatim):** from `.sdlc/todo.md`: "Add a team mode to the orchestrator: when active, role-based agents drive the sdlc stages — not built yet (2026-10-25)". The user chose it next (2026-11-23).

**The user's words:** asked what team mode means, the user chose "A stage agent per role": the orchestrator becomes a coordinator; Define goes to an analyst agent, Build to a builder agent, Review to the reviewers (as now), Ship to a release agent; each starts fresh from the record, and the role guard keeps it to its job. Define's approval (2026-11-23): "Approve as written" (the coordinator's "no code edits" stays an instruction; the proposed hook is dropped).

Today one session runs a whole feature: it writes the change file, builds, fixes review findings and ships, so its context grows with every stage, and nothing but its own discipline keeps the stages apart. Only the reviewers are separate agents, held to their role by the role guard. Team mode extends that to every stage:
- each stage starts from the record alone, which tests that the record is enough;
- the writer of the criteria isn't their builder;
- the coordinator's context stays small across a long feature.

## Decisions

**Approaches considered:**

| Approach | Trade-off |
|---|---|
| **A. Stage agents in the session** (the user's choice) | Uses Claude Code's subagents and the existing role guard; works wherever subagents do |
| B. People own the gates | A different feature (approvals by named people), not agents; ruled out by the user's choice |
| C. Orca workers per role | Its own worktree per role; ties the plugin to Orca; ruled out by the user's choice |

| Decision | Ruled out | Why |
|---|---|---|
| `"team": true` in `.sdlc/config.json`, full mode only (advisory runs no flow), set by `scaffold.py team on\|off` (asked with setup's mode question, `/sdlc:setup team`); the session status line says `team` | per-feature switch | a team works one way; a per-feature switch would split the record's habits |
| Three new agents beside the reviewers: `sdlc:analyst` (Define: reads the brief and the code, writes `<change>` above `## Review`, the state's plan through `state.py new`), `sdlc:builder` (Build: the red step, the code and tests, verify, the commit; never `<change>` above `## Review`), `sdlc:releaser` (Ship: Learn, `ship.py`, commit, push, PR, CI watch; never product code) | one generic "stage agent" | each role's limits are what the role guard enforces |
| The role guard holds them: the analyst writes only `<change>`, its work folder and `.sdlc/.work/`; the builder writes anything but `<change>` (its `## Review` is the coordinator's); the releaser writes only `knowledge/`, `CHANGELOG.md`, `<docs>/recurring-defects.md`, `<change>`, `.sdlc/` and its work files | instructions only | the reviewers' roles are already enforced this way; the analyst writing code or the builder rewriting criteria is the failure team mode exists to prevent |
| Models: the analyst on the top tier (opus: it decides what gets built), the builder and the releaser on the standard tier (sonnet, effort high), as flow.md's Models rule already sets for cheap and standard work; the model router enforces the analyst's tier like a reviewer's | all opus | the build is standard work; Define is the costly mistake |
| The coordinator (the main session) dispatches each stage with the record's paths, reads the record between stages, asks the user at the flow's stops and records gates with `state.py`; it doesn't write code or the record itself (instruction; a hook could deny the main session's code edits in team mode, proposed below) | the coordinator builds too | then nothing changes |
| S changes, Trivial ones and autopilot keep their flow; team mode applies to M and L | every size | a subagent per stage costs more than an S change is worth |

**Proposals not asked for:** a hook denying the main session's product-code edits in team mode; the user didn't keep it.

## Acceptance criteria

- **AC-001** `scaffold.py team on` records `"team": true` (refused in advisory mode or before setup); `off` removes it; any other value is refused; no argument prints it; the session status line says `team` when it is on.
- **AC-002** The role guard denies the analyst a write outside `<change>`, its work folder and `.sdlc/.work/`.
- **AC-003** The role guard denies the builder a write to `<change>`.
- **AC-004** The role guard denies the releaser a write to product code (outside `knowledge/`, `CHANGELOG.md`, `.sdlc/` and the docs folder).
- **AC-005** The model router denies the analyst below the top tier.
- **AC-006** The three agents exist with their role, inputs and limits, and the orchestrator (`SKILL.md` = `commands/start.md`) and `flow.md` say how a team-mode feature runs (who does each stage, what the coordinator does).

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_team_mode.py › TeamModeTest.test_team_is_set_through_scaffold_in_full_mode_only | `python3.10 -m unittest discover -s tests -t tests -p test_team_mode.py -k test_team_is_set_through_scaffold_in_full_mode_only` |
| AC-002 | tests/test_team_mode.py › TeamModeTest.test_the_analyst_writes_only_the_change_file | `python3.10 -m unittest discover -s tests -t tests -p test_team_mode.py -k test_the_analyst_writes_only_the_change_file` |
| AC-003 | tests/test_team_mode.py › TeamModeTest.test_the_builder_never_writes_the_change_file | `python3.10 -m unittest discover -s tests -t tests -p test_team_mode.py -k test_the_builder_never_writes_the_change_file` |
| AC-004 | tests/test_team_mode.py › TeamModeTest.test_the_releaser_writes_no_product_code | `python3.10 -m unittest discover -s tests -t tests -p test_team_mode.py -k test_the_releaser_writes_no_product_code` |
| AC-005 | tests/test_team_mode.py › TeamModeTest.test_the_analyst_runs_on_the_top_tier | `python3.10 -m unittest discover -s tests -t tests -p test_team_mode.py -k test_the_analyst_runs_on_the_top_tier` |
| AC-006 | tests/test_team_mode.py › TeamModeTest.test_the_agents_and_the_flow_describe_team_mode | `python3.10 -m unittest discover -s tests -t tests -p test_team_mode.py -k test_the_agents_and_the_flow_describe_team_mode` |

## Must never break

- A repo without `team` runs exactly as today.
- The reviewers' and the qa-tester's role limits are unchanged.

## Failure modes

- **Untrusted input:** `team` is agent-editable config. Turning it on only adds limits (role agents and their guards), so no trust-anchor notice is needed; turning it off returns to today's flow.
- **A role agent stops mid-stage:** the record and the state file hold where it stands, so the coordinator re-dispatches that stage, as a fresh session resumes today.

## Out of scope

- People as gate owners (approach B) and Orca workers (approach C).
- Team mode on S, Trivial and autopilot.

## Review

- **What fired:** a code review, because Public Surface isn't none (config `team`, `scaffold.py team`, three agents). Risk is low, so it wasn't asked. Four rounds by fresh `sdlc:code-reviewer` agents on opus; reports in `.sdlc/.work/findings/2026-11-23-l-team-mode/`.
- **Round 1, FAIL.** All fixed test first:
  - H1 to H3: the analyst could write all of `.sdlc/` and the docs (config, findings, constitution); the router let a sonnet analyst through before any state existed; the builder's change-file deny was case- and spelling-sensitive. Fix: `team_place()` in `canon()` spelling, and the router checks the analyst under config `team` with no state.
  - M1: the Define gate's `state.py` moves had no owner. Every stage move is now the coordinator's.
  - M2: the releaser was denied Learn's places (CLAUDE.md, `.claude/rules/`, hookify rules, a package's CHANGELOG.md).
  - M3: setup ran `team on` before `init`.
  - M4: stale docs.
  - M5: test gaps.
  - Also fixed: L1 (handoffs), L2 (`mode advisory` drops `team`), L4 (status from the honoured mode), F1 to F5.
- **Round 2, FAIL** (past the cap; the user chose one more fix round). All fixed test first:
  - N1: any `.sdlc/<x>/` counted as a feature folder.
  - N2 and N3: Windows short names and streams.
  - N4: the analyst could write the hooks' records in `.sdlc/.work/`.
  - Also fixed: L1 (fable with no state), L4, F1 to F4.
- **Round 3, FAIL** (the user chose one more fix round). All fixed test first:
  - H1: in the old layout, a drafted `change.md` couldn't be re-edited before `state.py new`.
  - M1: a config-named objects path.
  - L1 to L3: the short-name rule was too wide; reserved `.sdlc` names; the hookify match was loose.
- **Round 4, PASS.** Two lows, ticketed in `.sdlc/todo.md`: the objects path from config isn't checked for where a link leads; `team_place()` runs for every subagent's call.
- **Criteria narrowed by review:** AC-002 reads "`<change>`, its work folder and `.sdlc/.work/`". The guard now also denies `.sdlc/.work/` (round 2, N4) and admits the feature's state file and objects.md. The test asserts the narrower rule.
- **Left as tickets:** the builder can still write the reviewers' reports and the state file (round 1 L3). In a workbench, an app repo without its own config can't take Learn's files (round 2 L3).
- **Tests:** `tests/test_team_mode.py`, 9 tests; full suite 865 OK on Python 3.10.
- **Lessons filed:** none. The canon()-spelling lesson already stands in recurring defects.
