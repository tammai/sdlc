#!/usr/bin/env python3
"""One command that proves a feature: the project's verify plan, then every acceptance criterion against the test
change.md names for it (plan.md on a 1.x feature) (ADR 0013, 0020).

Usage: verify.py [--root DIR] [--feature NAME] [--timeout S] [red AC-nnn [AC-nnn ...] | status | trace]
  Runs the verify plan (lint, typecheck, build, test from .sdlc/config.json, per package), then, for every `AC-nnn`
  in change.md: a row in its `## Acceptance tests` table (plan.md's on a 1.x feature), a `manual` row's reason, the
  test file, a recorded red run, and the row's Run command passing. Writes the result to .sdlc/.work/verify.json and
  exits 0 on pass, 1 on a failure, 2 when there's no feature to verify. On an old S fix with no record, the state
  file's `Repro: <test file> › <name> | <command>` line is AC-001. A plan without the table, and no Repro line, is an
  old plan: the AC checks are skipped and the plan is from sdlc 1.x. While a backlog part is `in progress`, an AC
  that only parts not started yet own (backlog.md's ACs column) waits, and so does a task whose ACs are all theirs:
  the run records them as `skipped` and can't be reused for Review; with no part in progress everything is checked. Then drift from the plan (the state file's
  `## Tasks` and `## Public Surface`; plan.md on 1.x): a changed file no task or acceptance test names, a task whose
  files didn't change, an export or dependency the Public Surface doesn't list; each needs a `## Deviations` line
  (`state.py deviation`) naming it, with What:, Why: and Effect:.
`red AC-nnn [AC-nnn ...]`, run before those ACs' code is written: runs each AC's test and records it failing (exit 0).
  A test that passes, can't be found or can't run is refused (exit 1, and none of the named ACs is recorded): it
  would prove nothing.
`trace`: when an AC cites a spec (`AC-003 … prd.md §4.2` or `§FR-002`), checks that each cited ref is in that spec and
  that each `FR-nnn` the spec has is named by an AC or set aside in `## Out of scope`; exit 1 on a finding, 0 when it
  traces or no AC cites a spec. L's plan self-approval runs it; a full run prints the same findings as `trace:` notes
  (advisory, recorded in verify.json) and never fails on them.
A passing run prints the tree and HEAD that `state.py verified` takes.
Each run also writes the freshness hook's copy of itself (.sdlc/.work/verify-freshness.json).
`status`: JSON for Review. `reuse` is true only when the last run passed, the freshness hook's copy of it agrees
  (same tree, every red AC), and the code hasn't changed since; otherwise `reason` says why and Review reruns verify.
Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
sys.path.insert(0, HERE)
import backlog  # noqa: E402  (a backlog's parts: which ACs belong to parts not started yet)
import diff_stats  # noqa: E402  (changed files and the Public Surface check, since the feature's Base)
import scaffold  # noqa: E402  (the verify plan and the shell that runs project commands)
import sdlc_layout  # noqa: E402
import verify_freshness as vf  # noqa: E402  (worktree trees)

RECORD = os.path.join(".sdlc", ".work", "verify.json")
AC_ID = re.compile(r"\bAC-\d{3}\b")
TABLE_ROW = re.compile(r"^\s*\|\s*(AC-\d{3})\s*\|(.*?)\|(.*?)\|\s*$")
AC_ENTRY = re.compile(r"^\s*[-*]\s+\**AC-\d{3}")
FR_ID = re.compile(r"\bFR-\d{3}\b")
# In an AC's text: a `<file>.md`, then the `§<ref>`s that follow it
SPEC_TOKEN = re.compile(r"(?P<file>[\w./-]+\.md)|§\s*(?P<ref>[\w.-]+)")
TASK_START = re.compile(r"^\s*(\d+)\.\s")
BACKTICKED = re.compile(r"`([^`]+)`")
# What running the tests or tools leaves behind when a repo doesn't ignore it: never drift
GENERATED = re.compile(r"(^|/)(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|node_modules|\.tox)/|\.py[co]$")


def section(text, heading):
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def acceptance_map(plan_text):
    """Rows of a `## Acceptance tests` table, or None when the text has no such section."""
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
        rows.append({"ac": m.group(1), "test": test, "file": None if manual else test.split("›")[0].strip().strip("`").strip(),
                     "run": run if manual else run.strip("`").strip(), "manual": manual})
    return rows


def spec_acs(spec_text):
    return list(dict.fromkeys(AC_ID.findall(spec_text)))


def ac_entries(change_text):
    """{AC: its text} for each `- **AC-nnn** …` entry of `## Acceptance criteria`; a blank line ends an entry."""
    out, current = {}, None
    for line in (section(change_text, "Acceptance criteria") or "").splitlines():
        if AC_ENTRY.match(line):
            current = AC_ID.search(line).group(0)
            out[current] = line
        elif current and line.strip():
            out[current] += "\n" + line
        else:
            current = None
    return out


def spec_text(root, name):
    """The spec an AC cites, as repo-relative path or under the docs folder; None when missing or outside the repo
    (the path comes from the change file, so it never reads beyond the repo)."""
    base = os.path.realpath(root)
    for rel in (name, os.path.join(sdlc_layout.paths(root)["docs_dir"], name)):
        path = os.path.realpath(os.path.join(root, rel))
        if path.startswith(base + os.sep) and os.path.isfile(path):
            return read(path)
    return None


def has_ref(text, ref):
    """An `FR-nnn` id anywhere in the spec, or a heading numbered `ref` (§4.2 is not found under only a 4.2.1)."""
    if FR_ID.fullmatch(ref):
        return re.search(rf"\b{ref}\b", text) is not None
    return re.search(rf"^#{{1,6}}\s*(?:§\s*)?{re.escape(ref)}(?![\w-]|\.\d)", text, re.M) is not None


def trace(root, feature):
    """None when no AC cites a spec (`<file>.md §<ref>`); else the findings, empty when it traces: a cited ref the
    spec lacks, and an `FR-nnn` of a cited spec that no AC names and `## Out of scope` doesn't set aside."""
    change = docs(root, feature)[0]
    cited, covered, findings = {}, set(), []
    for ac, text in ac_entries(change).items():
        covered |= set(FR_ID.findall(text))
        file = None
        for m in SPEC_TOKEN.finditer(text):
            if m.group("file"):
                file = m.group("file")
            elif file:
                ref = m.group("ref").rstrip(".-")
                if file not in cited:
                    cited[file] = spec_text(root, file)
                if cited[file] is None or not has_ref(cited[file], ref):
                    findings.append(f"{ac}: {file} §{ref} is not in the spec")
    if not cited:
        return None
    covered |= set(FR_ID.findall(section(change, "Out of scope") or ""))
    for file, text in cited.items():
        findings += [f"{fr} ({file}) has no AC and isn't in ## Out of scope"
                     for fr in dict.fromkeys(FR_ID.findall(text or "")) if fr not in covered]
    return findings


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


