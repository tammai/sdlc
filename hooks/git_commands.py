"""Which shell commands are a git commit or push (or Graphite's equivalents): the patterns the commit and push
security reviews use to decide that a Bash call gets a review, and pretooluse uses to keep those commands off the
Monitor tool. A leaf module, no environment or other imports, so importing it can't fail and costs nothing."""
import re

_GIT_OPT_VALUE = r'''(?:[^\s"']|"[^"]*"|'[^']*')+'''
_GIT_VALUE_OPTS = r'git-dir|work-tree|namespace|config-env|attr-source'
_GIT_GLOBAL_OPTS = (
    r'(?:\s+-[Cc]\s+' + _GIT_OPT_VALUE
    + r'|\s+--[^\s=]+=' + _GIT_OPT_VALUE
    + r'|\s+--(?:' + _GIT_VALUE_OPTS + r')\s+' + _GIT_OPT_VALUE
    # `--help` / `--version` run no subcommand.
    + r'|\s+(?:--(?!(?:' + _GIT_VALUE_OPTS + r'|help|version)\s)[^\s=]+|-[pP])(?=\s))*'
)
GIT_COMMIT_RE = re.compile(
    # Without the global-option tolerance, `git -C /repo commit` is silently
    # dropped by the handler — see #2089's secondary finding. The gt branch
    # has no global-option layer to worry about.
    # `(?!-)`: not the plumbing commands `git commit-graph` / `git commit-tree`.
    r'\bgit' + _GIT_GLOBAL_OPTS + r'\s+commit\b(?!-)'
    r'|\bgt\s+(?:create|modify)\b'
)
# Match either the `--amend` flag (with the leading whitespace boundary
# preserved from the original) OR `gt modify` which is semantically an
# amend. The handler treats matches as "find the pre-amend SHA via reflog
# and diff against THAT, not against the post-amend HEAD's parent" — same
# code path for both git --amend and gt modify.
GIT_PUSH_RE = re.compile(
    r'(?:\bgit' + _GIT_GLOBAL_OPTS + r'\s+push\b|\bgt\s+submit\b)'
)
