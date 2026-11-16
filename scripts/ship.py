#!/usr/bin/env python3
"""Ship's one command: everything before the commit, so Ship is a single shell call (ADR 0020).

Usage: ship.py [--root DIR] FEATURE [--message SUBJECT] [--review TEXT] [--note TEXT] [--waive-baseline] [--timeout S]
               [--json]
       ship.py [--root DIR] FEATURE --status
  1. `Owner:` must be `git config user.email`; someone else's is refused (the user decides a handover).
  2. `--review TEXT`: when the change file has no `## Review` yet, appends one holding TEXT (an S change, or an M no
     review ran on); one written already is left as it is.
  3. The last passing verify.py run is reused when the code hasn't changed since (`verify.py status`); otherwise
     verify.py runs now, and a failure stops here with nothing moved, unless `--waive-baseline` and only the test
     step failed and every failing test its report names is listed in .sdlc/baseline.md: the user's brownfield repo
     then ships past failures it already had. Output that doesn't name its failures (or names fewer than its summary
     counts) is refused, as is any failure the baseline doesn't list. The waived tests are written to the Gate log.
  4. On the default branch (and not on a branch named after the feature, which origin/HEAD can name on a repo whose
     first push was that branch), switches to a new branch named after the feature; one that exists already is
     refused. This comes before the state moves, so a refusal leaves the state file as it was.
  5. `state.py advance FEATURE 4 --gate pass --verified <head> <tree>` (already at Stage 4 is fine), then
     `state.py set FEATURE Status done`, so the kept record says done; the commit review still reviews this commit
     as the feature's (hooks/sdlc_review_gate.py: the commit that finishes a feature).
  6. Stages every changed and untracked file except .sdlc/.work/, state.py's control contract and what the tests
     leave behind (`__pycache__`, caches), and writes the commit message (SUBJECT, by default the change file's
     title, then `Record: <change>`) to .sdlc/.work/commit-msg.txt.
  7. In a workbench, each repo the feature branched (`## Repos`) is checked to be on its feature branch, staged the
     same way, given its own message (.sdlc/.work/commit-msg-<repo>.txt) naming the change file, and a PR body
     (.sdlc/.work/pr-<repo>.md) linking the others; `repos` lists them with the workbench in merge order: workbench,
     then providers, then consumers (workbench.json `contract`). The caller commits each (`git -C <repo> commit -F
     <message>`), pushes, opens each PR with its body, and records it: `state.py pr FEATURE <repo> <url>`.
`--json` (#76): the success object gains `result: ready` and `problems: []`; a refusal is one JSON document,
  `{result: refused, feature, problems}`, each problem `{severity, code, message, fix?}` (verify's own when
  verify stopped it), instead of the `ship: …` line. Exit codes are the same.
`--status`: a workbench feature's recorded PRs (`## PRs`), each one's state from gh, a warning for each consumer
  merged before its provider (or an app before the workbench's contract PR), never a block; `done` only when every PR
  is merged. Always exit 0 once the state file is read.
The commit stays in the caller's command, where the commit's security review and the user's permission rules see
it: `ship.py … && git commit -F .sdlc/.work/commit-msg.txt && git push -u origin HEAD && gh pr create --fill`.
Exit 0 ready to commit, 1 refused or verify failed, 2 usage. Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
sys.path.insert(0, HERE)
import sdlc_layout  # noqa: E402
import sdlc_scopes  # noqa: E402  (a workbench: its repos, the feature's ## Repos and ## PRs, merge order)
import capabilities  # noqa: E402  (the living spec, #73: checked first, written after verify)
import problems as P  # noqa: E402  (a refusal's code and fix, for --json)
import verify  # noqa: E402  (status, the full run, and what the tests leave behind)

MESSAGE = os.path.join(".sdlc", ".work", "commit-msg.txt")
# state.py's control contract: runtime files, never committed, even where the repo's .gitignore misses them
CONTRACT = re.compile(r"^\.sdlc/state/[^/]+(\.json|\.events\.jsonl|\.commands/)")


class Refused(Exception):
    """Ship stopped before anything moved. `code` and `fix` are for --json (#76); `problems`, verify's own, when it
    stopped on them."""

    def __init__(self, message, code="ship_refused", fix=None, problems=()):
        super().__init__(message)
        self.code, self.fix, self.problems = code, fix, list(problems)

    def as_problems(self):
        own = P.problem(self.code, str(self).split("\n")[0] if self.problems else str(self), fix=self.fix)
        return [own] + self.problems


def git(root, *args, check=True):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8", errors="replace")
    if check and p.returncode:
        raise Refused(f"git {args[0]}: {(p.stderr or p.stdout).strip()}", "git_failed")
    return p.stdout


def field(text, name):
    m = re.search(rf"^{name}:[ \t]*(\S+)", text, re.M)
    return m.group(1) if m else None


def add_review(root, change, text):
    path = os.path.join(root, change)
    body = verify.read(path)
    if body is None:
        raise Refused(f"{change} not found", "change_file_missing")
    if re.search(r"^## Review\b", body, re.M):
        return False
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(body.rstrip("\n") + f"\n\n## Review\n\n{text}\n")
    return True


def baseline_failures(root):
    """The failing tests .sdlc/baseline.md lists: its Failing tests rows, not the template's 'none' row."""
    text = verify.read(os.path.join(root, ".sdlc", "baseline.md")) or ""
    section = re.search(r"^## Failing tests\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    listed = []
    for line in (section.group(1) if section else "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 2 and not set(cells[0]) <= set("-: ") \
                and cells[0] not in ("Package", "—", "-") and cells[1].lower() != "none":
            listed.append(cells[1])
    return listed


def verified(root, feature, timeout, waive_baseline=False):
    """(head, tree, waiver): waiver is a Gate log line when a failed run was let through on the baseline, else None."""
    st = verify.status(root, feature)
    if st["reuse"]:
        return st["head"], st["tree"], None
    last, notes = verify.full(root, feature, timeout, whole=True)
    if last["result"] == "pass":
        return last["head"], last["tree"], None
    listed = baseline_failures(root)
    # The workbench's baseline lists its own tests: an app repo's failure (`api: … test: exit`) is never waived by it
    apps = tuple(f"{name}: " for name, _ in verify.branched_repos(root, feature))
    if waive_baseline and listed and all(re.match(r"[^\n]*\btest: exit", f) and not (apps and f.startswith(apps))
                                         for f in last["failures"]):
        problem, waived = baseline_match(last, listed)
        if not problem:
            return last["head"], last["tree"], ("Stage 4: baseline failures waived (listed in .sdlc/baseline.md): "
                                                + ", ".join(waived))
        raise Refused("verify failed:\n" + "\n".join(notes + last["failures"]) + "\n" + problem, "verify_failed",
                      problems=notes + last["failures"] + [P.problem("baseline_waiver_refused", problem)])
    waivable = listed and not (apps and any(f.startswith(apps) for f in last["failures"]))
    hint = ("\nIf only the test step failed and every failure is in .sdlc/baseline.md, rerun with --waive-baseline."
            if waivable else "")
    raise Refused("verify failed:\n" + "\n".join(notes + last["failures"]) + hint, "verify_failed",
                  fix="fix the failures and run ship.py again" + (", or rerun with --waive-baseline" if waivable else ""),
                  problems=notes + last["failures"])


# #56 P2: the failing tests each runner's report names, and the count its own summary gives
NAMED = (
    re.compile(r"^(?:FAILED|ERROR) ([^\s(]\S*)", re.M),  # pytest's short summary
    re.compile(r"^\s*● (?!Console$)(.+?)\s*$", re.M),  # jest
    re.compile(r"^\s*FAIL\s+(\S+ > .+?)\s*$", re.M),  # vitest
    re.compile(r"^not ok \d+ - (.+?)\s*$", re.M),  # node --test, TAP, top-level tests
    re.compile(r"^\s*✖ (?!failing tests:)(.+?)(?: \([\d.]+m?s\))?\s*$", re.M),  # node --test, spec reporter
)
COUNTED = (
    re.compile(r"^\s*Tests:?\s+(\d+) failed", re.M),  # jest, vitest
    re.compile(r"^[#ℹ] fail (\d+)\s*$", re.M),  # node --test
)
PYTEST_SUMMARY = re.compile(r"^[= ]*\d+ (?:failed|passed|errors?|skipped|deselected|xfailed|xpassed|warnings?)\b"
                            r".* in [\d.]+s\b", re.M)


def failing_tests(out):
    """([names], count): the failing tests named in a test run's output (pytest, unittest, jest, vitest, go test,
    node --test) and the count the runners' own summaries give (go has none: its `--- FAIL` lines are the count);
    count is None when no summary was found."""
    names, count = [], None

    def add(name):
        if name not in names:
            names.append(name)
    for pattern in NAMED:
        for m in pattern.finditer(out):
            add(m.group(1))
    for m in re.finditer(r"^(?:FAIL|ERROR): (\w+) \(([\w.]+)\)", out, re.M):  # unittest
        method, where = m.groups()
        add(where if where.endswith("." + method) else f"{where}.{method}")
    found = [int(n) for p in COUNTED for n in p.findall(out)]
    found += [int(n) for line in PYTEST_SUMMARY.findall(out) for n in re.findall(r"(\d+) (?:failed|errors?)\b", line)]
    found += [int(n) for m in re.finditer(r"^FAILED \(([^)]*)\)", out, re.M)
              for n in re.findall(r"(?:failures|errors)=(\d+)", m.group(1))]
    go = re.findall(r"^\s*--- FAIL: (\S+)", out, re.M)
    for name in go:
        add(name)
    if found or go:
        count = sum(found) + len(go)
    return names, count


def leaves(name):
    """A test's name and its shorter forms: the part after `::`, ` › `, ` > ` or a dotted name's last `.`, and a
    go subtest's parent."""
    out = {name.strip()}
    for sep in ("::", " › ", " > "):
        if sep in name:
            out.add(name.rsplit(sep, 1)[1].strip())
    for n in list(out):
        if re.fullmatch(r"[\w.]+", n) and "." in n:
            out.add(n.rsplit(".", 1)[1])
        if re.match(r"Test\w*/", n):
            out.add(n.split("/", 1)[0])
    return out


def baseline_match(last, listed):
    """(problem, None) when a failing test isn't in the baseline or the failures can't be named; else (None, names).
    Each failing test step's output (verify.json `last.test_output`) must name as many tests as its summary counts."""
    outputs = last.get("test_output") or {}
    listed_leaves = set().union(*(leaves(cell) for cell in listed))
    names = []
    for failure in last["failures"]:
        step = failure.split(": exit", 1)[0]
        found, count = failing_tests(outputs.get(step) or "")
        if not found or count != len(found):
            counted = "no summary count" if count is None else f"its summary counts {count}"
            return (f"--waive-baseline refused: couldn't match the failing tests to .sdlc/baseline.md: {step} named "
                    f"{len(found)} failing test(s) and {counted}. Fix them, or, with the user's OK, rerun the tests "
                    "with a runner whose report names each failure"), None
        names += found
    unlisted = [n for n in names if not leaves(n) & listed_leaves]
    if unlisted:
        return (f"--waive-baseline refused: failing tests not in .sdlc/baseline.md: {', '.join(unlisted)}. Fix them; "
                "adding one to the baseline needs the user's OK and a Deviations line"), None
    return None, names


def state_py(root, *args, ok=None):
    p = subprocess.run([sys.executable, os.path.join(HERE, "state.py"), "--root", root, *args], capture_output=True,
                       encoding="utf-8", errors="replace")
    if p.returncode and not (ok and ok in p.stdout):
        raise Refused(f"state.py {args[0]}: {p.stdout.strip()}", "state_refused")


def title(root, change):
    m = re.search(r"^#[ \t]+(.+?)\s*$", verify.read(os.path.join(root, change)) or "", re.M)
    return m.group(1) if m else None


def on_default_branch(root):
    current = git(root, "branch", "--show-current").strip()
    remote_head = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False).strip()
    default = remote_head.split("/", 1)[1] if "/" in remote_head else None
    return current == default if default else current in ("main", "master")


def to_stage(root):
    tracked = git(root, "diff", "-z", "--name-only", "HEAD").split("\0")
    untracked = git(root, "ls-files", "-z", "--others", "--exclude-standard").split("\0")
    return sorted({f for f in tracked + untracked
                   if f and not f.startswith(".sdlc/.work/") and not CONTRACT.search(f) and not verify.GENERATED.search(f)})


def ship(root, feature, message, review=None, note=None, timeout=1800, waive_baseline=False):
    paths = sdlc_layout.paths(root, feature)
    state = verify.read(os.path.join(root, paths["state"]))
    if state is None:
        raise Refused(f"no state file for {feature}", "no_state_file")
    owner, me = field(state, "Owner"), git(root, "config", "user.email", check=False).strip()
    message = message or title(root, paths["change"]) or feature
    if owner and me and owner != me:
        raise Refused(f"Owner is {owner}, not {me}: ask the user before taking it over", "owner_differs",
                      fix="ask the user whether to take it over (state.py set <feature> Owner <you>)")
    if review:
        add_review(root, paths["change"], review)
    # Every refusal comes before the state moves, so a refusal leaves the state file as it was
    repos = check_repos(root, state) if sdlc_scopes.is_workbench(root) else None
    living_spec(root, feature)
    head, tree, waiver = verified(root, feature, timeout, waive_baseline)
    branch = None
    if git(root, "branch", "--show-current").strip() != feature and on_default_branch(root):
        if git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{feature}", check=False).strip():
            raise Refused(f"a branch named {feature} exists already: switch to it (or rename it) and run ship.py "
                          "again", "branch_exists", fix=f"git switch {feature}")
        branch = feature
        git(root, "switch", "-c", branch)
    written = living_spec(root, feature, write=True)
    if waiver:
        state_py(root, "log", feature, waiver)
    state_py(root, "advance", feature, "4", "--gate", "pass", "--verified", head, tree, *(["--note", note] if note else []),
          ok="already at Stage 4")
    state_py(root, "set", feature, "Status", "done")
    files = to_stage(root)
    if files:
        git(root, "add", "-A", "--", *files)
    os.makedirs(os.path.join(root, ".sdlc", ".work"), exist_ok=True)
    with open(os.path.join(root, MESSAGE), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{message}\n\nRecord: {paths['change']}\n")
    out = {"ok": True, "head": head, "tree": tree, "branch": branch, "staged": files, "message": MESSAGE}
    if written:
        out["capabilities"] = written
    if sdlc_scopes.is_workbench(root):
        out["repos"] = ship_repos(root, feature, paths["change"], message, files, branch, repos)
    return out


def living_spec(root, feature, write=False):
    """The living spec (#73), when config turns it on: checked before anything moves, written after verify, so the
    capability files are docs in Ship's own commit. The files written or deleted."""
    try:
        files, problems = (capabilities.merge if write else capabilities.plan)(root, feature)
    except ValueError as e:
        raise Refused(f"living_spec: {e}", "living_spec_folder_invalid")
    if problems:
        raise Refused("the change file's ## Capabilities can't be applied:\n" + "\n".join(problems),
                      "capabilities_invalid", fix=problems[0].fix, problems=problems)
    return sorted(files)


def check_repos(root, state):
    """A workbench feature's repos to ship, [(name, record)], checked before anything moves: the manifest reads,
    every branch line names a writable cloned repo (never another team's), each is on its feature branch, and every
    listed repo folder is gitignored in the workbench (else the workbench commit would take it in as a gitlink)."""
    try:
        kept, dropped = sdlc_scopes.branched_repos(root, state)
        listed = [r["name"] for r in sdlc_scopes.manifest(root)]
    except ValueError as e:
        raise Refused(str(e), "workbench_invalid")
    if dropped:
        raise Refused("; ".join(why for _, why in dropped) + ": sdlc doesn't stage or commit there. Fix workbench.json "
                      "or the state file's ## Repos line, then run ship.py again", "repo_not_writable")
    for name in listed:
        ignored = subprocess.run(["git", "-C", root, "check-ignore", "-q", f"{name}/"], capture_output=True).returncode
        if os.path.isdir(os.path.join(root, name)) and ignored != 0:
            raise Refused(f"{name}/ isn't gitignored in the workbench, so its commit would take the repo in: add "
                          f"/{name}/ to .gitignore (scaffold.py workbench add does) and run ship.py again", "repo_not_ignored")
    # Any other git repo inside the workbench that git would stage (listed or not) goes in as a gitlink too
    for entry in git(root, "ls-files", "-z", "--others", "--exclude-standard").split("\0"):
        if entry.endswith("/") and os.path.exists(os.path.join(root, entry, ".git")):
            raise Refused(f"{entry} is a git repo inside the workbench that isn't gitignored, so the workbench commit "
                          f"would take it in: list it (scaffold.py workbench add) or add /{entry} to .gitignore, then "
                          "run ship.py again", "nested_repo_not_ignored")
    for name, rec in kept:
        current = git(os.path.join(root, name), "branch", "--show-current").strip()
        if current != rec["branch"]:
            raise Refused(f"{name} is on {current or 'a detached HEAD'}, not the feature's branch {rec['branch']}: "
                          f"switch it back (git -C {shlex.quote(name)} switch {shlex.quote(rec['branch'])}) and run "
                          "ship.py again", "repo_off_branch",
                          fix=f"git -C {shlex.quote(name)} switch {shlex.quote(rec['branch'])}")
    return kept


def ship_repos(root, feature, change, message, workbench_files, workbench_branch, repos):
    """A workbench feature: each repo it branched (check_repos), staged on its feature branch with its own commit
    message naming the change file, and a PR body linking the others; listed with the workbench in merge order."""
    urls = {r["name"]: r["url"] for r in sdlc_scopes.manifest(root)}
    work = os.path.join(root, ".sdlc", ".work")
    branch_now = workbench_branch or git(root, "branch", "--show-current").strip()
    entries = {sdlc_scopes.WORKBENCH_SCOPE: {
        "name": sdlc_scopes.WORKBENCH_SCOPE, "path": root, "branch": branch_now, "staged": workbench_files,
        "message": os.path.join(root, MESSAGE),
        "url": git(root, "remote", "get-url", "origin", check=False).strip() or None}}
    for name, rec in repos:
        repo = os.path.join(root, name)
        files = to_stage(repo)
        ahead = git(repo, "rev-list", "--count", f"{rec['base']}..HEAD", check=False).strip()
        if not files and ahead in ("", "0"):
            continue  # branched but never changed: no commit, no PR
        if files:
            git(repo, "add", "-A", "--", *files)
        msg = os.path.join(work, f"commit-msg-{name}.txt")
        with open(msg, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"{message}\n\nRecord: {change} in the workbench ({os.path.basename(root)})\n")
        entries[name] = {"name": name, "path": repo, "branch": rec["branch"], "staged": files, "message": msg,
                         "url": urls.get(name)}
    order = sdlc_scopes.merge_order(root, list(entries))
    plan = [f"{i}. {n}" for i, n in enumerate(order, 1)]
    out = []
    for name in order:
        e = entries[name]
        others = [f"- {n}: {entries[n]['url'] or '(no remote)'} (branch `{entries[n]['branch']}`)"
                  for n in order if n != name]
        body = os.path.join(work, f"pr-{'workbench' if name == sdlc_scopes.WORKBENCH_SCOPE else name}.md")
        with open(body, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"{message}\n\nOne sdlc feature across repos: `{feature}`, recorded in the workbench "
                    f"(`{change}`).\n\nMerge order:\n" + "\n".join(plan) + "\n\nThe other PRs of this feature:\n"
                    + ("\n".join(others) or "- none") + "\n")
        out.append({**e, "pr_body": body,
                    "record": f"state.py pr {feature} \"{name}\" <url> (after gh pr create in {e['path']})"})
    return out


def pr_state(url, cwd):
    """(state, mergedAt, error) of a PR from gh (SDLC_GH: the gh command line to use instead, for tests), run in the
    repo's own folder so a bare number names that repo's PR; the URL goes after `--`, never read as an option."""
    gh = shlex.split(os.environ.get("SDLC_GH") or "gh", posix=os.name != "nt")
    gh = [w.strip('"') for w in gh]
    try:
        p = subprocess.run(gh + ["pr", "view", "--json", "state,mergedAt", "--", url], capture_output=True,
                           encoding="utf-8", errors="replace", timeout=60, cwd=cwd)
        data = json.loads(p.stdout) if p.returncode == 0 else None
        error = None if p.returncode == 0 else (p.stderr or p.stdout).strip()[-300:] or f"gh exit {p.returncode}"
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        data, error = None, str(e) or type(e).__name__
    if not isinstance(data, dict):
        return "UNKNOWN", None, error or "gh gave no PR state"
    return str(data.get("state") or "UNKNOWN").upper(), data.get("mergedAt"), None


def status(root, feature):
    """`--status`: each recorded PR's state in merge order, a warning per pair merged out of order (never a block),
    and `done` only when every PR is merged."""
    state = verify.read(os.path.join(root, sdlc_layout.paths(root, feature)["state"]))
    if state is None:
        raise Refused(f"no state file for {feature}", "no_state_file")
    prs = sdlc_scopes.feature_prs(state)
    if not prs:
        return {"done": False, "prs": [], "warnings": [],
                "note": f"no PRs recorded: after each gh pr create, run state.py pr {feature} <repo> <url>"}
    rows, errors = [], []
    for name in sdlc_scopes.merge_order(root, list(prs)):
        try:
            where = root if name == sdlc_scopes.WORKBENCH_SCOPE else sdlc_scopes.repo_dir(root, name)
            if not os.path.isdir(where) and not prs[name].isdigit():
                where = root  # a full URL names its repo itself
            st, merged, error = pr_state(prs[name], where) if os.path.isdir(where) else (
                "UNKNOWN", None, f"{name}/ isn't cloned, and a bare PR number needs its repo")
        except ValueError as e:
            st, merged, error = "UNKNOWN", None, str(e)
        rows.append({"repo": name, "url": prs[name], "state": st, "merged_at": merged if st == "MERGED" else None})
        if error:  # gh missing, signed out or rate-limited: said, never shown as "not merged yet"
            errors.append(f"{name}: couldn't read {prs[name]} with gh ({error})")
    warnings = []
    for i, early in enumerate(rows):
        for late in rows[i + 1:]:
            if not late["merged_at"] or not sdlc_scopes.must_follow(root, early["repo"], late["repo"]):
                continue
            if not early["merged_at"] or early["merged_at"] > late["merged_at"]:
                when = "is still open" if not early["merged_at"] else "merged after it"
                warnings.append(f"{late['repo']} merged before {early['repo']}, which {when}: the merge order is "
                                "workbench, then the provider, then its consumers")
    out = {"done": all(r["merged_at"] for r in rows), "prs": rows, "warnings": warnings}
    if errors:
        out["errors"] = errors
        out["note"] = "some PR states are unknown, so out-of-order merges among them can't be checked"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("feature")
    ap.add_argument("--message")
    ap.add_argument("--review")
    ap.add_argument("--note")
    ap.add_argument("--waive-baseline", action="store_true",
                    help="ship past a failed test step when .sdlc/baseline.md lists failing tests")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--json", action="store_true",
                    help="a refusal as one JSON document too: result, then each problem's code, message and fix")
    ap.add_argument("--status", action="store_true",
                    help="a workbench feature: its PRs' states, warnings for out-of-order merges; never blocks")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.status:
        try:
            print(json.dumps(status(os.path.abspath(a.root), a.feature), ensure_ascii=False))
        except Refused as e:
            print(f"ship: {e}")
            return 1
        return 0
    try:
        out = ship(os.path.abspath(a.root), a.feature, a.message, a.review, a.note, a.timeout, a.waive_baseline)
    except Refused as e:
        if a.json:
            P.emit("refused", e.as_problems(), feature=a.feature)
        else:
            print(f"ship: {e}")
        return 1
    print(json.dumps({"result": "ready", **out, "problems": []} if a.json else out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
