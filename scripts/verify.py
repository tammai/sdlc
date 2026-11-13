#!/usr/bin/env python3
"""One command that proves a feature: the project's verify plan, then every acceptance criterion against the test
change.md names for it (plan.md on a 1.x feature) (ADR 0013, 0020).

Usage: verify.py [--root DIR] [--feature NAME] [--timeout S] [red AC-nnn [AC-nnn ...] | status | trace]
  Runs the verify plan (lint, typecheck, build, test from .sdlc/config.json, per package; in a workbench also each
  repo the feature branched, from its own config in its folder, a failure naming the repo), then, for every `AC-nnn`
  in change.md: a row in its `## Acceptance tests` table (plan.md's on a 1.x feature), a `manual` row's reason, the
  test file, a recorded red run, and the row's Run command passing. Writes the result to .sdlc/.work/verify.json and
  exits 0 on pass, 1 on a failure, 2 when there's no feature to verify. On an old S fix with no record, the state
  file's `Repro: <test file> › <name> | <command>` line is AC-001. A plan without the table, and no Repro line, is an
  old plan: the AC checks are skipped and the plan is from sdlc 1.x. While a backlog part is `in progress`, an AC
  that only parts not started yet own (backlog.md's ACs column) waits, and so does a task whose ACs are all theirs:
  the run records them as `skipped` and can't be reused for Review; with no part in progress everything is checked. Then drift from the plan (the state file's
  `## Tasks` and `## Public Surface`; plan.md on 1.x): a changed file no task or acceptance test names, a task whose
  files didn't change, an export or dependency the Public Surface doesn't list; each needs a `## Deviations` line
  (`state.py deviation`) naming it, with What:, Why: and Effect:. Then, only in a spec-backed repo (an rspec
  criteria.lock.json, config `spec_lock` or acceptance/manifest.json), the test lock (spec 03 S4): a test file locked
  at its red run that changed or was deleted fails the run, unless a `test-change <file> What: … Why: …` deviation
  names it and `red --at` ran its ACs with the file as it is now.
`red AC-nnn [AC-nnn ...]`, run before those ACs' code is written: runs each AC's test and records it failing (exit 0),
  and, in a spec-backed repo, locks each test file it ran (its sha256 under the state file's `## Test lock`). A test that passes, can't be
  found or can't run is refused (exit 1, and none of the named ACs is recorded): it would prove nothing.
`red --at <ref> AC-nnn …`: the ACs' test files as they are now, run in a temporary git worktree at `ref` (the
  feature's Base); each must fail there, which shows a changed test still fails without the feature.
Recorded acceptance tests (spec 03 S3): a row whose Test is a file in the repo's `acceptance/` bundle runs only when
  `acceptance/manifest.json` lists it `open` with its sha256; `contracts.py …` in its Run cell is the vendored
  runner. The first such row starts `accept.start` and waits for `accept.base_url` (.sdlc/config.json), the rows run
  with ACCEPT_BASE_URL set, and the build is stopped at the end. Recorded tests aren't locked: the manifest guards them.
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
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
sys.path.insert(0, HERE)
import backlog  # noqa: E402  (a backlog's parts: which ACs belong to parts not started yet)
import diff_stats  # noqa: E402  (changed files and the Public Surface check, since the feature's Base)
import scaffold  # noqa: E402  (the verify plan and the shell that runs project commands)
import sdlc_layout  # noqa: E402
import spec_lock  # noqa: E402  (the criteria an rspec spec locked: spec-backed changes)
import state  # noqa: E402  (the state file: ## Test lock, ## Criteria)
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


def spec_backed(root, feature):
    """Spec 03 S2. None when no AC cites a criterion and the state names no `Slice criteria:`; else the findings,
    each a failure: a cited ID the lock doesn't hold, one `state.py cite` didn't record at Define, a `stale criterion`
    whose lock hash changed since, and a slice criterion no AC cites and `## Out of scope` doesn't set aside with a
    reason."""
    change = docs(root, feature)[0]
    citations = spec_lock.cited(ac_entries(change))
    text = read(os.path.join(root, sdlc_layout.paths(root, feature)["state"])) or ""
    assigned = spec_lock.CRITERION_ID.findall((re.search(r"^Slice criteria:(.*)$", text, re.M) or [None, ""])[1])
    if not citations and not assigned:
        return None
    locked, findings = spec_lock.load(root)
    recorded = state.criteria_hashes(text)
    for ac, ids in citations.items():
        for cid in ids:
            entry = locked.get(cid)
            if entry is None:
                findings.append(f"{ac}: {cid} is not in the lock")
            elif spec_lock.criterion_line(root, entry) is None:
                findings.append(f"{cid}: its line isn't in {entry.get('file')} ({entry.get('spec')}), so nothing "
                                "shows or checks its text")
            elif cid not in recorded:
                findings.append(f"{ac}: {cid} wasn't recorded at Define (`state.py cite {feature} {cid}`)")
            elif recorded[cid] != entry.get("text_sha256"):
                findings.append(f"stale criterion: {cid} changed since Define: stop and ask about the amended text, "
                                f"then `state.py cite {feature} {cid}`")
    cited_ids = {cid for ids in citations.values() for cid in ids}
    aside = (section(change, "Out of scope") or "").splitlines()
    for cid in assigned:
        # Set aside: a line naming the ID with a reason, which is what's left without the list marker and the IDs
        if cid not in cited_ids and not any(
                cid in spec_lock.CRITERION_ID.findall(line)
                and re.search(r"\w", spec_lock.CRITERION_ID.sub("", re.sub(
                    r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?", "", line)))
                for line in aside):
            findings.append(f"{cid} is not covered: no AC cites it and ## Out of scope doesn't set it aside with a "
                            "reason")
    return findings


def run(cmd, cwd, timeout, env=None):
    sh = scaffold.shell()
    try:
        p = subprocess.run(sh + [cmd] if sh else cmd, shell=not sh, cwd=cwd, capture_output=True,
                           encoding="utf-8", errors="replace", timeout=timeout,
                           env={**os.environ, **env} if env else None)
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
    in_repos = repo_changes(root, feature)  # a workbench: what the feature changed in each app repo
    every = facts["changed_files"] + in_repos
    changed = [f for f in facts["changed_files"] if not f.startswith(".sdlc/") and not f.lower().endswith(".md")
               and not (docs_dir and f.startswith(docs_dir + "/")) and not GENERATED.search(f)]
    changed += [f for f in in_repos if "/.sdlc/" not in f and not f.lower().endswith(".md") and not GENERATED.search(f)]
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
              if any("/" in f or "." in f for f in files) and not files & set(every)
              and not (task_acs.get(n) and task_acs[n] <= set(later))]
    surface = facts.get("surface") or {}
    items += [(n, "surface") for n in surface.get("undeclared_exports", []) + surface.get("undeclared_dependencies", [])]
    deviations = section(plan_text, "Deviations") or ""
    return [{"item": i, "kind": k, "covered": covered(i, deviations)} for i, k in items]


def _branched(root, feature):
    """([(name, record)], [why]) of the repos a workbench feature branched (its `## Repos`) that sdlc may act on, and
    why each other branch line is left alone (sdlc_scopes.branched_repos); elsewhere ([], [])."""
    import sdlc_scopes  # noqa: PLC0415
    if not sdlc_scopes.is_workbench(root):
        return [], []
    located = sdlc_layout.features(root).get(feature)
    text = read(os.path.join(root, located["state"])) if located else None
    try:
        kept, dropped = sdlc_scopes.branched_repos(root, text)
    except ValueError as e:
        return [], [str(e)]
    return kept, [why for _, why in dropped]


def branched_repos(root, feature):
    """[(name, base)] of the repos a workbench feature branched that sdlc may act on; elsewhere []."""
    return [(n, r["base"]) for n, r in _branched(root, feature)[0]]


def repo_changes(root, feature):
    """Files changed in each branched repo since its base (committed, uncommitted, untracked), named from the
    workbench (`api/src/a.go`); a repo git can't read: none."""
    out = []
    for name, base in branched_repos(root, feature):
        repo = os.path.join(root, name)
        diff = diff_stats.git(repo, "diff", "-z", "--name-only", "--no-renames", base, check=False)
        new = diff_stats.git(repo, "ls-files", "-z", "--others", "--exclude-standard", check=False)
        out += sorted(f"{name}/{f}" for f in set((diff or "").split("\0")) | set((new or "").split("\0")) if f)
    return out


