"""One problem's shape for scripts agents and other tools read (#76): `{severity, code, message, target?, fix?}`.

A Problem is the message string itself, so plain-text output, the verify record and every caller that compares or
prints it see exactly the text they did before; `--json` reads the code, target and fix it carries. `code` is
snake_case and stable: tools match on it, never on the message. `fix` is one sentence or command that resolves it.
Stdlib only, Python 3.9+.
"""
import json
import sys


class Problem(str):
    code, severity, target, fix = "unclassified", "error", None, None


def problem(code, message, target=None, fix=None, severity="error"):
    p = Problem(message)
    p.code, p.severity, p.target, p.fix = code, severity, target, fix
    return p


def tag(code, messages, severity="error"):
    """Each message that isn't a Problem yet, tagged with `code`: for a helper whose messages share one cause."""
    return [m if isinstance(m, Problem) else problem(code, m, severity=severity) for m in messages]


def as_dict(p):
    p = p if isinstance(p, Problem) else problem("unclassified", p)
    d = {"severity": p.severity, "code": p.code, "message": str(p)}
    if p.target:
        d["target"] = p.target
    if p.fix:
        d["fix"] = p.fix
    return d


def emit(result, problems, **extra):
    """The one JSON document a `--json` run prints on stdout."""
    sys.stdout.reconfigure(encoding="utf-8")
    doc = {"result": result, **extra, "problems": [as_dict(p) for p in problems]}
    print(json.dumps(doc, indent=2, ensure_ascii=False))
