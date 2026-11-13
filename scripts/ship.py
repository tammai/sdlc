#!/usr/bin/env python3
"""Ship's one command: everything before the commit, so Ship is a single shell call (ADR 0020).

Usage: ship.py [--root DIR] FEATURE [--message SUBJECT] [--review TEXT] [--note TEXT] [--waive-baseline] [--timeout S]
       ship.py [--root DIR] FEATURE --status
  1. `Owner:` must be `git config user.email`; someone else's is refused (the user decides a handover).
  2. `--review TEXT`: when the change file has no `## Review` yet, appends one holding TEXT (an S change, or an M no
     review ran on); one written already is left as it is.
  3. The last passing verify.py run is reused when the code hasn't changed since (`verify.py status`); otherwise
     verify.py runs now, and a failure stops here with nothing moved, unless `--waive-baseline` and only the test
     step failed while .sdlc/baseline.md lists failing tests: the user's brownfield repo then ships past failures it
     already had. verify.py doesn't read the baseline, so the caller has checked that every failure is listed; the
     waiver is written to the Gate log.
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
import verify  # noqa: E402  (status, the full run, and what the tests leave behind)

MESSAGE = os.path.join(".sdlc", ".work", "commit-msg.txt")
# state.py's control contract: runtime files, never committed, even where the repo's .gitignore misses them
CONTRACT = re.compile(r"^\.sdlc/state/[^/]+(\.json|\.events\.jsonl|\.commands/)")


class Refused(Exception):
    pass


def git(root, *args, check=True):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8", errors="replace")
    if check and p.returncode:
        raise Refused(f"git {args[0]}: {(p.stderr or p.stdout).strip()}")
    return p.stdout


def field(text, name):
    m = re.search(rf"^{name}:[ \t]*(\S+)", text, re.M)
    return m.group(1) if m else None


def add_review(root, change, text):
    path = os.path.join(root, change)
    body = verify.read(path)
    if body is None:
        raise Refused(f"{change} not found")
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
    if waive_baseline and listed and all(re.match(r"[^\n]*\btest: exit", f) for f in last["failures"]):
        return last["head"], last["tree"], f"Stage 4: baseline failures waived: only the test step failed; {len(listed)} listed in .sdlc/baseline.md"
    hint = "\nIf only the test step failed and every failure is in .sdlc/baseline.md, rerun with --waive-baseline." if listed else ""
    raise Refused("verify failed:\n" + "\n".join(notes + last["failures"]) + hint)


def state_py(root, *args, ok=None):
    p = subprocess.run([sys.executable, os.path.join(HERE, "state.py"), "--root", root, *args], capture_output=True,
                       encoding="utf-8", errors="replace")
    if p.returncode and not (ok and ok in p.stdout):
        raise Refused(f"state.py {args[0]}: {p.stdout.strip()}")


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
        raise Refused(f"no state file for {feature}")
    owner, me = field(state, "Owner"), git(root, "config", "user.email", check=False).strip()
    message = message or title(root, paths["change"]) or feature
    if owner and me and owner != me:
        raise Refused(f"Owner is {owner}, not {me}: ask the user before taking it over")
    if review:
        add_review(root, paths["change"], review)
    # Every refusal comes before the state moves, so a refusal leaves the state file as it was
    repos = check_repos(root, state) if sdlc_scopes.is_workbench(root) else None
    head, tree, waiver = verified(root, feature, timeout, waive_baseline)
    branch = None
    if git(root, "branch", "--show-current").strip() != feature and on_default_branch(root):
        if git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{feature}", check=False).strip():
            raise Refused(f"a branch named {feature} exists already: switch to it (or rename it) and run ship.py again")
        branch = feature
        git(root, "switch", "-c", branch)
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
    if sdlc_scopes.is_workbench(root):
        out["repos"] = ship_repos(root, feature, paths["change"], message, files, branch, repos)
    return out


def check_repos(root, state):
    """A workbench feature's repos to ship, [(name, record)], checked before anything moves: the manifest reads,
    every branch line names a writable cloned repo (never another team's), each is on its feature branch, and every
    listed repo folder is gitignored in the workbench (else the workbench commit would take it in as a gitlink)."""
    try:
        kept, dropped = sdlc_scopes.branched_repos(root, state)
        listed = [r["name"] for r in sdlc_scopes.manifest(root)]
    except ValueError as e:
        raise Refused(str(e))
    if dropped:
        raise Refused("; ".join(why for _, why in dropped) + ": sdlc doesn't stage or commit there. Fix workbench.json "
                      "or the state file's ## Repos line, then run ship.py again")
    for name in listed:
        ignored = subprocess.run(["git", "-C", root, "check-ignore", "-q", f"{name}/"], capture_output=True).returncode
        if os.path.isdir(os.path.join(root, name)) and ignored != 0:
            raise Refused(f"{name}/ isn't gitignored in the workbench, so its commit would take the repo in: add "
                          f"/{name}/ to .gitignore (scaffold.py workbench add does) and run ship.py again")
    # Any other git repo inside the workbench that git would stage (listed or not) goes in as a gitlink too
    for entry in git(root, "ls-files", "-z", "--others", "--exclude-standard").split("\0"):
        if entry.endswith("/") and os.path.exists(os.path.join(root, entry, ".git")):
            raise Refused(f"{entry} is a git repo inside the workbench that isn't gitignored, so the workbench commit "
                          f"would take it in: list it (scaffold.py workbench add) or add /{entry} to .gitignore, then "
                          "run ship.py again")
    for name, rec in kept:
        current = git(os.path.join(root, name), "branch", "--show-current").strip()
        if current != rec["branch"]:
            raise Refused(f"{name} is on {current or 'a detached HEAD'}, not the feature's branch {rec['branch']}: "
                          f"switch it back (git -C {shlex.quote(name)} switch {shlex.quote(rec['branch'])}) and run "
                          "ship.py again")
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
        raise Refused(f"no state file for {feature}")
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
        print(f"ship: {e}")
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
