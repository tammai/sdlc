#!/usr/bin/env python3
"""Writes a review report in the shape the trust anchor and the round cap read, for the two reviews that don't write one.

Usage: review_report.py [--root DIR] FEATURE --agent code-reviewer|dependency-audit --round N --findings FILE
                        [--command TEXT] [--summary TEXT]
  The built-in `code-review` skill reports bare findings in the session (no severity, no file), and the dependency audit
  is a command whose output is no report either. The caller rates each finding (review-brief.md's Severity list) and
  writes them to FILE with the Write tool (Review refuses a heredoc):
      {"findings": [{"id": "C1", "severity": "high|medium|low", "bug": false, "text": "what and where"}]}
  This writes `.sdlc/.work/findings/<feature>/<agent>-r<N>.md` (never over an earlier one) and ends it with the verdict
  the ratings give: `VERDICT: FAIL — <ids>` for every high and, in round 1 only, every `bug`, else `VERDICT: PASS`
  (from round 2 a non-high bug is listed to fix before Ship, test first, with no new round). The caller doesn't
  type the verdict, so it can't disagree with the ratings above it. An empty list is a pass.
Exit 0 written (prints the path), 1 refused, 2 usage. Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import sys

AGENTS = {"code-reviewer": "Code review", "dependency-audit": "Dependency audit"}
SEVERITIES = ("high", "medium", "low")


class Refused(Exception):
    pass


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise Refused(f"can't read {path}: {e}")
    items = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise Refused('the file must be {"findings": [...]}')
    seen = set()
    for i, f in enumerate(items, 1):
        if not isinstance(f, dict) or not isinstance(f.get("id"), str) or not f["id"].strip():
            raise Refused(f"finding {i} has no id")
        if f["id"] in seen:
            raise Refused(f"two findings are named {f['id']}")
        seen.add(f["id"])
        if f.get("severity") not in SEVERITIES:
            raise Refused(f"{f['id']}: severity must be one of {', '.join(SEVERITIES)}")
        if not isinstance(f.get("text"), str) or not f["text"].strip():
            raise Refused(f"{f['id']} has no text")
        if not isinstance(f.get("bug", False), bool):
            raise Refused(f"{f['id']}: bug is true or false")
    return items


def one_line(text):
    return " ".join(text.split())  # a newline in a finding must not start a line that looks like the verdict


def render(agent, n, findings, command=None, summary=None):
    # Round 1 fails on every high and every bug. From round 2 only a high fails: a bug is fixed test first and closed
    # by verify.py, without another review round (cuti-os and bug-hunter needed 5-9 rounds chasing fix-of-a-fix bugs).
    failing = [f["id"] for f in findings if f["severity"] == "high" or (n == 1 and f.get("bug"))]
    to_fix = [f["id"] for f in findings if n > 1 and f.get("bug") and f["severity"] != "high"]
    lines = [f"# {AGENTS[agent]}, round {n}", ""]
    if command:
        lines += [f"Command: `{one_line(command).replace('`', chr(39))}`", ""]
    if summary:
        lines += [one_line(summary), ""]
    lines += ["## Findings", ""]
    if findings:
        lines += [f"- **{f['id']}** ({f['severity']}{', bug' if f.get('bug') else ''}): {one_line(f['text'])}"
                  for f in findings]
    else:
        lines.append("- none")
    if to_fix:
        lines += ["", f"Fix before Ship, test first, no new round: {', '.join(to_fix)}"]
    verdict = f"VERDICT: FAIL — {', '.join(failing)}" if failing else "VERDICT: PASS"
    return "\n".join(lines + ["", verdict]) + "\n"


def write(root, feature, agent, n, findings_file, command=None, summary=None):
    if not re.fullmatch(r"[\w.-]+", feature) or feature.startswith("."):
        raise Refused(f"{feature!r} isn't a feature name")
    if n < 1:
        raise Refused("rounds start at 1")
    text = render(agent, n, load(findings_file), command, summary)
    folder = os.path.join(root, ".sdlc", ".work", "findings", feature)
    path = os.path.join(folder, f"{agent}-r{n}.md")
    if os.path.exists(path):
        raise Refused(f"{os.path.relpath(path, root)} exists: a round's report is never overwritten (next round: r{n + 1})")
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("feature")
    ap.add_argument("--agent", choices=sorted(AGENTS), required=True)
    ap.add_argument("--round", type=int, required=True, dest="n")
    ap.add_argument("--findings", required=True)
    ap.add_argument("--command", help="the audit's command, recorded in the report")
    ap.add_argument("--summary", help="one line for the top of the report")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        path = write(os.path.abspath(a.root), a.feature, a.agent, a.n, a.findings, a.command, a.summary)
    except Refused as e:
        print(f"review_report: {e}")
        return 1
    print(os.path.relpath(path, os.path.abspath(a.root)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
