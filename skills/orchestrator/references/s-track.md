# S, start to finish

Everything an S change needs, in one file: don't load start.md, define.md, build.md, review.md, ship.md or the templates. `$S` is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py"`, `$V` is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py"` (type it in full each time, or the hooks won't see the run).

1. **Setup check, one call:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" status`. `setup: none` → ask once whether to set it up (`/sdlc:setup`); no → go on and record it as a deviation. Then `scaffold.py paths <name>` for `state` and `intents`. Name: `<yyyy-mm-dd>-s-<slug>`; branch the same.
2. **Understand it.** Read the code it touches. Unclear what, why or how → ask, one question at a time. A bug: write the test that shows it, run only that test, and see it fail; find the root cause, not the symptom.
3. **Write the record**, each file once, a few lines each, with your file-writing tool:
   - `<state>`: `# <name>`, `Status: active`, `Process: 2`, `Track: S   (footprint: <n> files)`, `Risk: low|high`, `Top model: opus`, `Base: <git rev-parse --short HEAD>`, `Owner: <git config user.email>`, `Tool: <agent>`, `Current: Stage 1 – Define`, then `## Gate log`, `## Deviations`, `## Open questions`, each with `-`. Then `$S sync <name>`.
   - `intent.md`: what it's for, the request verbatim, the decision with what was ruled out, and for a bug the proof and root cause.
   - `spec.md`: `## Acceptance criteria` (`AC-001` …; a bug's AC-001 is the test that shows it), `## Acceptance tests`, `## Must never break`, `## Out of scope`. The table, exactly this shape (the Test cell is the file path, ` › `, the test name; `verify.py` parses it):
     ```
     | AC | Test | Run |
     |---|---|---|
     | AC-001 | tests/test_calc.py › test_add_positive | `python -m unittest tests.test_calc.T.test_add_positive` |
     ```
   - `plan.md`: `## How the build runs` (inline), `## Tasks` (numbered, each naming its files in backticks), `## Public Surface` (only exports and dependencies the change adds or whose signature it changes, what `verify.py`'s drift check compares; new behaviour inside an existing one isn't surface; `- none` if none), `## Deviations`.
   Then `$S advance <name> 4 --gate pass` (no stop on S).
4. **Build.** Write every AC's test, then one call before their code: `$V red AC-001 AC-002 …` (the bug's test already fails: record it); if one is refused, nothing is recorded: fix it and rerun. Write the code, independent edits as parallel tool calls in one turn, running only the nearby tests. Then `$V` once: lint, typecheck, build, the full suite, each AC's test, drift. Fix until it passes. A change from the plan goes in `plan.md`'s `## Deviations` as `What: … Why: … Effect: …`.
5. **Review decision, by this list only.** Security when `Risk: high` or a changed path matches `areas.sensitive` or `areas.migrations` (the effective ones, plugin defaults included: `scaffold.py config`); UI when a changed path matches `areas.ui`; code (low) when `plan.md`'s `## Public Surface` isn't `- none`. Nothing fires → none: the default for S, and no review this list doesn't name runs. Run each that fires once, fresh, on `opus`; highs go back to step 4. Write `review.md` once: `## Recommended and chosen` (which triggers fired, so what ran), `## Verdicts` (or "none ran"), `## Fixed`, `## Lessons filed`.
6. **Ship.** S never enters Stage 5: go from 4 straight to 8. Learn: only a non-obvious lesson, via `sdlc:managing-knowledge`, linked in `review.md`; else nothing. One shell call: `$S verified <name> <head> <tree> && $S advance <name> 8 --gate pass --note "<review decision in a few words>" && ` the commit (code, tests and the record, with a message naming `<intents>`), push and `gh pr create`. `<head>` and `<tree>` are from `$V`'s passing line (writing the record doesn't change code, so don't rerun `$V`; if code changed since, rerun it). Watch CI (one fix, then ask); no remote: commit only and stop with the branch ready. End with a few lines: what changed, the test result, branch and commit (and the PR). Then `$S set <name> Status done`, and don't commit that change: it rides with the next commit.

Stay inside the change: files the tests leave behind (`__pycache__`, caches) aren't drift and need no `.gitignore` edit; mention them in one line at most.

Anything that isn't S after all (a second area, an unclear cause, high risk that needs the user's call): stop, say so, and continue as M from `define.md`.
