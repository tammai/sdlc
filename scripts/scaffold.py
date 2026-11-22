#!/usr/bin/env python3
"""sdlc scaffold bookkeeping: the deterministic half of /sdlc:setup, /sdlc:upgrade and /sdlc:eject.

Claude makes the judgment calls (what to generate, how to merge an edited file); this script owns the
records so they stay exact:
  .sdlc/config.json          human-editable project overrides on top of the plugin's
                             templates/project/config.defaults.json (deep-merged, project wins; lists replace)
  .sdlc/scaffold.lock.json   machine-only: scaffold_version, file hashes + classes, keyed-merge entries,
                             applied/skipped migrations, setup progress

Every command prints one JSON object. Exit 0 = ok, 1 = error ({"error": ...}), 2 = refused (file was edited).
Usage: python3 scaffold.py [--root DIR] <command> [args]   (see `python3 scaffold.py -h`)
Stdlib only, Python 3.9+.
"""
import argparse
import copy
import functools
import glob
import hashlib
import json
import os
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

# The resolver sits beside the hooks; found from this file, not CLAUDE_PLUGIN_ROOT (tests point that at a fake plugin)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks"))
import sdlc_layout  # noqa: E402
import sdlc_scopes  # noqa: E402

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = ".sdlc/config.json"
LOCK = ".sdlc/scaffold.lock.json"
SCRATCH = ".sdlc/.work"  # gitignored scratch: the lock's and config's temp copies go here while they're saved
SETTINGS = ".claude/settings.json"
LOCAL_SETTINGS = ".claude/settings.local.json"
GITIGNORE = ".gitignore"
PLUGIN_MERGE = LOCAL_SETTINGS + "#plugin"  # lock key for the plugin-enablement keys we add to settings.local.json
TEAM_PLUGIN_MERGE = SETTINGS + "#plugin"  # the ones enable-plugin --team (or a setup before 2.0.1) added there
MARKETPLACE = ("sdlc", {"source": {"source": "github", "repo": "tammai/sdlc"}})
PLUGIN_KEY = "sdlc@sdlc"
AGENTS = "AGENTS.md"
AGENTS_MERGE = AGENTS + "#sdlc"  # lock key for the managed block in AGENTS.md
FILE_CLASSES = ("generated", "seeded")
DEFAULTS = "templates/project/config.defaults.json"
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*(?:\|\s*([a-z_]+)\s*)?\}\}")


class Refused(Exception):
    pass


class CommandsFailed(Exception):
    """run-commands: some command couldn't start; carries the full result for the JSON output."""


# --- io ---------------------------------------------------------------------------

def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        raise ValueError(f"{path} is not valid JSON: {e}")


def check_writable(target, shown=None):
    """Refuses a file its owner protected (the read-only attribute, a mode, or a Windows ACL that `os.access` can't
    see), as the in-place `open('w')` did: it opens the file for writing without truncating, then closes it."""
    try:
        with open(target, "r+b"):
            pass
    except PermissionError:
        raise PermissionError(f"{shown or target} is protected from writing; not written") from None


def write_json(path, data, scratch=None):
    """Atomically, so a command reading it meanwhile (every save re-reads the lock) never sees half a file; through a
    link to the file it names, keeping that file's mode, in the platform's line endings: as the in-place write did. On
    Windows a reader holding the file open makes the rename fail for a moment: retry. `scratch`: a folder beside the
    file for its temp copy (the lock's and config's go in `.sdlc/.work/`, gitignored, so a kill leaves nothing to
    commit); used only when the file is where its path says, not linked elsewhere."""
    target = os.path.realpath(path)
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    temp_dir = None
    # scratch only once it exists (setup's gitignore step, or the first scratch file, makes it): a new repo's first
    # save never creates a folder git would commit; a file in its place, or none, puts the temp beside the file
    if scratch and os.path.isdir(scratch) and os.path.dirname(os.path.realpath(scratch)) == os.path.dirname(target):
        _sweep_temps(os.path.dirname(target))  # an earlier version made its temp copies beside the file
        temp_dir = scratch
    try:
        mode = stat.S_IMODE(os.stat(target).st_mode)
    except FileNotFoundError:
        mode = None  # a new file: what an ordinary create gives (0666 less the umask)
    if mode is not None:
        check_writable(target, path)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    for attempt in range(50):
        try:
            return _write_atomic(target, text, newline=None, mode=mode, temp_dir=temp_dir)
        except OSError as e:
            if temp_dir:  # scratch on another device or not writable: the temp goes beside the file, as before
                temp_dir = None
                continue
            if not getattr(e, "during_replace", False):  # a refusal that won't clear (a folder, a protection)
                raise
            if os.name != "nt" or attempt == 49:
                raise
            time.sleep(0.05)


UNREADABLE = "unreadable"  # sha256 of a path that exists but can't be read: never a hash, so it matches no record


def sha256(path):
    try:
        with open(path, "rb") as f:
            # CRLF counts as LF: git (core.autocrlf) checks out CRLF on Windows, and the lock holds LF hashes
            return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    except FileNotFoundError:
        return None
    except OSError:  # a folder, a looping link: matches no recorded hash ("" included); file_state lists it outside
        return UNREADABLE


@functools.lru_cache(maxsize=64)
def _real_root(root):
    return os.path.realpath(root)  # once per process: status checks every tracked file at each session start


def inside_repo(root, path):
    """Whether `path` (repo-relative or absolute) resolves inside `root` after links: the one check every reader and
    writer of a recorded path uses (another drive counts as outside)."""
    real_root = _real_root(root)
    try:
        return os.path.commonpath([real_root, os.path.realpath(os.path.join(root, path))]) == real_root
    except ValueError:
        return False


def rel(root, path):
    r = os.path.relpath(os.path.join(root, path), root).replace(os.sep, "/")
    if r == ".." or r.startswith("../"):
        raise ValueError(f"{path} is outside the project root")
    return r


# --- versions -----------------------------------------------------------------------

def parse_version(v):
    """(major, minor, patch, release, n): a pre-release (`3.5.0-rc.2`) is (3, 5, 0, 0, 2) and sorts before its
    release (3, 5, 0, 1, 0), so a repo upgraded with rc.1 is behind rc.2 and 3.5.0."""
    m = re.match(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-(?:[0-9A-Za-z.]*?(\d+)|[0-9A-Za-z.]*))?", str(v or "").strip())
    if not m:
        raise ValueError(f"not a version: {v!r}")
    pre = "-" in m.group(0)
    return (*(int(x or 0) for x in m.groups()[:3]), 0 if pre else 1, int(m.group(4) or 0))


def deep_merge(base, override):
    out = dict(base)
    for k, v in override.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def effective_config(config):
    return deep_merge(read_json(os.path.join(PLUGIN_ROOT, DEFAULTS), {}), config or {})


