#!/usr/bin/env python3
"""Check the shared sdlc files, whichever agent or person changed them (seeded by the sdlc plugin v{{plugin_version}}).

Only active features count (`Status: active` in their state file):
  - the record matches the phase reached: past Define (Stage 1), the change file (<docs>/changes/<feature>.md) has its
    `## Acceptance tests` table; in Ship (Stage 4), its `## Review` section says what was reviewed.
  - the baseline: against --base, a new row or a higher lint count needs a feature's Deviations entry naming it.
  - past Define, each `## Acceptance tests` row's test file exists (`manual` and `departure D-nnn` rows name none).
  - the test lock: each file under the state file's `## Test lock` still has the sha256 it had at its red run (LF or
    CRLF), unless a `test-change <file> What: … Why: …` deviation names it. With --base, a feature whose state file
    changed since then is checked too, active or not: Ship marks it done in the commit that finishes it.

Usage: python3 .sdlc/ci/invariants.py [--base REF] [--json] [--require-ancestor]   (--require-ancestor: unused since 2.0)
       python3 .sdlc/ci/invariants.py --baseline-tests LOG   (the generated test step, after a failed run: exit 0 when
       every failing test LOG names is in the baseline's Failing tests and the names match the runner's count)
Exits 1 and prints one line per problem. As a pre-commit hook: python3 .sdlc/ci/invariants.py --base HEAD
--json: one JSON document instead, `{result: ok|fail, problems: [{severity, code, message, target?, fix?}]}`, the
message being the line's text after `sdlc invariants: `; codes are stable, for tools to match on.
Stdlib only, Python 3.9+; it imports nothing from the plugin.
"""
import argparse
import glob
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys

SDLC = ".sdlc"
STAGE = re.compile(r"^Current:\s*Stage\s+(\d+)", re.M)


class Problem(str):
    """A problem's text, as printed, carrying its stable code, target and fix for --json."""

    def __new__(cls, code, message, target=None, fix=None):
        p = super().__new__(cls, message)
        p.code, p.target, p.fix = code, target, fix
        return p

    def as_dict(self):
        d = {"severity": "error", "code": self.code, "message": str(self)}
        d.update({k: v for k, v in (("target", self.target), ("fix", self.fix)) if v})
        return d