def save_record(root, rec, *runs):
    """Writes verify.json, then the freshness hook's copy of the same run, so a run counts whatever spelling ran it
    (a subagent's `verify.py; git status` is one the hook doesn't match). A later hand edit to either still shows as
    "records disagree"."""
    path = os.path.join(root, RECORD)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
    vf.record_verify(root, rec["feature"], list(runs))


def docs(root, feature):
    """(the human record's text, the plan's text, the plan's path): the change file and the state file, which holds
    the plan from Define on; spec.md and plan.md for a feature whose state file has no `## Tasks` (1.x)."""
    paths = sdlc_layout.paths(root, feature)
    folder = os.path.join(root, paths["intents"])
    human = read(os.path.join(root, paths["change"])) or read(os.path.join(folder, "spec.md")) or ""
    state_path = os.path.join(root, paths["state"])
    state = read(state_path) or ""
    if section(state, "Tasks") is not None:
        return human, state, state_path
    plan_path = os.path.join(folder, "plan.md")
    return human, read(plan_path) or "", plan_path


REPRO = re.compile(r"^Repro:\s*(.+?)\s*\|\s*(.+?)\s*$", re.M)


def acceptance(root, feature):
    """(AC ids, rows): from change.md and its `## Acceptance tests` table (plan.md's table on a 1.x feature), or, on
    an old S fix with no record, from the state file's `Repro: <test file> › <name> | <command>` line as AC-001.
    Rows are None for an old plan with none of them."""
    spec_text, plan_text, _ = docs(root, feature)
    rows = acceptance_map(spec_text)
    if rows is None:
        rows = acceptance_map(plan_text)
    if rows is not None:
        return spec_acs(spec_text), rows
    m = REPRO.search(read(os.path.join(root, sdlc_layout.paths(root, feature)["state"])) or "")
    if not m:
        return [], None
    row = acceptance_map(f"## Acceptance tests\n| AC-001 | {m.group(1)} | {m.group(2)} |\n")
    return ["AC-001"], row


