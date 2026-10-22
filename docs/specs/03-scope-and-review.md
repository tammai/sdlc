# Spec 03: Scope tracing and review

Every addition is traced to a request from spec to diff, and review gets measured facts so unrequested scope is caught mechanically where possible.

**Entry points:** Stages 1–3 and 6; `/sdlc:review-pr`, `/sdlc:code-review` · **Source:** `skills/writing-specs`, `clarifying-specs`, `designing-solutions`, `writing-plans`, `analyzing-consistency`, `agents/code-architect.md`, `commands/review-pr.md`, `scripts/diff_stats.py`, `templates/spec-template.md`, `templates/design-template.md` · **Decision:** [ADR 0003](../adr/0003-guard-against-over-engineering.md)

## User scenarios

1. **Inferred requirement.** Given a spec where Claude added "audit logging" the user never asked for, when Stage 1 reaches its gate, then it's listed on its own with a reason and dropped unless the user keeps it; dropped items go to Non-Goals.
2. **Design addition.** Given a design that adds a `RateLimiter` interface, when Complexity Tracking has no requirement for it, then it comes out of the design.
3. **Undeclared export.** Given a plan whose Public Surface lists `createSession`, when the diff also exports `sneaky`, then `diff_stats.py --plan` flags it as undeclared, which reviewers treat as high severity.

## Requirements

### Spec, design, plan

| ID | Requirement | Guarantee |
|---|---|---|
| SCO-FR-001 | Every FR and SC is tagged `[user]`, `[clarified]` or `[inferred]`; a required Non-Goals section; future-proofing words need a measurable requirement; assumptions add no work. | `[instructed]` writing-specs, spec-template |
| SCO-FR-002 | At the Stage 1 gate, `[inferred]` items are listed separately, dropped unless kept; kept → `[clarified]`, dropped → Non-Goals. The spec leaves Stage 1 with no `[inferred]` tags. | `[instructed]` writing-specs, orchestrator §1 |
| SCO-FR-003 | Clarification answers tag what they add or settle `[clarified]`, and move rejected inferred items to Non-Goals. | `[instructed]` clarifying-specs |
| SCO-FR-004 | Performance, scale and constraints in the design cite an SC id or say `n/a`. | `[instructed]` designing-solutions |
| SCO-FR-005 | Architect options: minimal change; minimal plus one named extension (only if a requirement strains the minimal one); pragmatic. Minimal is recommended unless it fails a named requirement. Every brief includes the Non-Goals. | `[instructed]` designing-solutions, code-architect.md |
| SCO-FR-006 | Complexity Tracking is always filled: every new module, layer, abstraction, dependency, service, config key or store cites a requirement and why a simpler alternative was rejected, or it comes out; a "Deliberately not built" section. | `[instructed]` designing-solutions, design-template |
| SCO-FR-007 | Every plan task has a `Requirements:` line; the plan's self-review checks both directions; a **Public Surface** section declares every new export, endpoint, command, config key, env var and dependency, or "none". | `[instructed]` writing-plans |
| SCO-FR-008 | Consistency analysis: leftover `[inferred]` or a planned Non-Goal is CRITICAL; other scope creep (task without requirement, Complexity row or surface line without requirement, design numbers without an SC) is HIGH, and so is an acceptance scenario with no named test in the plan. Runs on L, and on M with more than ~8 tasks. | `[instructed]` analyzing-consistency, orchestrator §3 |

### Review facts (`diff_stats.py`)

| ID | Requirement | Guarantee |
|---|---|---|
| SCO-FR-010 | Diff base: merge-base with origin/main, origin/master, main or master, else HEAD; includes committed, uncommitted and untracked changes. Not a git repo → error. | `[enforced]` test_diff_stats › test_base_is_merge_base_with_main, test_no_changes, test_not_a_git_repo |
| SCO-FR-011 | Counts added code and comment lines per source file, block-comment and docstring aware; modified files count only added lines. | `[enforced]` › test_comment_counting_c_like, test_comment_counting_python_docstrings, test_modified_file_counts_only_added_lines |
| SCO-FR-012 | Flags comment-heavy files and diffs (over 25% comments with at least 20 added lines). Test files are excluded from the ratio and from export checks. | `[enforced]` › test_comment_heavy_flags, test_test_files_are_excluded_from_ratio_and_exports |
| SCO-FR-013 | New exports (TS/JS, Python, Go) are classified by caller files: unused, only used by tests, used only inside their own file, or single-use. | `[enforced]` › test_export_usage, test_python_and_go_exports |
| SCO-FR-014 | Flags interfaces and abstract classes with at most one implementation, and new dependencies (package.json sections, requirements files, go.mod). | `[enforced]` › test_single_implementation_abstraction, test_new_dependencies |
| SCO-FR-015 | With `--plan`, new exports and dependencies missing from Public Surface are flagged as undeclared, declared items not in the diff as not built; endpoints, commands, config and env are listed to check by hand; a plan without the section is flagged. | `[enforced]` › test_plan_surface_flags_undeclared_and_unbuilt, test_plan_surface_none_declared, test_plan_without_surface_section_is_flagged, test_plan_surface_in_markdown |
| SCO-FR-016 | Markdown output for reviewer prompts; informational, exits 0 unless git fails. | `[enforced]` › test_markdown_output |

### Review

| ID | Requirement | Guarantee |
|---|---|---|
| SCO-FR-020 | The reviewer is never the context that wrote the code. | `[instructed]` orchestrator §6 |
| SCO-FR-021 | `diff_stats.py` output goes into every reviewer's prompt (with `--plan` except on S); reviewers confirm or dismiss each flag with a reason. | `[instructed]` orchestrator §6, review-pr.md |
| SCO-FR-022 | `/sdlc:review-pr` picks agents by diff: code-reviewer always; pr-test-analyzer, comment-analyzer, silent-failure-hunter, type-design-analyzer when relevant; code-simplifier after review. | `[instructed]` review-pr.md (vendored, patched) |
| SCO-FR-023 | Severity: unrequested public surface without a stated reason is high (blocks the gate); comment noise is medium and fixed in Stage 6. S track runs code-reviewer then code-simplifier. | `[instructed]` orchestrator §6, review-pr.md |
| SCO-FR-024 | Feedback is verified before agreeing; pushback with evidence; YAGNI check on "professional" additions. | `[instructed]` receiving-code-review (vendored) |
| SCO-FR-025 | One whole-branch review per feature, in Stage 6: under the orchestrator, `executing-plans` and `subagent-driven-development` skip their own final whole-branch review (per-task reviews still run) and report their Rulings, which go into `state.md`. Stage 6 reviewers get the plan's Review Focus and those Rulings; on M and L its whole-branch `code-reviewer` runs on the top tier; a code change made to fix a finding goes back to Stage 5 for another round. | `[instructed]` orchestrator §4, §6; executing-plans, final-review.md (vendored, patched) |

## Non-goals

- Blocking merges automatically on diff facts: they're evidence for reviewers, not verdicts.
- Detecting endpoints, CLI commands, config keys or env vars mechanically.

## Known gaps

- Spec, design and plan tracing are instructions plus user approval. The S track has no plan, so the surface check doesn't apply there.
- Export detection is regex-based for TS/JS, Python and Go; other languages get comment counts only.
