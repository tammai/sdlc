# S, start to finish

Everything an S change needs, in one file: don't load start.md, define.md, build.md, review.md, ship.md or the templates. `$S` is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py"`, `$V` is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py"`. The record is two files: `<intents>/change.md` for people and the state file for the agent.

1. **Setup check, one call:** name it `<yyyy-mm-dd>-s-<slug>` (the branch too), then `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" status && python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <name>` (`state` and `intents`). `setup: none` → ask once whether to set it up (`/sdlc:setup`); no → go on and record it as a deviation.
2. **Understand it.** Read the code it touches. Unclear what, why or how → ask, one question at a time. A bug: write the test that shows it, run only that test, and see it fail; find the root cause, not the symptom.
3. **Write the record and the tests in one turn**, as parallel writes with your file-writing tool, a few lines each:
   - `<state>`: `# <name>`, `Status: active`, `Process: 2`, `Track: S   (footprint: <n> files)`, `Risk: low|high`, `Top model: opus`, `Base: <git rev-parse --short HEAD>`, `Owner: <git config user.email>`, `Tool: <agent>`, `Current: Stage 1 – Define`; then `## Tasks` (numbered, each naming its files in backticks), `## Public Surface` (only exports and dependencies the change adds or whose signature it changes, what `verify.py`'s drift check compares; new behaviour inside an existing one isn't surface; `- none` if none), and `## Gate log`, `## Deviations`, `## Open questions`, each with `-`.
   - `<intents>/change.md`: `## Why` (what it's for, the request verbatim, and for a bug the proof and root cause), `## Decisions` (the decision and what was ruled out), `## Acceptance criteria` (`AC-001` …; a bug's AC-001 is the test that shows it), `## Acceptance tests`, `## Must never break`, `## Out of scope`. The table, exactly this shape (the Test cell is the file path, ` › `, the test name; `verify.py` parses it):
     ```
     | AC | Test | Run |
     |---|---|---|
     | AC-001 | tests/test_calc.py › test_add_positive | `python -m unittest tests.test_calc.T.test_add_positive` |
     ```
   - every AC's test (the bug's is already written).
   Then one call: `$S sync <name> && $S advance <name> 4 --gate pass && $V red AC-001 AC-002 …` (no stop on S). If a test is refused, nothing is recorded: fix it and rerun the red step.
4. **Build.** Write the code, independent edits as parallel tool calls in one turn, running only the nearby tests. Then `$V` once: lint, typecheck, build, the full suite, each AC's test, drift. Fix until it passes. A change from the plan: `$S deviation <name> "<file or task> What: … Why: … Effect: …"`, one line.
5. **Review decision, by this list only.** Security when `Risk: high` or a changed path matches `areas.sensitive` or `areas.migrations` (the effective ones, plugin defaults included: `scaffold.py config`); UI when a changed path matches `areas.ui`; code (low) when `## Public Surface` isn't `- none`. Nothing fires → none: the default for S, and no review this list doesn't name runs. Run each that fires once, fresh, on `opus`; highs go back to step 4. Then append `## Review` to `change.md` (the template's lines, one each: what fired and so ran, verdicts or "none ran", fixed, lessons filed).
6. **Ship.** S never enters Stage 5: go from 4 straight to 8. Learn: only a non-obvious lesson, via `sdlc:managing-knowledge`, linked in `## Review`; else nothing. One shell call: `$S verified <name> <head> <tree> && $S advance <name> 8 --gate pass --note "<review decision in a few words>" && ` the commit (code, tests, `change.md` and the state file, with a message naming `<intents>`), push, `gh pr create`, `&& $S set <name> Status done` (that change rides with the next commit). `<head>` and `<tree>` are from `$V`'s passing line (writing the record doesn't change code, so don't rerun `$V`; if code changed since, rerun it). No remote: commit only. Watch CI (one fix, then ask). End with a few lines: what changed, the test result, branch and commit (and the PR).

Stay inside the change: files the tests leave behind (`__pycache__`, caches) aren't drift and need no `.gitignore` edit; mention them in one line at most.

Anything that isn't S after all (a second area, an unclear cause, high risk that needs the user's call): stop, say so, and continue as M from `define.md`.