def later_parts(root, feature):
    """{AC: part} for each AC that only parts not started yet (todo or blocked) own, while a part is in progress:
    that part can't have their tests yet. {} without a backlog or with no part in progress, so feature close, Ship
    and the time between parts check everything."""
    text = read(os.path.join(root, sdlc_layout.paths(root, feature)["work"], "backlog.md"))
    rows = backlog.slices(text) if text else []
    if not any(r["status"].startswith("in progress") for r in rows):
        return {}
    started = [r for r in rows if r["status"].startswith(("in progress", "done"))]
    owned = {ac for r in started for ac in backlog.ac_ids(r["acs"])}
    later = {}
    for r in rows:
        if r not in started:
            for ac in backlog.ac_ids(r["acs"]):
                if ac not in owned:
                    later.setdefault(ac, r["id"])
    return later


def covered(item, deviations):
    return any(item in line and all(re.search(rf"{part}:\s*[^·\s]", line) for part in ("What", "Why", "Effect"))
               for line in deviations.splitlines())


def drift(root, feature, later=()):
    """[{item, kind, covered}] for what the change did that the plan didn't say, or None without a Base or a plan.
    A task whose ACs are all in `later` (parts not started yet) isn't expected to have changed its files."""
    spec_text, plan_text, plan_path = docs(root, feature)
    if not plan_text.strip():
        return None
    state = read(os.path.join(root, sdlc_layout.paths(root, feature)["state"])) or ""
    m = re.search(r"^Base:\s*`?([0-9a-f]{7,40})\b", state, re.M)
    if not m:
        return None
    facts = diff_stats.collect(root, m.group(1), [plan_path] if os.path.exists(plan_path) else [])
    docs_dir = sdlc_layout.docs_dir(root)
    changed = [f for f in facts["changed_files"] if not f.startswith(".sdlc/") and not f.lower().endswith(".md")
               and not (docs_dir and f.startswith(docs_dir + "/")) and not GENERATED.search(f)]
    tasks, task_acs, current = {}, {}, None
    for line in (section(plan_text, "Tasks") or "").splitlines():
        t = TASK_START.match(line)
        if t:
            current = t.group(1)
        if current:
            tasks.setdefault(current, set()).update(BACKTICKED.findall(line))
            task_acs.setdefault(current, set()).update(AC_ID.findall(line))
    named = set().union(*tasks.values()) if tasks else set()
    rows = acceptance_map(spec_text)  # sdlc 2.0: the table is change.md's; 1.x: plan.md's
    named |= {r["file"] for r in (rows if rows is not None else acceptance_map(plan_text)) or [] if r["file"]}
    items = [(f, "file") for f in changed if f not in named]
    # A task's files count against everything changed: a README-only task did its work
    items += [(f"task {n}", "task") for n, files in tasks.items()
              if any("/" in f or "." in f for f in files) and not files & set(facts["changed_files"])
              and not (task_acs.get(n) and task_acs[n] <= set(later))]
    surface = facts.get("surface") or {}
    items += [(n, "surface") for n in surface.get("undeclared_exports", []) + surface.get("undeclared_dependencies", [])]
    deviations = section(plan_text, "Deviations") or ""
    return [{"item": i, "kind": k, "covered": covered(i, deviations)} for i, k in items]


