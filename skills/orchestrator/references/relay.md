# Relay: a thin main session on L, independent checkers on M and L

**When.** M and L in an interactive Claude Code session. A backlog keeps the in-session flow (`backlog-slices.md`: its slices pause and resume across sessions), as do S, autopilot and headless runs (`--autopilot`, `claude -p`), and the other agents (Codex, Cursor, Antigravity) keep the in-session flow: read the phase files as the core says.

- **M: the main session is the maker** (ADR 0018). It does Define and Build itself, from `define.md` and `build.md`, asks the user directly, and fixes the checker's highs itself, each with a failing test first. For Prove it reads `prove.md` (the evidence, security, the `review.md` round shape, the stop rules, the end-of-Prove report), and this file's Prove section overrides its brief, dispatch and moves, so the checker stays independent of the session that wrote the code. Only the Prove section and the moves for M below apply; the stage agents and the Protocol are L's.
- **L: the main session coordinates; it never does a phase's work.** It holds the state file, the user's exchanges and one-line status. It reads this file and the core, not `define.md`, `build.md` or `prove.md`. It never reads briefs, findings, documents or code. It passes paths, runs the `state.py` moves and shows the user what an agent hands it. Its context stays small (about 30–50k), so every turn is cheap.

## Stage agents (L)

A Define agent, then one Build agent per part. Each is `general-purpose` and names its tier (Model Selection in `sdlc:subagent-driven-development`): the Define agent top (`model: opus`, where brainstorming and the design run) and each Build agent standard (`model: sonnet`). Each is spawned once and resumed with `SendMessage` every time after, so it never re-reads its files. Start a fresh one from the files instead after `/clear` or in a new session. A fresh one's brief names the feature, its phase file and `plan.md`'s `## Handoff to Build`. The checkers (`prove.md`) are spawned fresh every round and never resumed: their value is not having seen the build.

- **Define agent.** Its brief: "You are the Define agent for `<feature>`. Read `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/define.md` and follow it from step 1, then the Protocol in `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/relay.md`. You ask the user nothing directly." It writes `intent.md`, `spec.md` and `plan.md` on the recommended answers, then writes its approval message to `<intents>/approval.md` and ends with `ASK:`. Every decision the user's reply settles goes into `plan.md`'s `## Handoff to Build` with its reason before the agent's `DONE:`, because the next agent knows only what is written.
- **Build agent.** Its brief: "You are the Build agent for `<feature>`. Read `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/build.md` and `prove.md`, then `<intents>/plan.md` (its `## Handoff to Build` first), `spec.md` and `intent.md`, and the Protocol in `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/relay.md`. Build the whole change." It builds natively in its own context, whatever `Build:` says, and runs `verify.py` red per AC and once at the end. Then it writes the list of files it changed to `.sdlc/.work/findings/<feature>/changed-r<round>.txt` and ends with `DONE: build pass`. **It never judges Prove.** It doesn't write the checkers' briefs or read their verdict as pass or fail. When a round fails, it is resumed with the reports to **fix** every high finding: it knows the design, so it breaks fewer of its rules. It may not downgrade or waive a high finding. If it disagrees with one, it ends with `ASK:` and a file stating the finding and its case, because a waiver is the user's.
- **Several distinct parts:** one Build agent per part, **one after another** in the same worktree (`verify.py`'s records are single files that two agents would overwrite). Each is kept alive for its part's fixes.

## Protocol (L)

A stage agent can't start agents of its own: where a skill or phase file says to dispatch one (`sdlc:designing-solutions`' explorers, a Prove reviewer), it writes the brief to a file and asks for it with `DISPATCH:`. It ends every turn with exactly one of these lines, as its last line. The main session acts on it mechanically, then resumes the agent with the answer:

| Line | The main session |
|---|---|
| `DISPATCH: <agent type> (<model>) → <brief path>` (one per line, several allowed; Define's explorers, never Prove's checkers) | spawns each, in one message so they run at the same time, each with the brief "Read `<brief path>` and do what it says. Write your report to `.sdlc/.work/findings/<feature>/<agent>-r<round>.md` and answer with that path only." Then it resumes the stage agent with the paths. |
| `ASK: <file path>` | shows the file to the user verbatim and resumes the agent with the reply verbatim. |
| `QUESTION: <one line>` | asks the user, and resumes the agent with the answer. |
| `STATUS: <one line>` | shows it to the user, and resumes the agent with "continue". |
| `DONE: <phase> pass\|fail — <one line>` | runs the phase move below, then resumes or starts the next agent. |

**State.** The main session runs the moves: `advance`, `round` and `verified` (the `tree` from `verify.py status`, a short JSON it may read). Stage agents run `set`, `log`, `deviation` and `blocker`. Both read the state file.

## Prove: the main session dispatches, the checkers judge

