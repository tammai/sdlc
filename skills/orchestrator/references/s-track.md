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
   - `plan.md`: `## How the build runs` (inline), `## Tasks` (numbered, each naming its files in backticks), `## Public Surface` (`- none` if none), `## Deviations`.
   Then `$S advance <name> 4 --gate pass` (no stop on S).
4. **Build.** For each AC, `$V red AC-nnn` before its code (the bug's test already fails: record it). Write the code, running only the nearby tests. Then `$V` once: lint, typecheck, build, the full suite, each AC's test, drift. Fix until it passes. A change from the plan goes in `plan.md`'s `## Deviations` as `What: … Why: … Effect: …`.
5. **Review decision.** Recommend from the diff: security when risk is high or a path in `areas.sensitive` or `areas.migrations` changed; UI when `areas.ui` changed; code (low) when the change touches persisted data, concurrency or a public interface; otherwise none. Run what you recommend, each once, fresh, on `opus`; highs go back to step 4. Write `review.md` once: `## Recommended and chosen` (what, why, chosen by the recommendation), `## Verdicts` (or "none ran"), `## Fixed`, `## Lessons filed`.
6. **Ship.** S never enters Stage 5: go from 4 straight to 8. Learn: only a non-obvious lesson, via `sdlc:managing-knowledge`, linked in `review.md`; else nothing. `$S verified <name> <HEAD> <tree>` (the `tree` from `$V status`; `reuse: true` means the last run still counts, since writing the record doesn't change code, so don't rerun `$V`) and `$S advance <name> 8 --gate pass --note "<review decision in a few words>"`. One commit: code, tests and the record, with a message naming `<intents>`. Push and open the PR, watch CI (one fix, then ask); no remote: stop with the branch ready. Then `$S set <name> Status done`, and don't commit that change: it rides with the next commit.

Stay inside the change: files the tests leave behind (`__pycache__`, caches) aren't drift and need no `.gitignore` edit; mention them in one line at most.

Anything that isn't S after all (a second area, an unclear cause, high risk that needs the user's call): stop, say so, and continue as M from `define.md`.