def plugin_version():
    manifest = read_json(os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json"), {})
    return manifest.get("version", "0.0.0")


# --- project state ---------------------------------------------------------------------

LOCK_KINDS = {dict: "an object", list: "a list", str: "a string", bool: "true or false"}
LOCK_SHAPE = {"scaffold_version": str, "files": dict, "declined": list, "merged": dict, "migrations": dict,
              "setup": dict, "command_runs": dict, "hosts": list}  # every key a command reads (conventions: per entry)
LOCK_NESTED = {"setup": {"kind": str, "completed_steps": list, "pending": dict, "complete": bool},
               "migrations": {"applied": list, "skipped": dict}}


def check_lock(lock):
    """The lock's shape, checked the first time anything reads it (it is repo data, read like input). Null fields
    read as empty; `conventions` items are checked per entry where they're read, so one bad entry is that item's
    error in the upgrade plan."""
    def bad(what):
        return ValueError(f"{LOCK}: {what}; fix it, or restore it from git")

    def fields(obj, shape, where):  # each key: absent or null reads as its reader's default, else the right type
        for key, kind in shape.items():
            if obj.get(key) is None:
                obj.pop(key, None)
            elif not isinstance(obj[key], kind):
                raise bad(f"'{where}{key}' must be {LOCK_KINDS[kind]}")

    if not isinstance(lock, dict):
        raise bad("not a JSON object")
    fields(lock, LOCK_SHAPE, "")
    lock.setdefault("files", {})
    lock.setdefault("declined", [])
    for key, shape in LOCK_NESTED.items():
        if key in lock:
            fields(lock[key], shape, key + ".")
    for where, paths in (("files", lock["files"]), ("declined", lock["declined"])):
        for path in paths:  # eject deletes and status hashes these: relative, and inside the repo
            if not isinstance(path, str) or relative_root(path) in (None, "."):
                raise bad(f"'{where}' names {path!r}, which isn't a relative path inside the project")
    for path, e in lock["files"].items():
        if not isinstance(e, dict) or not isinstance(e.get("class"), str):
            raise bad(f"'files' entry {path!r} must be an object with a string 'class'")
        problem = template_problem(e["template"]) if e.get("template") is not None else None
        if problem:
            raise bad(f"'files' entry {path!r}: {problem}")
        if git_internal(path):
            raise bad(f"'files' names {path!r}, under .git/, which the plugin never writes")
        if not all(isinstance(e.get(k), (str, type(None))) for k in ("sha256", "template", "render_sha256")):
            raise bad(f"'files' entry {path!r}: 'sha256', 'template' and 'render_sha256' must be strings")
    strings = [("declined", lock["declined"]), ("hosts", lock.get("hosts", [])),
               ("setup.completed_steps", lock.get("setup", {}).get("completed_steps", [])),
               ("migrations.applied", lock.get("migrations", {}).get("applied", []))]
    for where, items in strings:
        if not all(isinstance(x, str) for x in items):
            raise bad(f"every '{where}' item must be a string")
    if not all(isinstance(v, list) for v in lock.get("merged", {}).values()):
        raise bad("every 'merged' value must be a list")
    for scope, steps in lock.get("command_runs", {}).items():  # contract and doctor read every run
        if not isinstance(steps, dict) or not all(isinstance(r, dict) for r in steps.values()):
            raise bad(f"'command_runs.{scope}' must be an object of runs")
    return lock


_ABSENT = object()


def check_config(config):
    if not isinstance(config, dict):
        raise ValueError(f"{CONFIG} is not a JSON object (changed while this command ran?); not saved")


LOCK_RECORDS = ("files", "conventions", "command_runs")  # sections whose entries are records, merged whole


def merge_into(base, ours, theirs, whole=False, records=False, top=True):
    """Another command's changes (`theirs`, the lock on disk now, against `base`, the lock as this command read it)
    applied into this command's copy `ours`, in place: an object or list this command holds stays the one it saves,
    so a later change through that reference (a rollback) still lands. Objects merge key by key and lists by item,
    except a record (an entry of a LOCK_RECORDS section, such as one file's record): where both changed it, this
    command's wins whole, as every save did before. A key both added starts from empty. Returns the merged value."""
    if theirs == base:
        return ours
    if isinstance(ours, dict) and isinstance(theirs, dict) and not whole:
        base = base if isinstance(base, dict) else {}
        for key in [k for k in ours if k in base and k not in theirs and ours[k] == base[k]]:
            del ours[key]  # they removed it, this command left it alone
        for key, value in theirs.items():
            was = base.get(key, _ABSENT)
            if value == was:
                continue  # they didn't change it
            if key not in ours:
                if was is _ABSENT:
                    ours[key] = value  # they added it
                continue  # this command removed what they changed: this command's wins
            ours[key] = merge_into(was, ours[key], value, whole=records, records=top and key in LOCK_RECORDS,
                                   top=False)
        return ours
    if isinstance(ours, list) and isinstance(theirs, list) and not any(
            isinstance(x, (dict, list)) for x in ours + theirs):  # a list of objects merges whole (below)
        base = base if isinstance(base, list) else []
        ours[:] = [x for x in ours if not (x in base and x not in theirs)]  # what they removed
        ours.extend(x for x in theirs if x not in base and x not in ours)  # what they added
        return ours
    if ours != base:
        return ours  # both changed it: this command's wins whole
    if isinstance(ours, list) and isinstance(theirs, list):
        ours[:] = theirs  # theirs, in the object this command holds
        return ours
    if isinstance(ours, dict) and isinstance(theirs, dict):
        ours.clear()
        ours.update(theirs)
        return ours
    return theirs


class Project:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        for rel in (CONFIG, LOCK):  # committed: a link out of the repo or into .git is never read or written
            problem = link_problem(self.root, rel)
            if problem:
                raise ValueError(problem)
        self._config, self._config_checked = read_json(self.path(CONFIG)), False
        self._config_read = copy.deepcopy(self._config)  # save writes config.json only when this command changed it
        raw = read_json(self.path(LOCK), _ABSENT)
        # a lock file holding JSON null exists: it is refused like any other non-object, never read as absent
        self._lock_null = raw is None
        self._lock, self._checked, self._base, self._fresh = (None if raw is _ABSENT else raw), False, None, False

    @property
    def lock(self):
        """The lock, shape-checked on first read, so every reader gets the check (None when there is none). The
        copy taken then is what `save` merges this command's changes against."""
        if self._lock_null:
            check_lock(None)
        if self._lock is not None and not self._checked:
            check_lock(self._lock)
            self._checked = True
            if not self._fresh:  # read from disk: what save merges this command's changes against
                self._base = copy.deepcopy(self._lock)
        return self._lock

    @lock.setter
    def lock(self, value):  # a new lock (init) or none (eject): checked like any, nothing to merge against
        self._lock, self._checked, self._base, self._lock_null, self._fresh = value, False, None, False, True

    @property
    def config(self):
        """config.json, checked on first read: a JSON object (None when there is none)."""
        if self._config is not None and not self._config_checked:
            if not isinstance(self._config, dict):
                raise ValueError(f"{CONFIG} is not a JSON object; fix it, or restore it from git")
            self._config_checked = True
        return self._config

    @config.setter
    def config(self, value):
        self._config, self._config_checked = value, False

    def lock_exists(self):
        """Whether a lock file is there, whatever its shape (init refuses over one unless --force)."""
        return self._lock is not None or self._lock_null

    def path(self, p):
        return os.path.join(self.root, p)

    def require_lock(self):
        if self.lock is None:
            raise ValueError(f"no {LOCK}; run `init` first")
        return self.lock

    def save(self):
        """Writes the lock only when this command set it (init) or read and changed it, and config.json only when this
        command changed it: an untouched file stays exactly as it is on disk, whatever another command saved."""
        # every check and merge first, then the writes: a refusal leaves both files as they were
        lock_changed = self._lock is not None and (self._fresh or (self._checked and self._lock != self._base))
        config_changed = self._config is not None and self._config != self._config_read
        if config_changed and isinstance(self._config_read, dict):  # read from disk: merge onto it now, like the lock
            self._merge_onto_disk(CONFIG, self._config_read, self.config, check_config, top=False)
        if config_changed and lock_changed:  # a config that will refuse the write refuses before the lock is written
            target = os.path.realpath(self.path(CONFIG))
            if os.path.exists(target):
                check_writable(target, CONFIG)
        if lock_changed:
            before = copy.deepcopy(self._lock)
            lock = self.merged_lock()
            try:
                write_json(self.path(LOCK), lock, scratch=self.path(SCRATCH))
            except BaseException:  # not written: undo the merge in place, so only this command's changes remain
                merge_into(copy.deepcopy(self._lock), self._lock, before)
                raise
            self._base, self._fresh = copy.deepcopy(self._lock), False  # written: later saves merge against it
        if config_changed:
            write_json(self.path(CONFIG), self.config, scratch=self.path(SCRATCH))
            self._config_read = copy.deepcopy(self._config)

    def merged_lock(self):
        """The lock to write: this command's changes merged onto the file as it is now, when another command saved
        since this one read it. A lock removed meanwhile (eject) is not recreated."""
        if self._base is None:
            return self.lock  # a new lock (init): checked, so it is written in the checked shape
        self._merge_onto_disk(LOCK, self._base, self._lock, check_lock)
        return self._lock  # the base moves on only once this is written (save)

    def _merge_onto_disk(self, name, base, ours, check, top=True):
        """This command's changes (`ours` against `base`, the file as it read it) merged onto the file as it is on
        disk now. Removed or broken meanwhile: an error, never recreated or overwritten with this command's older
        copy (eject removes the lock)."""
        disk = read_json(self.path(name), _ABSENT)
        if disk is _ABSENT:
            raise ValueError(f"{name} was removed while this command ran; not saved")
        check(disk)
        if disk != base:
            merge_into(base, ours, disk, top=top)

    @staticmethod
    def merged(entry):
        """The recorded text isn't the template's own render: the user's edits merged in (upgrade's "apply merge")."""
        return bool(entry.get("render_sha256")) and entry.get("render_sha256") != entry.get("sha256")

    def untracked(self, path):
        """Whether git doesn't track the repo file `path` (outside a git repo: False, nothing to tell apart). A
        committed lock entry can name a local file git never saw (`.env`, a key): one that differs from the lock is the
        user's, so it's offered, never rendered over or deleted."""
        def git(*args):  # literal pathspecs: a `*` or `:!` in a recorded name is just a character
            return subprocess.run(["git", "--literal-pathspecs", "-C", self.root, *args], capture_output=True,
                                  encoding="utf-8", errors="replace")
        # In a repo, at its top or below it (a monorepo package): a `.git` here or in any parent, or GIT_DIR set. When
        # git can't answer there, every file counts as untracked (fail closed), never as tracked
        repo = bool(os.environ.get("GIT_DIR"))
        for d in {os.path.abspath(self.root), os.path.realpath(self.root)}:  # the real parents too: git walks those
            while not repo:
                repo = os.path.lexists(os.path.join(d, ".git"))
                if os.path.dirname(d) == d:
                    break
                d = os.path.dirname(d)
        try:
            if git("rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
                return repo  # a repo git refuses (safe.directory, a bad GIT_DIR): count it untracked, so it's kept
            return git("ls-files", "--error-unmatch", "--", path).returncode != 0
        except OSError:  # no git at all
            return repo

    def file_state(self, path, entry):
        if not inside_repo(self.root, path):  # through a link out of the repo: never read (a device, a huge file)
            return "outside"
        actual = sha256(self.path(path))
        if actual is None:
            return "missing"
        if actual == UNREADABLE:  # a folder or a looping link where the file was: listed, never read, written or deleted
            return "outside"
        return "unchanged" if actual == entry.get("sha256") else "modified"


# --- commands ----------------------------------------------------------------------------

def cmd_init(p, a):
    if p.lock_exists() and not a.force:  # whatever its shape: --force restarts over one
        raise ValueError(f"{LOCK} already exists (setup started or done); use status, or --force to restart")
    version = plugin_version()
    host = valid_host(a.host) if a.host else detect_host()["host"]
    if host is None:
        raise ValueError("can't tell which coding agent is running setup; pass --host "
                         f"({', '.join(HOSTS)})")
    # A restart (--force) keeps the location already recorded unless one is given: documents may already be there
    docs = sdlc_layout.validate_docs_dir(a.docs_dir or sdlc_layout.docs_dir(p.root) or sdlc_layout.DOCS_DEFAULT)
    if p._config is not None and not isinstance(p._config, dict) and not a.force:
        raise ValueError(f"{CONFIG} is not a JSON object; fix it, or pass --force to start it again")
    if not isinstance(p._config, dict):  # none, or (--force) one that isn't an object: overrides only, as new
        p.config = {"min_plugin_version": version, "project": {"kind": a.kind}}
    # Features from before setup stay where they are until `relocate` moves them: never a half-moved repo
    legacy = [os.path.basename(os.path.dirname(x)) for x in sorted(glob.glob(p.path(".sdlc/*/state.md")))]
    if not legacy:
        p.config["docs_dir"] = docs
    p.lock = {"scaffold_version": version, "hosts": [host], "files": {}, "merged": {},
              "migrations": {"applied": [], "skipped": {}},
              "setup": {"kind": a.kind, "completed_steps": [], "complete": False}}
    p.save()
    return {"initialized": True, "scaffold_version": version, "host": host, "kind": a.kind,
            "docs_dir": p.config.get("docs_dir"),
            "legacy_features": legacy}


def team_rules(p):
    """The repo's own hookify rules (not sdlc-*): their messages reach the model, so they're shown, not trusted."""
    rules = []
    for path in sorted(glob.glob(p.path(".claude/hookify/*.md"))):
        name = os.path.basename(path)
        # A symlink could pull any local file into the model's context through this listing
        if name.startswith("sdlc-") or os.path.islink(path):
            continue
        text, why = repo_text(p.root, f".claude/hookify/{name}", 8192)
        if why:
            continue  # doctor's hookify row names it
        front, _, body = text.partition("\n---")
        field = lambda k: (re.search(rf"^{k}:\s*(\S+)", front, re.M) or [None, None])[1]
        rules.append({"file": f".claude/hookify/{name}", "event": field("event"), "action": field("action") or "warn",
                      "enabled": (field("enabled") or "true").lower() != "false",
                      "message": body.strip()[:200]})
    return rules


DOCS_SITE_MARKERS = ("docusaurus.config.js", "docusaurus.config.ts", "docusaurus.config.mjs", "mkdocs.yml",
                     "mkdocs.yaml", "docs/.vitepress", "docs/conf.py")


def docs_site(p):
    """The file that shows the repo builds a site from docs/ (so docs/sdlc would be published), or None."""
    for marker in DOCS_SITE_MARKERS:
        if os.path.exists(p.path(marker)):
            return marker
    astro = sorted(glob.glob(p.path("astro.config.*")))
    if astro and os.path.isdir(p.path("src/content/docs")):
        return os.path.basename(astro[0])
    return None


def cmd_status(p, a):
    pv = plugin_version()
    out = {"plugin_version": pv, "configured": p.config is not None, "team_rules": team_rules(p),
           "docs_site": docs_site(p), "layout": sdlc_layout.paths(p.root)["layout"]}
    if p.lock is None:
        out.update(setup="none", drift=None)
        return out
    sv = p.lock.get("scaffold_version", "0.0.0")
    minv = (p.config or {}).get("min_plugin_version", "0.0.0")
    if parse_version(pv) < parse_version(minv):
        drift = "plugin_too_old"
    elif parse_version(sv) < parse_version(pv):
        drift = "behind"
    elif parse_version(sv) > parse_version(pv):
        drift = "ahead"
    else:
        drift = "current"
    setup = p.lock.get("setup", {})
    out.update(setup="complete" if setup.get("complete") else "in_progress",
               completed_steps=setup.get("completed_steps", []), pending_steps=setup.get("pending", {}),
               scaffold_version=sv, min_plugin_version=minv, drift=drift,
               pending_migrations=[m["id"] for m in pending_migrations(p)],
               files={path: {"class": e["class"], "state": p.file_state(path, e)}
                      for path, e in sorted(p.lock.get("files", {}).items())})
    return out


def cmd_paths(p, a):
    return sdlc_layout.paths(p.root, a.name)


def cmd_config(p, a):
    return {"config": effective_config(p.config), "overrides": p.config or {}}


def cmd_step_done(p, a):
    """Records a setup step done, or with --pending held open for a reason (impeccable loading next session): a
    pending step isn't done, so a resumed setup runs it again, and the setup can't be marked complete until it is."""
    setup = p.require_lock().setdefault("setup", {"completed_steps": [], "complete": False})
    setup.setdefault("completed_steps", [])
    pending = setup.setdefault("pending", {})
    if a.pending:
        pending[a.step] = a.pending
        if a.step in setup["completed_steps"]:
            setup["completed_steps"].remove(a.step)
    else:
        pending.pop(a.step, None)
        if a.step not in setup["completed_steps"]:
            setup["completed_steps"].append(a.step)
    if not pending:
        setup.pop("pending")
    if a.complete:
        if pending:
            p.save()
            raise Refused("steps still pending: " + "; ".join(f"{k} ({v})" for k, v in pending.items()))
        setup["complete"] = True
    p.save()
    out = {"completed_steps": setup["completed_steps"], "complete": setup.get("complete", False)}
    if pending:
        out["pending"] = pending
    return out


def cmd_record(p, a):
    files = p.require_lock()["files"]
    recorded = {}
    # as render takes it: a shell loop's trailing `\r` and a Windows separator are not part of the name
    template = cli_template(a.template) if a.template is not None else None
    for path in a.paths:
        r = rel(p.root, path)
        if git_internal(r, p.root):
            raise Refused(f"{r} is in a .git folder (or links into one), which the plugin never records")
        if not inside_repo(p.root, r):
            raise Refused(f"{r} resolves outside the project through a link; not recorded")
        h = sha256(p.path(r))
        if h is None:
            raise ValueError(f"cannot record {r}: file does not exist")
        if h == UNREADABLE:
            raise Refused(f"{r} isn't a readable file (a folder or a looping link); not recorded")
        entry = files.get(r, {})
        entry.update({"class": a.cls, "sha256": h})
        if template:
            problem = template_problem(template)
            if problem or not template_exists(template):
                raise Refused(problem or f"no template {template!r} in the plugin; not recorded")
            entry["template"] = template
            # what the plugin would have written: a text that differs holds the user's edits (Project.merged)
            entry["render_sha256"] = hashlib.sha256(render_source(template, p).encode("utf-8")).hexdigest()
        files[r] = entry
        recorded[r] = entry
    p.save()
    return {"recorded": recorded}


def cmd_forget(p, a):
    """Hand files to the user for good: untracked, and never re-added by an upgrade."""
    lock = p.require_lock()
    files = lock["files"]
    declined = lock["declined"]
    forgotten = []
    for x in a.paths:
        path = rel(p.root, x)
        if files.pop(path, None) is not None:
            forgotten.append(path)
        if path not in declined:
            declined.append(path)
    p.save()
    return {"forgotten": forgotten, "declined": declined}


DESIGN_MODES = ("builtin", "impeccable")
# impeccable's detector hook checks the same thing after every UI edit, so in that mode this one isn't installed
IMPECCABLE_REPLACES = "sdlc-ui-hardcoded-values.md"


def design_mode(p):
    """Who does UI design work (config `design`): `builtin` (sdlc's design system, rule and guardrail, the default)
    or `impeccable` (the impeccable skill, with sdlc keeping the gates)."""
    mode = (p.config or {}).get("design") if p else None
    return mode if mode in DESIGN_MODES else "builtin"


def shipped_files(p=None):
    """(template, dest, class) for every plugin file setup always installs: policy rules and guardrails.
    Lint snippets and CI are left out: setup adds those only by choice."""
    skip = IMPECCABLE_REPLACES if design_mode(p) == "impeccable" else None
    out = []
    rules = os.path.join(PLUGIN_ROOT, "templates", "project", "rules")
    for name in sorted(os.listdir(rules)) if os.path.isdir(rules) else []:
        if name.endswith(".md"):
            dest = name if name == "sdlc.md" else f"sdlc-{name}"
            out.append((f"templates/project/rules/{name}", f".claude/rules/{dest}", "generated"))
    hookify = os.path.join(PLUGIN_ROOT, "templates", "project", "hookify")
    for name in sorted(os.listdir(hookify)) if os.path.isdir(hookify) else []:
        if name.startswith("sdlc-") and name.endswith(".md") and name != skip:
            out.append((f"templates/project/hookify/{name}", f".claude/hookify/{name}", "seeded"))
    return out


def guardrail_list(p):
    return [(t, d) for t, d, cls in shipped_files(p) if t.startswith("templates/project/hookify/")]


def cmd_guardrails(p, a):
    """The guardrails setup renders for this repo's design mode. With --render, writes every one itself, seeded and
    recorded, in one call: setup's step used to loop over this list in the shell, and on Windows a `\\r` on each
    path made every render fail unseen (3.12.0 smoke C3). A guardrail the user edited, a file the plugin never
    wrote, and one the user declined (`forget`) are left as they are."""
    listed = guardrail_list(p)
    out = {"design": design_mode(p), "guardrails": [{"template": t, "dest": d} for t, d in listed]}
    if not a.render:
        return out
    lock = p.require_lock()
    if "claude-code" not in hosts(p):
        raise Refused("guardrails are Claude Code's (.claude/hookify/); this repo isn't set up for Claude Code, so "
                      "other agents get the rules through AGENTS.md")
    if cmd_status(p, None)["drift"] == "behind":
        raise Refused("the scaffold is behind the plugin: /sdlc:upgrade brings the guardrails forward on its branch, "
                      "with the version and migrations; --render is setup's")
    groups = {k: [] for k in ("rendered", "kept", "deleted", "declined", "outside", "failed", "unrecorded")}
    for template, dest in listed:
        entry = lock["files"].get(dest)
        state = p.file_state(dest, entry) if entry else None
        if dest in lock["declined"]:
            groups["declined"].append(dest)
        elif state == "missing":  # the plugin wrote it and the user deleted it: theirs to bring back (upgrade offers)
            groups["deleted"].append(dest)
        elif state == "outside" or not inside_repo(p.root, dest):
            groups["outside"].append(dest)
        else:
            before = copy.deepcopy(lock["files"].get(dest))
            try:  # cmd_render's own rules and write, recorded as it goes: a later failure loses nothing written
                cmd_render(p, argparse.Namespace(template=template, dest=dest, cls="seeded", if_unchanged=True))
                groups["rendered"].append(dest)
            except Refused:  # edited by the user, or a file the plugin never wrote: left as it is
                groups["kept"].append(dest)
            except Exception as e:  # one guardrail's error (I/O, a template value) never stops the others
                written = lock["files"].get(dest) != before  # cmd_render set the entry, then the lock save failed
                groups["unrecorded" if written else "failed"].append(
                    f"{dest} ({getattr(e, 'strerror', None) or e or type(e).__name__})")
    out.update({k: v for k, v in groups.items() if v or k not in ("failed", "unrecorded")})
    if groups["failed"] or groups["unrecorded"]:
        out["error"] = "; ".join(x for x in (
            "could not write: " + "; ".join(groups["failed"]) if groups["failed"] else "",
            "written but the lock couldn't be saved (run --render again once .sdlc/scaffold.lock.json is writable): "
            + "; ".join(groups["unrecorded"]) if groups["unrecorded"] else "") if x)
        raise CommandsFailed(out)
    return out


def skill_dirs(root):
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    dirs = [os.path.join(root, d) for d in (".claude", ".agents", ".cursor", ".agent")]
    return dirs + [config, os.path.join(os.path.expanduser("~"), ".agents")]


def skill_folder_installed(root, name):
    """A skill in the project's or the user's agent skill folders: those load in every session, nothing to enable."""
    return any(os.path.isfile(os.path.join(d, "skills", name, "SKILL.md")) for d in skill_dirs(root))


def plugin_ids(name):
    """The installed Claude Code plugin ids named `name`, from any marketplace."""
    return [k for k in installed_plugins() if k.split("@")[0] == name]


def skill_installed(root, name):
    """Whether a skill is installed for this repo: in the agent skill folders, or as a Claude Code plugin of that
    name, enabled or not. File existence only; `plugin_enabled` says whether a plugin loads here."""
    return skill_folder_installed(root, name) or bool(plugin_ids(name))


def plugin_enabled(root, plugin_id):
    """Whether Claude Code loads the plugin in this repo: `enabledPlugins` in the user's settings, then the project's
    committed and local ones (each overrides the one before). Not listed anywhere means off."""
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    on = None
    for data in (read_json(os.path.join(config, "settings.json"), {}), read_fixed_json(root, SETTINGS, {}),
                 read_fixed_json(root, LOCAL_SETTINGS, {})):
        plugins = data.get("enabledPlugins")
        if isinstance(plugins, dict) and plugin_id in plugins:
            on = plugins[plugin_id] is True
    return bool(on)


def impeccable_hook_off(root):
    """impeccable's own off switch for its detector hook (`/impeccable hooks off`): `hook.enabled: false` in
    `.impeccable/config.json` or the machine's `config.local.json`, the later winning. The committed one is read
    through sdlc_scopes.read_repo_text: a link out of the repo or into .git reads as absent."""
    off = False
    for name in ("config.json", "config.local.json"):
        if name == "config.json":
            text = sdlc_scopes.read_repo_text(root, ".impeccable/config.json")
            try:
                data = json.loads(text) if text is not None else {}
            except json.JSONDecodeError as e:
                raise ValueError(f"{os.path.join(root, '.impeccable', name)} is not valid JSON: {e}")
        else:
            data = read_json(os.path.join(root, ".impeccable", name), {})
        hook = data.get("hook") if isinstance(data, dict) else None
        if isinstance(hook, dict) and "enabled" in hook:
            off = hook["enabled"] is False
    return off


def impeccable_hook_wired(root):
    """A skill-folder install's detector hook is a manifest `/impeccable hooks on` writes into the Claude Code
    settings (the plugin ships its own); look for its hook.mjs in either file."""
    for rel in (LOCAL_SETTINGS, SETTINGS):
        hooks = read_fixed_json(root, rel, {}).get("hooks")
        if "impeccable" in json.dumps(hooks or {}) and "hook.mjs" in json.dumps(hooks or {}):
            return True
    return False


def impeccable_status(root):
    """Where impeccable stands for this repo: `state` is `missing`, `disabled` (a Claude Code plugin installed but
    not turned on here, so none of its commands load) or `enabled`; `hook` is whether its detector hook runs here,
    which is what may replace sdlc's UI guardrail. A disabled plugin names the `plugin` id sdlc can turn on."""
    ids = plugin_ids("impeccable")
    on = [i for i in ids if plugin_enabled(root, i)]
    if on:
        return {"state": "enabled", "via": "plugin", "plugin": on[0], "hook": not impeccable_hook_off(root)}
    if skill_folder_installed(root, "impeccable"):
        return {"state": "enabled", "via": "skill",
                "hook": impeccable_hook_wired(root) and not impeccable_hook_off(root)}
    if ids:
        return {"state": "disabled", "via": "plugin", "plugin": ids[0], "hook": False,
                "enable": f"scaffold.py design impeccable --enable (or claude plugin enable {ids[0]} --scope local)"}
    return {"state": "missing", "hook": False}


def impeccable_installed(root):
    return skill_installed(root, "impeccable")


def cmd_design(p, a):
    """Who does UI design work; with a mode, records it in config (`design`). sdlc never installs impeccable; with
    --enable it turns an installed impeccable plugin on for this repo, on this machine (a keyed merge into
    .claude/settings.local.json that `enable-plugin --remove` and eject take back). Claude Code loads plugins at
    session start, so impeccable's commands, and its detector hook, arrive next session."""
    if a.mode and a.mode not in DESIGN_MODES:
        raise Refused(f"design is one of {', '.join(DESIGN_MODES)}, not {a.mode!r}")
    out = {}
    if a.enable:
        status = impeccable_status(p.root)
        if status["state"] == "missing":
            raise Refused("impeccable isn't installed on this machine: sdlc never installs it "
                          "(npx impeccable install, or /plugin marketplace add pbakaus/impeccable)")
        if status["state"] == "disabled":
            p.require_lock()
            off_in = [rel for rel in (SETTINGS, LOCAL_SETTINGS)
                      if (read_fixed_json(p.root, rel, {}).get("enabledPlugins") or {}).get(status["plugin"]) is False]
            if off_in:  # someone turned it off here on purpose: theirs to change, never overwritten
                raise Refused(f"{status['plugin']} is set to false in {', '.join(off_in)}: change it there if the "
                              "user wants it on")
            local_path = fixed_target(p, LOCAL_SETTINGS)
            local = read_json(local_path, {})
            added = merge_plugin_keys(p, local, PLUGIN_MERGE, [("enabledPlugins", status["plugin"], True)])
            if added:
                exclude_locally(p, LOCAL_SETTINGS)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                write_json(local_path, local)
            p.save()
            out["enabled"] = {"plugin": status["plugin"], "in": LOCAL_SETTINGS,
                              "loads": "next session: restart Claude Code (or /reload-plugins) before /impeccable"}
    if a.mode:
        p.config = p.config or {}
        p.config["design"] = a.mode
        p.save()
    out.update(design=design_mode(p), impeccable_installed=impeccable_installed(p.root),
               impeccable=impeccable_status(p.root))
    if a.mode:
        out["guardrail"] = swap_ui_guardrail(p, loads_later="enabled" in out)
    return out


def cmd_review_rounds(p, a):
    """The last review round before the user decides (config's `review_rounds`); with a number, records it. The hook
    applies a lower value at once; a higher one only as hooks/review_rounds.py allows."""
    import review_rounds  # beside the hooks (sys.path above): one range check for both
    if a.rounds is not None:
        try:
            n = review_rounds.configured(int(a.rounds)) if re.fullmatch(r"[0-9]{1,3}", a.rounds.strip()) else None
        except ValueError:
            n = None
        if n is None:
            raise Refused(f"review_rounds is a whole number from {review_rounds.CAP} to {review_rounds.MOST}, "
                          f"not {a.rounds!r}")
        p.config = p.config or {}
        p.config["review_rounds"] = n
        p.save()
    rounds = review_rounds.configured((p.config or {}).get("review_rounds")) or review_rounds.CAP
    return {"review_rounds": rounds, "applies": ("a lower cap at once; a higher one from the next feature on once committed, or at once when "
                        "the user typed /sdlc:setup review-rounds <n> themselves")}


def swap_ui_guardrail(p, loads_later=False):
    """Make the installed UI guardrail match the mode, whenever the mode is set (setup renders guardrails before it
    asks the mode). impeccable: removed only once impeccable's detector hook runs here, so nothing goes unchecked in
    between: not in the call that turned the plugin on (it loads next session), and setting the mode again after a
    restart finishes the swap. An unchanged copy is deleted and untracked,
    not declined, so builtin can bring it back; an edited one is the user's call. builtin: rendered again unless the
    user declined it."""
    tpl, dest = f"templates/project/hookify/{IMPECCABLE_REPLACES}", f".claude/hookify/{IMPECCABLE_REPLACES}"
    if p.lock is None or "claude-code" not in hosts(p) or not template_exists(tpl):
        return None
    files = p.lock["files"]
    entry = files.get(dest)
    if design_mode(p) == "impeccable":
        if not entry:
            return None
        if loads_later or not impeccable_status(p.root)["hook"]:
            return {"kept": dest, "why": "impeccable's detector hook doesn't run here yet: set the mode again once "
                                         "it does (after a restart, or /impeccable hooks on)"}
        state = p.file_state(dest, entry)
        if state == "outside":  # through a link out of the repo: never deleted
            return {"kept": dest, "why": "it resolves outside the project through a link: remove it by hand if wanted"}
        if state == "modified":
            return {"ask": dest, "why": "edited since the plugin wrote it: delete it only if the user agrees"}
        if os.path.exists(p.path(dest)):
            os.remove(p.path(dest))
        files.pop(dest)
        p.save()
        return {"removed": dest}
    if dest in p.lock.get("declined", []) or (entry and os.path.exists(p.path(dest))):
        return None
    try:
        cmd_render(p, argparse.Namespace(template=tpl, dest=dest, cls="seeded", if_unchanged=True))
    except Refused as e:
        return {"ask": dest, "why": str(e)}
    return {"added": dest}


def format_value(node, flt):
    if flt == "yaml_list":  # for frontmatter, e.g. `paths:` in .claude/rules
        items = node if isinstance(node, list) else [node]
        return "\n".join("  - " + json.dumps(str(x)) for x in items)
    if flt == "json":
        return json.dumps(node)
    if flt:
        raise ValueError(f"unknown template filter {flt!r}")
    if isinstance(node, list):
        return ", ".join(str(x) for x in node)
    if isinstance(node, dict):
        return json.dumps(node)
    return str(node)


def render_text(template_text, p):
    ctx = {"plugin_version": plugin_version(), "config": effective_config(p.config), "layout": sdlc_layout.paths(p.root)}
    missing = []

    def lookup(m):
        if m.group(1).split(".")[0] not in ctx:
            return m.group(0)  # not ours: GitHub ${{ github.ref }}, other tools' templates, ...
        node = ctx
        for part in m.group(1).split("."):
            if not isinstance(node, dict) or part not in node:
                missing.append(m.group(1))
                return m.group(0)
            node = node[part]
        return format_value(node, m.group(2))

    text = PLACEHOLDER.sub(lookup, template_text)
    if missing:
        raise ValueError("template placeholders without a value: " + ", ".join(sorted(set(missing))))
    return text


def cmd_render(p, a):
    lock = p.require_lock()
    # a shell loop over this script's own output on Windows hands both on with a trailing `\r` (3.12.0 smoke C3):
    # no template or path of the plugin's ends in whitespace, so it is dropped, never written into a file name
    template = cli_template(a.template)
    text = render_source(template, p)
    dest = rel(p.root, a.dest.strip())
    if git_internal(dest, p.root):
        raise Refused(f"{dest} is in a .git folder (or links into one), which the plugin never writes; nothing written")
    if not inside_repo(p.root, dest):
        raise Refused(f"{dest} resolves outside the project through a link; nothing written")
    entry = lock["files"].get(dest)
    if os.path.lexists(p.path(dest)) and sha256(p.path(dest)) == UNREADABLE:
        raise Refused(f"{dest} isn't a readable file (a folder or a looping link); nothing written")
    if a.if_unchanged and entry and (p.file_state(dest, entry) == "modified" or p.merged(entry)):
        raise Refused(f"{dest} was edited since the plugin wrote it; review the diff instead of overwriting")
    if a.if_unchanged and not entry and os.path.exists(p.path(dest)):
        raise Refused(f"{dest} exists but the plugin never wrote it; review the diff instead of overwriting")
    full = p.path(dest)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    before = sha256(full)
    with open(full, "w", encoding="utf-8", newline="\n") as f:  # LF on Windows too: upgrade-plan hashes the LF render
        f.write(text)
    after = sha256(full)
    if after == UNREADABLE:  # written but can't be read back (write-only): never recorded as a hash
        raise Refused(f"{dest} was written but can't be read back; not recorded")
    lock["files"][dest] = {"class": a.cls, "sha256": after, "template": template}
    p.save()
    return {"rendered": dest, "class": a.cls, "changed": before != after}


# --- conventions: a stack's rules for one area, written when the first feature touches it --------------
# The file is the user's from the start (in `declined`, never in `files`), so eject keeps it and upgrade never
# replaces it; the lock's `conventions` list remembers what each came from, so upgrade can offer a changed template
# as a diff. Stack and area come from these allowlists only; config supplies nothing but the package's path, and
# that only for the `paths:` frontmatter.

CONVENTION_STACKS = ("nuxt", "vue", "react", "nextjs", "flutter", "ios", "android", "node", "go", "fastapi")
CONVENTION_AREAS = ("layers", "schema", "contract", "auth", "data-access", "ui")
CONVENTIONS_DIR = "templates/project/conventions"


def convention_areas(stack):
    """The areas `stack` has a template for, in allowlist order."""
    return [a for a in CONVENTION_AREAS
            if os.path.isfile(os.path.join(PLUGIN_ROOT, CONVENTIONS_DIR, stack, a + ".md"))]


def convention_template(template):
    """A lock entry's template, only when it is one of ours (the lock is repo data, read like input)."""
    m = re.fullmatch(CONVENTIONS_DIR + r"/([a-z]+)/([a-z-]+)\.md", template if isinstance(template, str) else "")
    return bool(m) and m.group(1) in CONVENTION_STACKS and m.group(2) in convention_areas(m.group(1))


def convention_entry(dest, e):
    """A lock `conventions` entry, only when its path is exactly the one its allowlisted stack and area give, and its
    `root` passes the check `--package`'s path does."""
    if not isinstance(e, dict) or not convention_template(e.get("template")):
        return False
    root = e.get("root", ".")
    if root is None or relative_root(root) != root:
        return False
    return (dest == f".claude/rules/{e.get('stack')}-{e.get('area')}.md"
            and e["template"] == f"{CONVENTIONS_DIR}/{e.get('stack')}/{e.get('area')}.md")


def convention_root(p, package):
    """(package name or None, its path for `paths:`), refusing a package config doesn't list."""
    packages = (p.config or {}).get("packages")
    packages = [x for x in packages if isinstance(x, dict)] if isinstance(packages, list) else []
    names = [str(x.get("name")) for x in packages if isinstance(x.get("name"), str)]
    if not packages:
        if package:
            raise Refused(f"--package {package}: {CONFIG} lists no packages; leave it out for a single project")
        return None, "."
    match = next((x for x in packages if x.get("name") == package), None)
    if match is None:
        raise Refused(f"name the package with --package, one of: {', '.join(names) or '(none)'}")
    root = relative_root(match.get("path"))
    if root is None:
        raise Refused(f"package {package}: its path {match.get('path')!r} must be relative and inside the project")
    return package, root


def relative_root(path):
    """A package path as `paths:` takes it ("apps/api", or "." for the project), or None when it isn't a relative
    path inside the project. Used for config's path and for the lock's `root` read back."""
    if not isinstance(path, str):
        return None
    path = path.replace("\\", "/").strip()
    parts = [x for x in path.split("/") if x not in ("", ".")]
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path) or ".." in parts:
        return None
    return "/".join(parts) or "."


def convention_text(template, root, backend_only=False):
    """The rule file: the template's globs under `root` (`backend_only`, for the API in a one-deployable app: without
    its `src/` ones, which there are the web app's), a provenance line, then the template's body."""
    with open(os.path.join(PLUGIN_ROOT, template), encoding="utf-8") as f:
        source = f.read().replace("\r\n", "\n")
    m = re.match(r"^---\n.*?\n---\n", source, re.S)
    globs = rule_scope(source)
    if not m or not globs:
        raise ValueError(f"{template} has no paths: frontmatter")
    if backend_only:
        if not any(g.startswith("backend/") for g in globs):
            raise Refused(f"{template} has no backend/ paths: --one-deployable is for the API's conventions (node)")
        globs = [g for g in globs if not g.startswith("src/")]
    globs = globs if root == "." else [f"{root}/{g}" for g in globs]
    return (f"---\npaths:\n{format_value(globs, 'yaml_list')}\n---\n"
            f"<!-- Written by the sdlc plugin from {template}. Yours to edit: an upgrade offers template changes as a "
            f"diff and never overwrites this file. -->\n" + source[m.end():].lstrip("\n"))  # no version: a release
    # that leaves the template alone must render the same text, or every upgrade would re-offer every convention


def convention_lock(lock):
    """The lock's `conventions` (null reads as empty, as upgrade-plan reads it) and `declined`, checked before anything
    is written; require_lock has already checked `declined`."""
    if lock.get("conventions") is None:
        lock["conventions"] = {}
    if not isinstance(lock["conventions"], dict):
        raise Refused(f"{LOCK}: 'conventions' must be an object of rendered rule files; fix or remove it")
    return lock["conventions"], lock["declined"]


def cmd_conventions(p, a):
    lock = p.require_lock()
    rendered, declined = convention_lock(lock)
    if a.seen:  # the user has been shown an upgrade's diff: the current template is the baseline from now on
        if getattr(a, "one_deployable", False):
            raise Refused("--one-deployable applies to a new render, not --seen: the lock entry keeps its own")
        dest = rel(p.root, a.seen)
        e = rendered.get(dest)
        if not convention_entry(dest, e):
            raise Refused(f"{dest} is not a convention this plugin rendered")
        text = convention_text(e["template"], e.get("root", "."), e.get("one_deployable") is True)
        e.update(version=plugin_version(), sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())
        p.save()
        return {"seen": dest, "version": e["version"]}
    if not a.stack:
        return {"stacks": {s: convention_areas(s) for s in CONVENTION_STACKS}, "rendered": rendered}
    if a.stack not in CONVENTION_STACKS:
        raise Refused(f"unknown stack {a.stack!r}; allowed: {', '.join(CONVENTION_STACKS)}")
    if not a.area:
        raise Refused(f"name an area; {a.stack} has: {', '.join(convention_areas(a.stack)) or '(none)'}")
    if a.area not in CONVENTION_AREAS:
        raise Refused(f"unknown area {a.area!r}; allowed: {', '.join(CONVENTION_AREAS)}")
    areas = convention_areas(a.stack)
    if a.area not in areas:
        raise Refused(f"{a.stack} has no {a.area} convention; its areas: {', '.join(areas) or '(none)'}")
    package, root = convention_root(p, a.package)
    dest = f".claude/rules/{a.stack}-{a.area}.md"
    if not inside_repo(p.root, ".claude/rules"):  # .claude or .claude/rules is a link out
        raise Refused(f".claude/rules resolves outside the project ({os.path.realpath(p.path('.claude/rules'))}); "
                      f"nothing written")
    target = p.path(dest)
    if (os.path.isfile(target) and not os.path.islink(target) and os.path.getsize(target) == 0
            and convention_entry(dest, rendered.get(dest))):
        os.remove(target)  # an interrupted render's empty placeholder (the lock says we made it): nothing to lose
    if os.path.lexists(target):  # a lock entry alone isn't a file: one the user deleted renders again
        raise Refused(f"{dest} exists; it is never overwritten: widen its paths: by hand for another package")
    template = f"{CONVENTIONS_DIR}/{a.stack}/{a.area}.md"
    text = convention_text(template, root, a.one_deployable)
    entry = {"stack": a.stack, "area": a.area, "package": package, "root": root, "template": template,
             "version": plugin_version(), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    if a.one_deployable:
        entry["one_deployable"] = True
    previous, added = rendered.get(dest), dest not in declined
    rendered[dest] = entry
    if added:
        declined.append(dest)
    p.save()  # the lock first: a kill before the file lands leaves an entry with no file, which a rerun renders
    try:
        os.makedirs(os.path.dirname(p.path(dest)), exist_ok=True)
        _publish_new(p.path(dest), text)
    except Exception as exc:  # no file landed (a kill isn't an Exception: its entry stays for the rerun)
        if previous is None:  # the lock goes back to what it was
            rendered.pop(dest, None)
        else:
            rendered[dest] = previous
        if added:
            declined.remove(dest)
        p.save()
        if isinstance(exc, FileExistsError):  # another writer got there after the check: theirs stays
            raise Refused(f"{dest} appeared while rendering; it is never overwritten")
        raise
    out = {"rendered": dest, "paths": rule_scope(text)}
    try:  # the AGENTS.md block carries every area rule to the other agents: say when it needs a rebuild
        if agents_state(p) == "stale":
            out["agents"] = "stale: run `scaffold.py agents`"
    except ValueError:
        pass
    return out


def convention_updates(p):
    """Rendered conventions whose template changed since: the user's file against the new render, as a diff."""
    import difflib
    out = []
    rendered = (p.lock or {}).get("conventions", {})
    rendered = {} if rendered is None else rendered
    if not isinstance(rendered, dict):  # reported, not raised: the rest of the upgrade plan still stands
        return [{"error": f"{LOCK}: 'conventions' must be an object of rendered rule files; fix or remove it"}]
    for dest, e in sorted(rendered.items()):
        if not convention_entry(dest, e):
            if isinstance(dest, str) and dest.startswith(".claude/rules/") and "/" not in dest[len(".claude/rules/"):]:
                out.append({"path": dest, "error": "its lock entry doesn't match a convention the plugin renders "
                                                   "(stack, area, template or root); fix or remove it"})
            continue  # anything else the lock names here is never read
        if not os.path.isfile(p.path(dest)):
            continue
        try:
            new = convention_text(e["template"], e.get("root", "."), e.get("one_deployable") is True)
        except Refused as exc:  # a hand-edited entry: that item's error, the rest of the plan stands
            out.append({"path": dest, "template": e["template"], "error": str(exc)})
            continue
        if hashlib.sha256(new.encode("utf-8")).hexdigest() == e.get("sha256"):
            continue
        if not inside_repo(p.root, dest):  # .claude/rules links out: never read
            out.append({"path": dest, "template": e["template"], "error": "it resolves outside the project"})
            continue
        try:
            with open(p.path(dest), encoding="utf-8") as f:
                have = f.read().replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError) as exc:
            out.append({"path": dest, "template": e["template"], "error": f"can't read it as UTF-8 text: {exc}"})
            continue
        diff = "".join(difflib.unified_diff(have.splitlines(True), new.splitlines(True), dest, dest + " (template)"))
        if not diff:  # the file already reads like the new template: nothing to offer
            continue
        out.append({"path": dest, "template": e["template"], "from": e.get("version"), "diff": diff})
    return out


# --- commands contract -------------------------------------------------------------------
# The project's own commands live in config: `commands` for a single project, or `packages` (each with name,
# path, stack and commands) for a monorepo. A command set to null means "not applicable" (e.g. typecheck for
# shell scripts). Stages, verify.py, CI, the allowlist and the freshness hook all read them from here.

ROOT_SCOPE = sdlc_scopes.ROOT_SCOPE


def scopes(config):
    """[{name, path, stack, commands, accept, named}]: one per package, or the root project when there are no
    packages. The same parser the hooks use (hooks/sdlc_scopes.py)."""
    return sdlc_scopes.scopes(effective_config(config))


def executable(cmd):
    """First word of a command that names a program (skips leading VAR=value assignments)."""
    for tok in cmd.split():
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok):
            return tok
    return None