def git(*args):
    p = subprocess.run(["git", *args], capture_output=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout


def read(path, tolerant=False):
    """A text file's content, or None. `tolerant`: a file a person saves by hand (the baseline, from a Windows
    editor) needn't be UTF-8, so undecodable bytes become U+FFFD instead of an error; the record files stay strict."""
    try:
        with open(path, encoding="utf-8", errors="replace" if tolerant else "strict") as f:
            return f.read().replace("\r\n", "\n")
    except OSError:
        return None


def config():
    """config.json as an object; {} when it's missing, not JSON or not an object."""
    try:
        data = json.loads(read(os.path.join(SDLC, "config.json")) or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def features():
    """{name: (state path, change file)} in either layout; the new one wins a name in both."""
    docs = str(config().get("docs_dir") or "docs/sdlc").strip("/")
    found = {}
    for path in sorted(glob.glob(os.path.join(SDLC, "*", "state.md"))):
        name = os.path.basename(os.path.dirname(path))
        found[name] = (path, os.path.join(os.path.dirname(path), "change.md"))
    for path in sorted(glob.glob(os.path.join(SDLC, "state", "*.md"))):
        found[os.path.basename(path)[:-3]] = (path, os.path.join(docs, "changes", os.path.basename(path)))
    return found


def section(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def check_record(path, stage, build=2, ship=4):
    problems = []
    change = read(path) or ""
    if stage >= build and "## Acceptance tests" not in change:
        problems.append(Problem("no_acceptance_tests", f"{path}: past Define but no `## Acceptance tests` table naming "
                                "each AC's test", path, "add `## Acceptance tests`, one row per AC with its test"))
    if stage >= ship and not section(change, "Review").strip():
        problems.append(Problem("no_review_section", f"{path}: in Ship but no `## Review` section saying what was "
                                "reviewed", path, "write `## Review` in the change file (Review does)"))
    return problems


LOCK_LINE = re.compile(r"^- `([^`]+)` sha256:([0-9a-f]{64})\s*$", re.M)
ROW = re.compile(r"^\s*\|\s*(AC-\d{3})\s*\|(.*?)\|(.*?)\|\s*$", re.M)


def sha256s(path):
    """The file's sha256 as it is, and with its line endings as LF and as CRLF: the lock was written on whichever
    checkout the developer had; None when there's no file."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    lf = data.replace(b"\r\n", b"\n")
    return {hashlib.sha256(d).hexdigest() for d in (data, lf, lf.replace(b"\n", b"\r\n"))}


def app_repos():
    """In a workbench, the app repos cloned inside it (workbench.json, each in a folder named after it): their files
    aren't in the workbench's checkout, so CI can't check them here; each repo's own CI covers its tests."""
    try:
        data = json.loads(read("workbench.json") or "{}")
    except ValueError:
        return ()
    repos = data.get("repos") if isinstance(data, dict) else None
    return tuple(r["name"].strip("/") + "/" for r in repos or [] if isinstance(r, dict) and isinstance(r.get("name"), str))


def check_lock(state_path, state):
    """A test file locked at its red run (`## Test lock`) that changed or was deleted, without a `test-change <file>
    What: … Why: …` deviation naming it. CI can't rerun the red step; the deviation records why it changed."""
    deviations = section(state, "Deviations").splitlines()
    problems = []
    for file, sha in LOCK_LINE.findall(section(state, "Test lock")):
        if file.replace("\\", "/").startswith(app_repos()):
            continue
        now = sha256s(file)
        if now is not None and sha in now:
            continue
        if any(f"test-change {file} " in line and re.search(r"What:\s*\S", line) and re.search(r"Why:\s*\S", line)
               for line in deviations):
            continue
        what = "was deleted" if now is None else "changed"
        problems.append(Problem("test_lock_changed", f"{state_path}: {file} {what} since its red run (## Test lock) "
                                f"and no `test-change {file} What: … Why: …` deviation says why", file,
                                f'add a deviation under ## Deviations: "test-change {file} What: … Why: …"'))
    return problems


def check_test_files(path):
    """Each `## Acceptance tests` row's test file exists; `manual` and `departure D-nnn` rows name none."""
    problems = []
    for ac, test, _ in ROW.findall(section(read(path) or "", "Acceptance tests")):
        test = test.strip().strip("`").strip()
        if test.lower() == "manual" or re.fullmatch(r"departure\s+D-\d{3,}", test, re.I):
            continue
        file = test.split("›")[0].strip().strip("`").strip()
        if file and not file.replace("\\", "/").startswith(app_repos()) and not os.path.exists(file):
            problems.append(Problem("test_file_missing", f"{path}: {ac}: its test file {file} doesn't exist", file))
    return problems


def changed_since(base):
    """Paths changed between `base` and the working tree; None when git can't tell."""
    code, out = git("diff", "--name-only", base)
    return set(out.splitlines()) if code == 0 else None


def baseline_rows(text):
    """{key: count}: failing tests by (package, test), lint by (package, tool, rule, file); placeholder rows skipped."""
    rows = {}
    for heading in ("Failing tests", "Lint and type errors"):
        for line in section(text or "", heading).splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not line.startswith("|") or len(cells) < 2 or set(cells[0]) <= set("-: ") \
                    or cells[0] in ("Package", "—", "-") or cells[1].lower() == "none":
                continue
            if heading == "Failing tests":
                rows[("test", cells[0], cells[1])] = 1
            elif len(cells) >= 5:
                try:
                    count = int(cells[4])
                except ValueError:
                    count = 1
                rows[("lint", *cells[:4])] = count
    return rows


def baseline_path():
    """(path, problem): config's `baseline` read by ship.py's rules (configured_baseline): a blank or non-string value
    is .sdlc/baseline.md, `\\` is `/`, an absolute path in the repo is made relative. Only a regular file the repo
    tracks under exactly that name is read (in a git repo), so the growth check's `git show <base>:<path>` and the
    waiver read the same file: a path that leaves the repo, a link (the file or a folder on the way), a case variant,
    a path into .git or a control character is refused (problem says why) and the check fails."""
    import stat
    import unicodedata
    value = config().get("baseline")
    if not isinstance(value, str) or not value.strip():
        value = SDLC + "/baseline.md"
    path = value.replace("\\", "/")
    fix = "set config's `baseline` to a file the repo tracks, or remove it to use .sdlc/baseline.md"
    if any(unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") for c in path):
        return None, Problem("baseline_refused", "config's `baseline` holds a control character: not read",
                             "baseline", fix)
    leaves = Problem("baseline_refused", f"config's `baseline` ({value}) leaves the repo: not read", "baseline", fix)
    if os.path.isabs(path) or path.startswith("//") or re.match(r"[A-Za-z]:", path):
        # by its text first: resolving a value out of the repo would open it (a UNC path: a remote share)
        for root in (os.getcwd(), os.path.realpath(".")):
            prefix = root.replace("\\", "/").rstrip("/") + "/"
            if os.path.normcase(path).startswith(os.path.normcase(prefix)):
                path = path[len(prefix):]
                break
        else:
            return None, leaves
    path = posixpath.normpath(path)
    if path == ".." or path.startswith(("../", "/")):
        return None, leaves
    parts = path.split("/")  # each folder on the way checked first, so no call follows a link it holds
    if any(os.path.islink("/".join(parts[:i])) for i in range(1, len(parts))):
        return None, Problem("baseline_refused", f"{path} goes through a link: not read", path, fix)
    if not os.path.lexists(path):
        return path, None  # no baseline: nothing listed
    if os.path.islink(path):
        return None, Problem("baseline_refused", f"{path} is a link: not read", path,
                             "make it a regular file: at the base, git reads a link as its target's name")
    if not stat.S_ISREG(os.stat(path).st_mode):  # a FIFO would stall the job
        return None, Problem("baseline_refused", f"{path} isn't a regular file: not read", path, fix)
    try:
        outside_git = git("rev-parse", "--git-dir")[0] != 0
    except OSError:  # git isn't installed (a test job's slim image)
        outside_git = True
    if outside_git:
        return path, None  # not a git repo, or no git (a CI checkout always is one): no growth check to disagree
    code, out = git("ls-files", "-s", "-z", "--", f":(literal){path}")
    entries = [e.split("\t", 1) for e in out.split("\0") if "\t" in e]
    if code or len(entries) != 1 or entries[0][1] != path or entries[0][0].split()[0] not in ("100644", "100755"):
        return None, Problem("baseline_refused", f"{path} isn't a file the repo tracks under that name: not read "
                             "(a folder link, another case, or a path into .git)", path, fix)
    return path, None


def check_baseline(base, deviations):
    path, refused = baseline_path()
    if refused:
        return [refused]
    code, before = git("show", f"{base}:{path}")
    old = baseline_rows(before) if code == 0 else {}
    if not old:
        return []  # no baseline at the base yet: the first fill is the recording, not growth
    problems = []
    for key, count in baseline_rows(read(path, tolerant=True)).items():
        if count <= old.get(key, 0):
            continue
        names = [key[2]] if key[0] == "test" else [key[3], key[4]]
        if not all(n in deviations for n in names):
            what = key[2] if key[0] == "test" else f"{key[3]} in {key[4]}"
            problems.append(Problem("baseline_grew", f"{path}: `{what}` was added or went up without a Deviations "
                                    "entry in a feature's state file naming it", what,
                                    f"name `{what}` in a Deviations line of the feature's state file, with why"))
    return problems


# --baseline-tests: a failed test run passes when only baselined tests failed (ship.py --waive-baseline's rule)
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
    """([names], count): the failing tests a run's output names (pytest, unittest, jest, vitest, go test, node --test)
    and the count the runners' own summaries give; count is None when no summary was found."""
    names, count = [], None
    for pattern in NAMED:
        for m in pattern.finditer(out):
            if m.group(1) not in names:
                names.append(m.group(1))
    for m in re.finditer(r"^(?:FAIL|ERROR): (\w+) \(([\w.]+)\)", out, re.M):  # unittest
        method, where = m.groups()
        name = where if where.endswith("." + method) else f"{where}.{method}"
        if name not in names:
            names.append(name)
    found = [int(n) for p in COUNTED for n in p.findall(out)]
    found += [int(n) for line in PYTEST_SUMMARY.findall(out) for n in re.findall(r"(\d+) (?:failed|errors?)\b", line)]
    found += [int(n) for m in re.finditer(r"^FAILED \(([^)]*)\)", out, re.M)
              for n in re.findall(r"(?:failures|errors)=(\d+)", m.group(1))]
    go = re.findall(r"^\s*--- FAIL: (\S+)", out, re.M)
    for n in go:  # one at a time, as ship.py: a name failing in two packages is one name, counted twice
        if n not in names:
            names.append(n)
    if found or go:
        count = sum(found) + len(go)
    return names, count


def leaves(name):
    """A test's name and its shorter forms: after `::`, ` › `, ` > ` or a dotted name's last `.`; a go subtest's
    parent. The same rule as ship.py --waive-baseline, so CI waives exactly what Ship does."""
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


def check_test_log(log_path):
    """Problems with a failed test run whose output is at log_path: none when every failing test it names is in the
    baseline's Failing tests and the names match the runner's own count."""
    path, refused = baseline_path()
    if refused:
        return [refused]
    listed = [key[2] for key in baseline_rows(read(path, tolerant=True)) if key[0] == "test"]
    try:  # a runner's raw output: cp1252 on a Windows runner, so never a decode error
        with open(log_path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        text = ""
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)  # runners colour their output when CI is set
    names, count = failing_tests(text)
    if not names or count != len(names):
        counted = "no summary count" if count is None else f"its summary counts {count}"
        return [Problem("baseline_unmatched", f"the test run failed and its output named {len(names)} failing test(s) "
                        f"while {counted}, so it can't be matched to {path}", log_path,
                        "fix the failing tests, or use a runner whose report names each failure")]
    listed_leaves = set().union(*(leaves(cell) for cell in listed)) if listed else set()
    unlisted = [n for n in names if not leaves(n) & listed_leaves]
    return [Problem("baseline_test_failed", f"failing test not in {path}: {n}", n,
                    "fix it; adding it to the baseline needs the user's OK and a Deviations line") for n in unlisted]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", help="the commit to compare the baseline against")
    ap.add_argument("--baseline-tests", metavar="LOG",
                    help="a failed test run's output: pass when every failing test it names is in the baseline")
    ap.add_argument("--json", action="store_true", help="one JSON document: result and each problem's code")
    ap.add_argument("--require-ancestor", action="store_true", help="accepted for old CI workflows; unused since 2.0")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # file names and messages aren't ASCII; Windows consoles default to cp1252
    if a.baseline_tests:  # the generated test step's check, from any package folder: the repo is two folders up
        log = os.path.abspath(a.baseline_tests)
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        problems = check_test_log(log)
        if a.json:
            print(json.dumps({"result": "fail" if problems else "ok", "problems": [p.as_dict() for p in problems]},
                             indent=2, ensure_ascii=False))
            return 1 if problems else 0
        for line in problems:
            print(f"sdlc invariants: {line}")
        if not problems:
            print("sdlc invariants: every failing test is listed in the baseline; this run passes")
        return 1 if problems else 0
    problems, deviations = [], ""
    changed = changed_since(a.base) if a.base else None
    for name, (state_path, change_path) in features().items():
        state = read(state_path) or ""
        deviations += section(state, "Deviations")  # any feature's: one may record it and finish in the same push
        active = re.search(r"^Status:\s*active\b", state, re.M)
        # Ship marks the feature done in its own commit, so the push that finishes it is checked too
        if active or (changed and state_path.replace(os.sep, "/") in changed):
            problems += check_lock(state_path, state)
        if not active:
            continue
        stage = STAGE.search(state)
        # a feature not yet migrated to Process: 3 (sdlc 2.x) still counts Build as 4 and Ship as 8
        current = re.search(r"^Process:\s*3\b", state, re.M)
        build, ship = (2, 4) if current else (4, 8)
        stage = int(stage.group(1)) if stage else 0
        problems += check_record(change_path, stage, build, ship)
        if stage >= build:
            problems += check_test_files(change_path)
    if a.base:
        problems += check_baseline(a.base, deviations)
    if a.json:
        print(json.dumps({"result": "fail" if problems else "ok", "problems": [p.as_dict() for p in problems]},
                         indent=2, ensure_ascii=False))
        return 1 if problems else 0
    for line in problems:
        print(f"sdlc invariants: {line}")
    if not problems:
        print("sdlc invariants: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
