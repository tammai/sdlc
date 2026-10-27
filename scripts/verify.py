#!/usr/bin/env python3
"""One command that proves a feature: the project's verify plan, then every acceptance criterion against the test
plan.md names for it (ADR 0013).

Usage: verify.py [--root DIR] [--feature NAME] [--timeout S]
  Runs the verify plan (lint, typecheck, build, test from .sdlc/config.json, per package), then, for every `AC-nnn`
  in spec.md: a row in plan.md's `## Acceptance tests` table, a `manual` row's reason, the test file, a recorded red
  run, and the row's Run command passing. Writes the result to .sdlc/.work/verify.json and exits 0 on pass, 1 on a
  failure, 2 when there's no feature to verify. A plan without the table is an old plan: the AC checks are skipped
  and Prove uses the verifier.
Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
sys.path.insert(0, HERE)
import scaffold  # noqa: E402  (the verify plan and the shell that runs project commands)
import sdlc_layout  # noqa: E402
import verify_freshness as vf  # noqa: E402  (worktree trees)

RECORD = os.path.join(".sdlc", ".work", "verify.json")
AC_ID = re.compile(r"\bAC-\d{3}\b")
TABLE_ROW = re.compile(r"^\s*\|\s*(AC-\d{3})\s*\|(.*?)\|(.*?)\|\s*$")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def section(text, heading):
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def acceptance_map(plan_text):
    """Rows of plan.md's `## Acceptance tests` table, or None when the plan has no such section."""
    body = section(plan_text, "Acceptance tests")
    if body is None:
        return None
    rows = []
    for line in body.splitlines():
        m = TABLE_ROW.match(line)
        if not m:
            continue
        test, run = m.group(2).strip(), m.group(3).strip()
        manual = test.lower() == "manual"
        rows.append({"ac": m.group(1), "test": test, "file": None if manual else test.split("›")[0].strip(),
                     "run": run if manual else run.strip("`").strip(), "manual": manual})
    return rows


def spec_acs(spec_text):
    return list(dict.fromkeys(AC_ID.findall(spec_text)))


def run(cmd, cwd, timeout):
    sh = scaffold.shell()
    try:
        p = subprocess.run(sh + [cmd] if sh else cmd, shell=not sh, cwd=cwd, capture_output=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return p.returncode, (p.stdout + p.stderr)[-2000:]


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def load_record(root):
    try:
        return json.loads(read(os.path.join(root, RECORD)) or "{}")
    except ValueError:
        return {}


def save_record(root, rec):
    path = os.path.join(root, RECORD)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)


def docs(root, feature):
    folder = os.path.join(root, sdlc_layout.paths(root, feature)["intents"])
    return read(os.path.join(folder, "spec.md")) or "", read(os.path.join(folder, "plan.md")) or ""


def full(root, feature, timeout=1800):
    started = time.time()
    rec = load_record(root)
    if rec.get("feature") != feature:
        rec = {"feature": feature}
    failures, notes = [], []
    config = json.loads(read(os.path.join(root, ".sdlc", "config.json")) or "{}")
    for step in scaffold.verify_plan(config)["verify"]:
        code, out = run(step["run"], os.path.join(root, step["cwd"]), timeout)
        if code:
            failures.append(f"{step['scope'] or scaffold.ROOT_SCOPE} {step['step']}: exit {code}\n{out[-500:]}")
    spec_text, plan_text = docs(root, feature)
    rows = acceptance_map(plan_text)
    manual = []
    if rows is None:
        notes.append("no acceptance tests section: old plan, Prove uses the verifier")
    else:
        by_ac = {r["ac"]: r for r in rows}
        for ac in spec_acs(spec_text):
            row = by_ac.get(ac)
            if not row:
                failures.append(f"{ac}: no row in ## Acceptance tests")
            elif row["manual"]:
                if row["run"]:
                    manual.append(ac)
                else:
                    failures.append(f"{ac}: a manual row needs its reason in the Run column")
            elif not os.path.exists(os.path.join(root, row["file"])):
                failures.append(f"{ac}: {row['file']} not found")
            elif ac not in rec.get("red", {}):
                failures.append(f"{ac}: no red run recorded (run `verify.py red {ac}` before writing its code)")
            else:
                code, out = run(row["run"], root, timeout)
                if code:
                    failures.append(f"{ac}: its test fails (exit {code})\n{out[-500:]}")
    rec["last"] = {"at": now(), "tree": vf.worktree_tree(root), "head": vf.git_head(root),
                   "result": "fail" if failures else "pass", "seconds": round(time.time() - started, 1),
                   "failures": failures, "manual": manual}
    save_record(root, rec)
    return rec["last"], notes


def active_feature(root):
    for name, f in sdlc_layout.features(root).items():
        text = read(os.path.join(root, f["state"])) or ""
        if re.search(r"^Status:\s*active\b", text, re.M | re.I):
            return name
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--feature")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    feature = a.feature or active_feature(root)
    if not feature:
        print("verify: no active feature (pass --feature)")
        return 2
    last, notes = full(root, feature, a.timeout)
    for line in notes + last["failures"]:
        print(line)
    if last["manual"]:
        print("checked by reading, not by a test: " + ", ".join(last["manual"]))
    print(f"verify {feature}: {last['result'].upper()} ({last['seconds']}s)")
    return 0 if last["result"] == "pass" else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
