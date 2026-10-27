---
description: List all configured hookify rules
allowed-tools: ["Glob", "Read", "Skill"]
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc-extras plugin's folder (a companion to sdlc). Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# List Hookify Rules

**Load sdlc:writing-hook-rules skill first** to understand rule format.

Show all configured hookify rules in the project.

## Steps

1. Use Glob tool to find all hookify rule files:
   ```
   pattern: ".claude/hookify.*.local.md"
   ```

2. For each file found:
   - Use Read tool to read the file
   - Extract frontmatter fields: name, enabled, event, pattern
   - Extract message preview (first 100 chars)

3. Present results in a table:

```
## Configured Hookify Rules

| Name | Enabled | Event | Pattern | File |
|------|---------|-------|---------|------|
| warn-dangerous-rm | ✅ Yes | bash | rm\s+-rf | hookify.dangerous-rm.local.md |
| warn-console-log | ✅ Yes | file | console\.log\( | hookify.console-log.local.md |
| check-tests | ❌ No | stop | .* | hookify.require-tests.local.md |

**Total**: 3 rules (2 enabled, 1 disabled)
```

4. For each rule, show a brief preview:
```
### warn-dangerous-rm
**Event**: bash
**Pattern**: `rm\s+-rf`
**Message**: "⚠️ **Dangerous rm command detected!** This command could delete..."

**Status**: ✅ Active
**File**: .claude/hookify.dangerous-rm.local.md
```

5. Add helpful footer:
```
---

To modify a rule: Edit the .local.md file directly
To disable a rule: Set `enabled: false` in frontmatter
To enable a rule: Set `enabled: true` in frontmatter
To delete a rule: Remove the .local.md file
To create a rule: Use `/sdlc:hookify` command

**Remember**: Changes take effect immediately - no restart needed
```

## If No Rules Found

If no hookify rules exist:

```
## No Hookify Rules Configured

You haven't created any hookify rules yet.

To get started:
1. Use `/sdlc:hookify` to analyze conversation and create rules
2. Or manually create `.claude/hookify.my-rule.local.md` files
3. See `/sdlc-extras:hookify-help` for documentation

Example:
```
/sdlc:hookify Warn me when I use console.log
```

See the sdlc plugin's `examples/` folder for example rule files.
```
