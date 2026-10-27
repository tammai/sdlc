#!/usr/bin/env python3
"""PreToolUse hook executor for hookify plugin.

This script is called by Claude Code before any tool executes.
It reads .claude/hookify.*.local.md files and evaluates rules.
"""

import os
import sys
import json

# Add plugin root to Python path for imports
PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT')
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

try:
    from core.config_loader import attach_problems, load_rules
    from core.rule_engine import RuleEngine
except ImportError:
    sys.exit(0)  # never blocks or speaks on its own error (.claude/rules/hooks.md)


def main():
    """Main entry point for PreToolUse hook."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Determine event type for filtering
        # For PreToolUse, we use tool_name to determine "bash" vs "file" event
        tool_name = input_data.get('tool_name', '')

        # Any other tool gets only `event: all` rules: load_rules(None) would add stop and prompt rules too
        event = 'all'
        if tool_name in ('Bash', 'PowerShell'):
            event = 'bash'
        elif tool_name in ['Edit', 'Write', 'MultiEdit', 'NotebookEdit']:
            event = 'file'

        # Load rules
        problems = []
        rules = load_rules(event=event, problems=problems)

        # Evaluate rules
        engine = RuleEngine()
        result = engine.evaluate_rules(rules, input_data)
        result = attach_problems(result, problems + engine.problems)

        # Always output JSON (even if empty)
        print(json.dumps(result), file=sys.stdout)

    except Exception:
        pass  # on its own error: allow, with no output

    finally:
        # ALWAYS exit 0 - never block operations due to hook errors
        sys.exit(0)


if __name__ == '__main__':
    main()
