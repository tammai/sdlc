---
description: "Comprehensive PR review using specialized agents"
argument-hint: "[review-aspects]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Task"]
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# Comprehensive PR Review

Paths: `<change>` is the feature's change file (its record for people), `<state>` its state file (the agent's), `<work>` the folder beside it for working files (backlog, part plans, QA report) and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout (`intents` is a pre-2.0 feature's documents folder).

Run a comprehensive pull request review using multiple specialized agents, each focusing on a different aspect of code quality.

**Review Aspects (optional):** "$ARGUMENTS"

## Review Workflow:

1. **Determine Review Scope**
   - Check git status to identify changed files
   - Parse arguments to see if user requested specific review aspects
   - Default: Run all applicable reviews

2. **Available Review Aspects:**

   - **comments** - Analyze code comment accuracy and maintainability
   - **tests** - Review test coverage quality and completeness
   - **errors** - Check error handling for silent failures
   - **types** - Analyze type design and invariants (if new types added)
   - **code** - General code review for project guidelines
   - **ui** - Check UI changes against the design system and for AI-slop styling, states and accessibility
   - **simplify** - Simplify code for clarity and maintainability
   - **all** - Run all applicable reviews (default)

3. **Identify Changed Files**
   - Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md` and include its output in every agent's prompt: comment share, new files, single-use/unused exports, single-implementation abstractions, new dependencies. Agents confirm or dismiss each flag with a reason; they are facts, not verdicts.
   - The changed files are the diff stats' "Changed files" list: everything since the feature's `Base:` (or the merge-base with main), committed, uncommitted and untracked. Don't use `git diff --name-only`: it lists only unstaged changes and misses committed work. If the list is empty but the feature has work, stop and say so instead of reviewing nothing.
   - Check if PR already exists: `gh pr view`
   - Identify file types and what reviews apply

4. **Determine Applicable Reviews**

   Based on changes:
   - **Always applicable**: code-reviewer (general quality)
   - **If test files changed**: pr-test-analyzer
   - **If comments/docs added, or diff stats flag comment-heavy files**: `sdlc-extras:comment-analyzer`
   - **If error handling changed**: silent-failure-hunter
   - **If types added/modified**: `sdlc-extras:type-design-analyzer`
   - **If UI files changed** (paths in `areas.ui`, from `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" config`): ui-reviewer, with `<docs>/design-system.md`. Its High findings are Critical. Add "visual check requested" to its brief only when the user asked for screenshots.
   - **Before the other reviewers**: `sdlc-extras:code-simplifier` (polish and refine), so they review the code that will merge
   - The three `sdlc-extras:` agents come from the optional sdlc-extras companion plugin. When it isn't installed, skip them and say so in the summary; code-reviewer still covers comments and types at a coarser grain.

5. **Launch Review Agents**

   Name each agent's `model` from the tiers in `sdlc:orchestrator` → Model selection (every review agent on opus); during an active feature the model-router hook denies a launch without one.

   **Sequential approach** (one at a time):
   - Easier to understand and act on
   - Each report is complete before next
   - Good for interactive review

   **Parallel approach** (user can request):
   - Launch all agents simultaneously
   - Faster for comprehensive review
   - Results come back together

6. **Aggregate Results**

   After agents complete, summarize:
   - **Critical Issues** (must fix before merge). Unrequested public surface (an export, file, endpoint, option, config key or dependency the spec/plan didn't ask for, with no stated reason) is always Critical.
   - **Important Issues** (should fix)
   - **Suggestions** (nice to have)
   - **Positive Observations** (what's good)

7. **Provide Action Plan**

   Organize findings:
   ```markdown
   # PR Review Summary

   ## Critical Issues (X found)
   - [agent-name]: Issue description [file:line]

   ## Important Issues (X found)
   - [agent-name]: Issue description [file:line]

   ## Suggestions (X found)
   - [agent-name]: Suggestion [file:line]

   ## Strengths
   - What's well-done in this PR

   ## Recommended Action
   1. Fix critical issues first
   2. Address important issues
   3. Consider suggestions
   4. Re-run review after fixes
   ```

## Usage Examples:

**Full review (default):**
```
/sdlc:review-pr
```

**Specific aspects:**
```
/sdlc:review-pr tests errors
# Reviews only test coverage and error handling

/sdlc:review-pr comments
# Reviews only code comments

/sdlc:review-pr simplify
# Simplifies the changed code (runs before the reviewers in a full review)
```

**Parallel review:**
```
/sdlc:review-pr all parallel
# Launches all agents in parallel
```

## Agent Descriptions:

**comment-analyzer**:
- Verifies comment accuracy vs code
- Identifies comment rot
- Checks documentation completeness

**pr-test-analyzer**:
- Reviews behavioral test coverage
- Identifies critical gaps
- Evaluates test quality

**silent-failure-hunter**:
- Finds silent failures
- Reviews catch blocks
- Checks error logging

**type-design-analyzer**:
- Analyzes type encapsulation
- Reviews invariant expression
- Rates type design quality

**ui-reviewer**:
- Checks tokens and components against the design system
- Flags AI-slop styling and filler copy
- Checks states and accessibility basics
- Screenshots only on request

**code-reviewer**:
- Checks CLAUDE.md compliance
- Detects bugs and issues
- Reviews general code quality

**code-simplifier**:
- Simplifies complex code
- Improves clarity and readability
- Applies project standards
- Preserves functionality

## Tips:

- **Run early**: Before creating PR, not after
- **Focus on changes**: Agents analyze the changes since the base (the diff stats name it)
- **Address critical first**: Fix high-priority issues before lower priority
- **Re-run after fixes**: Verify issues are resolved
- **Use specific reviews**: Target specific aspects when you know the concern

## Workflow Integration:

**Before committing:**
```
1. Write code
2. Run: /sdlc:review-pr code errors
3. Fix any critical issues
4. Commit
```

**Before creating PR:**
```
1. Stage all changes
2. Run: /sdlc:review-pr all
3. Address all critical and important issues
4. Run specific reviews again to verify
5. Create PR
```

**After PR feedback:**
```
1. Make requested changes
2. Run targeted reviews based on feedback
3. Verify issues are resolved
4. Push updates
```

## Notes:

- Agents run autonomously and return detailed reports
- Each agent focuses on its specialty for deep analysis
- Results are actionable with specific file:line references
- Agents use appropriate models for their complexity
- All agents available in `/agents` list
