# Spec 05: Security

Security feedback runs continuously while code is written, plus an explicit pass in Stage 7 for risky work.

**Entry points:** always-on hooks; Stage 7 of the orchestrator · **Source:** `hooks/security_reminder_hook.py` and modules, `hooks/sdlc_review_gate.py`, `hooks/sg-python.sh`, `hooks/ensure_agent_sdk.py`, `hooks/patterns.py`, `skills/orchestrator/SKILL.md` §7, `templates/project/rules/sensitive.md`, `templates/project/hookify/sdlc-secret-values.md`

## User scenarios

1. **Risky edit.** When Claude writes code matching a known-dangerous pattern (e.g. `eval`, `innerHTML`, `pickle.loads`), then a short warning is added to Claude's context.
2. **End of turn.** When Claude finishes a turn that changed code, then the changed lines are reviewed by a model and findings come back for Claude to address.
3. **Payments feature.** Given work touching payments, then it's at least M, and Stage 7 runs the full pass: reviewer agents with a security brief and a dependency audit.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| SEC-FR-001 | After each Edit/Write, regex rules flag dangerous patterns (25 rules: GitHub Actions injection, `child_process.exec`, `new Function`, `eval`, `dangerouslySetInnerHTML`, `document.write`, `innerHTML`/`outerHTML`/`insertAdjacentHTML`, pickle/marshal/shelve, `os.system`, shell subprocess, Go shell exec, unsafe YAML, cipher without IV, AES-ECB, TLS verification off, unsafe XML, `torch.load`, scripts without SRI) and warn Claude. | `[vendored]` patterns.py |
| SEC-FR-002 | At the end of a turn, the diff since the turn's start (baseline from `git stash create`) is reviewed by a model for concrete vulnerabilities and areas of concern; findings make Claude continue. Only code changed in the session is reviewed. | `[vendored]` security_reminder_hook.py |
| SEC-FR-003 | After `git commit`, `git push` or `gt`, a background review of the committed changes runs and wakes Claude with findings. | `[vendored]` hooks.json, security_reminder_hook.py |
| SEC-FR-009 | (Claude Code) While exactly one sdlc feature is active and its `Base:` is an ancestor of HEAD, the commit review runs once per review-ready diff: a commit made before Stage 5 is deferred (not reviewed, not recorded as reviewed), and the next commit from Stage 5 on is reviewed together with every unreviewed commit since `Base:`, as one net diff from `Base:` (every hunk of every commit, side branches included), and all of them are then recorded as reviewed; an amend is then reviewed whole, never as a delta. The state file is writable by the agent being reviewed, so deferral is bounded: never for a commit touching `.claude/`, `.sdlc/config.json`, `.github/`, `hooks/` or another agent's config, and not once 10 commits are unreviewed. 30 or more unreviewed commits: no widening. No active feature, several, a `Base:` outside this history, or any error: each commit is reviewed as before. The push review is unchanged; deferred commits a later commit doesn't cover are reviewed when pushed (within its range limit). | `[enforced]` test_sdlc_review_gate › test_build_commits_wait_for_the_review_ready_one_whose_review_covers_their_changes, test_without_an_active_feature_a_commit_is_reviewed_as_before, test_a_feature_whose_base_is_not_in_this_history_defers_nothing, test_deferral_is_capped_so_a_stuck_stage_cant_skip_reviews_forever; the hook's use of the plan `[vendored]` patch (NOTICE.md) |
| SEC-FR-004 | The reviewer's Python environment is built on first session start under the security state directory (`$SECURITY_WARNINGS_STATE_DIR`, else `$CLAUDE_CONFIG_DIR/security`, else `~/.claude/security`). Without credentials (API key or Claude Code OAuth token), model reviews are skipped and the user is told once. The SDK is installed at a pinned version (`AGENT_SDK_SPEC` in `ensure_agent_sdk.py`, override with `SG_AGENT_SDK_SPEC`); bump it deliberately. | `[vendored]` ensure_agent_sdk.py, _base.py; detection reused by doctor `[enforced]` test_doctor › test_environment_and_plugin_checks_always_run |
| SEC-FR-005 | Kill switches and toggles via environment: `SECURITY_GUIDANCE_DISABLE`, `ENABLE_PATTERN_RULES`, `ENABLE_CODE_SECURITY_REVIEW`, `ENABLE_COMMIT_REVIEW`, `ENABLE_STOP_REVIEW`, `MAX_STOP_HOOK_FIRINGS`, `MAX_DIFF_FILES`. | `[vendored]` |
| SEC-FR-006 | Writing a real-looking secret is blocked (file tools, notebook cells and Bash commands); editing sensitive files warns. | `[enforced]` test_guardrails › test_file_guardrails_on_write |
| SEC-FR-007 | Stage 7 full pass: `feature-reviewer` and `code-reviewer` with a security-only brief (injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk) and the stack's dependency audit; light (M) = hook findings plus dependency audit. | `[instructed]` orchestrator §7 |
| SEC-FR-008 | Gate: no critical or high finding open, no secrets in the diff; results in `docs/sdlc/intents/<feature>/security.md`. Work on auth, payments, secrets, PII or migrations always gets the full pass. | `[instructed]` orchestrator §0, §7; rules/sensitive.md |

## Non-goals

- Deep vulnerability scanning, SAST/DAST suites, dependency monitoring (Anthropic's `claude-security` isn't bundled; see `skills/orchestrator/references/integrations.md`).

## Known gaps

- A widened commit review (SEC-FR-009) still goes through the reviewer's 30-file prioritiser; files it drops are recorded as reviewed with the rest, as for any large commit.

- The security-guidance hooks are vendored and not covered by this repo's tests; behavior is upstream's. The reviewer environment has not yet been built on this machine (doctor reports it).