def resolves(exe, cwd):
    if "/" in exe:
        return os.path.exists(os.path.normpath(os.path.join(cwd, exe)))
    return shutil.which(exe) is not None


def shell():
    """bash for the POSIX-style commands configs hold; on Windows, Git's bash, not System32's (WSL)."""
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return [found, "-c"]
    git = shutil.which("git")
    for cand in ([os.path.join(os.path.dirname(os.path.dirname(git)), "bin", "bash.exe")] if git else []):
        if os.path.exists(cand):
            return [cand, "-c"]
    return None


def cmd_run_commands(p, a):
    """Run install, then the verify plan, each in its directory; record every exit in the lock. A command that
    can't start (tool missing, timeout) fails this; a non-zero exit is only recorded (a known failure is normal
    in brownfield; the baseline step classifies it)."""
    p.require_lock()
    sh = shell()
    plan = verify_plan(p.config)
    runs, not_runnable = {}, []
    for step in plan["install"] + plan["verify"]:
        cwd = p.path(step["cwd"])
        exe = executable(step["run"])
        rec = {"command": step["run"], "ran": False, "exit": None,
               "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        if exe and resolves(exe, cwd):
            try:
                proc = subprocess.run(sh + [step["run"]] if sh else step["run"], shell=not sh, cwd=cwd,
                                      capture_output=True, encoding="utf-8", errors="replace", timeout=a.timeout)
                rec.update(exit=proc.returncode, ran=proc.returncode not in (126, 127),
                           tail=(proc.stdout + proc.stderr).strip()[-300:])
            except subprocess.TimeoutExpired:
                rec["tail"] = f"timed out after {a.timeout}s"
        else:
            rec["tail"] = f"{exe} not found"
        runs.setdefault(step["scope"] or ROOT_SCOPE, {})[step["step"]] = rec
        if not rec["ran"]:
            not_runnable.append(f"{step['scope'] or ROOT_SCOPE} {step['step']}")
    # The lock is committed: keep the outcome, never the output (it can hold tokens); the tail is printed only.
    # The run can take minutes: the save merges onto the lock as it is then, so a change made meanwhile is kept
    p.require_lock()["command_runs"] = {
        name: {k: {f: r[f] for f in ("command", "ran", "exit", "at")} for k, r in steps.items()}
        for name, steps in runs.items()}
    try:
        p.save()
    except (ValueError, OSError) as e:  # the lock went away or couldn't be written: what ran is still the user's
        raise CommandsFailed({"scopes": runs, "not_runnable": not_runnable, "lock_error": str(e)})
    if not_runnable:
        raise CommandsFailed({"scopes": runs, "not_runnable": not_runnable})
    return {"scopes": runs, "not_runnable": []}


def verify_steps(config, scope_name):
    """The steps run-commands runs for one scope, in order."""
    plan = verify_plan(config)
    return [s["step"] for s in plan["install"] + plan["verify"] if (s["scope"] or ROOT_SCOPE) == scope_name]


def cmd_contract(p, a):
    cfg = effective_config(p.config)
    required = cfg.get("contract", {}).get("required", [])
    out = {"required": required, "monorepo": bool(cfg.get("packages")), "scopes": {}}
    names = set()
    for sc in scopes(p.config):
        problems = []
        if not sc["named"]:
            problems.append("package without a name")
        elif sc["name"] in names:
            problems.append(f"duplicate package name {sc['name']!r}")
        names.add(sc["name"])
        cwd = p.path(sc["path"])
        if not os.path.isdir(cwd):
            problems.append(f"path {sc['path']!r} does not exist")
        cmds = sc["commands"]
        missing = [k for k in required if k not in cmds]
        not_applicable = [k for k in required if k in cmds and cmds[k] is None]
        not_found = {}
        for key, cmd in cmds.items():
            if cmd and os.path.isdir(cwd):
                exe = executable(cmd)
                if exe and not resolves(exe, cwd):
                    not_found[key] = exe
        out["scopes"][sc["name"] or "?"] = {"path": sc["path"], "missing": missing, "not_applicable": not_applicable,
                                            "not_found": not_found, "problems": problems,
                                            "ok": not missing and not problems}
    out["ok"] = all(s["ok"] for s in out["scopes"].values())
    out["tools_ok"] = all(not s["not_found"] for s in out["scopes"].values())
    # Last recorded runs, with any whose command has changed since dropped: they no longer prove anything
    current = {(sc["name"], k): v for sc in scopes(p.config) for k, v in sc["commands"].items()}
    current.update({(ROOT_SCOPE, s["step"]): s["run"] for s in verify_plan(p.config)["verify"]
                    if s["scope"] == ROOT_SCOPE})
    out["runs"] = {name: {k: r for k, r in steps.items() if current.get((name, k)) == r.get("command")}
                   for name, steps in ((p.lock or {}).get("command_runs") or {}).items()}
    return out


def verify_plan(config):
    cfg = effective_config(config)
    order = cfg.get("verify", {}).get("order", ["lint", "typecheck", "build", "test"])
    plan = {"install": [], "verify": []}
    # A root `commands.test` beside packages (`turbo run test`) runs from the root after every package's steps; the
    # other root commands keep not running there, as before workbenches (an existing monorepo behaves as it did)
    root_test = sdlc_scopes.root_commands(cfg).get("test")
    root = {"name": ROOT_SCOPE, "path": ".", "commands": {"test": root_test} if root_test else {}}
    for sc in scopes(config) + [root]:
        cmds = sc["commands"]
        if cmds.get("install") and sc is not root:
            plan["install"].append({"scope": sc["name"], "cwd": sc["path"], "step": "install", "run": cmds["install"]})
        for step in order:
            if cmds.get(step):
                plan["verify"].append({"scope": sc["name"], "cwd": sc["path"], "step": step, "run": cmds[step]})
    return plan


def cmd_commands(p, a):
    return {"scopes": scopes(p.config), **verify_plan(p.config)}


# --- generated CI workflow (template "builtin:ci") -------------------------------------------

STACK_ALIASES = {"typescript": "node", "ts": "node", "javascript": "node", "js": "node", "bun": "node",
                 "uv": "python", "kotlin": "java", "gradle": "java", "maven": "java",
                 "csharp": "dotnet", "fsharp": "dotnet", "cargo": "rust", "bash": "shell", "sh": "shell"}
CI_SETUP = {
    "node": ["- uses: actions/setup-node@v7", "  with:", '    node-version: "{node_version}"', "- run: corepack enable"],
    "python": ["- uses: astral-sh/setup-uv@v10.3.3"],  # setup-uv has no moving major tag: pin a full version
    "go": ["- uses: actions/setup-go@v7", "  with:", "    go-version-file: {go_mod}"],
    "rust": ["- uses: dtolnay/rust-toolchain@stable", "  with:", "    components: clippy, rustfmt"],
    "dart": ["- uses: dart-lang/setup-dart@v1"],
    "flutter": ["- uses: subosito/flutter-action@v2", "  with:", "    channel: stable"],
    "swift": ["- uses: maxim-lobanov/setup-xcode@v1", "  with:", "    xcode-version: latest-stable"],
    "java": ["- uses: actions/setup-java@v6", "  with:", "    distribution: temurin", '    java-version: "{java_version}"'],
    "dotnet": ["- uses: actions/setup-dotnet@v6", "  with:", '    dotnet-version: "{dotnet_version}"'],
    "shell": ["- run: sudo apt-get install -y shellcheck shfmt bats"],
}


def project_stacks(config, package=None):
    """Distinct toolchains, from each package's `stack` (only `package`'s when given), else `project.stack`."""
    cfg = effective_config(config)

    def names(stack):  # one name or a list of them: a lone string is never read as its letters
        return [stack] if isinstance(stack, str) else list(stack or [])

    raw = [st for sc in scopes(config) if sc["stack"] and package in (None, sc["name"]) for st in names(sc["stack"])]
    raw = raw or ([] if package else names(cfg.get("project", {}).get("stack")))
    found = []
    for st in raw:
        st = STACK_ALIASES.get(str(st).lower(), str(st).lower())
        if st not in found:
            found.append(st)
    return found


def generate_ci(p, package=None):
    """One workflow for every package, or (`package`) one that runs only when that package or a shared one changes."""
    cfg = effective_config(p.config)
    ci = cfg.get("ci", {})
    plan = verify_plan(p.config)
    pkg_scopes = scopes(p.config)
    if package:
        pkg_scopes = [sc for sc in pkg_scopes if sc["name"] == package]
        if not pkg_scopes:
            raise ValueError(f"no package named {package!r} in .sdlc/config.json")
        plan = {k: [s for s in v if s["scope"] == package] for k, v in plan.items()}
    if not plan["verify"]:
        raise ValueError("no commands in .sdlc/config.json to put in CI (set `commands`, or `packages[].commands`)")
    go_scope = next((sc for sc in pkg_scopes if os.path.exists(p.path(os.path.join(sc["path"], "go.mod")))), None)
    go_mod = os.path.normpath(os.path.join(go_scope["path"] if go_scope else ".", "go.mod")).replace(os.sep, "/")
    values = {"node_version": ci.get("node_version", "22"), "java_version": ci.get("java_version", "21"),
              "dotnet_version": ci.get("dotnet_version", "8.0.x"), "go_mod": go_mod}
    runners = ci.get("os", ["ubuntu-latest"])

    # no package names a stack: every package takes `project.stack`, as the whole-repo workflow always did
    shared = None if package or any(sc["stack"] for sc in pkg_scopes) else project_stacks(p.config)

    def scope_stacks(name):
        return shared if shared is not None else project_stacks(p.config, None if name == ROOT_SCOPE else name)

    # Xcode runs only on macOS: Swift packages get a job of their own there, whatever runners ci.os names, so the
    # other packages keep theirs (and their Linux-only setup steps) instead of all paying for macOS minutes
    mac = {sc["name"] for sc in pkg_scopes if "swift" in scope_stacks(sc["name"])}

    def job_parts(on_mac):
        return ([s for sc in pkg_scopes if (sc["name"] in mac) == on_mac for s in scope_stacks(sc["name"])],
                [s for s in plan["install"] + plan["verify"] if (s["scope"] in mac) == on_mac])
    jobs = [(name, runs, *job_parts(on_mac)) for name, runs, on_mac in
            (("verify", runners, False), ("verify-macos", ["macos-latest"], True))]
    jobs = [j for j in jobs if any(s in plan["verify"] for s in j[3])]
    pad = " " * 6
    name, group, trigger = "name: sdlc verify", "sdlc-verify", ["  pull_request:", "  push:", "    branches: [main, master]"]
    if package:
        name, group = f"name: {json.dumps('sdlc verify ' + package)}", f"sdlc-verify-{package}"
        # "*" is root files only: workspace manifests and lockfiles every package depends on
        paths = ["    paths:"] + [f"      - {json.dumps(x)}" for x in
                                   (f"{pkg_scopes[0]['path']}/**", "packages/**", "*", f".github/workflows/{group}.yml")]
        trigger = ["  pull_request:", *paths, "  push:", "    branches: [main, master]", *paths]
    lines = [
        f"# Managed by the sdlc plugin v{plugin_version()} (seeded: replaced on upgrade only while unedited).",
        "# Generated from the commands in .sdlc/config.json: the same commands verify.py runs.",
        name, "", "on:", *trigger, "",
        "concurrency:", f"  group: {group}-${{{{ github.ref }}}}", "  cancel-in-progress: true", "",
        "permissions:", "  contents: read", "",
        "defaults:", "  run:", "    shell: bash  # Git Bash on Windows runners: same shell everywhere", "",
        "jobs:"]
    for i, (job, runs, stacks, steps) in enumerate(jobs):
        lines += ([""] if i else []) + [
            f"  {job}:", "    strategy:", "      fail-fast: false", "      matrix:", f"        os: {json.dumps(runs)}",
            "    runs-on: ${{ matrix.os }}", "    timeout-minutes: 30", "    steps:", pad + "- uses: actions/checkout@v7"]
        for st in dict.fromkeys(stacks):
            if st in CI_SETUP:
                lines += [pad + x.format(**values) for x in CI_SETUP[st]]
            else:
                lines.append(pad + f"# TODO: add the toolchain setup for '{st}'")
        if not package:
            lines += [pad + x for x in workbench_checkout(p)]
        for step in steps:
            label = step["step"] if step["scope"] == ROOT_SCOPE else f"{step['scope']} · {step['step']}"
            lines.append(pad + f"- name: {json.dumps(label, ensure_ascii=False)}")
            if step["cwd"] != ".":
                lines.append(pad + f"  working-directory: {step['cwd']}")
            lines += [pad + "  run: |", pad + "    " + step["run"]]
    return "\n".join(lines) + "\n"


WORKBENCH_REPO = re.compile(r"^(?:[A-Za-z0-9][A-Za-z0-9-]{0,38}/)?[A-Za-z0-9._-]{1,100}$")


def workbench_checkout(p):
    """The CI steps that check out the workbench for an app repo that consumes its contract, else []: the app's
    config names its workbench (`"workbench": "<name>"` or `"<owner>/<name>"`) and the workbench above it lists the
    app with `contract.consumes`. The branch with the PR's own name when the workbench has one (the same feature's
    unmerged contract change), else main; the contract lands at ../contract, where the app's generate step reads it.
    The branch reaches the script only through env."""
    name = sdlc_scopes.workbench_of(p.root)
    if not name or not WORKBENCH_REPO.match(name) or name.startswith(".") or "/." in name:
        return []
    parent = os.path.dirname(p.root)
    if not sdlc_scopes.is_workbench(parent):
        return []
    try:
        entry = next((r for r in sdlc_scopes.manifest(parent) if r["name"] == os.path.basename(p.root)), None)
    except ValueError:
        return []
    if not entry or not entry["contract"].get("consumes"):
        return []
    repo = name if "/" in name else "${{ github.repository_owner }}/" + name
    token = "${{ secrets.WORKBENCH_TOKEN || github.token }}"
    return [
        "# The workbench holds the API contract: its branch named like this PR's, else main (a private workbench",
        "# needs a WORKBENCH_TOKEN secret that can read it)",
        "- name: \"workbench branch\"", "  id: workbench", "  env:", f"    GH_TOKEN: {token}",
        "    BRANCH: ${{ github.head_ref || github.ref_name }}", "  run: |",
        f'    if gh api "repos/{repo}/branches/$BRANCH" --silent 2>/dev/null; then',
        '      echo "ref=$BRANCH" >> "$GITHUB_OUTPUT"', "    else", '      echo "ref=main" >> "$GITHUB_OUTPUT"', "    fi",
        "- uses: actions/checkout@v7", "  with:", f"    repository: {repo}",
        "    ref: ${{ steps.workbench.outputs.ref }}", "    path: .workbench", f"    token: {token}",
        "    persist-credentials: false",
        "# Only the contract stays: the checkout leaves the app's tree before its own steps run",
        "- name: \"workbench contract\"", "  run: |",
        "    rm -rf ../contract && cp -R .workbench/contract ../contract && rm -rf .workbench"]


def generate_contract_check(p):
    """Workflow that fails a PR making a breaking change to a published contract version (contract-check.sh)."""
    cfg = effective_config(p.config)
    contract = cfg.get("api_contract") or {}
    if not contract.get("path") or not contract.get("spec"):
        raise ValueError("no api_contract in .sdlc/config.json (set `api_contract.path` and `api_contract.spec`)")
    path = contract["path"].rstrip("/")
    pad = " " * 6
    lines = [
        f"# Managed by the sdlc plugin v{plugin_version()} (seeded: replaced on upgrade only while unedited).",
        "# Published contract versions take additions only: see .sdlc/ci/contract-check.sh.",
        "# No path filter: it runs on every pull request, so it can be a required check.",
        "name: sdlc contract", "", "on:", "  pull_request:", "",
        "permissions:", "  contents: read", "",
        "jobs:", "  contract:", "    runs-on: ubuntu-latest", "    timeout-minutes: 15", "    steps:",
        pad + "- uses: actions/checkout@v7", pad + "  with:", pad + "    fetch-depth: 0",
        pad + "- uses: actions/setup-go@v7", pad + "  with:", pad + "    go-version: stable",
        pad + f"- run: go install github.com/oasdiff/oasdiff@v{cfg.get('ci', {}).get('oasdiff_version', '1.33.0')}",
        pad + "- name: \"published versions only grow\"",
        pad + f'  run: bash .sdlc/ci/contract-check.sh "origin/${{{{ github.base_ref }}}}" {path} {contract["spec"]}']
    return "\n".join(lines) + "\n"


INVARIANTS = [("templates/project/ci/invariants.py", ".sdlc/ci/invariants.py"),
              ("builtin:invariants", ".github/workflows/sdlc-invariants.yml")]


def generate_invariants(p):
    """Workflow that checks the shared sdlc files (invariants.py): on Linux only, with the history the checks compare."""
    pad = " " * 6
    lines = [
        f"# Managed by the sdlc plugin v{plugin_version()} (seeded: replaced on upgrade only while unedited).",
        "# Checks the record and the baseline of active features: see .sdlc/ci/invariants.py.",
        "name: sdlc invariants", "", "on:", "  pull_request:", "  push:", "    branches: [main, master]", "",
        "permissions:", "  contents: read", "",
        "jobs:", "  invariants:", "    runs-on: ubuntu-latest", "    timeout-minutes: 10", "    steps:",
        pad + "- uses: actions/checkout@v7", pad + "  with:", pad + "    fetch-depth: 0",
        pad + '- name: "shared sdlc files"',
        pad + "  env:  # branch names reach the shell only as variables",
        pad + "    BASE_REF: ${{ github.base_ref }}", pad + "    BEFORE: ${{ github.event.before }}",
        pad + "  run: |",
        pad + '    if [ -n "$BASE_REF" ]; then',
        pad + '      python3 .sdlc/ci/invariants.py --base "origin/$BASE_REF" --require-ancestor',
        pad + '    elif [ -n "$BEFORE" ] && [ "$BEFORE" != 0000000000000000000000000000000000000000 ]; then',
        pad + '      python3 .sdlc/ci/invariants.py --base "$BEFORE"',
        pad + "    else",
        pad + "      python3 .sdlc/ci/invariants.py",
        pad + "    fi"]
    return "\n".join(lines) + "\n"


def generate_codeowners(p):
    """CODEOWNERS from `project.owners`, in config order: the last matching line wins, so order is the user's."""
    owners = effective_config(p.config).get("project", {}).get("owners") or {}
    if not owners:
        raise ValueError("no project.owners in .sdlc/config.json (set `{pattern: [handles]}`)")
    lines = [f"# Managed by the sdlc plugin v{plugin_version()} (seeded: replaced on upgrade only while unedited).",
             "# Generated from project.owners in .sdlc/config.json."]
    lines += [f"{pattern} {' '.join(handles)}" for pattern, handles in owners.items()]
    return "\n".join(lines) + "\n"


def render_source(template, p):
    problem = template_problem(template)
    if problem:
        raise Refused(problem)
    if template == "builtin:ci":
        return generate_ci(p)
    if template.startswith("builtin:ci:"):
        return generate_ci(p, template[len("builtin:ci:"):])
    if template == "builtin:contract-check":
        return generate_contract_check(p)
    if template == "builtin:codeowners":
        return generate_codeowners(p)
    if template == "builtin:invariants":
        return generate_invariants(p)
    if template == "builtin:agents-mirror":
        return agents_mirror(p) or ""
    with open(os.path.join(PLUGIN_ROOT, template), encoding="utf-8") as f:
        return render_text(f.read(), p)


@functools.lru_cache(maxsize=None)
def _templates_base():
    return os.path.realpath(os.path.join(PLUGIN_ROOT, "templates"))  # once per process: the lock checks every entry


BUILTINS = ("ci", "contract-check", "codeowners", "invariants", "agents-mirror")


def template_problem(template):
    """Why `template` isn't one of the plugin's own, or None. The committed lock names templates, and an upgrade
    renders them without a question, so every route checks here: a known builtin, or a relative path under the
    plugin's templates/ that still resolves inside it after links (another drive counts as outside)."""
    if not isinstance(template, str) or not template:
        return "a template must be a non-empty string"
    if template.startswith("builtin:"):
        name = template[len("builtin:"):]
        if name in BUILTINS or re.fullmatch(r"ci:[A-Za-z0-9][A-Za-z0-9._-]*", name):
            return None
        return f"{template!r} isn't one of the plugin's builtin templates"
    parts = template.split("/")
    if "\\" in template or re.match(r"^[A-Za-z]:", template) or parts[0] != "templates" or \
            any(x in ("", ".", "..") for x in parts):
        return f"template {template!r} isn't a path under the plugin's templates/"
    base = _templates_base()
    try:
        inside = os.path.commonpath([base, os.path.realpath(os.path.join(PLUGIN_ROOT, template))]) == base
    except ValueError:
        inside = False
    return None if inside else f"template {template!r} resolves outside the plugin's templates/"


_git_segment = sdlc_scopes.git_segment  # the one `.git` segment rule every check shares


def git_internal(path, root=None):
    """`path` (repo-relative) is, or with `root` resolves through links into, a git dir at any depth: nothing the
    plugin records, renders or deletes may land there. Both forms, so a committed link `x -> .git` doesn't pass."""
    forms = [str(path)]
    if root is not None:
        try:
            forms.append(os.path.relpath(os.path.realpath(os.path.join(root, path)), _real_root(root)))
        except ValueError:  # another drive: inside_repo refuses it
            pass
    return any(_git_segment(x) for f in forms for x in f.replace("\\", "/").split("/") if x not in ("", "."))


FIXED_FILES = (AGENTS, GITIGNORE, SETTINGS, LOCAL_SETTINGS)
UNMERGE_KEYS = {AGENTS: (AGENTS_MERGE,), GITIGNORE: (GITIGNORE,), SETTINGS: (SETTINGS, TEAM_PLUGIN_MERGE),
                LOCAL_SETTINGS: (PLUGIN_MERGE,)}  # each fixed file's lock `merged` keys: what eject takes back


def link_problem(root, rel):
    """Why the repo file `rel`, named by sdlc rather than recorded (FIXED_FILES, CLAUDE.md, .claude/rules), can't be
    opened, or None: a committed link that leads out of the repo or into a git dir would have sdlc read a file it
    shouldn't (and copy its text into the repo), or write into it."""
    if not inside_repo(root, rel) or git_internal(rel, root):
        return (f"{rel} is a link (or under one) that leads out of the repo or into .git: not read or written; "
                "replace the link with a plain file")
    return None


def repo_text(root, rel, limit=-1):
    """(text, None) for the repo file `rel` named by sdlc, or (None, why) when it isn't read: link_problem holds, or
    it can't be opened (a broken or looping link, a folder). Every reader of such a file goes through it, so one bad
    file is skipped or reported, never a traceback that hides the rest."""
    rel = rel.replace(os.sep, "/")
    if link_problem(root, rel):
        return None, f"{rel} (linked out of the repo or into .git)"
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            return f.read(limit), None
    except OSError as e:
        return None, f"{rel} ({e.strerror or type(e).__name__})"


def fixed_problem(p, rel):
    return link_problem(p.root, rel)


def read_fixed_json(root, rel, default=None):
    """The repo's JSON file `rel` (a settings file), or `default` when it's missing or link_problem holds: read as
    absent, so a linked file never decides anything."""
    return default if link_problem(root, rel) else read_json(os.path.join(root, rel), default)


def fixed_target(p, rel):
    """The full path of the fixed-name file `rel`, refused as fixed_problem says."""
    problem = fixed_problem(p, rel)
    if problem:
        raise Refused(problem)
    return p.path(rel)


def template_exists(template):
    if template_problem(template):
        return False
    return template.startswith("builtin:") or os.path.exists(os.path.join(PLUGIN_ROOT, template))


def cli_template(text):
    """A template named on the command line, as the lock stores it: a shell loop's trailing `\\r` and a Windows
    separator are not part of the name (3.12.0 smoke C3). An empty one is refused, never read as none."""
    template = text.strip().replace(os.sep, "/")
    if not template:
        raise Refused("a template must be a non-empty string")
    return template


def cmd_preview(p, a):
    template = cli_template(a.template)
    return {"template": template, "text": render_source(template, p)}


# --- keyed merges ------------------------------------------------------------------------

def merged_list(p, target):
    return p.require_lock().setdefault("merged", {}).setdefault(target, [])


def allow_entries(config):
    entries = []
    for sc in scopes(config):
        for cmd in sc["commands"].values():
            if cmd and f"Bash({cmd}:*)" not in entries:
                entries.append(f"Bash({cmd}:*)")
    return entries


def cmd_allow(p, a):
    if getattr(a, "from_commands", False):
        a.add = list(a.add or []) + allow_entries(p.config)
    settings_path = fixed_target(p, SETTINGS)
    settings = read_json(settings_path, {})
    allow = settings.setdefault("permissions", {}).setdefault("allow", [])
    ours = merged_list(p, SETTINGS)
    added, removed = [], []
    for entry in a.add or []:
        if entry not in allow:
            allow.append(entry)
            added.append(entry)
            if entry not in ours:
                ours.append(entry)
    for entry in a.remove or []:
        if entry in ours:  # only ever remove what we added
            ours.remove(entry)
            if entry in allow:
                allow.remove(entry)
                removed.append(entry)
    write_json(settings_path, settings)
    p.save()
    return {"added": added, "removed": removed, "owned": ours}


def installed_plugins():
    """Claude Code's install record on this machine: {plugin id: entries}."""
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    records = read_json(os.path.join(config, "plugins", "installed_plugins.json"), {})
    records = records.get("plugins", records) if isinstance(records, dict) else {}
    return records if isinstance(records, dict) else {}


def not_the_installed_copy():
    """Why enabling sdlc for the repo would be wrong here, or None: the running plugin isn't Claude Code's
    installed sdlc (loaded with --plugin-dir, or not installed at all), so enabling it would load a second copy."""
    entries = installed_plugins().get(PLUGIN_KEY)
    entries = [entries] if isinstance(entries, dict) else entries if isinstance(entries, list) else []
    here = os.path.normcase(os.path.realpath(PLUGIN_ROOT))
    if any(isinstance(e, dict) and e.get("installPath")
           and os.path.normcase(os.path.realpath(e["installPath"])) == here for e in entries):
        return None
    return (f"this session runs sdlc from {PLUGIN_ROOT} (--plugin-dir or a checkout), not the installed copy; "
            "enabling the installed one would load two")


PLUGIN_ID = re.compile(r"^[a-z0-9][a-z0-9-]*@[a-z0-9][a-z0-9-]*$")


def companions(p=None):
    """The plugins sdlc pairs with: id, its marketplace (and `source` for one other than sdlc's), a one-line `why`,
    and whether it's on by `default`. Read from the plugin's own shipped defaults only, never the repo's
    .sdlc/config.json: that file is committed, and enable-plugin doesn't ask, so a repo must not be able to name a
    plugin or marketplace for it to turn on."""
    shipped = read_json(os.path.join(PLUGIN_ROOT, DEFAULTS), {}).get("companions") or []
    return [c for c in shipped if isinstance(c, dict) and PLUGIN_ID.match(str(c.get("id", "")))]


SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def skill_companions(root):
    """The skills sdlc pairs with (a `skill` entry in the shipped `companions`): sdlc never installs one, it reports
    whether it's installed and the command that installs it, for the user to run. Shipped defaults only."""
    shipped = read_json(os.path.join(PLUGIN_ROOT, DEFAULTS), {}).get("companions") or []
    return [{"skill": c["skill"], "why": c.get("why", ""), "install": c.get("install", ""),
             "installed": skill_installed(root, c["skill"])}
            for c in shipped if isinstance(c, dict) and SKILL_NAME.match(str(c.get("skill", "")))]


def conflicts():
    """What clashes with sdlc (shipped defaults only, like companions): a `plugin` (by name, any marketplace) that
    enable-plugin turns off for this repo, or `files` (a tool written into the repo, such as spec-kit's) to report."""
    shipped = read_json(os.path.join(PLUGIN_ROOT, DEFAULTS), {}).get("conflicts") or []
    return [c for c in shipped if isinstance(c, dict) and c.get("name") and (c.get("plugin") or c.get("files"))]


def enabled_elsewhere(p):
    """Plugin ids turned on in the user's or the project's committed settings (what this repo's local file would
    otherwise inherit)."""
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    on = []
    for data in (read_json(os.path.join(config, "settings.json"), {}), read_fixed_json(p.root, SETTINGS, {})):
        plugins = data.get("enabledPlugins")
        on += [k for k, v in (plugins.items() if isinstance(plugins, dict) else []) if v is True and k not in on]
    return on


def conflicts_in_repo(p):
    found = []
    for c in conflicts():
        hits = [f for f in c.get("files") or [] if glob.glob(p.path(f.rstrip("/")))]
        if hits:
            found.append({"name": c["name"], "found": hits, "why": c.get("why", "")})
    return found


def cmd_enable_plugin(p, a):
    """Turn sdlc, and the companions this machine wants, on for this repo: a keyed merge into
    .claude/settings.local.json, which is never committed, so nobody else's setup changes and nothing needs asking.
    With --team (asked at setup: the team's call) the keys that turn plugins on go to the committed
    .claude/settings.json instead, so every teammate who trusts the repo gets them (a cloud session doesn't install
    plugins from that file, so it needs the wiki's "Cloud sessions" routes).
    A companion is on when its `default` is true or it's named with --with; only listed ones can be. A key the user
    already set, in either file, is theirs and is never recorded or removed."""
    known = {c["id"]: c for c in companions(p)}
    unknown = [i for i in a.with_ or [] if i not in known]
    if unknown:
        raise ValueError(f"not a companion of sdlc: {', '.join(unknown)} (the list: {', '.join(known) or 'none'})")
    if a.remove:
        removed, kept = unmerge_plugin_keys(p, LOCAL_SETTINGS, PLUGIN_MERGE)
        return {"removed": removed, "kept": kept, "owned": merged_list(p, PLUGIN_MERGE)}
    if a.remove_team:  # the keys --team (or a setup before 2.0.1) put in the committed settings.json
        removed, kept = unmerge_plugin_keys(p, SETTINGS, TEAM_PLUGIN_MERGE)
        return {"removed": removed, "kept": kept}
    team_path, local_path = fixed_target(p, SETTINGS), fixed_target(p, LOCAL_SETTINGS)
    skipped = not_the_installed_copy()
    wanted = [] if skipped else [("extraKnownMarketplaces", MARKETPLACE[0], MARKETPLACE[1]),
                                 ("enabledPlugins", PLUGIN_KEY, True)]
    for c in known.values():
        if c.get("default") or c["id"] in (a.with_ or []):
            market = c.get("marketplace")
            source = MARKETPLACE[1] if market == MARKETPLACE[0] else {"source": c["source"]} if c.get("source") else None
            if market and source:
                wanted.append(("extraKnownMarketplaces", market, source))
            wanted.append(("enabledPlugins", c["id"], True))
    # A plugin that clashes with sdlc is turned off for this repo only, on this machine; the user's setting elsewhere stays
    clash = {c["plugin"]: c for c in conflicts() if c.get("plugin")}
    turning_off = [(i, clash[i.split("@", 1)[0]]) for i in enabled_elsewhere(p) if i.split("@", 1)[0] in clash]
    off = [("enabledPlugins", i, False) for i, _ in turning_off]
    team, local = read_json(team_path, {}), read_json(local_path, {})
    # A repo whose plugin keys are already the team's keeps adding there (a later --with, upgrade's re-run)
    if a.team or p.require_lock().get("merged", {}).get(TEAM_PLUGIN_MERGE):
        added_team = merge_plugin_keys(p, team, TEAM_PLUGIN_MERGE, wanted)
        added_local = merge_plugin_keys(p, local, PLUGIN_MERGE, off)
    else:
        added_team = []
        added_local = merge_plugin_keys(p, local, PLUGIN_MERGE, wanted + off, also_set=team)
    if added_team:
        os.makedirs(os.path.dirname(team_path), exist_ok=True)
        write_json(team_path, team)
    if added_local:
        excluded = exclude_locally(p, LOCAL_SETTINGS)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        write_json(local_path, local)
    p.save()
    enabled = dict(team.get("enabledPlugins") or {}, **(local.get("enabledPlugins") or {}))
    ours = merged_list(p, PLUGIN_MERGE)
    out = {"added": added_team + added_local, "owned": ours + merged_list(p, TEAM_PLUGIN_MERGE),
           "companions": [{"id": i, "why": c.get("why", ""), "on": enabled.get(i) is True} for i, c in known.items()]}
    if added_team:
        out["commit"] = SETTINGS  # the team's file: setup commits it with the step
    off = [{"id": i, "why": c.get("why", ""), "scope": "this repo only (.claude/settings.local.json); --remove undoes it"}
           for i, c in turning_off if f"enabledPlugins.{i}" in ours]
    if off:
        out["turned_off"] = off
    in_repo = conflicts_in_repo(p)
    if in_repo:
        out["conflicts_in_repo"] = in_repo
    skills = skill_companions(p.root)
    if skills:
        out["skills"] = skills
    if skipped:
        out["skipped"] = skipped
    if added_local and excluded:
        out["excluded"] = excluded
    return out


def merge_plugin_keys(p, settings, merge_key, wanted, also_set=None):
    """Adds each (section, key, value) missing from settings, and from also_set (the committed file, which a
    local write never shadows), recording it under merge_key. Returns the tags it added."""
    ours, added = merged_list(p, merge_key), []
    for section, key, value in wanted:
        tag = f"{section}.{key}"
        if tag in added or any(isinstance(s.get(section), dict) and key in s[section] for s in (settings, also_set or {})):
            continue
        settings.setdefault(section, {})[key] = value
        added.append(tag)
        if tag not in ours:
            ours.append(tag)
    return added


def exclude_locally(p, rel_path):
    """Keeps a machine-local file out of git without touching the team's .gitignore: a line in .git/info/exclude
    when git doesn't ignore it yet. Returns the exclude file's path when it added one, else None (or not a repo)."""
    check = subprocess.run(["git", "-C", p.root, "check-ignore", "-q", rel_path], capture_output=True)
    if check.returncode != 1:  # 0: already ignored; 128: not a git repo
        return None
    path = git_out(p, "rev-parse", "--git-path", "info/exclude").strip()
    path = path if os.path.isabs(path) else p.path(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n{rel_path}\n")
    return path.replace(os.sep, "/")


def unmerge_plugin_keys(p, path, merge_key):
    """Takes back the plugin keys sdlc recorded under merge_key from the settings file at path; the user's stay.
    Returns (removed, kept): kept are keys sdlc wrote whose value the user has changed since, which are theirs now."""
    ours = merged_list(p, merge_key)
    if not ours:
        return [], []
    full = fixed_target(p, path)
    settings, removed, kept = read_json(full, {}), [], []
    clash = {c["plugin"] for c in conflicts() if c.get("plugin")}
    for tag in list(ours):
        section, _, key = str(tag).partition(".")
        if section not in ("extraKnownMarketplaces", "enabledPlugins") or not key:
            ours.remove(tag)  # not a shape sdlc writes: drop the record, touch nothing
            continue
        node = settings.get(section)
        if isinstance(node, dict) and key in node:
            # The lock records which keys sdlc wrote, not their values: enable-plugin writes false only for a
            # conflicting plugin and true for the rest, so a key holding the other value was set by the user
            if section == "enabledPlugins" and node[key] is not (key.split("@", 1)[0] not in clash):
                kept.append(tag)
            else:
                del node[key]
                if not node:
                    del settings[section]
                removed.append(tag)
        ours.remove(tag)
    if removed:
        write_json(full, settings)
    p.save()
    return removed, kept


def cmd_gitignore(p, a):
    path = fixed_target(p, GITIGNORE)
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []
    ours = merged_list(p, GITIGNORE)
    added, removed = [], []
    for line in a.add or []:
        if line not in lines:
            lines.append(line)
            added.append(line)
            if line not in ours:
                ours.append(line)
    for line in a.remove or []:
        if line in ours:
            ours.remove(line)
            if line in lines:
                lines.remove(line)
                removed.append(line)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    p.save()
    # A line only ignores untracked files: what was committed before it (the hooks' scratch, say) stays tracked and
    # shows as modified after every run. Untrack it from the index; the files stay on disk
    untracked = []
    for line in a.add or []:
        pattern = ":(glob)" + line.rstrip("/")  # glob magic: `*` stays within a folder, as in .gitignore
        listed = subprocess.run(["git", "-C", p.root, "ls-files", "--", pattern], capture_output=True,
                                encoding="utf-8", errors="replace")
        files = [f for f in listed.stdout.splitlines() if f] if listed.returncode == 0 else []
        if files and subprocess.run(["git", "-C", p.root, "rm", "-r", "--cached", "-q", "--", pattern],
                                    capture_output=True).returncode == 0:
            untracked += files
    return {"added": added, "removed": removed, "owned": ours, "untracked": untracked}


# --- workbench: repos cloned inside a parent workbench repo ----------------------------------

TEMP_PREFIX = ".sdlc-tmp-"  # scaffold's own: the sweep below never touches a file someone else named


def _sweep_temps(folder):
    """Removes scaffold's own temp files (TEMP_PREFIX) in `folder` over an hour old: a kill leaves one behind; a younger
    one may be another writer's, mid-write."""
    for old in glob.glob(os.path.join(glob.escape(folder), TEMP_PREFIX + "*")):
        try:
            if os.path.isfile(old) and not os.path.islink(old) and time.time() - os.path.getmtime(old) > 3600:
                os.remove(old)
        except OSError:
            pass  # gone already, or not ours to remove


def _temp_copy(path, text, errors="strict", newline="\n", folder=None):
    """`text` complete and synced in a temp file in `folder` (default: beside `path`; on the same filesystem); the
    caller moves it into place or removes it. A kill leaves its temp file behind, so this first sweeps that folder's
    old ones (_sweep_temps)."""
    import tempfile
    folder = folder or os.path.dirname(path) or "."
    _sweep_temps(folder)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=TEMP_PREFIX)
    try:
        f = os.fdopen(fd, "w", encoding="utf-8", errors=errors, newline=newline)
    except BaseException:
        for cleanup in (lambda: os.close(fd), lambda: os.remove(tmp)):
            try:
                cleanup()
            except OSError:
                pass  # closed already by the failed wrapper, or held: the original error is the one to see
        raise
    try:
        with f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return tmp


def _write_atomic(path, text, errors="strict", newline="\n", mode=False, temp_dir=None):
    """Temp file in the same folder (or `temp_dir`, on the same filesystem), fsync, rename, the temp file removed on
    failure: a crash never leaves half a committed file. Through a link to the file it names. `mode`: False keeps the
    file's own mode (an ordinary new file's when there is none yet); None gives an ordinary new file's mode (0666
    less the umask); a number sets it. A permission error from the rename (another process has the file open) is
    marked `during_replace`, the only one worth retrying."""
    path = os.path.realpath(path)
    if mode is False:
        try:
            mode = stat.S_IMODE(os.stat(path).st_mode)
        except FileNotFoundError:
            mode = None
    tmp = _temp_copy(path, text, errors, newline, temp_dir)
    try:
        if mode is None:
            umask = os.umask(0)
            os.umask(umask)
            mode = 0o666 & ~umask
        os.chmod(tmp, mode)
        try:
            os.replace(tmp, path)
        except PermissionError as e:
            e.during_replace = True
            raise
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _publish_new(path, text):
    """Write `path` only if nothing is there, never over a file, and never in part: a complete temp file
    hard-linked into place (the link fails on an existing name). Where the filesystem has no hard links, the name is
    claimed with an exclusive create of an empty placeholder, then the temp file replaces that placeholder: never
    over anyone else's file, and a kill leaves the file absent, complete, or (in the instant between the two) empty."""
    tmp = _temp_copy(path, text)
    try:
        os.chmod(tmp, 0o644)  # mkstemp's 0600 would make a rule file other tools can't read
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise
        except OSError:  # no hard links here (FAT, some network shares)
            os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644))  # FileExistsError: someone else's
            try:
                os.replace(tmp, path)
            except BaseException:
                os.remove(path)  # our empty placeholder
                raise
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _workbench_data(p):
    """The manifest file's whole object (validated through sdlc_scopes.manifest), or a new one."""
    sdlc_scopes.manifest(p.root)
    path = p.path(sdlc_scopes.WORKBENCH_FILE)
    return read_json(path) if os.path.exists(path) else {"repos": []}