def repo_trees(root, feature):
    """{name: worktree tree} of each branched repo: what a verify run covered beyond the workbench's own tree."""
    return {name: vf.worktree_tree(os.path.join(root, name)) for name, _ in branched_repos(root, feature)}


def repo_failures(root, feature, timeout):
    """In a workbench: each repo the feature branched (its state's `## Repos`) runs its own verify plan, from its own
    .sdlc/config.json, in its folder; each failure starts with the repo's name. Elsewhere: []."""
    kept, dropped = _branched(root, feature)
    # A branch line sdlc may not act on (another team's repo, one not cloned) fails verify, and its commands never run
    failures = [f"not run: {why}" for why in dropped]
    for name, _ in kept:
        repo = os.path.join(root, name)
        try:
            config = json.loads(read(os.path.join(repo, ".sdlc", "config.json")) or "null")
        except ValueError:
            config = None
        if not isinstance(config, dict):
            failures.append(f"{name}: no readable .sdlc/config.json (its small sdlc setup holds its commands)")
            continue
        try:
            steps = scaffold.verify_plan(config)["verify"]
        except ValueError as e:
            failures.append(f"{name}: {e}")
            continue
        for step in steps:
            code, out = run(step["run"], os.path.join(repo, step["cwd"]), timeout)
            if code:
                failures.append(f"{name}: {step['scope'] or scaffold.ROOT_SCOPE} {step['step']}: exit {code}\n"
                                f"{out[-500:]}")
    return failures


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
    failures += repo_failures(root, feature, timeout)
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
        ran, build = {}, Build(root)
        try:
            for ac in acs:
                row = by_ac.get(ac)
                recorded = row and not row["manual"] and bundle_check(root, row)
                if not row:
                    failures.append(f"{ac}: no row in ## Acceptance tests")
                elif row["manual"]:
                    if row["run"]:
                        manual.append(ac)
                    else:
                        failures.append(f"{ac}: a manual row needs its reason in the Run column")
                elif not os.path.exists(os.path.join(root, row["file"])):
                    failures.append(f"{ac}: {row['file']} not found")
                elif recorded and recorded[1]:
                    failures.append(recorded[1])
                elif ac not in rec.get("red", {}):
                    failures.append(f"{ac}: no red run recorded (run `verify.py red {ac}` before writing its code)")
                elif recorded and build.ensure():
                    failures.append(f"{ac}: {build.error}")
                else:
                    code, out = run_once(ran, resolve(row["run"]) if recorded else row["run"], root, timeout,
                                         build.env if recorded else None)
                    if code:
                        failures.append(f"{ac}: its test fails (exit {code})\n{out[-500:]}")
        finally:
            build.close()
    backed = spec_lock.spec_backed_repo(root)  # sdlc 3.5: the test lock and cited criteria, in such a repo only
    if backed:
        failures += lock_failures(root, feature, rows or [], rec)
    drifted = drift(root, feature, later)
    if drifted is None:
        notes.append("no plan (the state file's ## Tasks) or no Base:, so drift wasn't checked")
    for d in drifted or []:
        if not d["covered"]:
            failures.append(f"drift: {d['item']} has no Deviations entry with What:, Why: and Effect:")
    failures += (spec_backed(root, feature) if backed else None) or []
    cited_count = len({c for ids in spec_lock.cited(ac_entries(docs(root, feature)[0])).values() for c in ids}) \
        if backed else 0
    if cited_count > 10:
        notes.append(f"warning: {cited_count} cited criteria: a change takes about 10; split the slice")
    traced = trace(root, feature) or []  # advisory: a note, never a failure, until its false-positive rate is known
    notes += [f"trace: {t}" for t in traced]
    rec["last"] = {"at": vf.now(), "tree": vf.worktree_tree(root), "head": vf.git_head(root),
                   "result": "fail" if failures else "pass", "seconds": round(time.time() - started, 1),
                   "failures": failures, "manual": manual, "drift": drifted or [], "skipped": skipped,
                   "trace": traced, "repos": repo_trees(root, feature)}
    save_record(root, rec, ("full", None))
    return rec["last"], notes


