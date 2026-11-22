# Troubleshooting

Start with `/sdlc:doctor`: it names the procedure (R-number) for each problem it finds.

Below, `state.py` means `python3 <plugin>/scripts/state.py <command> <feature> …`. It updates the state file and its control contract together. Never edit the state file by hand.

| Symptom | Go to |
|---|---|
| `/sdlc:*` commands missing | [R1](#r1-plugin-wont-load-or-components-are-missing) |
| First session slow, security reviewer unavailable | [R2](#r2-first-session-is-slow-or-the-security-reviewer-is-unavailable) |
| Security warnings too noisy or slow | [R3](#r3-security-hook-is-too-noisy-or-too-slow) |
| Turn won't end: "re-run tests" | [R4](#r4-blocked-at-stop-with-re-run-tests) |
| `verify.py` flips between pass and fail | [R5](#r5-verifypy-gives-different-answers-each-time) |
| Ralph loop won't stop | [R6](#r6-ralph-loop-wont-stop) |
| hookify rule silent or too loud | [R7](#r7-a-hookify-rule-doesnt-fire-or-fires-too-much) |
| Wrong feature resumed | [R8](#r8-sdlcstart-picks-the-wrong-feature-or-says-there-are-several) |
| State file wrong or lost | [R9](#r9-a-state-file-is-missing-stale-or-wrong) |
| Hooks fail on Windows / odd Python | [R10](#r10-hooks-error-on-windows-or-with-an-odd-python) |
| Hooks feel slow | [R10a](#r10a-hooks-feel-slow) |
| A gate blocks and you disagree | [R11](#r11-a-gate-is-blocking-and-you-disagree) |
| Setup stopped halfway | [R12](#r12-setup-stopped-halfway) |
| Project command wrong or tool missing | [R13](#r13-a-project-command-is-missing-wrong-or-its-tool-isnt-installed) |
| Upgrade keeps asking about a file | [R14](#r14-an-upgrade-wont-overwrite-a-file-or-keeps-asking-about-it) |
| Want a declined migration back | [R15](#r15-a-migration-was-declined-and-you-want-it-after-all) |
| Old failure blamed on your feature | [R16](#r16-verifypy-blames-the-feature-for-an-old-failure-or-the-baseline-looks-wrong) |
| Eject broke the build | [R17](#r17-eject-left-something-behind-or-broke-the-build) |
| Subagent dispatch denied | [R18](#r18-a-subagent-dispatch-is-denied-by-the-model-router) |
| "Verification anchors changed" | [R19](#r19-a-trust-anchor-notice-stops-the-turn) |
| Everything denied after a review | [R20](#r20-every-edit-and-command-is-denied-after-a-review) |

## R1. Plugin won't load or components are missing

1. `/plugin`: is `sdlc` installed and enabled? If not, [install](Install.md) it.
2. Commands use the `sdlc:` prefix. Restart the session after an install or update.
3. Still missing: update the marketplace and reinstall from `/plugin`.
4. Maintainers: `claude plugin validate .` and check that `.claude-plugin/plugin.json` and `hooks/hooks.json` are valid JSON.

## R2. First session is slow or the security reviewer is unavailable

**Cause:** on the first session the SessionStart hook builds a Python venv (Claude Agent SDK) in the background. It does this only if the session has credentials (a Claude Code sign-in or `ANTHROPIC_API_KEY`). Without credentials the model reviews are skipped, but pattern warnings still work. Closing the session before the build finishes cancels it.

1. Keep a signed-in session open until it finishes (timeout 180 s).
2. If it failed, check network access to the Python package index, then start a new session.
3. To rebuild, delete `agent-sdk-venv` from the security state directory (`/sdlc:doctor` prints the path; see [Where things live](Where-things-live.md#by-path)) and start a new session.
4. The venv lives outside the plugin, so it survives plugin updates.

## R3. Security hook is too noisy or too slow

1. **Find which part fires:** edit pattern warnings, the turn-end review, or the commit/push review. The turn-end and commit reviews run only while a **security-touched** feature is active (ADR 0019), once per review-ready diff. Any other change is recorded as reviewed without a model call. If a sensitive path gets no review, add it to `areas.sensitive`.
2. Turn off only that part ([switches](Configuration.md#security-hook-switches)).
3. Prefer fixing the finding. For a recurring false positive, tell the reviewer why in your reply; acknowledged findings are fine.
4. `SECURITY_GUIDANCE_DISABLE=1` is a last resort. If you use it, record it with `state.py deviation`.

## R4. Blocked at Stop with "re-run tests"

The freshness hook acts only while an active feature (`Process: 3`) is at `Current: Stage 3 – Review`. How it works: [Verification](Verification.md#the-freshness-hook).

1. Run the **full** test command: `commands.test` in `.sdlc/config.json` (monorepo: the stale package's own, from its `path`; the message names it) or the `test:` on the state file's `Commands:` line. A filtered run doesn't count.
2. Change no code after that run. Formatters, `sed -i` and subagents all count as changes.
3. `.md`, `.mdx`, `.txt`, `.rst` and anything under `.sdlc/`, `knowledge/`, `.claude/` or `docs/` never make results stale.
4. Wrong test command: fix it in `.sdlc/config.json` (or the `Commands:` line without setup). This raises a trust-anchor notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
5. Freshness state corrupt: delete `.sdlc/.work/verify-freshness.json`; the next full run recreates it.
6. The hook never fails the session on its own error. It writes `.sdlc/.work/verify-freshness.error`, which doctor reports. If it blocks wrongly, run the hook tests ([runbook](../runbook.md#run-the-tests)) and open an issue with the transcript and that file.

## R5. `verify.py` gives different answers each time

1. Don't retry until green: a flaky test doesn't pass the gate.
2. Run the failing test alone up to 5 times (its row in the change file's `## Acceptance tests` has a command that runs only that test). Record the results in `## Review`.
3. Fix or quarantine it with your approval, recorded with `state.py deviation`.

## R6. Ralph loop won't stop

(Ralph comes with the optional `sdlc-extras` plugin.)

1. `/sdlc-extras:cancel-ralph`. It reports the iteration it stopped at.
2. If that fails, delete `.claude/ralph-loop.local.md`; the stop hook then lets the session end.
3. Always start loops with `--max-iterations`.
4. A malformed state file no longer crashes the hook. Delete it if the loop keeps going.

## R7. A hookify rule doesn't fire, or fires too much

1. **Location:** `.claude/hookify.<name>.local.md` (personal) or `.claude/hookify/<name>.md` (team), under the folder the session started in.
   <details><summary>Session started above the repo (workbench)</summary>

   The repo's rules also apply to a file tool on a path inside it, or to a command that starts with `cd <repo>`, uses `git -C <repo>`, or runs with its cwd there. This holds only when the starting folder has no `.sdlc/` and the repo has `.sdlc/config.json`. `bash -c "cd ..."` and scripts don't count.
   </details>
2. **Frontmatter:** `enabled: true`; `event` is one of `bash`, `file`, `stop`, `prompt`, `all`; `action` is `warn` or `block`.
3. **Parser limits:** never put `---` in a pattern (write `-{3}`), keep each `pattern:` on its own line, and don't quote patterns. Matching is case-insensitive.
4. **Fields:** bash rules use `command`; file rules use `file_path`, `new_text` (or `content` on Write), `old_text` or `content`; prompt rules use `user_prompt`. Operators: `regex_match`, `not_regex_match`, `contains`, `not_contains`, `equals`, `starts_with`, `ends_with`.
5. A rule triggers only when all its conditions match. Warnings reach Claude as context; a block shows as the permission-denied reason.
6. With `sdlc-extras`, `/sdlc-extras:hookify-list` shows the active rules and `/sdlc-extras:hookify-configure` toggles them. Without it, edit `enabled:` in the rule file.
7. Firing too often: narrow the pattern, add a condition, or switch `block` to `warn`.

## R8. `/sdlc:start` picks the wrong feature, or says there are several

1. `/sdlc:status` lists every feature with its phase and status.
2. A finished feature: `state.py set <feature> Status done`. One on hold: `state.py set <feature> Status paused` (this raises one trust-anchor notice, [R19](#r19-a-trust-anchor-notice-stops-the-turn)).
3. If it still asks which one, answer the prompt.

## R9. A state file is missing, stale or wrong

| Problem | Fix |
|---|---|
| Wrong field | `state.py set <feature> <Field> <value>` (Status, Track, Risk, Top model, Base, Owner, Tool, Slice gates, Process). Changing Track, Risk, Top model, Base or Process raises a notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)) |
| Wrong phase | `state.py advance <feature> <n>` without `--gate` (1 Define, 2 Build, 3 Review, 4 Ship; a backlog stays at 2 between parts) |
| Hand-edited, or `.json` missing/damaged | `state.py sync <feature>` rewrites the control contract. It refuses a state file without `Status:`, `Current: Stage <n> – <name>` and `Process: 3` |
| State file lost | Restore it from git history. Otherwise see below |

<details><summary>Rebuilding a lost state file</summary>

1. Write a new one from the template in `skills/orchestrator/references/flow.md` (S: `s-track.md`).
2. Rewrite its plan sections (how the build runs, handoff, tasks, Public Surface, deviations) from the change file and the diff. Otherwise `verify.py`'s drift check fails.
3. Tick the phases the change file shows as done (`## Acceptance tests` filled → Define; `## Review` written → Review) and set `Current:` to the next stage.
4. Run `state.py sync <feature>`, then `state.py deviation <feature> "state file reconstructed"`.
</details>

## R10. Hooks error on Windows or with an odd Python

`hooks/sg-python.sh` tries `python3`, `python` and `py -3`, skips the Microsoft Store stub, and forces UTF-8. It caches its choice in `sdlc-hook-python` (in the plugin's data folder, else `~/.cache/sdlc/`). Under Claude Code it also writes `sdlc-hook-python.fast`, which hooks start directly. While that path exists, a PATH change won't reach the hooks.

1. Force a fresh probe: delete both cache files.
2. See which Python it picked: `bash hooks/sg-python.sh -c "import sys; print(sys.version)"`.
3. Doctor's "hook python" row fails: install Python 3 from python.org (not the Microsoft Store) and, on Windows, Git Bash.

The Ralph loop's hook (`sdlc-extras`) runs under bash.

## R10a. Hooks feel slow

1. Set `SDLC_HOOK_TIMES=1`, for example `"env": {"SDLC_HOOK_TIMES": "1"}` in `.claude/settings.local.json`, then restart.
2. Each hook appends `{"t", "hook", "event", "tool", "ms", "rc"}` to `.sdlc/.work/hook-times.jsonl`. Times include the launcher; turn the setting off after measuring.
3. It needs bash 5+ (`EPOCHREALTIME`). macOS's stock bash 3.2 logs nothing, so run `brew install bash`.
4. Totals per hook:
   `python3 -c "import json,collections; c=collections.Counter(); [c.update({(e['hook'], e['event']): e['ms']}) for e in map(json.loads, open('.sdlc/.work/hook-times.jsonl'))]; print(c.most_common())"`

The security review after a commit, push or Stop runs in the background (`asyncRewake`), so its time doesn't hold up tool calls.

## R11. A gate is blocking and you disagree

A gate is a decision, not a fault. Say `skip` or `just ship it`: the agent names the skipped gates, records them as a deviation, and continues ([9](Shipping-and-gates.md#9-skip-a-gate-deliberately)). [Hard stops](How-it-works.md#hard-stops) are different: they always wait for your answer and can't be skipped.

## R12. Setup stopped halfway

1. Run `/sdlc:setup` again. It resumes from `completed_steps` in the lock, on the same `sdlc/setup` branch.
2. Config or lock won't parse: fix the JSON or restore it from git, then rerun.
3. To restart clean, delete the branch, run `python3 <plugin>/scripts/scaffold.py init --kind <greenfield|brownfield> --force`, then rerun setup.
4. "Working tree not clean": commit or stash first.

## R13. A project command is missing, wrong, or its tool isn't installed

1. `/sdlc:doctor` or `python3 <plugin>/scripts/scaffold.py contract` shows the missing commands and the tools not on PATH, per package.
2. Commands live in `.sdlc/config.json` (`commands`, or `packages[].commands`). Use what the team already runs; set a step to `null` if it doesn't apply.
3. Install the missing tool the way the project expects (its lockfile and toolchain files say which version), or fix the command.
4. Run `scaffold.py run-commands` to record a run, then `/sdlc:upgrade` so CI follows. Changing commands during a feature raises a notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).

## R14. An upgrade won't overwrite a file, or keeps asking about it

This is on purpose: the file is seeded and you edited it (`scaffold.py render --if-unchanged` exits 2). Choose:

- **apply** takes the proposed merge,
- **skip** asks again next time,
- **keep mine** runs `scaffold.py forget <path>`, so the file is yours for good.

A plugin file you deleted is offered back once; declining it forgets it.

## R15. A migration was declined and you want it after all

`/sdlc:upgrade --revisit` lists skipped migrations, with the reason you gave, and offers each again. `scaffold.py migrations --revisit` shows the list without changing anything.

## R16. `verify.py` blames the feature for an old failure, or the baseline looks wrong

1. Check `.sdlc/baseline.md`. It lists failing tests (file › name) and lint/type errors as counts per rule and file. A count that went **up** counts as new.
2. A brownfield repo with no baseline: rerun setup's baseline step.
3. Adding a pre-existing failure is **your** call. Add it with a note and record it with `state.py deviation`. During a feature this raises a notice ([R19](#r19-a-trust-anchor-notice-stops-the-turn)).
4. `verify.py` doesn't read the baseline. When only the test step fails and every failure is baselined, Build logs it (`state.py log`) and passes the gate. Ship needs `ship.py <feature> --waive-baseline`, which matches failing test names from the runner's report. If it says it "couldn't match the failing tests", fix the failures or use a reporter it reads (pytest, unittest, jest, vitest, go test, node --test). See [spec 04 Known gaps](../specs/04-verification.md#known-gaps).

## R17. Eject left something behind or broke the build

1. `scaffold.py eject` (a dry run) shows what it would still remove. Edited plugin files are deleted only when you say so.
2. Remove leftover imports of deleted files by hand (`eslint.sdlc.mjs` in `eslint.config.*`, `extend = ".sdlc/lint/ruff.sdlc.toml"` in `pyproject.toml`), then rerun the verify commands.

## R18. A subagent dispatch is denied by the model router

The router checks dispatches only while a feature (`Process: 3`) is `Status: active`. The deny reason names the failed check. Every dispatch is logged to `.sdlc/.work/dispatches.jsonl`.

| Denied because | Fix |
|---|---|
| No model named | Name `sonnet` or `opus`. Exempt: forks, and impeccable's own `impeccable-*` agents |
| Fable | Only on request: `state.py set <feature> "Top model" fable` on **every** active feature (raises a notice, [R19](#r19-a-trust-anchor-notice-stops-the-turn)) |
| Haiku | Denied everywhere. Use `sonnet` with `effort: high` |
| Reviewer below Opus | Every review agent (code-reviewer, feature-reviewer, ui-reviewer, qa-tester, pr-test-analyzer, silent-failure-hunter) needs `opus` (or `fable`), at every size |

Forks are never checked; they run on the session model. To keep Fable out of forks, don't run the session on Fable.

## R19. A trust-anchor notice stops the turn

The files the hooks trust (state, change file, baseline, config) are writable by the agent the hooks check. So `hooks/trust_anchor.py` can't prevent a change; instead it **shows** you each change. What it reports: [The trust anchor stopped me](Shipping-and-gates.md#21-the-trust-anchor-stopped-me).

1. **Stricter** changes (Track up, Risk low → high) only show "Stricter process: …" and don't block.
2. **Any other** change blocks the stop once. The agent must tell you what changed and why, without undoing it on its own. Your answer to its `Trust anchor` dialog, or your next message, accepts the change as the new anchor. Autopilot stops at a notice you haven't seen.
3. **"verify records disagree":** rerun `verify.py` and say why the record changed.
4. **Wrong change:** say so and have it reverted (`state.py set`, or restore the file from git). Reverting is itself a notice.

## R20. Every edit and command is denied after a review

**Cause:** the review-rounds hook holds a feature whose last allowed review round still ends `VERDICT: FAIL` (round 2, unless `review_rounds` in `.sdlc/config.json` allows more). Everything except the project's tests, `verify.py` and a reviewer's report is denied until you decide.

1. Claude should already be asking in a `Review cap` dialog: one more fix round, a waiver (`waived round <N>`), or stop. Answer it, or send any message; either allows one more round.
2. To allow more rounds for this and later features, type `/sdlc:setup review-rounds <n>` (2 to 5) yourself. The hook reads the number from your prompt and writes it to `.sdlc/config.json`; commit that so later features start from it. This prompt only sets the cap and doesn't also grant a round, so a number at or below the round already reached keeps the hold.
3. A number the agent writes into config can only **lower** the cap: a feature's ceiling follows config down, and goes up only on your typed command. If a value you committed doesn't take effect, check the feature's `ceiling` in `.sdlc/.work/review-rounds.json`.
