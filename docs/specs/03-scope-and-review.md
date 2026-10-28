# Spec 03: Scope tracing and review

Every addition is traced to a request from intent to diff, and review gets measured facts so unrequested scope is caught mechanically where possible.

**Entry points:** Define and Review; `/sdlc:review-pr`, `/sdlc:code-review` · **Source:** `skills/orchestrator/references/define.md`, `review.md`, `review-brief.md`, `templates/change-template.md`, the state template in `references/start.md`, `templates/plan-template.md` (a part's plan), `agents/code-reviewer.md`, `commands/review-pr.md`, `plugins/sdlc-extras/agents/` (comment-analyzer, type-design-analyzer, code-simplifier), `scripts/diff_stats.py` · **Decision:** [ADR 0003](../adr/0003-guard-against-over-engineering.md), [ADR 0020](../adr/0020-sdlc-2-slim-process-core.md)

## User scenarios

1. **A proposal nobody asked for.** Given Define would add "audit logging" the user never asked for, when it writes the change file, then it lists it under the proposals not asked for, with a reason, and drops it unless the user keeps it.
2. **Undeclared export.** Given a state file whose Public Surface lists `createSession`, when the diff also exports `sneaky`, then `diff_stats.py --plan` flags it as undeclared, which reviewers treat as high severity.
3. **Review picked from the diff.** Given a change that touches a migration path, when the build ends, then the agent recommends a security review with that reason.

## Requirements

### The record: the change file and the plan

| ID | Requirement | Guarantee |
|---|---|---|
| SCO-FR-002 | Define adds no hardening, stricter validation, options, config or tooling that neither the request nor an applicable failure mode calls for; anything else it would add is listed under the change file's proposals not asked for and dropped unless the user keeps it. | `[instructed]` orchestrator: define, change-template |
| SCO-FR-027 | The spec lists the failure modes that apply to the change, only those (concurrent use, scale or large inputs, persisted-data migration and compatibility, partial failure or a crash mid-write, untrusted input, I/O errors), each turned into a criterion or a must-never-break line within the ~10-criteria budget; reviewers check the same list. | `[instructed]` change-template, orchestrator: define, `review-brief.md` |
| SCO-FR-028 | Every feature, at every size, has a change file, `<docs>/changes/<feature>.md`, from `templates/change-template.md`, under fixed headings a person and a script can both read: `## Why` (the request verbatim, what it's for and who it serves, why now, the user's words), `## Decisions` (what was ruled out and why, a bug's proof and root cause, proposals not asked for), what must be true (each AC with its test), and `## Review` last, written in Review. S fills it in a few lines. On L its Why and Decisions hold the design `brainstorming` returns, and there is no `design.md`. With the state file's plan sections (the how, with a Deviations section `state.py deviation` writes to), it lets a fresh agent build with no conversation. | `[instructed]` orchestrator: define, build; brainstorming, change-template |
| SCO-FR-007 | The state file's plan sections, at every size, written once in Define: how the build runs and why, a handoff for the next session, tasks each naming their files in backticks, and a **Public Surface** section declaring every new export, endpoint, command, config key, env var and dependency, or "none"; a part's `plan-B<n>.md` (from `plan-template.md`) the same. | `[instructed]` orchestrator: start, define, s-track, "Backlog slices", plan-template |

### Review facts (`diff_stats.py`)

| ID | Requirement | Guarantee |
|---|---|---|
| SCO-FR-010 | Diff base: the feature's `Base:` (from the state file given as `--plan` or the `state.md` beside a plan, else the only active feature's), else merge-base with origin/main, origin/master, main or master, else HEAD; includes committed, uncommitted and untracked changes, and lists every changed file, which `/sdlc:review-pr` picks reviewers from. Not a git repo → error. | `[enforced]` test_diff_stats › test_base_is_merge_base_with_main, test_base_is_the_active_features_base_even_on_main, test_a_state_file_as_the_plan_gives_its_own_base, test_no_changes, test_not_a_git_repo |
| SCO-FR-011 | Counts added code and comment lines per source file, block-comment and docstring aware; modified files count only added lines. | `[enforced]` › test_comment_counting_c_like, test_comment_counting_python_docstrings, test_modified_file_counts_only_added_lines |
| SCO-FR-012 | Flags comment-heavy files and diffs (over 25% comments with at least 20 added lines). Test files are excluded from the ratio and from export checks. | `[enforced]` › test_comment_heavy_flags, test_test_files_are_excluded_from_ratio_and_exports |
| SCO-FR-013 | New exports (TS/JS, Python, Go) are classified by caller files: unused, only used by tests, used only inside their own file, or single-use. | `[enforced]` › test_export_usage, test_python_and_go_exports |
| SCO-FR-014 | Flags interfaces and abstract classes with at most one implementation, and new dependencies (package.json sections, requirements files, go.mod). | `[enforced]` › test_single_implementation_abstraction, test_new_dependencies |
| SCO-FR-015 | With `--plan`, new exports and dependencies missing from Public Surface are flagged as undeclared, declared items not in the diff as not built; endpoints, commands, config and env are listed to check by hand; a plan without the section is flagged. `--plan` takes the state file (or a 1.x `plan.md`) and repeats: the union of the plans' lists is what's declared (a feature split into parts checks the state file and every `plan-B<n>.md` at Feature close). | `[enforced]` › test_plan_surface_flags_undeclared_and_unbuilt, test_plan_surface_none_declared, test_plan_without_surface_section_is_flagged, test_plan_surface_in_markdown, test_feature_close_checks_the_union_of_every_slice_plans_surface |
| SCO-FR-016 | Markdown output for reviewer prompts; informational, exits 0 unless git fails. | `[enforced]` › test_markdown_output |

### Review

| ID | Requirement | Guarantee |
|---|---|---|
| SCO-FR-020 | The reviewer is never the context that wrote the code: each review is a fresh agent. | `[instructed]` orchestrator: review |
| SCO-FR-021 | `diff_stats.py` output, with `--plan`, informs the review recommendation and goes into every reviewer's brief; reviewers confirm or dismiss each flag with a reason. | `[instructed]` orchestrator: review, review-brief, review-pr.md |
| SCO-FR-022 | `/sdlc:review-pr` reviews the local diff and picks agents by it: code-reviewer always; pr-test-analyzer, `sdlc-extras:comment-analyzer`, silent-failure-hunter, `sdlc-extras:type-design-analyzer` when relevant; `sdlc-extras:code-simplifier` before the other reviewers. The three `sdlc-extras:` agents come from the optional companion plugin: without it they're skipped and the summary says so. `/sdlc:code-review` reviews a GitHub PR; Review is the third entry point. Changed files come from `diff_stats.py` (since the feature's `Base:`), not the unstaged diff. | `[instructed]` review-pr.md (vendored, patched) |
| SCO-FR-023 | Severity (`review-brief.md`): high is a failing or unproven acceptance criterion, wrong behaviour against the spec or a must-never-break line, data loss, a security issue, a crash window the spec rules out, an error path breaking the spec's format, a test gap rated 8 or more, unrequested public surface without a stated reason, or a broken constitution MUST rule; code-style issues are fixed in passing and never high; everything else is medium or low and ticketed. Simplifications are findings in the default and high code review; there is no separate simplifier pass. | `[instructed]` `review-brief.md`, orchestrator: review |
| SCO-FR-024 | Feedback is verified before agreeing; pushback with evidence; YAGNI check on "professional" additions. | `[instructed]` skills/orchestrator/references/receiving-code-review.md (vendored) |
| SCO-FR-025 | One whole-branch review step per feature, after the build (after the last part, when split): no review agents run during the build. The code review's depth follows the recommendation (low: correctness against each AC and must-never-break line; default: also silent failures, test gaps, simplifications and security basics; high: also a deeper pass on each failure mode). Each review runs once, on `opus` (ORC-FR-015); its high findings are fixed back in Build with a failing test first, and the review isn't rerun; a later code change goes back to Build for `verify.py` and through Review again, and Ship checks that the code still matches the `Verified:` tree before committing. | `[instructed]` orchestrator: build, review, ship; review-brief |
| SCO-FR-029 | The `code-reviewer` is read-only: it reads code, diffs and history and may run the project's test command, and writes and runs no scripts of its own (its one write is its report under `.sdlc/.work/findings/`); a suspicion that needs a probe goes in its report as a finding. | `[instructed]` code-reviewer.md, orchestrator: review |
| SCO-FR-026 | The role-guard hook denies Edit, Write, MultiEdit and NotebookEdit inside the project to the reviewers of `sdlc:` and of the `sdlc-extras:` companion (code-reviewer, comment-analyzer, feature-reviewer, pr-test-analyzer, silent-failure-hunter, type-design-analyzer, ui-reviewer) and to the code-explorer, except an agent's own report under `.sdlc/.work/findings/` (the code-reviewer and code-explorer have the Write tool for it); `code-simplifier` edits by design and isn't one; other callers get no output. | `[enforced]` test_role_guard › test_reviewer_cannot_edit, test_reviewer_writes_its_findings_file_and_nothing_else, test_define_explorers_write_only_their_report |

## Non-goals

- Blocking merges automatically on diff facts: they're evidence for reviewers, not verdicts.
- Detecting endpoints, CLI commands, config keys or env vars mechanically.

## Known gaps

- Tracing through the change file and the plan is instructions plus, on M and L, the user's approval; on S nobody reads them before the build.
- Which reviews run is a recommendation; on S a recommendation of none means no reviewer checks the surface flags.
- Reviewers can't edit files: the code-reviewer has Write only for its report under `.sdlc/.work/findings/`, and the role-guard hook denies every other file edit to every `sdlc:` and `sdlc-extras:` reviewer, `ui-reviewer` included (any file under `.sdlc/.work/findings/` is allowed, so a misnamed report there isn't caught). They keep Bash (for `git diff`, tests and browsers), so a shell edit is still only instructed against; the freshness hook's worktree diff catches one during Review (Stage 5).
- Export detection is regex-based for TS/JS, Python and Go; other languages get comment counts only.