# Exits that mean the test never ran: shell can't execute / not found (126, 127; cmd.exe 9009), pytest no tests
# collected (5) or usage error such as an unknown node id (4), our timeout (124)
NOT_RUNNABLE = {126, 127, 9009, 5, 4, 124}
# Runner output that means the named test wasn't found. Only the runner's own lookup: an ImportError or
# AttributeError about the code under test is the normal red of a test written first
NOT_FOUND = re.compile(r"no tests ran|collected 0 items|No tests found|no tests to run|ERROR: not found:|"
                       r"has no attribute '?test\w*", re.I)


def file_sha(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def lock_failures(root, feature, rows, rec):
    """Spec 03 S4: a test file locked at its red run that changed or was deleted since, unless the state file has a
    `test-change <file> What: … Why: …` deviation and every AC whose row names the file was red at Base with the file
    as it is now (`red --at`). A file deleted that no row names any more needs only the deviation."""
    text = (read(os.path.join(root, sdlc_layout.paths(root, feature)["state"])) or "").replace("\r\n", "\n")
    deviations = (section(text, "Deviations") or "").splitlines()
    # red_at records only a run at the feature's Base or a part's Slice base; one whose base isn't behind HEAD any more
    # (a rewritten history) proves nothing about this code
    at_base = {ac: r for ac, r in (rec.get("red_at_base") or {}).items() if r.get("base") and subprocess.run(
        ["git", "-C", root, "merge-base", "--is-ancestor", r["base"], "HEAD"], capture_output=True).returncode == 0}
    out = []
    for f, sha in state.test_lock(text):
        now = file_sha(os.path.join(root, f))
        if now == sha:
            continue
        owners = [r["ac"] for r in rows if r["file"] == f and not r["manual"]]
        noted = any(f"test-change {f} " in line and re.search(r"What:\s*\S", line) and re.search(r"Why:\s*\S", line)
                    for line in deviations)
        rered = all((at_base.get(ac) or {}).get("sha256") == now for ac in owners) if now else not owners
        if not (noted and rered):
            what = "was deleted" if now is None else "changed"
            out.append(f"test lock: {f} {what} since its red run ({', '.join(owners) or 'no AC names it now'}): "
                       f"record why with `state.py deviation <feature> \"test-change {f} What: … Why: …\"`, then "
                       f"`verify.py red --at <Base> {' '.join(owners) or '<AC>'}` to show it still fails without the "
                       "feature")
    return out


def feature_bases(root, feature):
    """{commit: name} that `red --at` may run at: the feature's `Base:` and, while a part runs, its `Slice base:`."""
    text = read(os.path.join(root, sdlc_layout.paths(root, feature)["state"])) or ""
    names = [m.group(1) for m in (re.search(r"^Base:\s*`?([0-9a-f]{7,40})\b", text, re.M),
                                  re.search(r"^Slice:.*?\bSlice base:\s*([0-9a-f]{7,40})\b", text, re.M)) if m]
    return {commit_of(root, n): n for n in names if commit_of(root, n)}


def commit_of(root, ref):
    p = subprocess.run(["git", "-C", root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
                       capture_output=True, encoding="utf-8", errors="replace")
    return p.stdout.strip() or None


def red_at(root, feature, ref, acs, timeout=1800):
    """`red --at <ref>` (spec 03 S4): the ACs' test files as they are now, run in a temporary worktree at `ref` (the
    code without the feature); each must fail there. Recorded per AC with the file's hash, all or nothing; the
    worktree is always removed."""
    if not spec_lock.spec_backed_repo(root):
        return None, ["red --at: the test lock is on only in a spec-backed repo (an rspec criteria.lock.json, config "
                      "spec_lock or acceptance/manifest.json); here a changed test needs no re-red"]
    rows = acceptance(root, feature)[1] or []
    chosen, reasons = [], []
    for ac in acs:
        row = next((r for r in rows if r["ac"] == ac), None)
        if not row or row["manual"]:
            reasons.append(f"{ac}: no test row to run at {ref}")
        elif bundle_check(root, row) is not None:
            reasons.append(f"{ac}: a recorded acceptance test isn't locked: its manifest's sha256 guards it")
        elif spec_lock.inside(root, row["file"]) is None:  # it is copied into the temporary worktree
            reasons.append(f"{ac}: {row['file']} isn't a path inside the repo")
        elif not os.path.isfile(os.path.join(root, row["file"])):
            reasons.append(f"{ac}: {row['file']} not found")
        else:
            chosen.append(row)
    bases = feature_bases(root, feature)
    base = commit_of(root, ref)
    if base not in bases:
        reasons.append(f"red --at {ref}: that isn't the feature's Base or its part's Slice base "
                       f"({', '.join(bases.values()) or 'none recorded'}); the changed test must fail on the code the "
                       "feature or part started from")
    if reasons:
        return None, reasons
    git = ["git", "-C", root]
    # A run killed mid-way leaves its worktree folder behind, which prune keeps: remove those first
    listed = subprocess.run(git + ["worktree", "list", "--porcelain"], capture_output=True, encoding="utf-8",
                            errors="replace").stdout
    for line in listed.splitlines():
        folder = os.path.dirname(line[9:])
        if line.startswith("worktree ") and os.path.basename(folder).startswith("sdlc-red-at-"):
            try:
                # A day: longer than any run, whatever its --timeout and number of rows, so a live one stays
                stale = time.time() - os.path.getmtime(folder) > 24 * 3600
            except OSError:
                stale = True
            if stale:
                subprocess.run(git + ["worktree", "remove", "--force", line[9:]], capture_output=True)
                shutil.rmtree(folder, ignore_errors=True)
    subprocess.run(git + ["worktree", "prune"], capture_output=True)
    tmp = tempfile.mkdtemp(prefix="sdlc-red-at-")
    tree = os.path.join(tmp, "base")
    try:
        p = subprocess.run(git + ["worktree", "add", "--detach", tree, ref], capture_output=True, encoding="utf-8",
                           errors="replace")
        if p.returncode:
            return None, [f"red --at {ref}: no worktree ({p.stderr.strip()[-300:]})"]
        for row in chosen:
            dest = os.path.join(tree, row["file"])
            os.makedirs(os.path.dirname(dest) or tree, exist_ok=True)
            shutil.copyfile(os.path.join(root, row["file"]), dest)
        ran = {}
        for row in chosen:
            code, out = run_once(ran, row["run"], tree, timeout)
            if code == 0:
                reasons.append(f"{row['ac']}: its test passes at {ref}, without the feature, so it proves nothing")
            elif code in NOT_RUNNABLE or NOT_FOUND.search(out):
                reasons.append(f"{row['ac']}: the test did not run at {ref} (exit {code})\n{out[-500:]}")
    finally:
        subprocess.run(git + ["worktree", "remove", "--force", tree], capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)
        subprocess.run(git + ["worktree", "prune"], capture_output=True)
    if reasons:
        return None, reasons
    rec = load_record(root)
    if rec.get("feature") != feature:
        rec = {"feature": feature}
    at = vf.now()
    for row in chosen:
        rec.setdefault("red_at_base", {})[row["ac"]] = {"at": at, "ref": ref, "base": base, "file": row["file"],
                                                        "sha256": file_sha(os.path.join(root, row["file"]))}
    save_record(root, rec)
    return [r["ac"] for r in chosen], []


# --- recorded acceptance tests (spec 03 S3, contracts C4) ------------------------------------------------------

BUNDLE = "acceptance"
CONTRACTS = os.path.join(HERE, "contracts", "v1", "contracts.py")
RUNNERS = ("http", "playwright", "maestro")  # contracts v1 runs HTTP replay; Playwright and Maestro run their own


def bundle_check(root, row):
    """None when the row's test isn't in the repo's acceptance/ bundle; else (manifest entry, problem or None). Only
    an open entry whose file matches its sha256, for a runner there is, runs."""
    rel = (row.get("file") or "").replace("\\", "/")
    if not rel.startswith(BUNDLE + "/"):
        return None
    ac = row["ac"]
    text = read(os.path.join(root, BUNDLE, "manifest.json"))
    if text is None:  # a folder that happens to be named acceptance: the repo's own tests
        return None
    try:
        manifest = json.loads(text)
    except ValueError:
        manifest = None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("tests"), list):
        return {}, f"{ac}: {BUNDLE}/manifest.json isn't a manifest (an object with tests), so {rel} can't be trusted"
    entry = next((t for t in manifest.get("tests") or [] if isinstance(t, dict)
                  and t.get("path") == rel[len(BUNDLE) + 1:]), None)
    if entry is None:
        return {}, f"{ac}: {rel} isn't in {BUNDLE}/manifest.json"
    if entry.get("visibility") != "open":
        return entry, f"{ac}: {rel} is a hidden test: the builder never runs it"
    if entry.get("runner") not in RUNNERS:
        return entry, f"{ac}: not run: no runner for {entry.get('runner')!r} in contracts v1"
    if entry.get("runner") == "maestro" and not shutil.which("maestro"):  # `maestro test <path>`, as rspec records
        return entry, f"{ac}: not run: maestro not installed"
    if file_sha(os.path.join(root, rel)) != entry.get("sha256"):
        return entry, (f"{ac}: {rel} differs from the sha256 in {BUNDLE}/manifest.json: a recorded test changes only "
                       "through the spec's amend flow")
    return entry, None


def resolve(cmd):
    """`contracts.py …` in a Run cell is the vendored contracts runner, run by this Python."""
    m = re.match(r"\s*contracts\.py\b", cmd)
    if not m:
        return cmd
    exe, script = sys.executable.replace("\\", "/"), CONTRACTS.replace("\\", "/")
    return f'"{exe}" "{script}"' + cmd[m.end():]


def accept_target(root):
    """((start command, base URL, cwd), None) from config `accept` (the root's, else the one package that sets a
    start), or (None, the reason it can't start)."""
    try:
        config = json.loads(read(os.path.join(root, ".sdlc", "config.json")) or "{}")
    except ValueError as e:
        return None, f"not run: .sdlc/config.json isn't valid JSON ({e})"
    if not isinstance(config, dict):
        return None, "not run: .sdlc/config.json isn't a JSON object"
    found = [(sc["accept"], sc["path"]) for sc in scaffold.scopes(config)
             if isinstance(sc.get("accept"), dict) and sc["accept"].get("start")]
    if isinstance(config.get("accept"), dict) and config["accept"].get("start"):
        found = [(config["accept"], ".")]
    if len(found) != 1:
        return None, ("not run: accept.start and accept.base_url aren't set in .sdlc/config.json" if not found else
                      "not run: several packages set accept.start; set the root's accept to choose")
    accept, path = found[0]
    if not accept.get("base_url"):
        return None, "not run: accept.base_url isn't set in .sdlc/config.json"
    return (accept["start"], accept["base_url"], os.path.join(root, path)), None


class Build:
    """The local build recorded tests run against: started by the first row that needs it, stopped by close()."""
    WAIT = 60

    def __init__(self, root):
        self.root, self.proc, self.env, self.error, self.started = root, None, None, None, False

    def ensure(self):
        """None once the build answers; else the reason it isn't running (kept in self.error)."""
        if self.started:
            return self.error
        self.started = True
        target, self.error = accept_target(self.root)
        if self.error:
            return self.error
        start, url, cwd = target
        if answers(url):
            self.error = (f"not run: something already answers at {url}; stop it, so the tests reach the build "
                          "this run starts")
            return self.error
        sh = scaffold.shell()
        spawn = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
                 else {"start_new_session": True})
        try:
            self.proc = subprocess.Popen(sh + [start] if sh else start, shell=not sh, cwd=cwd,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **spawn)
        except OSError as e:
            self.error = f"not run: accept.start didn't start ({e})"
            return self.error
        deadline = time.time() + self.WAIT
        while time.time() < deadline:
            if self.proc.poll() is not None:
                self.error = f"not run: accept.start exited ({self.proc.returncode}) before {url} answered"
                return self.error
            if answers(url):
                break
            time.sleep(0.25)
        else:
            self.error = f"not run: the build at {url} didn't answer within {self.WAIT}s"
            return self.error
        self.env = {"ACCEPT_BASE_URL": url}
        return None

    def close(self):
        """Stops the build and everything it started (a shell, a dev server's children). POSIX: the whole process
        group, even once its first process has exited. Windows: the tree under the first process, while it runs
        (taskkill can't find children whose parent has exited)."""
        if not self.proc:
            return
        if os.name == "nt":
            if self.proc.poll() is None:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)
        else:
            import signal
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(self.proc.pid, sig)
                except OSError:  # the group is gone
                    break
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    continue
                time.sleep(0.2)  # the group's other processes get the same signal; give them a moment
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def answers(url):
    """Any HTTP answer from `url`, an error status included."""
    try:
        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=2).close()
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def red(root, feature, acs, timeout=1800):
    """({AC: exit code}, []) when every AC's test fails as it should before its code exists, else (None, reasons)
    and nothing is recorded: a batch is recorded whole or not at all."""
    rows, codes, reasons, ran = acceptance(root, feature)[1] or [], {}, [], {}
    build = Build(root)
    try:
        for ac in acs:
            code, reason = red_one(root, rows, ac, timeout, ran, build)
            if reason:
                reasons.append(reason)
            else:
                codes[ac] = code
    finally:
        build.close()
    if reasons:
        return None, reasons
    # The test lock (spec 03 S4), in a spec-backed repo only: each builder-written test, as it was when it failed;
    # recorded tests have their manifest's hash instead
    entries = []
    for row in rows if spec_lock.spec_backed_repo(root) else ():
        if row["ac"] in codes and not row["manual"] and bundle_check(root, row) is None:
            entries += [row["file"], file_sha(os.path.join(root, row["file"]))]
    if entries:
        try:
            state.run(argparse.Namespace(root=root, feature=feature, cmd="lock", entries=entries))
        except state.Refused as e:
            return None, [f"test lock not written: {e}"]
    rec = load_record(root)
    if rec.get("feature") != feature:
        rec = {"feature": feature}
    at, tree = vf.now(), vf.worktree_tree(root)
    for ac, code in codes.items():
        rec.setdefault("red", {})[ac] = {"at": at, "tree": tree, "exit": code}
    save_record(root, rec, *[("red", ac) for ac in codes])
    return codes, []


