#!/usr/bin/env python3
"""Stop hook executor for hookify plugin.

This script is called by Claude Code when agent wants to stop.
It reads .claude/hookify.*.local.md files and evaluates stop rules.
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
    """Main entry point for Stop hook."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Load stop rules
        problems = []
        rules = load_rules(event='stop', problems=problems)

        # Evaluate rules
        engine = RuleEngine()
        result = engine.evaluate_rules(rules, input_data)
        result = attach_problems(result, problems + engine.problems)

        # Always output JSON (even if empty)
        print(json.dumps(result), file=sys.stdout)

    except Exception:
        pass  # on its own error: allow, with no output

    finally:
        # ALWAYS exit 0
        sys.exit(0)


if __name__ == '__main__':
    main()
