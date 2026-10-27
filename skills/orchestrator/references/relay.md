# Relay: a thin main session, kept-alive stage agents (M and L)

**When.** M and L in an interactive Claude Code session. S, autopilot and headless runs (`--autopilot`, `claude -p`), and the other agents (Codex, Cursor, Antigravity) keep the in-session flow: read the phase files as the core says.

**The main session coordinates; it never does a phase's work.** It holds the state file, the user's exchanges and one-line status. It reads this file and the core, not `define.md`, `build.md` or `prove.md`. It never reads briefs, findings, documents or code. It passes paths, runs the `state.py` moves and shows the user what an agent hands it. Its context stays small (about 30–50k), so every turn is cheap.

## Stage agents

Two agents, `general-purpose`, each on the standard tier (`model: sonnet`). Each is spawned once and resumed with `SendMessage` every time after, so it never re-reads its files. Start a fresh one from the files instead after `/clear` or in a new session. A fresh one's brief names the feature, its phase file and `plan.md`'s `## Handoff to Build`.

- **Define agent.** Its brief: "You are the Define agent for `<feature>`. Read `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/define.md` and follow it from step 1, then the Protocol in `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/relay.md`. You ask the user nothing directly." It writes `intent.md`, `spec.md` and `plan.md` on the recommended answers, then writes its approval message to `<intents>/approval.md` and ends with `ASK:`. Every decision the user's reply settles goes into `plan.md`'s `## Handoff to Build` with its reason before the agent's `DONE:`, because the next agent knows only what is written.
- **Build agent.** Its brief: "You are the Build agent for `<feature>`. Read `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/build.md` and `prove.md`, then `<intents>/plan.md` (its `## Handoff to Build` first), `spec.md` and `intent.md`, and the Protocol in `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/relay.md`. Build the whole change." It builds natively in its own context, whatever `Build:` says, and runs `verify.py` red per AC and once at the end. Then it writes the Prove briefs and ends with `DONE: build pass` and one `DISPATCH:` per Prove agent from `prove.md`'s table. When Prove's results come back, it is resumed. It reads the findings, logs the round in `review.md`, and ends with `DONE: prove pass|fail`. On a fail, it is resumed in Build to fix the findings: it knows the design, so it breaks fewer of its rules.
- **L with several distinct parts:** one Build agent per part, **one after another** in the same worktree (`verify.py`'s records are single files that two agents would overwrite). Each is kept alive for its part's fixes.

## Protocol

A stage agent can't start agents of its own: where a skill or phase file says to dispatch one (`sdlc:designing-solutions`' explorers, a Prove reviewer), it writes the brief to a file and asks for it with `DISPATCH:`. It ends every turn with exactly one of these lines, as its last line. The main session acts on it mechanically, then resumes the agent with the answer:

| Line | The main session |
|---|---|
| `DISPATCH: <agent type> (<model>) → <brief path>` (one per line, several allowed) | spawns each, in one message so they run at the same time, each with the brief "Read `<brief path>` and do what it says. Write your report to `.sdlc/.work/findings/<agent>-r<round>.md` and answer with that path only." Then it resumes the stage agent with the paths. |
| `ASK: <file path>` | shows the file to the user verbatim and resumes the agent with the reply verbatim. |
| `QUESTION: <one line>` | asks the user, and resumes the agent with the answer. |
| `STATUS: <one line>` | shows it to the user, and resumes the agent with "continue". |
| `DONE: <phase> pass\|fail — <one line>` | runs the phase move below, then resumes or starts the next agent. |

**State.** The main session runs the moves: `advance`, `round` and `verified` (the `tree` from `verify.py status`, a short JSON it may read). Stage agents run `set`, `log`, `deviation` and `blocker`. Both read the state file.

**The moves:**

- Define agent `DONE: define pass` → `advance <f> 4 --gate pass`, then the Build agent.
- Build agent `DONE: build pass`:
  - with Prove: `advance <f> 5 --gate pass`, then its `DISPATCH:` lines.
  - with no Prove (M lite, `Prove: skip`): `verified`, `advance <f> 8 --gate pass`, Ship.
- `DONE: prove pass` → `round <f> <N> pass`, `verified`, `advance <f> 8 --gate pass`, then Ship in the main session (`ship.md`, at small context).
- `DONE: prove fail` → `round <f> <N> fail "<the line>"`, `advance <f> 4`, then resume the Build agent: "fix the findings in `review.md`, then `verify.py`". Its next `DONE: build pass` comes with the re-verification's `DISPATCH:` (an ac-checker on the ACs that failed, or nothing) → `advance <f> 5`, as above.
- The hard stops still go to the user: the round cap and a requirement failing twice come back as `ASK:`.
