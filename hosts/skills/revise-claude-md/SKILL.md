---
name: revise-claude-md
description: File learnings from this session into the right knowledge tier (CLAUDE.md, path-scoped rules, or knowledge/)
---

Review this session for learnings about working with Claude Code in this codebase. Update CLAUDE.md with context that would help future Claude sessions be more effective.

## Step 1: Reflect

What context was missing that would have helped Claude work more effectively?
- Bash commands that were used or discovered
- Code style patterns followed
- Testing approaches that worked
- Environment/configuration quirks
- Warnings or gotchas encountered

## Step 2: Find CLAUDE.md Files

```bash
find . -name "CLAUDE.md" -o -name ".claude.local.md" 2>/dev/null | head -20
```

Decide where each addition belongs, using the 3-tier model in the `sdlc:managing-knowledge` skill:
- `CLAUDE.md` - tier 1, only if it applies to almost every task (keep the file ≤ 60 lines; move something down a tier first if needed)
- `.claude/rules/<area>.md` - tier 2, if it only matters when touching certain paths
- `knowledge/**.md` - tier 3, for explanations, decisions, gotchas, runbooks (linked from `knowledge/index.md`)
- `.claude.local.md` - Personal/local only (gitignored)
- Corrected twice and mechanically checkable → propose a `/sdlc:hookify` rule instead of text

## Step 3: Draft Additions

**Keep it concise** - one line per concept. CLAUDE.md is part of the prompt, so brevity matters.

Format: `<command or pattern>` - `<brief description>`

Avoid:
- Verbose explanations
- Obvious information
- One-off fixes unlikely to recur

## Step 4: Show Proposed Changes

For each addition:

```
### Update: ./CLAUDE.md   (or .claude/rules/<area>.md, or knowledge/<folder>/<slug>.md)

**Why:** [one-line reason]

\`\`\`diff
+ [the addition - keep it brief]
\`\`\`
```

## Step 5: Apply with Approval

Ask if the user wants to apply the changes. Only edit files they approve. For tier-3 docs, follow the "File a lesson" steps in `sdlc:managing-knowledge` (OKF frontmatter, index line, log entry).