The main session writes each checker's brief itself, from the fixed text below and paths only; the maker adds nothing but its changed-file list (on M the main session writes that list too, and nothing else: no summary of the change, no hint about what to look at). For round `<N>`:

1. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md --base <Base> --plan <intents>/plan.md > .sdlc/.work/findings/<feature>/diff-r<N>.md` (output to the file; don't read it).
2. Dispatch, at the same time, each fresh: every `sdlc:code-reviewer` on `model: opus` (the code review stays on the top tier at every risk), the `sdlc:ac-checker` on `model: sonnet` (standard), the `sdlc:ui-reviewer` on opus on L and sonnet on M:
   - **M: the checker**, `sdlc:code-reviewer`: "You are Prove's checker for `<feature>`, round `<N>`. Read `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/review-brief.md`, then `.sdlc/.work/findings/<feature>/diff-r<N>.md`, `<intents>/spec.md` and `<intents>/plan.md`. First read each `AC-nnn` beside the test `plan.md`'s `## Acceptance tests` names and say whether it would fail if the behaviour were missing. Then review the diff in one pass for correctness, silent failures, test gaps (rated 1–10) and, unless a security review runs this round, security. Round 2 and later: only what `.sdlc/.work/findings/<feature>/changed-r<N>.txt` lists, and the earlier highs. Write your report to `.sdlc/.work/findings/<feature>/code-reviewer-r<N>.md`, ending with its VERDICT line, and answer with the path."
   - **L: the same review brief** without the AC part, for `sdlc:code-reviewer`; and `sdlc:ac-checker` with "the feature dir `<intents>`; report to `.sdlc/.work/findings/<feature>/ac-checker-r<N>.md`".
   - **When they apply:** `sdlc:ui-reviewer` on a UI diff, reporting to `ui-reviewer-r<N>.md`, and, when the feature is security-touched (`Risk: high` in state, or the maker's changed files touch `areas.sensitive` or `areas.migrations`), one more `sdlc:code-reviewer` with a security-only brief (injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk), reporting to `security-r<N>.md`.
3. Read only the verdicts: `grep -sh "^VERDICT" .sdlc/.work/findings/<feature>/{code-reviewer,ac-checker,security,ui-reviewer}-r<N>.md` (the folder also holds `diff-r<N>.md` and Define's explorer reports, which carry no verdict). Every report PASS → `DONE` for Prove (below). Any FAIL, or a report with no VERDICT line → the round failed. **The move comes from this output alone**, never from reading a report: on M, where the maker reads the reports to fix them, the round is still decided before it opens one. The trust anchor reads the same lines: leaving Stage 5 while the latest round has a FAIL is a notice.
4. Log round `<N>` in `review.md` in `prove.md`'s round shape, with the verdicts as the checkers wrote them; highs under `## Fixed` once fixed, the rest under `## Tickets` (L: resume the Build agent to do it).

**The moves on M** (the main session is the maker):

- Define's approval, then `advance <f> 4 --gate pass` and Build in this session (`build.md`).
- Build's gate: with Prove, `advance <f> 5 --gate pass` and Prove's round (above); with no Prove (M lite, `Prove: skip`), `verified`, `advance <f> 8 --gate pass`, Ship.
- Every verdict PASS → `round <f> <N> pass`, `verified`, `advance <f> 8 --gate pass`, Ship.
- Any FAIL → `round <f> <N> fail "<the VERDICT lines>"`, `advance <f> 4`, then fix every high in the checkers' reports here, each with a failing test first, then `verify.py`. Never downgrade or waive a high: a disagreement goes to the user, whose waiver is recorded with `state.py deviation`. Then `advance <f> 5` and round `<N+1>`: a fresh checker on what changed.
- The hard stops go to the user (`prove.md`): the round cap and a requirement failing twice.

**The moves on L:**

- Define agent `DONE: define pass` → `advance <f> 4 --gate pass`, then the Build agent.
- Build agent `DONE: build pass`:
  - a part that isn't the last: start the next part's Build agent; no Prove yet (one Prove, at the end, over the whole change since `Base:`).
  - with Prove: `advance <f> 5 --gate pass`, then Prove's round (above).
  - with no Prove (`Prove: skip`): `verified`, `advance <f> 8 --gate pass`, Ship.
- Every verdict PASS → `round <f> <N> pass`, `verified`, `advance <f> 8 --gate pass`, then Ship in the main session (`ship.md`, at small context).
- Any FAIL → `round <f> <N> fail "<the VERDICT lines>"`, `advance <f> 4`, then resume the Build agent whose part holds the finding's files: "fix every high in the checkers' `.sdlc/.work/findings/<feature>/*-r<N>.md` reports, each with a failing test first, then `verify.py`". Its next `DONE: build pass` → `advance <f> 5` and round `<N+1>`: fresh checkers on what changed, the ac-checker only on the ACs that failed.
- The hard stops still go to the user: the round cap and a requirement failing twice come back as `ASK:`.
