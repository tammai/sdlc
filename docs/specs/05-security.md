# Spec 05: Security

Security feedback runs continuously while code is written, plus an explicit pass in Stage 7 for risky work.

**Entry points:** always-on hooks; Stage 7 of the orchestrator · **Source:** `hooks/security_reminder_hook.py` and modules, `hooks/sg-python.sh`, `hooks/ensure_agent_sdk.py`, `hooks/patterns.py`, `skills/orchestrator/SKILL.md` §7, `templates/project/rules/sensitive.md`, `templates/project/hookify/sdlc-secret-values.md`

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
| SEC-FR-004 | The reviewer's Python environment is built on first session start under the security state directory (`$SECURITY_WARNINGS_STATE_DIR`, else `$CLAUDE_CONFIG_DIR/security`, else `~/.claude/security`). Without credentials (API key or Claude Code OAuth token), model reviews are skipped and the user is told once. The SDK is installed at a pinned version (`AGENT_SDK_SPEC` in `ensure_agent_sdk.py`, override with `SG_AGENT_SDK_SPEC`); bump it deliberately. | `[vendored]` ensure_agent_sdk.py, _base.py; detection reused by doctor `[enforced]` test_doctor › test_environment_and_plugin_checks_always_run |
| SEC-FR-005 | Kill switches and toggles via environment: `SECURITY_GUIDANCE_DISABLE`, `ENABLE_PATTERN_RULES`, `ENABLE_CODE_SECURITY_REVIEW`, `ENABLE_COMMIT_REVIEW`, `ENABLE_STOP_REVIEW`, `MAX_STOP_HOOK_FIRINGS`, `MAX_DIFF_FILES`. | `[vendored]` |
| SEC-FR-006 | Writing a real-looking secret is blocked (file tools, notebook cells and Bash commands); editing sensitive files warns. | `[enforced]` test_guardrails › test_file_guardrails_on_write |
| SEC-FR-007 | Stage 7 full pass: `feature-reviewer` and `code-reviewer` with a security-only brief (injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk) and the stack's dependency audit; light (M) = hook findings plus dependency audit. | `[instructed]` orchestrator §7 |
| SEC-FR-008 | Gate: no critical or high finding open, no secrets in the diff; results in `docs/sdlc/intents/<feature>/security.md`. Work on auth, payments, secrets, PII or migrations always gets the full pass. | `[instructed]` orchestrator §0, §7; rules/sensitive.md |

## Non-goals

- Deep vulnerability scanning, SAST/DAST suites, dependency monitoring (Anthropic's `claude-security` isn't bundled; see `skills/orchestrator/references/integrations.md`).

## Known gaps

- The security-guidance hooks are vendored and not covered by this repo's tests; behavior is upstream's. The reviewer environment has not yet been built on this machine (doctor reports it).