def full(root, feature, timeout=1800, whole=False):
    """The verify plan, every AC and drift. While a backlog part is in progress, the ACs and tasks of parts not
    started yet wait (recorded as `skipped`), unless `whole` (Ship)."""
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
    acs, rows = acceptance(root, feature)
    later = {} if whole else later_parts(root, feature)
    skipped = [ac for ac in acs if ac in later]
    acs = [ac for ac in acs if ac not in later]
    if skipped:
        notes.append("not checked yet, later parts: " + ", ".join(f"{ac} ({later[ac]})" for ac in skipped))
    manual = []
    if rows is None:
        notes.append("no acceptance tests section: every 2.0 plan has one")
    else:
        by_ac = {r["ac"]: r for r in rows}
        ran = {}
        for ac in acs:
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
                code, out = run_once(ran, row["run"], root, timeout)
                if code:
                    failures.append(f"{ac}: its test fails (exit {code})\n{out[-500:]}")
    drifted = drift(root, feature, later)
    if drifted is None:
        notes.append("no plan (the state file's ## Tasks) or no Base:, so drift wasn't checked")
    for d in drifted or []:
        if not d["covered"]:
            failures.append(f"drift: {d['item']} has no Deviations entry with What:, Why: and Effect:")
    traced = trace(root, feature) or []  # advisory: a note, never a failure, until its false-positive rate is known
    notes += [f"trace: {t}" for t in traced]
    rec["last"] = {"at": vf.now(), "tree": vf.worktree_tree(root), "head": vf.git_head(root),
                   "result": "fail" if failures else "pass", "seconds": round(time.time() - started, 1),
                   "failures": failures, "manual": manual, "drift": drifted or [], "skipped": skipped,
                   "trace": traced}
    save_record(root, rec, ("full", None))
    return rec["last"], notes


# Exits that mean the test never ran: shell can't execute / not found (126, 127; cmd.exe 9009), pytest no tests
# collected (5) or usage error such as an unknown node id (4), our timeout (124)
NOT_RUNNABLE = {126, 127, 9009, 5, 4, 124}
# Runner output that means the named test wasn't found. Only the runner's own lookup: an ImportError or
# AttributeError about the code under test is the normal red of a test written first
NOT_FOUND = re.compile(r"no tests ran|collected 0 items|No tests found|no tests to run|ERROR: not found:|"
                       r"has no attribute '?test\w*", re.I)


def red(root, feature, acs, timeout=1800):
    """({AC: exit code}, []) when every AC's test fails as it should before its code exists, else (None, reasons)
    and nothing is recorded: a batch is recorded whole or not at all."""
    rows, codes, reasons, ran = acceptance(root, feature)[1] or [], {}, [], {}
    for ac in acs:
        code, reason = red_one(root, rows, ac, timeout, ran)
        if reason:
            reasons.append(reason)
        else:
            codes[ac] = code
    if reasons:
        return None, reasons
    rec = load_record(root)
    if rec.get("feature") != feature:
        rec = {"feature": feature}
    at, tree = vf.now(), vf.worktree_tree(root)
    for ac, code in codes.items():
        rec.setdefault("red", {})[ac] = {"at": at, "tree": tree, "exit": code}
    save_record(root, rec, *[("red", ac) for ac in codes])
    return codes, []


def run_once(ran, cmd, root, timeout):
    """One test may prove several ACs (their rows share its Run command): it runs once per verify call."""
    if cmd not in ran:
        ran[cmd] = run(cmd, root, timeout)
    return ran[cmd]