def _gitignore_lines(p):
    """The workbench's .gitignore lines; bytes that aren't UTF-8 (a cp1252 comment) survive a rewrite unchanged."""
    try:
        with open(fixed_target(p, GITIGNORE), encoding="utf-8", errors="surrogateescape") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return []


def cmd_workbench(p, a):
    """List, add (clone, gitignore, record) or remove (record and gitignore line only) a repo of a workbench, or clone
    the repos it lists that aren't cloned yet."""
    if not sdlc_scopes.is_workbench(p.root, need_manifest=False):
        raise ValueError("not a workbench: .sdlc/config.json has no \"workbench\": true")
    if a.action == "list":
        return {"repos": sdlc_scopes.manifest(p.root)}
    if a.action == "clone":
        return _workbench_clone(p, a.target)
    data = _workbench_data(p)
    if a.action == "remove":
        name = sdlc_scopes.check_name(a.target)
        if not any(r.get("name") == name for r in data["repos"]):
            lines = _gitignore_lines(p)
            if not os.path.lexists(p.path(name)) and f"/{name}/" in (x.strip() for x in lines):
                # removed earlier while its folder was there: the folder is gone now, so the line sdlc wrote goes
                rest = [x for x in lines if x.strip() != f"/{name}/"]
                _write_atomic(fixed_target(p, GITIGNORE), "\n".join(rest) + ("\n" if rest else ""), "surrogateescape")
                return {"removed": name, "folder_kept": None}
            raise ValueError(f"no repo named {name!r} in {sdlc_scopes.WORKBENCH_FILE}")
        data["repos"] = [r for r in data["repos"] if r.get("name") != name]
        _write_atomic(p.path(sdlc_scopes.WORKBENCH_FILE), json.dumps(data, indent=2) + "\n")
        kept = name if os.path.lexists(p.path(name)) else None
        if not kept:  # while the folder is there its ignore line stays, so the workbench never commits the repo
            lines = [x for x in _gitignore_lines(p) if sdlc_scopes.ignored_name(x) != name]
            _write_atomic(fixed_target(p, GITIGNORE), "\n".join(lines) + ("\n" if lines else ""), "surrogateescape")
        return {"removed": name, "folder_kept": kept,
                **({"note": f"/{name}/ stays in .gitignore until you delete {name}/; run remove again after"}
                   if kept else {})}
    url = a.target
    raw_name = a.name if a.name is not None else re.sub(r"\.git$", "", url.rstrip("/\\").replace("\\", "/")
                                                         .rsplit("/", 1)[-1].rsplit(":", 1)[-1])
    entry = {"name": raw_name, "url": url, "role": a.role, "write": bool(a.write)}
    if a.owner:
        entry["owner"] = a.owner
    if a.contract:
        kind, _, version = a.contract.partition(":")
        entry["contract"] = {kind: version}
    checked = sdlc_scopes._check_entry(len(data["repos"]), entry, {str(r.get("name")).lower() for r in data["repos"]})
    name = checked["name"]
    dest = sdlc_scopes.repo_dir(p.root, name)
    if os.path.lexists(dest) and not os.path.isdir(os.path.join(dest, ".git")):
        raise ValueError(f"{name}/ exists and isn't a git repo: move it away or pick another --name")
    added = _ignore(p, name)  # before the clone: a crash after it leaves an ignored folder, never a repo git commits
    try:
        cloned = _clone_into(p, name, url, read_only=not checked["write"])
    except (ValueError, OSError):
        if added:  # a refused clone leaves the .gitignore as it was
            lines = [x for x in _gitignore_lines(p) if sdlc_scopes.ignored_name(x) != name]
            _write_atomic(fixed_target(p, GITIGNORE), "\n".join(lines) + ("\n" if lines else ""), "surrogateescape")
        raise
    data["repos"].append(entry)
    _write_atomic(p.path(sdlc_scopes.WORKBENCH_FILE), json.dumps(data, indent=2) + "\n")
    return {"added": checked, "cloned": cloned}