def run_once(ran, cmd, root, timeout, env=None):
    """One test may prove several ACs (their rows share its Run command): it runs once per verify call."""
    if cmd not in ran:
        ran[cmd] = run(cmd, root, timeout, env)
    return ran[cmd]


def red_one(root, rows, ac, timeout, ran, build):
    """(exit code, None) when the AC's test fails as it should, else (None, reason)."""
    row = next((r for r in rows if r["ac"] == ac), None)
    if not row:
        return None, f"{ac}: no row in ## Acceptance tests"
    if row["manual"]:
        return None, f"{ac}: a manual row has no test to run"
    if not os.path.exists(os.path.join(root, row["file"])):
        return None, f"{ac}: {row['file']} not found"
    recorded = bundle_check(root, row)
    if recorded and recorded[1]:
        return None, recorded[1]
    env = None
    if recorded:
        if build.ensure():
            return None, f"{ac}: {build.error}"
        env = build.env
    code, out = run_once(ran, resolve(row["run"]) if recorded else row["run"], root, timeout, env)
    if code == 0:
        return None, f"{ac}: its test passes before its code exists, so it proves nothing"
    # The vendored runner says `not run: <reason>` when it couldn't run a recorded test; for the project's own tests
    # that text is ordinary output
    if code in NOT_RUNNABLE or NOT_FOUND.search(out) or recorded and "not run: " in out:
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
    if not reason:  # a workbench: each branched repo's tree as the run saw it (a missing tree is a change)
        ran = last.get("repos") or {}
        moved = [n for n, t in repo_trees(root, feature).items() if not t or ran.get(n) != t]
        reason = f"code changed in {', '.join(moved)} since verify" if moved else ""
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
    ap.add_argument("--at", metavar="REF", help="red only: run the ACs' current tests at REF (the feature's Base)")
    ap.add_argument("action", nargs="?", choices=["red", "status", "trace"])
    ap.add_argument("acs", nargs="*")
    a = ap.parse_intermixed_args(argv)  # `red --at <ref> AC-001`: an option between positionals (Python < 3.12)
    root = os.path.abspath(a.root)
    feature = a.feature or active_feature(root)
    if not feature:
        print("verify: no active feature (pass --feature)")
        return 2
    if a.action == "status":
        print(json.dumps(status(root, feature), indent=2))
        return 0
    if a.action == "trace":
        cited = spec_backed(root, feature) if spec_lock.spec_backed_repo(root) else None
        found = trace(root, feature)
        if found is None and cited is None:
            print("trace: no spec refs in the ACs, nothing to trace")
            return 0
        found = (cited or []) + (found or [])
        for line in found:
            print(line)
        print(f"trace {feature}: " + (f"{len(found)} finding(s)" if found else "traced"))
        return 1 if found else 0
    if a.action == "red":
        if not a.acs or not all(AC_ID.fullmatch(ac) for ac in a.acs):
            print("verify red: name the acceptance criteria, e.g. AC-001 AC-002")
            return 2
        if a.at:
            done, reasons = red_at(root, feature, a.at, a.acs, a.timeout)
            for line in reasons or [f"{ac}: fails at {a.at} with its test as it is now" for ac in done]:
                print(line)
            print("nothing recorded" if reasons else "recorded: the changed tests still fail without the feature")
            return 1 if reasons else 0
        codes, reasons = red(root, feature, a.acs, a.timeout)
        for line in reasons or [f"{ac}: red recorded (exit {code})" for ac, code in codes.items()]:
            print(line)
        print("nothing recorded: fix those tests and rerun the whole batch" if reasons else "now write their code")
        return 1 if reasons else 0
    if a.at:
        print("verify: --at goes with red")
        return 2
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