def red_one(root, rows, ac, timeout, ran):
    """(exit code, None) when the AC's test fails as it should, else (None, reason)."""
    row = next((r for r in rows if r["ac"] == ac), None)
    if not row:
        return None, f"{ac}: no row in ## Acceptance tests"
    if row["manual"]:
        return None, f"{ac}: a manual row has no test to run"
    if not os.path.exists(os.path.join(root, row["file"])):
        return None, f"{ac}: {row['file']} not found"
    code, out = run_once(ran, row["run"], root, timeout)
    if code == 0:
        return None, f"{ac}: its test passes before its code exists, so it proves nothing"
    if code in NOT_RUNNABLE or NOT_FOUND.search(out):
        return None, f"{ac}: the test did not run (exit {code}): check the Test and Run cells\n{out[-500:]}"
    return code, None


def status(root, feature):
    """Whether Review can reuse the last verify: it passed, the hook's own copy agrees, and the code is unchanged."""
    rec = load_record(root)
    if rec.get("feature") != feature:
        rec = {}
    try:
        hook = json.loads(read(os.path.join(root, ".sdlc", ".work", "verify-freshness.json")) or "{}")
    except ValueError:
        hook = {}
    hook = (hook.get("verify") or {}) if hook.get("feature") == feature else {}
    last, hook_last = rec.get("last") or {}, hook.get("last") or {}
    current = vf.worktree_tree(root)
    if last.get("result") != "pass":
        reason = "no passing verify recorded"
    elif last.get("skipped"):
        reason = "the last verify was one part's: later parts' ACs weren't checked"
    elif hook_last.get("result") != "pass":
        reason = "hook record missing or unknown"
    elif hook_last.get("tree") != last.get("tree") or set(rec.get("red") or {}) - set(hook.get("red") or {}):
        reason = "records disagree"
    elif current != last.get("tree") and vf.changed_code_files(root, last.get("tree"), current) != []:
        reason = "code changed since verify"  # docs and the record (change.md, a lesson) don't count; unknown does
    else:
        reason = ""
    # The current tree and HEAD: what `state.py verified` records and Ship checks against (the core's "Verified tree")
    return {"reuse": not reason, "reason": reason, "manual": last.get("manual", []), "drift": last.get("drift", []),
            "trace": last.get("trace", []), "red": sorted(rec.get("red") or {}), "tree": current, "head": vf.git_head(root)}


def active_feature(root):
    return next((name for name, _ in sdlc_layout.active(root)), None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--feature")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("action", nargs="?", choices=["red", "status", "trace"])
    ap.add_argument("acs", nargs="*")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    feature = a.feature or active_feature(root)
    if not feature:
        print("verify: no active feature (pass --feature)")
        return 2
    if a.action == "status":
        print(json.dumps(status(root, feature), indent=2))
        return 0
    if a.action == "trace":
        found = trace(root, feature)
        if found is None:
            print("trace: no spec refs in the ACs, nothing to trace")
            return 0
        for line in found:
            print(line)
        print(f"trace {feature}: " + (f"{len(found)} finding(s)" if found else "traced"))
        return 1 if found else 0
    if a.action == "red":
        if not a.acs or not all(AC_ID.fullmatch(ac) for ac in a.acs):
            print("verify red: name the acceptance criteria, e.g. AC-001 AC-002")
            return 2
        codes, reasons = red(root, feature, a.acs, a.timeout)
        for line in reasons or [f"{ac}: red recorded (exit {code})" for ac, code in codes.items()]:
            print(line)
        print("nothing recorded: fix those tests and rerun the whole batch" if reasons else "now write their code")
        return 1 if reasons else 0
    last, notes = full(root, feature, a.timeout)
    for line in notes + last["failures"]:
        print(line)
    if last["manual"]:
        print("checked by reading, not by a test: " + ", ".join(last["manual"]))
    print(f"verify {feature}: {last['result'].upper()} ({last['seconds']}s)")
    if last["result"] == "pass":
        print(f"head {last['head']} tree {last['tree']}")
    return 0 if last["result"] == "pass" else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