def _clone_into(p, name, url, read_only=False):
    """Clone url into the workbench's <name>/ (url after `--`, never through a shell); True when it cloned, False when
    <name>/ already is a git repo; ValueError when it exists and isn't one, links outside, or the clone fails."""
    dest = sdlc_scopes.repo_dir(p.root, name)
    if os.path.lexists(dest):
        if not os.path.isdir(os.path.join(dest, ".git")):
            raise ValueError(f"{name}/ exists and isn't a git repo: move it away or pick another --name")
        if read_only:  # adopted as it is: it still never pushes to the other team's remote
            sdlc_scopes.disable_push(dest)
        return False
    proc = subprocess.run(["git", "clone", "-q", "--", sdlc_scopes.check_url(url), dest], capture_output=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode:
        raise ValueError(f"git clone failed: {(proc.stdout + proc.stderr).strip()[-300:]}")
    if read_only:
        try:
            sdlc_scopes.disable_push(dest)
        except ValueError:
            try:
                _remove_tree(dest)  # never left behind able to push to another team's remote
            except OSError:
                pass  # the push error is the one to report
            raise
    return True


def _remove_tree(path):
    """Remove a folder git wrote, its read-only object files too (Windows refuses to delete them)."""
    import stat

    def writable(func, p, _):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=writable)
    else:
        shutil.rmtree(path, onerror=writable)


def _ignore(p, name):
    """Add /<name>/ to the workbench's .gitignore unless a line already ignores it; True when it added one."""
    lines = _gitignore_lines(p)
    if any(sdlc_scopes.ignored_name(x) == name for x in lines):
        return False
    _write_atomic(fixed_target(p, GITIGNORE), "\n".join(lines + [f"/{name}/"]) + "\n", "surrogateescape")
    return True


def _workbench_clone(p, target):
    """Bring back repos the manifest lists but that aren't cloned (a fresh clone of the workbench): the named one, or
    every missing one; the URL comes from the validated manifest, never from the command line."""
    repos = sdlc_scopes.manifest(p.root)
    if target:
        name = sdlc_scopes.check_name(target)
        repos = [r for r in repos if r["name"] == name]
        if not repos:
            raise ValueError(f"no repo named {name!r} in {sdlc_scopes.WORKBENCH_FILE}")
    cloned, present, failed = [], [], []
    for r in repos:  # one repo failing never hides what the others did
        _ignore(p, r["name"])
        try:
            (cloned if _clone_into(p, r["name"], r["url"], read_only=not r["write"]) else present).append(r["name"])
        except (ValueError, OSError) as e:
            failed.append({"name": r["name"], "error": str(e)})
    out = {"cloned": cloned, "already_cloned": present}
    if failed:
        raise CommandsFailed(dict(out, failed=failed))
    return out


# --- hosts: which coding agents run this repo's sdlc ---------------------------------------
# Neither signal is an official contract: the plugin's install folder names its host reliably, the environment
# markers vary between releases, so the folder wins and the environment only decides when it is unambiguous.

HOSTS = ("claude-code", "codex", "cursor", "antigravity")
HOST_PATHS = [("claude-code", "/.claude/plugins/"), ("codex", "/.codex/plugins/"), ("cursor", "/.cursor/"),
              ("antigravity", "/.gemini/"), ("antigravity", "/.agents/plugins/")]
HOST_ENV = [("claude-code", ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")),
            ("codex", ("CODEX_THREAD_ID", "CODEX_SANDBOX", "CODEX_CI")),
            ("cursor", ("CURSOR_AGENT", "CURSOR_TRACE_ID")), ("antigravity", ("ANTIGRAVITY_AGENT",))]


def detect_host(env=None):
    env = os.environ if env is None else env
    norm = lambda x: os.path.abspath(x).replace("\\", "/").lower().rstrip("/") + "/"
    where = norm(PLUGIN_ROOT)
    by_path = next((h for h, marker in HOST_PATHS if marker in where), None)
    for h, var in (("claude-code", "CLAUDE_CONFIG_DIR"), ("codex", "CODEX_HOME")):  # a relocated config folder
        if not by_path and env.get(var) and where.startswith(norm(env[var])):
            by_path = h
    by_env = [h for h, keys in HOST_ENV if any(env.get(k) for k in keys)]
    if by_path:
        return {"host": by_path, "via": "install path", "environment": by_env}
    if len(by_env) == 1:
        return {"host": by_env[0], "via": "environment", "environment": by_env}
    return {"host": None, "via": None, "environment": by_env}  # nested agents or none: only the user can say


def hosts(p):
    """Hosts that have run setup here. Locks from before hosts were recorded were all written by Claude Code."""
    return list((p.lock or {}).get("hosts") or ["claude-code"])


def valid_host(h):
    if h not in HOSTS:
        raise ValueError(f"unknown host {h!r} (known: {', '.join(HOSTS)})")
    return h


def cmd_host(p, a):
    found = detect_host()
    out = dict(found, set_up=p.lock is not None)
    if p.lock is not None:
        out["hosts"] = hosts(p)
        out["joining"] = found["host"] is not None and found["host"] not in out["hosts"]
    return out


def cmd_add_host(p, a):
    lock = p.require_lock()
    current = hosts(p)
    added = valid_host(a.host) not in current
    if added:
        lock["hosts"] = current + [a.host]
        p.save()
    return {"hosts": hosts(p), "added": added}


# --- AGENTS.md: the project's instructions for Codex, Cursor and Antigravity ----------------
# All three read the root AGENTS.md (Codex caps the combined size at 32 KiB), so one managed block serves them and
# nothing loads twice. Content is copied in, not pointed to, so every line passes CLAUDE_ONLY. Claude Code doesn't
# read AGENTS.md: what the team wrote there outside the block is mirrored into a generated rule for it.

AGENTS_BLOCK = re.compile(r"<!-- sdlc:begin\b[^\n]*?-->.*?<!-- sdlc:end -->(?:\r?\n)?", re.S)
AGENTS_WORKFLOW = "templates/project/agents/workflow.md"
AGENTS_MIRROR = ".claude/rules/sdlc-agents-md.md"
CODEX_DOC_BYTES = 32 * 1024  # Codex's default project_doc_max_bytes: it reads AGENTS.md text up to this, then stops
# (pattern, replacement); None means no equivalent outside Claude Code, so the build stops at that line
CLAUDE_ONLY = [
    (re.compile(r"^@(\S+)\s*$"), r"Also read `\1`."),  # CLAUDE.md import line
    (re.compile(r"`?/sdlc:([a-z][a-z-]*)`?"), r"`/sdlc:\1` (Claude Code)"),
    (re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?"), None),
    (re.compile(r"\bscaffold\.py\b"), None),
]


def for_other_tools(text, source):
    """Strip frontmatter and managed-file comments, demote headings two levels, map Claude-only constructs."""
    lines = re.sub(r"^---\n.*?\n---\n", "", text.replace("\r\n", "\n"), count=1, flags=re.S).split("\n")
    out, fenced = [], False
    for n, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced and re.fullmatch(r"\s*<!--.*-->\s*", line):
            continue
        if not fenced and line.startswith("#"):
            line = "##" + line
        for rx, repl in CLAUDE_ONLY:
            if fenced and repl is not None:
                continue  # `@pytest.fixture` in a code sample is not an import
            if rx.search(line):
                if repl is None:
                    raise ValueError(f"{source}:{n}: `{rx.search(line).group(0)}` only works in Claude Code; "
                                     f"reword that line, then run `scaffold.py agents` again")
                line = rx.sub(repl, line)
        out.append(line)
    return "\n".join(out).strip("\n")


def rule_scope(text):
    m = re.match(r"^---\n(.*?)\n---", text.replace("\r\n", "\n"), re.S)
    if not m or "paths:" not in m.group(1):
        return []
    return [x.strip().strip("\"'") for x in re.findall(r"^\s*-\s*(.+)$", m.group(1).split("paths:", 1)[1], re.M)]


def area_rules(p):
    """[(source, text)]: the plugin's policy rules rendered from its templates, then the team's own .claude/rules.
    sdlc.md is the Claude Code workflow; the block's workflow section replaces it."""
    rules = []
    d = os.path.join(PLUGIN_ROOT, "templates", "project", "rules")
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if name.endswith(".md") and name != "sdlc.md":
            with open(os.path.join(d, name), encoding="utf-8") as f:
                rules.append((f"templates/project/rules/{name}", render_text(f.read(), p)))
    for path in sorted(glob.glob(p.path(".claude/rules/*.md"))):
        if not os.path.basename(path).startswith("sdlc"):
            text, why = repo_text(p.root, os.path.relpath(path, p.root))
            if not why:
                rules.append((f".claude/rules/{os.path.basename(path)}", text))
    return rules


def agents_block(p):
    """The managed block (LF), or None when no recorded host reads AGENTS.md."""
    if not set(hosts(p)) - {"claude-code"}:
        return None
    with open(os.path.join(PLUGIN_ROOT, AGENTS_WORKFLOW), encoding="utf-8") as f:
        parts = [f"<!-- sdlc:begin · generated by sdlc {plugin_version()} from CLAUDE.md, .claude/rules/ and the "
                 "plugin's policy rules; edit those, then rebuild it with the sdlc setup or upgrade -->",
                 "## Working in this repo (sdlc)", render_text(f.read(), p).strip()]
    text, why = repo_text(p.root, "CLAUDE.md") if os.path.lexists(p.path("CLAUDE.md")) else (None, "absent")
    if not why:
        parts += ["## Project instructions (from CLAUDE.md)", for_other_tools(text, "CLAUDE.md")]
    rules = area_rules(p)
    if rules:
        parts.append("## Area rules")
    for source, text in rules:
        body = for_other_tools(text, source)
        heading = re.match(r"^### (.+)\n*", body)
        title = heading.group(1) if heading else os.path.basename(source)[:-3]
        body = body[heading.end():] if heading else body
        scope = rule_scope(text)
        # Codex has no per-file scoping and the globs are file types, not folders, so the scope is stated
        applies = ("Applies when working on files matching " + ", ".join(f"`{g}`" for g in scope) + "."
                   if scope else "Applies to all files.")
        parts += [f"### {title}", applies, body]
    return "\n\n".join(x for x in parts if x) + "\n\n<!-- sdlc:end -->\n"


def agents_md_text(p):
    if fixed_problem(p, AGENTS):  # through a link out of the repo or into .git: never read, so never mirrored
        return None
    try:
        with open(p.path(AGENTS), encoding="utf-8", newline="") as f:  # newline="": keep the file's CRLF or LF
            return f.read()
    except FileNotFoundError:
        return None


def agents_mirror(p):
    """The rule that shows Claude Code the team's own AGENTS.md text, or None when there's nothing to show."""
    text = agents_md_text(p)
    # Only once another agent shares the repo: a Claude-only setup already migrated AGENTS.md into its own files
    if "claude-code" not in hosts(p) or not set(hosts(p)) - {"claude-code"} or not text:
        return None
    own = AGENTS_BLOCK.sub("", text).replace("\r\n", "\n").strip()
    if not own:
        return None
    return ("<!-- Managed by the sdlc plugin: AGENTS.md without its sdlc block, so Claude Code follows what the team "
            "wrote for other agents. Edit AGENTS.md; setup and upgrade refresh this file. -->\n" + own + "\n")


def codex_cut(p):
    """Why Codex misses part of the block, or None. The root AGENTS.md comes first in what Codex reads and the block
    sits at its end, so a root file over the cap loses the block's tail; nested AGENTS.md files come after it."""
    text = agents_md_text(p)
    size = len(text.encode("utf-8")) if text else 0
    if "codex" not in hosts(p) or size <= CODEX_DOC_BYTES or not AGENTS_BLOCK.search(text):
        return None
    return (f"{AGENTS} is {size // 1024} KiB and Codex reads only the first {CODEX_DOC_BYTES // 1024} KiB, so it misses "
            "the end of the sdlc block: shorten CLAUDE.md, .claude/rules/ or AGENTS.md's own text, or raise "
            "project_doc_max_bytes in ~/.codex/config.toml")


def agents_state(p):
    """off | in_sync | stale: AGENTS.md's block and the Claude Code mirror against a fresh build (line endings ignored)."""
    want, mirror = agents_block(p), agents_mirror(p)
    have = AGENTS_BLOCK.search(agents_md_text(p) or "")
    tracked = (p.lock or {}).get("files", {}).get(AGENTS_MIRROR)
    if want is None and have is None and mirror is None and not tracked:
        return "off"
    block_ok = (want is None and have is None) or (
        want is not None and have is not None
        and have.group(0).replace("\r\n", "\n").rstrip("\n") == want.rstrip("\n"))
    mirror_ok = (mirror is None and not tracked) or (
        mirror is not None and tracked is not None
        and inside_repo(p.root, AGENTS_MIRROR)  # through a link out of the repo: never read
        and sha256(p.path(AGENTS_MIRROR)) == hashlib.sha256(mirror.encode("utf-8")).hexdigest())
    return "in_sync" if block_ok and mirror_ok else "stale"


def write_agents(p, want):
    """Put `want` in AGENTS.md's managed block, or remove the block when it's None. Text outside it is kept as is."""
    ours = merged_list(p, AGENTS_MERGE)
    if want is None and not ours:  # no block to write or take back: AGENTS.md is the team's, never opened
        return "off"
    path = fixed_target(p, AGENTS)
    text = agents_md_text(p)
    existed = text is not None
    text = text or ""
    eol = "\r\n" if "\r\n" in text else "\n"
    have = AGENTS_BLOCK.search(text)
    if want is None:
        if not have:
            return "off"
        before, after = text[:have.start()], text[have.end():]
        if not after and before.endswith(eol * 2):
            before = before[:-len(eol)]  # the blank line the build put before the block
        text = before + after
        if "file" in ours and not text.strip():
            os.remove(path)
        else:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        ours.clear()
        p.save()
        return "removed"
    block = want.replace("\n", eol)
    if have:
        text = text[:have.start()] + block + text[have.end():]
    else:
        text += ((eol if not text.endswith(eol) else "") + eol if text else "") + block
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    for tag in ["block"] + ([] if existed else ["file"]):
        if tag not in ours:
            ours.append(tag)
    p.save()
    return "written"


def write_mirror(p):
    files = p.require_lock()["files"]
    if agents_mirror(p) is not None:
        return cmd_render(p, argparse.Namespace(template="builtin:agents-mirror", dest=AGENTS_MIRROR,
                                                cls="generated", if_unchanged=False))["rendered"]
    if AGENTS_MIRROR in files and not inside_repo(p.root, AGENTS_MIRROR):
        return None  # through a link out of the repo: kept, and still recorded so upgrade and eject list it
    if files.pop(AGENTS_MIRROR, None) is not None:
        if os.path.exists(p.path(AGENTS_MIRROR)):
            os.remove(p.path(AGENTS_MIRROR))
        p.save()
    return None


def cmd_agents(p, a):
    p.require_lock()
    if a.check:
        if agents_state(p) == "stale":
            raise ValueError(f"{AGENTS} or its Claude Code mirror is out of date with CLAUDE.md, .claude/rules/, "
                             "AGENTS.md or the recorded hosts; run `scaffold.py agents`")
        return {"state": agents_state(p), "hosts": hosts(p)}
    out = {"result": write_agents(p, agents_block(p)), "mirror": write_mirror(p), "hosts": hosts(p)}
    cut = codex_cut(p)
    return dict(out, warning=cut) if cut else out


# --- migrations ---------------------------------------------------------------------------

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def all_migrations():
    d = os.path.join(PLUGIN_ROOT, "migrations")
    found = []
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith(".md") or name.lower() == "readme.md":
            continue
        with open(os.path.join(d, name), encoding="utf-8") as f:
            fm = frontmatter(f.read())
        mid = name[:-3]
        version = fm.get("version") or mid.split("-", 1)[0]
        found.append({"id": mid, "version": version, "summary": fm.get("summary", ""),
                      "min_plugin_version": fm.get("min_plugin_version"),
                      "path": os.path.join("migrations", name).replace(os.sep, "/")})
    return sorted(found, key=lambda m: (parse_version(m["version"]), m["id"]))


def pending_migrations(p):
    lock = p.require_lock()
    sv = parse_version(lock.get("scaffold_version", "0.0.0"))
    pv = parse_version(plugin_version())
    done = set(lock.get("migrations", {}).get("applied", [])) | set(lock.get("migrations", {}).get("skipped", {}))
    return [m for m in all_migrations()
            # a release's migrations apply from its first candidate on (rc.1 runs 3.5.0's); the ids already
            # applied keep a later candidate from running them twice
            if sv < parse_version(m["version"]) and parse_version(m["version"])[:3] <= pv[:3]
            and m["id"] not in done]


def cmd_migrations(p, a):
    lock = p.require_lock()
    out = {"pending": pending_migrations(p)}
    if a.revisit:
        skipped = lock.get("migrations", {}).get("skipped", {})
        out["skipped"] = [dict(m, reason=skipped[m["id"]]) for m in all_migrations() if m["id"] in skipped]
    return out


def cmd_migration(p, a):
    known = {m["id"] for m in all_migrations()}
    if a.id not in known:
        raise ValueError(f"unknown migration {a.id!r}")
    mig = p.require_lock().setdefault("migrations", {"applied": [], "skipped": {}})
    applied, skipped = mig.setdefault("applied", []), mig.setdefault("skipped", {})
    if a.applied:
        skipped.pop(a.id, None)
        if a.id not in applied:
            applied.append(a.id)
    else:
        if a.id in applied:
            raise ValueError(f"{a.id} is already applied")
        skipped[a.id] = a.skipped
    p.save()
    return {"applied": applied, "skipped": skipped}


def old_features(p):
    """Active features started under sdlc 1.x (no `Process:` line): finished on 1.8.1 before a repo moves to 2.0."""
    found = []
    for name, f in sorted(sdlc_layout.features(p.root).items()):
        try:
            with open(p.path(f["state"]), encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        if re.search(r"^Status:\s*active\b", text, re.M | re.I) and not re.search(r"^Process:\s*[23]\b", text, re.M):
            found.append(name)
    return found


def cmd_prd(p, a):
    """The product doc's path; with a path, records it in config (`prd`): a PRD the repo already has, used as is, or
    the one setup just wrote. User-owned: the plugin never writes it after setup, and eject keeps it."""
    if a.path:
        path = sdlc_layout.validate_docs_dir(rel(p.root, a.path))
        if not os.path.isfile(p.path(path)):
            raise Refused(f"{path} not found: write the PRD first, then record it")
        p.config = p.config or {}
        p.config["prd"] = path
        p.save()
    path = sdlc_layout.prd(p.root)
    return {"prd": path, "exists": os.path.isfile(p.path(path))}


def cmd_add_config_keys(p, a):
    """sdlc 3.5's per-package keys (spec 03 S12), only in a spec-backed repo (an rspec criteria lock or an
    acceptance bundle): `accept.start` and `accept.base_url`, which start and reach the local build for recorded
    acceptance tests, added empty where missing; set values are kept. Elsewhere it adds nothing. The 3.5.0 migration
    runs it; safe to run twice."""
    if p.config is None:
        raise Refused(f"no {CONFIG}: set the repo up first (/sdlc:setup)")
    import spec_lock  # sibling script: what makes a repo spec-backed
    if not spec_lock.spec_backed_repo(p.root):
        return {"added": [], "note": "not a spec-backed repo (no criteria.lock.json or acceptance/manifest.json): "
                                     "nothing to add"}
    pkgs = p.config.get("packages") or []
    targets = [(pk.get("name") or "?", pk) for pk in pkgs] or [(ROOT_SCOPE, p.config)]
    added = []
    for name, entry in targets:
        where = "" if name == ROOT_SCOPE else f"{name}: "
        if "accept" in entry and entry["accept"] is None:  # null: no build to reach, left as the user set it
            continue
        accept = entry["accept"] = entry.get("accept") if isinstance(entry.get("accept"), dict) else {}
        for key in ("start", "base_url"):
            if key not in accept:
                accept[key] = ""
                added.append(f"{where}accept.{key}")
    if added:
        p.save()
    return {"added": added}


DEPLOY_TARGETS = ("none", "docker-compose", "gcp-cloud-run", "vercel", "cloudflare", "other")
DEFAULT_RUNBOOK = "knowledge/runbooks/deploy.md"


# never routine, whatever the config says: a committed config is untrusted, and production keeps its go-ahead.
# A name is production when any of its parts is one of these (`prod-eu`, `eu.live`); names are plain ASCII, so no
# space, zero-width or look-alike character can split or hide a part.
PRODUCTION_ENVS = ("prod", "production", "live", "prd")
ENV_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# /sdlc:deploy appends to the runbook: never a hook, the agent's settings or sdlc's own state
RUNBOOK_EXCLUDED = (".git", ".claude", ".sdlc")


def is_production(name):
    return any(part in PRODUCTION_ENVS for part in re.split(r"[._-]", name.lower()))


def runbook_path(root, value):
    """`value` as a normalised repo-relative path to a Markdown file inside the repo and outside `.git/`, `.claude/`
    and `.sdlc/`, checked again after symlinks are resolved; else None."""
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.replace("\\", "/")
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        return None
    norm = posixpath.normpath(raw)
    if norm in (".", "..") or norm.startswith("../"):
        return None
    real_root, real = os.path.realpath(root), os.path.realpath(os.path.join(root, norm))
    if not real.startswith(real_root + os.sep):
        return None
    for path in (norm, os.path.relpath(real, real_root).replace(os.sep, "/")):
        parts = path.split("/")
        if not path.lower().endswith(".md") or parts[0].rstrip(". ").lower() in RUNBOOK_EXCLUDED or \
                any(_git_segment(x) for x in parts):  # a git dir at any depth, in any spelling
            return None
    return norm


def stored_deploy(p):
    """config `deploy` with every value checked, since repo config is untrusted: a bad one is reported as null (or
    dropped, or a routine production made non-routine) and named in the second value."""
    current = (p.config or {}).get("deploy")
    current = current if isinstance(current, dict) else {}
    invalid = set()
    target = current.get("target")
    if target is not None and target not in DEPLOY_TARGETS:
        invalid.add("target")
        target = None
    raw_envs = current.get("environments", [])
    if not isinstance(raw_envs, list):
        invalid.add("environments")
        raw_envs = []
    envs = []
    for e in raw_envs:
        name = e.get("name") if isinstance(e, dict) else None
        if not isinstance(name, str) or not ENV_NAME.fullmatch(name) or any(x["name"] == name for x in envs):
            invalid.add("environments")
            continue
        routine = e.get("routine") is True
        if routine and is_production(name):
            invalid.add(f"environments.{name}.routine")
            routine = False
        envs.append({"name": name, "routine": routine})
    runbook = runbook_path(p.root, current.get("runbook", DEFAULT_RUNBOOK))
    if runbook is None:
        invalid.add("runbook")
    return {"target": target, "environments": envs, "runbook": runbook}, sorted(invalid)


def cmd_deploy(p, a):
    """How the project deploys (config `deploy`): the target, the environments, each routine (deploys without a
    go-ahead) or not, and the runbook /sdlc:deploy follows. With flags, records what they give and keeps the rest;
    --env replaces the whole list. A production name is never routine. Prints only checked values: a stored one that
    fails its check is null and listed in `invalid`, and recording drops it."""
    if a.target is not None and a.target not in DEPLOY_TARGETS:
        raise Refused(f"deploy target is one of {', '.join(DEPLOY_TARGETS)}, not {a.target!r}")
    envs = []
    for spec in a.env or []:
        name, _, flag = spec.partition(":")
        name = name.strip()
        if not ENV_NAME.fullmatch(name) or flag not in ("", "routine"):
            raise Refused(f"--env takes NAME or NAME:routine, NAME in letters, digits, '.', '_' and '-', not {spec!r}")
        if any(e["name"] == name for e in envs):
            raise Refused(f"environment {name!r} given twice")
        if flag and is_production(name):
            raise Refused(f"{name!r} is production: it always needs the go-ahead, so it can't be routine")
        envs.append({"name": name, "routine": flag == "routine"})
    runbook = None
    if a.runbook is not None:
        runbook = runbook_path(p.root, a.runbook)
        if runbook is None:
            raise Refused(f"runbook {a.runbook!r} is not a file path inside the repo")
    deploy, invalid = stored_deploy(p)
    if a.target is not None or a.env or runbook is not None:
        if a.target is not None:
            deploy["target"] = a.target
        if a.env:
            deploy["environments"] = envs
        deploy["runbook"] = runbook or deploy["runbook"] or runbook_path(p.root, DEFAULT_RUNBOOK)
        p.config = p.config or {}
        p.config["deploy"] = {k: v for k, v in deploy.items() if v is not None}
        p.save()
        deploy, invalid = stored_deploy(p)
    out = {"deploy": deploy}
    if invalid:
        out["invalid"] = invalid
    return out


OBJECT_INPUTS_MAX = 40


OBJECT_SOURCE = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".go", ".rb", ".java", ".kt", ".cs", ".php",
                 ".rs", ".swift", ".dart", ".ex", ".exs", ".scala", ".prisma", ".sql", ".graphql", ".gql", ".proto"}
OBJECT_SKIP_DIRS = {"test", "tests", "__tests__", "spec", "specs", "fixtures", "__fixtures__", "e2e", "docs", "doc",
                    "examples", "vendor", "node_modules", "dist", "build", "generated", "__generated__"}
OBJECT_KINDS = (  # rank, then a test on (folder names, lower-case base name): schema first, migrations last
    (0, lambda d, b: b.endswith((".prisma", ".proto")) or b.startswith(("schema.", "schemas.")) and not b.endswith(".py")),
    (1, lambda d, b: b.startswith(("models.", "schemas.", "schema.")) or ".entity." in b or ".model." in b
        or {"models", "model", "entities", "entity", "schemas"} & d),
    (2, lambda d, b: b.startswith(("types.", "enums.", "enum.")) or b.endswith(".d.ts") or {"types", "enums"} & d),
    (3, lambda d, b: b.startswith(("routes.", "router.", "urls.")) or {"routes", "api", "controllers"} & d),
)


def object_kind(path):
    """The rank of a tracked file as a drafting input (lower first), or None when it isn't one: source code only, no
    tests, docs, vendored or generated folders; a migration ranks last."""
    parts = path.lower().split("/")
    base, dirs = parts[-1], set(parts[:-1])
    if os.path.splitext(base)[1] not in OBJECT_SOURCE or dirs & OBJECT_SKIP_DIRS:
        return None
    if re.search(r"(^test_|[._-](test|spec)\.)", base) or re.search(r"(^|[._-])(seeds?|dump|fixtures?)([._-]|$)", base):
        return None
    if "migration" in path.lower() or "migrate" in dirs:
        return 4 if base.endswith(".sql") or {"migrations", "migrate"} & dirs else None
    for rank, test in OBJECT_KINDS:
        if test(dirs, base):
            return rank
    return 3 if base.endswith((".sql", ".graphql", ".gql")) else None


def tracked_regular_files(p):
    """Tracked paths that are regular files git stores in the repo: from the raw index (`-s -z`, so no name is quoted),
    without links (mode 120000), without a name holding a control or format character, and without any whose real
    path leaves the repo. [] when it isn't a git repo."""
    import objects
    import spec_lock
    try:
        raw = git_out(p, "ls-files", "-s", "-z")
    except (OSError, ValueError):
        return []
    out = []
    for entry in raw.split("\0"):
        meta, _, path = entry.partition("\t")
        if not path or meta.startswith("120000") or objects._odd(path) or spec_lock.inside(p.root, path) is None:
            continue
        out.append(path)
    return list(dict.fromkeys(out))  # an unmerged path is in the index once per stage


def object_inputs(p):
    """What `/sdlc:setup objects` drafts from: the PRD and impeccable's PRODUCT.md (each only when it is a regular file
    inside the repo), and the tracked source files that look like schema, models, types, enums or routes, ranked in
    that order with migrations last, at most OBJECT_INPUTS_MAX; `more` counts the ones left out."""
    import spec_lock

    def own_file(rel):
        full = spec_lock.inside(p.root, rel)
        return rel if full and os.path.isfile(full) and not os.path.islink(p.path(rel)) else None

    ranked = sorted((r, f) for f in tracked_regular_files(p) for r in [object_kind(f)] if r is not None)
    out = {"prd": own_file(sdlc_layout.prd(p.root)), "product": own_file("PRODUCT.md"),
           "files": [f for _, f in ranked[:OBJECT_INPUTS_MAX]]}
    if len(ranked) > OBJECT_INPUTS_MAX:
        out["more"] = len(ranked) - OBJECT_INPUTS_MAX
    return out


def cmd_objects(p, a):
    """The domain model (spec 13): the objects file's path, whether it exists and is on, and what to draft it from.
    With --enable, turns `objects` on in config, only in a set-up repo that isn't spec-backed (rspec's domain.md is the
    model there), and only once the file exists and `objects.py check` finds no error."""
    import objects  # the scripts' own check: one path rule and one file check for setup, Define and doctor
    import spec_lock
    if a.enable:
        if p.lock is None:
            raise ValueError("this repo isn't set up for sdlc yet: run /sdlc:setup first")
        if not (p.lock.get("setup") or {}).get("complete"):
            raise Refused("setup isn't finished yet: finish /sdlc:setup first, then /sdlc:setup objects")
    spec_backed = spec_lock.spec_backed_repo(p.root)
    value = (p.config or {}).get("objects")
    off = value is None or value is False  # exactly as objects.path() reads it: 0 and "" are values to judge
    rel, invalid = None, None
    try:  # the same rule Define's check uses, whether or not the switch is on yet
        rel = objects.target(p.root, True if off else value)
    except ValueError as e:
        invalid = str(e) if off else f"objects {value!r}: {e}"
    out = {"path": rel, "exists": bool(rel) and os.path.isfile(p.path(rel)),
           "on": not off and invalid is None and not spec_backed, "spec_backed": spec_backed}
    if invalid:
        out["invalid"] = invalid
    if not a.enable:
        out["inputs"] = object_inputs(p)
        return out
    if spec_backed:
        raise Refused("this repo is spec-backed: rspec's <spec>/domain.md is its domain model, and sdlc never writes it")
    if invalid:
        raise Refused(invalid)
    if not out["exists"]:
        raise Refused(f"no {rel} yet: draft it with the user first (/sdlc:setup objects)")
    errors = [x for x in objects.check_file(p.root, rel) if x.severity == "error"]
    if errors:
        raise Refused(f"{rel} fails objects.py check: " + "; ".join(f"{x.code}: {x}" for x in errors))
    p.config = p.config or {}
    p.config["objects"] = value if isinstance(value, str) else True
    p.save()
    out["on"] = True
    return out


def cmd_set_version(p, a):
    lock = p.require_lock()
    if parse_version(a.version)[0] >= 2 and old_features(p):
        raise Refused("finish these with sdlc 1.8.1 first: " + ", ".join(old_features(p)))
    lock["scaffold_version"] = a.version
    if a.min_plugin:
        parse_version(a.min_plugin)
        p.config = p.config or {}
        current = p.config.get("min_plugin_version", "0.0.0")
        if parse_version(a.min_plugin) > parse_version(current):  # never lowers the pin
            p.config["min_plugin_version"] = a.min_plugin
    p.save()
    return {"scaffold_version": lock["scaffold_version"],
            "min_plugin_version": (p.config or {}).get("min_plugin_version")}


# --- upgrade / eject plans ---------------------------------------------------------------

def cmd_upgrade_plan(p, a):
    lock = p.require_lock()
    plan = {"from": lock.get("scaffold_version"), "to": plugin_version(),
            "add": [], "regenerate": [], "replace": [], "review": [], "restore": [], "template_gone": [],
            "outside": []}
    tracked, declined = lock.get("files", {}), set(lock.get("declined", []))
    # new in this plugin version; the rules and guardrails are Claude Code's, the other hosts get them in AGENTS.md
    for tpl, dest, cls in shipped_files(p) if "claude-code" in hosts(p) else []:
        if dest not in tracked and dest not in declined:
            if not inside_repo(p.root, dest) or git_internal(dest, p.root):  # links out, or into .git: never rendered
                plan["outside"].append(dest)
                continue
            item = {"path": dest, "template": tpl, "class": cls}
            if os.path.exists(p.path(dest)):
                item["exists"] = True  # a file the plugin never wrote is in the way: review, never overwrite
            plan["add"].append(item)
    # the invariants check sits next to the verify workflow, for every host: offered to repos that chose CI
    if any(re.fullmatch(r"\.github/workflows/sdlc-verify(-.+)?\.yml", path) for path in tracked):
        for tpl, dest in INVARIANTS:
            if dest not in tracked and dest not in declined:
                if not inside_repo(p.root, dest) or git_internal(dest, p.root):
                    plan["outside"].append(dest)
                    continue
                item = {"path": dest, "template": tpl, "class": "seeded"}
                if os.path.exists(p.path(dest)):
                    item["exists"] = True
                plan["add"].append(item)
    for path, e in sorted(lock.get("files", {}).items()):
        tpl = e.get("template")
        if not tpl:
            continue
        if not inside_repo(p.root, path) or git_internal(path, p.root):  # links out, or into .git: never rendered
            plan["outside"].append(path)
            continue
        if not template_exists(tpl):
            plan["template_gone"].append(path)
            continue
        state = p.file_state(path, e)
        item = {"path": path, "template": tpl}
        if state == "outside":  # through a link out of the repo: listed, never rendered over
            plan["outside"].append(path)
        elif e["class"] == "generated" and not (state == "modified" and p.untracked(path)):
            plan["regenerate"].append(item)
        elif state == "unchanged":
            new = hashlib.sha256(render_source(tpl, p).encode("utf-8")).hexdigest()
            if p.merged(e):  # the user's merge: offered again only when the template moved on since
                if new != e.get("render_sha256"):
                    plan["review"].append(item)
            elif new != e.get("sha256"):
                plan["replace"].append(item)
        elif state == "modified":
            plan["review"].append(item)
        else:
            plan["restore"].append(item)  # user deleted a seeded file: offer, never force
    try:  # stale: run `agents` to rebuild AGENTS.md's block
        plan["agents"] = agents_state(p)
    except ValueError as e:  # a Claude-only line in CLAUDE.md shouldn't block the rest of the upgrade
        plan["agents"] = f"error: {e}"
    plan["conventions"] = convention_updates(p)  # user-owned: offered as a diff, never replaced
    plan["pending_migrations"] = pending_migrations(p)
    plan["old_features"] = old_features(p)  # 2.0 can't run them: the upgrade stops until they're finished on 1.8.1
    return plan


def eject_plan(p):
    lock = p.require_lock()
    layout = sdlc_layout.paths(p.root)
    keep = [CONFIG, sdlc_layout.prd(p.root), layout["constitution"], layout["design_system"], ".sdlc/baseline.md",
            "knowledge/", layout["docs_dir"] + "/capabilities/",  # the living spec (#73), when it's on
            layout["docs_dir"] + "/objects.md",  # the domain model (spec 13), user-owned
            layout["state_root"] + ("<feature>.md" if layout["layout"] == "new" else "<feature>/"),
            layout["changes_root"] + ("<feature>.md" if layout["layout"] == "new" else "<feature>/change.md"),
            layout["intents_root"] + "<feature>/"]
    try:  # a path config's `objects` names, when the rules accept it (eject never deletes it either way: it's not locked)
        import objects
        named = objects.path(p.root)
        if named:
            keep.append(named)
    except ValueError:
        pass
    # Only what is there: the report reads this list, and a repo may have no baseline, design system or features
    keep = [k for k in dict.fromkeys(keep) if os.path.exists(p.path(k.split("<feature>")[0]))]
    plan = {"delete": [], "ask": [], "already_gone": [], "outside": [], "unmerge": lock.get("merged", {}),
            "keep": keep}
    for path, e in sorted(lock.get("files", {}).items()):
        state = "outside" if git_internal(path, p.root) else p.file_state(path, e)
        if state == "outside":  # through a link out of the repo, or into .git: listed, never read or deleted
            plan["outside"].append(path)
            continue
        if state == "missing":
            plan["already_gone"].append(path)
        elif (e["class"] == "generated" and not (state == "modified" and p.untracked(path))) or (
                state == "unchanged" and not p.merged(e)):
            plan["delete"].append(path)
        else:
            plan["ask"].append(path)
    # a fixed-name file through a link out of the repo or into .git, with something recorded to unmerge from it:
    # listed (the user unmerges it by hand), never read or unmerged; one sdlc never merged into isn't named
    merged = lock.get("merged", {})
    recorded = {f: any(merged.get(k) for k in keys) for f, keys in UNMERGE_KEYS.items()}
    plan["outside"] += [f for f in FIXED_FILES if recorded.get(f) and fixed_problem(p, f) and f not in plan["outside"]]
    return plan


def _is_link(path):
    """A symlink, or a Windows junction (which os.path.islink doesn't report before Python 3.12)."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISLNK(st.st_mode) or getattr(st, "st_reparse_tag", 0) in (0xA0000003, 0xA000000C)  # junction, link


def cmd_eject(p, a):
    plan = eject_plan(p)
    if not a.apply:
        return plan
    extra = [rel(p.root, x) for x in a.also or []]
    unknown = [x for x in extra if x not in plan["ask"]]
    if unknown:
        raise ValueError("--also only accepts files listed under 'ask': " + ", ".join(unknown))
    deleted = []
    for path in plan["delete"] + extra:
        os.remove(p.path(path))
        deleted.append(path)
        d = os.path.dirname(p.path(path))
        while d != p.root and os.path.isdir(d) and not os.listdir(d):  # tidy dirs we emptied
            os.rmdir(d)
            d = os.path.dirname(d)
    skip = set(plan["outside"])
    allow = [] if SETTINGS in skip else list(plan["unmerge"].get(SETTINGS, []))  # copies: unmerge empties them
    if allow:
        cmd_allow(p, argparse.Namespace(add=[], remove=list(allow)))
    plugin_keys, plugin_kept = ([], []) if LOCAL_SETTINGS in skip else unmerge_plugin_keys(p, LOCAL_SETTINGS, PLUGIN_MERGE)
    team_keys, team_kept = ([], []) if SETTINGS in skip else unmerge_plugin_keys(p, SETTINGS, TEAM_PLUGIN_MERGE)
    ignore = [] if GITIGNORE in skip else list(plan["unmerge"].get(GITIGNORE, []))
    if ignore:
        cmd_gitignore(p, argparse.Namespace(add=[], remove=list(ignore)))
    agents = AGENTS not in skip and plan["unmerge"].get(AGENTS_MERGE) and write_agents(p, None) == "removed"
    os.remove(p.path(LOCK))
    p.lock = None
    work = p.path(".sdlc/.work")  # scratch; its .gitignore line is gone, so don't leave it to be committed
    scratch_removed = os.path.isdir(work)
    if _is_link(work):  # a committed link: remove the link itself, never what it points to
        try:
            os.unlink(work)
        except OSError:  # a Windows directory link or junction
            os.rmdir(work)
        scratch_removed = True
    elif scratch_removed:
        shutil.rmtree(work)
    out = {"deleted": deleted, "kept_edited": [x for x in plan["ask"] if x not in extra], "scratch_removed": scratch_removed,
           "unmerged": {SETTINGS: allow + team_keys, LOCAL_SETTINGS: plugin_keys, GITIGNORE: ignore, AGENTS: ["sdlc block"] if agents else []},
           "lock_removed": True, "outside": plan["outside"]}
    kept = {path: keys for path, keys in ((LOCAL_SETTINGS, plugin_kept), (SETTINGS, team_kept)) if keys}
    if kept:
        out["kept"] = kept  # plugin keys sdlc wrote that the user has since changed
    return out


# --- relocate: legacy layout -> state in .sdlc/state, documents in docs_dir -------------------------

def git_out(p, *args):
    proc = subprocess.run(["git", "-C", p.root, *args], capture_output=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise ValueError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def relocate_plan(p, docs):
    """[[from, to], ...] for every tracked file of each legacy feature and doc still in .sdlc/, and the names whose
    target exists. Only tracked files: git mv refuses ignored ones (.DS_Store), and a failure part-way would strand the
    rest. state.md moves last, so an interrupted run leaves the feature readable where it was."""
    moves, conflicts = [], []
    for path in sorted(glob.glob(p.path(".sdlc/*/state.md"))):
        name = os.path.basename(os.path.dirname(path))
        if name in ("state", "intents"):
            continue
        src = f".sdlc/{name}"
        tracked = [f for f in git_out(p, "ls-files", "--", src).splitlines() if f != f"{src}/state.md"]
        # A 2.0 feature's change file goes to changes/; anything else is a pre-2.0 document, kept with its feature
        planned = [[f, f"{docs}/changes/{name}.md" if f == f"{src}/change.md" else f"{docs}/intents/{name}/{f[len(src) + 1:]}"]
                   for f in sorted(tracked)]
        planned.append([f"{src}/state.md", f".sdlc/state/{name}.md"])
        if any(os.path.exists(p.path(dst)) for _, dst in planned):
            conflicts.append(name)
        else:
            moves += planned
    tracked_docs = set(git_out(p, "ls-files", "--", ".sdlc/constitution.md", ".sdlc/design-system.md").splitlines())
    for doc in ("constitution.md", "design-system.md"):
        src, dst = f".sdlc/{doc}", f"{docs}/{doc}"
        if src != dst and src in tracked_docs:
            if os.path.exists(p.path(dst)):
                conflicts.append(doc)
            else:
                moves.append([src, dst])
    return moves, conflicts


def cmd_relocate(p, a):
    """Dry run by default. --apply moves with git mv, all or nothing: any conflict and nothing moves, so the repo is
    never half-moved; docs_dir is recorded with the move."""
    docs = sdlc_layout.validate_docs_dir(a.docs_dir or sdlc_layout.docs_dir(p.root) or sdlc_layout.DOCS_DEFAULT)
    moves, conflicts = relocate_plan(p, docs)
    out = {"docs_dir": docs, "moves": moves, "conflicts": conflicts, "applied": False}
    if not a.apply or conflicts:
        return out
    if git_out(p, "status", "--porcelain").strip():
        raise ValueError("uncommitted changes: commit or stash them first, so the move is one reviewable commit")
    lock = p.require_lock()
    for src, dst in moves:
        os.makedirs(os.path.dirname(p.path(dst)), exist_ok=True)
        git_out(p, "mv", src, dst)
        if src in lock.get("files", {}):
            lock["files"][dst] = lock["files"].pop(src)
    for feature in {s.split("/")[1] for s, _ in moves if s.count("/") > 1}:  # tidy emptied feature folders
        for d, _, _ in sorted(os.walk(p.path(f".sdlc/{feature}")), key=lambda w: -len(w[0])):
            if not os.listdir(d):
                os.rmdir(d)
    p.config = p.config or {}
    p.config["docs_dir"] = docs
    p.save()
    out["applied"] = True
    return out


# --- cli ----------------------------------------------------------------------------------

def build_parser():
    ap = argparse.ArgumentParser(prog="scaffold.py", description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="start setup: write lock (and a default config if none)")
    s.add_argument("--kind", choices=["greenfield", "brownfield"], required=True)
    s.add_argument("--force", action="store_true")
    s.add_argument("--docs-dir",
                   help=f"where sdlc documents live (default: the recorded docs_dir, else {sdlc_layout.DOCS_DEFAULT})")
    s.add_argument("--host", help="the coding agent running setup (default: detected; see `host`)")
    s.set_defaults(fn=cmd_init)

    sub.add_parser("host", help="which coding agent is running, which have set up this repo, and whether it's joining") \
        .set_defaults(fn=cmd_host)
    s = sub.add_parser("add-host", help="record another coding agent joining a set-up repo")
    s.add_argument("host")
    s.set_defaults(fn=cmd_add_host)

    s = sub.add_parser("paths", help="where a feature's state and documents live in this repo's layout")
    s.add_argument("name", nargs="?")
    s.set_defaults(fn=cmd_paths)

    sub.add_parser("status", help="setup state, drift, pending migrations, file states").set_defaults(fn=cmd_status)
    sub.add_parser("config", help="effective config (plugin defaults + project overrides)").set_defaults(fn=cmd_config)

    s = sub.add_parser("step-done", help="mark a setup step complete (resumable setup)")
    s.add_argument("step")
    s.add_argument("--complete", action="store_true", help="also mark the whole setup complete")
    s.add_argument("--pending", metavar="REASON", help="hold the step open instead (it runs again on resume)")
    s.set_defaults(fn=cmd_step_done)

    s = sub.add_parser("record", help="hash files written by Claude into the lock")
    s.add_argument("cls", choices=FILE_CLASSES)
    s.add_argument("paths", nargs="+")
    s.add_argument("--template", help="plugin-relative template the file came from")
    s.set_defaults(fn=cmd_record)

    s = sub.add_parser("forget", help="drop files from the lock (they become user-owned)")
    s.add_argument("paths", nargs="+")
    s.set_defaults(fn=cmd_forget)

    s = sub.add_parser("render", help="render a plugin template into the project and record it")
    s.add_argument("template", help="plugin-relative, e.g. templates/project/rules/sdlc.md, or builtin:ci[:<package>]")
    s.add_argument("dest")
    s.add_argument("--class", dest="cls", choices=FILE_CLASSES, default="generated")
    s.add_argument("--if-unchanged", action="store_true", help="refuse (exit 2) if the user edited the file")
    s.set_defaults(fn=cmd_render)

    s = sub.add_parser("conventions", help="a stack's convention for one area as .claude/rules/<stack>-<area>.md "
                       "(user-owned); no arguments: the stacks and their areas")
    s.add_argument("stack", nargs="?", help=", ".join(CONVENTION_STACKS))
    s.add_argument("area", nargs="?", help=", ".join(CONVENTION_AREAS))
    s.add_argument("--package", help="the package in .sdlc/config.json whose path scopes the rule (monorepo)")
    s.add_argument("--one-deployable", action="store_true",
                   help="the API mounted in a Nuxt or Next.js app: keep only the template's backend/ paths")
    s.add_argument("--seen", metavar="PATH", help="after an upgrade showed a convention's diff: take the current "
                   "template as its baseline")
    s.set_defaults(fn=cmd_conventions)

    s = sub.add_parser("workbench", help="list, add (clone + gitignore + record), remove, or clone listed repos")
    s.add_argument("action", choices=["list", "add", "remove", "clone"])
    s.add_argument("target", nargs="?", default="",
                   help="add: the clone URL; remove: the repo's name; clone: a listed repo's name (default: all missing)")
    s.add_argument("--name", help="add: folder and manifest name (default: from the URL)")
    s.add_argument("--role", choices=list(sdlc_scopes.ROLES), default="app")
    s.add_argument("--write", action="store_true", help="add: sdlc may change this repo (apps this project owns)")
    s.add_argument("--owner", help="add: the owning team's handle")
    s.add_argument("--contract", help="add: provides:v<N> or consumes:v<N>")
    s.set_defaults(fn=cmd_workbench)
    sub.add_parser("contract", help="check the project's commands in config (per package in a monorepo)") \
        .set_defaults(fn=cmd_contract)
    s = sub.add_parser("run-commands", help="run install and the verify plan once; record each exit in the lock")
    s.add_argument("--timeout", type=int, default=900, help="seconds per command (default 900)")
    s.set_defaults(fn=cmd_run_commands)
    sub.add_parser("commands", help="scopes and the install/verify plan (what verify.py and CI run)") \
        .set_defaults(fn=cmd_commands)

    s = sub.add_parser("preview", help="render a template to stdout without writing")
    s.add_argument("template")
    s.set_defaults(fn=cmd_preview)

    for name, fn, what in [("allow", cmd_allow, "permissions.allow entries in .claude/settings.json"),
                           ("gitignore", cmd_gitignore, ".gitignore lines")]:
        s = sub.add_parser(name, help=f"keyed merge of {what}; only removes entries it added")
        s.add_argument("--add", nargs="+")
        s.add_argument("--remove", nargs="+")
        if name == "allow":
            s.add_argument("--from-commands", action="store_true", help="add Bash(<cmd>:*) for every command in config")
        s.set_defaults(fn=fn)

    s = sub.add_parser("enable-plugin", help="turn sdlc and its companions on in .claude/settings.local.json")
    s.add_argument("--with", dest="with_", action="append", metavar="ID", help="also a companion that isn't on by default")
    s.add_argument("--team", action="store_true",
                   help="write the keys that turn plugins on to the committed .claude/settings.json (teammates; not cloud sessions)")
    s.add_argument("--remove", action="store_true", help="remove only the keys this command added")
    s.add_argument("--remove-team", action="store_true",
                   help="remove only the plugin keys this command added to .claude/settings.json")
    s.set_defaults(fn=cmd_enable_plugin)

    s = sub.add_parser("agents", help="rebuild AGENTS.md's sdlc block for the recorded hosts, and its Claude Code mirror")
    s.add_argument("--check", action="store_true", help="exit 1 if the block is out of date; write nothing")
    s.set_defaults(fn=cmd_agents)

    s = sub.add_parser("migrations", help="pending migrations in apply order")
    s.add_argument("--revisit", action="store_true", help="also list skipped ones")
    s.set_defaults(fn=cmd_migrations)

    s = sub.add_parser("migration", help="record a migration as applied or skipped")
    s.add_argument("id")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--applied", action="store_true")
    g.add_argument("--skipped", metavar="REASON")
    s.set_defaults(fn=cmd_migration)

    s = sub.add_parser("prd", help="the product doc's path; with a path, record it in config")
    s.add_argument("path", nargs="?")
    s.set_defaults(fn=cmd_prd)
    s = sub.add_parser("deploy", help="how the project deploys (target, environments, runbook); with flags, record it")
    s.add_argument("--target", help=", ".join(DEPLOY_TARGETS))
    s.add_argument("--env", action="append", metavar="NAME[:routine]",
                   help="an environment, routine when it deploys without a go-ahead; repeat for each (replaces the list)")
    s.add_argument("--runbook", help=f"the deploy runbook's path (default {DEFAULT_RUNBOOK})")
    s.set_defaults(fn=cmd_deploy)
    s = sub.add_parser("objects", help="the domain model's file, switch and drafting inputs; --enable turns it on")
    s.add_argument("--enable", action="store_true",
                   help="turn config's objects on, once the file exists and passes objects.py check")
    s.set_defaults(fn=cmd_objects)
    s = sub.add_parser("design", help="who does UI design work (builtin or impeccable); with a mode, record it")
    s.add_argument("mode", nargs="?")
    s.add_argument("--enable", action="store_true",
                   help="turn an installed but disabled impeccable plugin on for this repo, on this machine")
    s.set_defaults(fn=cmd_design)
    s = sub.add_parser("review-rounds", help="the last review round before the user decides (2 to 5); with a number, "
                                             "record it")
    s.add_argument("rounds", nargs="?")
    s.set_defaults(fn=cmd_review_rounds)
    s = sub.add_parser("guardrails", help="the guardrails setup renders for this repo's design mode")
    s.add_argument("--render", action="store_true",
                   help="write every one (seeded), leaving edited, foreign and declined ones as they are")
    s.set_defaults(fn=cmd_guardrails)
    sub.add_parser("add-config-keys", help="in a spec-backed repo, add sdlc 3.5's keys (accept.start, "
                   "accept.base_url) empty where missing, per package").set_defaults(fn=cmd_add_config_keys)

    s = sub.add_parser("set-version", help="set scaffold_version (and raise min_plugin_version)")
    s.add_argument("version")
    s.add_argument("--min-plugin")
    s.set_defaults(fn=cmd_set_version)

    s = sub.add_parser("relocate", help="move a legacy layout: state to .sdlc/state, documents to docs_dir (dry run)")
    s.add_argument("--docs-dir", help=f"where documents go (default: the recorded docs_dir, else {sdlc_layout.DOCS_DEFAULT})")
    s.add_argument("--apply", action="store_true", help="move with git mv and record docs_dir")
    s.set_defaults(fn=cmd_relocate)

    sub.add_parser("upgrade-plan", help="what an upgrade would regenerate/replace/review").set_defaults(fn=cmd_upgrade_plan)

    s = sub.add_parser("eject", help="show the eject plan; --apply to carry it out")
    s.add_argument("--apply", action="store_true")
    s.add_argument("--also", nargs="+", help="edited files from 'ask' the user agreed to delete")
    s.set_defaults(fn=cmd_eject)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        result = a.fn(Project(a.root), a)  # inside the try: Project refuses a linked config or lock
        code = 0
    except Refused as e:
        result, code = {"refused": str(e)}, 2
    except CommandsFailed as e:
        result, code = e.args[0], 1
    except (ValueError, OSError) as e:
        result, code = {"error": str(e)}, 1
    sys.stdout.reconfigure(encoding="utf-8")  # a cp1252 pipe (Windows) can't encode non-ASCII paths or summaries
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
