"""The project's scopes, read one way by scripts and hooks alike: one per package of a monorepo (`packages` in
.sdlc/config.json), else the whole project. A root `commands` block beside `packages` holds workspace-wide commands
(`pnpm install`, `turbo run test`): it is not a scope of its own, but `root_commands` gives it to the verify plan, and
a full run of its test covers every package.

Cheap to import: hooks load it on every tool call."""
import posixpath

ROOT_SCOPE = "(root)"


def norm(path):
    """A repo-relative folder with `/`, no leading `./` or trailing slash; the repo itself is "."."""
    p = posixpath.normpath(str(path or ".").replace("\\", "/"))
    return "." if p in ("", ".") else p.strip("/")


def _dict(value):
    return value if isinstance(value, dict) else {}


def packages(config):
    """The `packages` entries; ValueError naming the problem when `packages` isn't a list of objects (callers report
    it: scripts as a message, hooks as their error marker), never a guess at what was meant."""
    pkgs = _dict(config).get("packages")
    if pkgs in (None, []):
        return []
    if not isinstance(pkgs, list):
        raise ValueError("packages in .sdlc/config.json is not a list")
    for i, pk in enumerate(pkgs):
        if not isinstance(pk, dict):
            raise ValueError(f"packages[{i}] in .sdlc/config.json is not an object")
    return pkgs


def scopes(config):
    """[{name, path, stack, commands, accept, named}]: one per package, else the root project. A package without a
    name is named after its path (`named` False, so the contract check can still report it)."""
    cfg = _dict(config)
    pkgs = packages(cfg)
    if pkgs:
        out = []
        for pk in pkgs:
            path = norm(pk.get("path"))
            name = pk.get("name") if isinstance(pk.get("name"), str) and pk.get("name") else None
            out.append({"name": name or path, "path": path, "stack": pk.get("stack"),
                        "commands": _dict(pk.get("commands")), "accept": pk.get("accept", {}), "named": bool(name)})
        return out
    return [{"name": ROOT_SCOPE, "path": ".", "stack": None, "commands": _dict(cfg.get("commands")),
             "accept": cfg.get("accept", {}), "named": True}]  # accept null: not applicable, kept as None


# --- the workbench: one repo per app, cloned inside a parent workbench repo ---------------------------------------
# A workbench is a repo whose .sdlc/config.json says `"workbench": true` (exactly true), with workbench.json at its
# root listing the repos cloned inside it. product-rebuild's repos.yaml is never read: the two are kept apart.
# workbench.json is committed, so every value in it is untrusted: names are plain folder names one level below the
# workbench, never `.git`, `.sdlc`, `.claude` or anything with a path separator, drive or leading dash.

WORKBENCH_FILE = "workbench.json"
WORKBENCH_SCOPE = "(workbench)"
ROLES = ("app", "specs", "tests", "designs", "other")
_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_CONTRACT_KEYS = ("provides", "consumes")


# The code points HFS+ ignores in a name (git's is_hfs_dotgit), so `.g‌it` opens `.git` there
HFS_IGNORED = dict.fromkeys([0x200C, 0x200D, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x206A, 0x2070), 0xFEFF])


def dot_segment(seg, name):
    """A path segment a filesystem opens as the dot folder `name` (`.git`, `.claude`, `.sdlc`): in any case (macOS
    and Windows ignore it), with the trailing dots or spaces and the NTFS stream suffix Windows ignores, the code
    points HFS+ ignores, or its numbered 8.3 short name (dot dropped, six characters, `~1`; `~1`-`~4` past `.git`, as
    git bars them; not the hashed short name Windows gives past `~4`). Case is folded as APFS folds it (`.ſdlc` opens
    `.sdlc`) and as NTFS upper-cases it (`.gıt` may open `.git`). Every check of those folders uses this one rule, so
    they can't drift apart."""
    seg = str(seg).translate(HFS_IGNORED).split(":", 1)[0].rstrip(". ")
    short = name.lstrip(".")[:6]
    names = {name} | {f"{short}~{n}" for n in ((1,) if name == ".git" else (1, 2, 3, 4))}
    return seg.casefold() in names or seg.upper().casefold() in names


def odd_name(text):
    """Whether a name has a control or format character, which could fake a section of a brief or hide a name."""
    import unicodedata
    return any(unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") for c in str(text))


def git_segment(seg):
    """A path segment a filesystem opens as a git dir (dot_segment for `.git`)."""
    return dot_segment(seg, ".git")


def _inside(base, rel):
    """The full path of `rel` under `base`, or OSError when, after links, it leaves `base` or lands in a git dir: the
    file is committed, so a link to another file is never read (a FIFO or /dev/zero would hang the hook too)."""
    import os
    full = os.path.join(base, rel)
    real_base = os.path.normcase(os.path.realpath(base))
    real = os.path.normcase(os.path.realpath(full))
    try:
        inside = os.path.commonpath([real_base, real]) == real_base
    except ValueError:  # another drive
        inside = False
    if not inside or any(git_segment(x) for x in os.path.relpath(real, real_base).split(os.sep)):
        raise OSError(f"{rel} is a link out of the repo or into .git: not read")
    if os.path.exists(real) and not os.path.isfile(real):  # a FIFO, device or folder would hang or fail the hook
        raise OSError(f"{rel} isn't a regular file: not read")
    return full


def read_repo_text(base, rel):
    """The text of the committed file `rel` under `base`, or None when it's missing, unreadable, or a link out of the
    repo or into .git (_inside): read as absent, never through the link."""
    try:
        with open(_inside(base, rel), encoding="utf-8") as f:
            return f.read()
    except (OSError, ValueError):
        return None


def read_repo_json(base, rel):
    """The JSON file `rel` under `base` (a repo root), read only when _inside allows it."""
    import json
    with open(_inside(base, rel), encoding="utf-8") as f:
        return json.load(f)


MODES = ("full", "advisory")
SKIPPABLE = ("security-review", "code-review", "ui-review", "pr")
ANCHOR = ".sdlc/.work/trust-anchor.json"  # the trust anchor's record; its `_config` holds the accepted mode and skips
CONFIG_KEY = "_config"


def gate_root(path, session=True):
    """The folder whose config sets the mode and skips for a call at `path`, the same for every reader and the trust
    anchor: from the session's project folder (CLAUDE_PROJECT_DIR) when set, else `path`, the outermost folder
    holding `.sdlc` up to its git top level (a nested `.sdlc` inside the repo can't redirect it), else the nearest one
    up; for an app repo of a workbench, the workbench. None when no folder up holds `.sdlc`: nothing is read or
    written then."""
    import os
    start = os.path.abspath((os.environ.get("CLAUDE_PROJECT_DIR") if session else None) or path or os.getcwd())
    d = start if os.path.isdir(start) else os.path.dirname(start)
    held = []
    probe = d
    while True:
        if os.path.isdir(os.path.join(probe, ".sdlc")):
            held.append(probe)
        if os.path.exists(os.path.join(probe, ".git")) and held:
            break  # the repo's top: the outermost `.sdlc` within it decides
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    if not held:
        return None
    root = held[-1] if os.path.exists(os.path.join(probe, ".git")) else held[0]
    parent = os.path.dirname(os.path.realpath(root))
    try:
        if os.path.isfile(os.path.join(parent, WORKBENCH_FILE)) and guarded_workbench(parent):
            return parent
    except Exception:
        pass
    return root


def _gating(raw):
    """(mode, skips) as a config object states them: unknown values count as full and are left out."""
    raw = raw if isinstance(raw, dict) else {}
    mode = raw.get("mode") if raw.get("mode") in MODES else "full"
    listed = raw.get("skip") if isinstance(raw.get("skip"), list) else []
    return mode, (sorted({x for x in listed if x in SKIPPABLE}) if mode == "full" else [])


def _config(root):
    """The config object at `root`, read only from a regular file inside the repo (a FIFO or a link out reads as
    none): {} on any doubt."""
    try:
        cfg = read_repo_json(root, ".sdlc/config.json")  # _inside: inside the repo, a regular file
    except Exception:
        return {}
    return cfg if isinstance(cfg, dict) else {}


def configured(root):
    """(mode, skips) the working config at `root` asks for, accepted or not."""
    return _gating(_config(root))


def committed(root):
    """(mode, skips) HEAD's committed config at `root` states, or full with none when git can't say (a short
    timeout: a stalled git must not hold a hook to its own limit)."""
    import json
    import subprocess
    try:
        p = subprocess.run(["git", "-C", root, "show", "HEAD:./.sdlc/config.json"], capture_output=True,
                           encoding="utf-8", errors="replace", timeout=2)
        return _gating(json.loads(p.stdout)) if p.returncode == 0 else ("full", [])
    except Exception:
        return "full", []


def accepted(root):
    """(mode, skips) the user has accepted here: the trust anchor's record; with no readable, well-formed record,
    HEAD's committed config (a team's choice on a fresh clone)."""
    import json
    try:
        with open(_inside(root, ANCHOR), encoding="utf-8") as f:  # a regular file inside the repo only
            entry = json.load(f).get(CONFIG_KEY)
        if valid_record(entry):
            return _gating(entry)
    except Exception:
        pass
    return committed(root)


def write_record(base, rel, data):
    """Write the JSON record `rel` under `base` as a fresh regular file swapped into place: a FIFO there can't hang
    the hook and a link there is replaced, never written through. False when it can't be written."""
    import json
    import os
    import tempfile
    full = os.path.join(base, rel)
    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        folder = os.path.realpath(os.path.dirname(full))
        real_base = os.path.realpath(base)
        if folder != real_base and not folder.startswith(real_base + os.sep):
            return False  # a linked folder would carry the record out of the repo
        fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(full))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, full)
        return True
    except OSError:
        try:
            os.remove(tmp)
        except (OSError, NameError):
            pass
        return False


def valid_record(entry):
    """The trust anchor's accepted mode-and-skips record is well formed: a known mode and a list of known step
    names. Anything else counts as damaged (never as accepted)."""
    return (isinstance(entry, dict) and entry.get("mode") in MODES and isinstance(entry.get("skip"), list)
            and all(isinstance(x, str) and x in SKIPPABLE for x in entry["skip"]))


def effective(root):
    """(mode, skips) the hooks honour at `root`: what config asks, but only as far as the user accepted it, so a
    relaxing edit counts only once the trust anchor has shown it and the user replied (ADR 0030)."""
    want_mode, want_skip = configured(root)
    if want_mode == "full" and not want_skip:
        return "full", []  # nothing to relax: no record or git read on this, the common path
    ok_mode, ok_skip = accepted(root)
    if want_mode == "advisory":
        return ("advisory", []) if ok_mode == "advisory" else ("full", [])
    return "full", ([x for x in want_skip if x in ok_skip] if ok_mode == "full" else want_skip)


def mode(root):
    """The effective mode at `root` (effective): `advisory` (skills and agents as aids, no hook gates anything) or
    `full`, the default. Never raises."""
    try:
        return effective(root)[0] if root else "full"
    except Exception:
        return "full"


def advisory(root):
    """Whether the hooks stay silent at `root` (a gate_root): the effective mode is advisory."""
    return mode(root) == "advisory"


def advisory_from(path):
    """advisory() for a call at `path` (a cwd or file), through gate_root. Never raises."""
    try:
        return advisory(gate_root(path))
    except Exception:
        return False


def skipped(root):
    """The steps the effective config skips at `root` (full mode only, known names only, accepted only)."""
    try:
        return effective(root)[1] if root else []
    except Exception:
        return []


def is_workbench(root, need_manifest=True):
    """True when root's own config says `"workbench": true` and (unless need_manifest is False, for the command that
    writes the first entry) workbench.json exists beside it. Any read error: False (never a guess)."""
    import os
    try:
        declared = read_repo_json(root, ".sdlc/config.json").get("workbench") is True
    except Exception:
        return False
    return declared and (not need_manifest or os.path.isfile(os.path.join(root, WORKBENCH_FILE)))


SEEDED_MARKER = ".sdlc/.work/read-only-seeded"  # the read-only watch has taken this workbench's first look


def guarded_workbench(root):
    """For the write guards: a workbench (is_workbench), a folder holding workbench.json whose .sdlc/config.json
    exists but can't be read as an object (a merge-conflict marker, a bad edit), or one the read-only watch has
    seeded (its marker), so `"workbench": false` in a config the agent can edit never turns them off. The guards fail
    closed there."""
    import os
    if is_workbench(root):
        return True
    if os.path.isfile(os.path.join(root, SEEDED_MARKER)):  # whatever workbench.json and the config say now
        return True
    config = os.path.join(root, ".sdlc", "config.json")
    if not os.path.isfile(os.path.join(root, WORKBENCH_FILE)) or not os.path.exists(config):
        return False
    try:
        return not isinstance(read_repo_json(root, ".sdlc/config.json"), dict)
    except Exception:
        return True


NO_PUSH = "sdlc-read-only-repo-no-push"  # the push URL of a read-only repo: not a repo, so every push fails


def disable_push(folder):
    """Point every remote's push URL of a read-only repo at NO_PUSH, so nothing reaches the other team's remote;
    fetch and pull keep their URLs. Errors: ValueError."""
    import subprocess
    run = lambda *a: subprocess.run(["git", "-C", folder, *a], capture_output=True, encoding="utf-8",
                                    errors="replace")
    remotes = run("remote")
    if remotes.returncode:
        raise ValueError(f"git remote failed in {folder}: {remotes.stderr.strip()}")
    for remote in remotes.stdout.split():
        p = run("remote", "set-url", "--push", remote, NO_PUSH)
        if p.returncode:
            raise ValueError(f"couldn't disable push for {remote} in {folder}: {p.stderr.strip()}")


def workbench_of(root):
    """The workbench an app repo belongs to (its config's `"workbench": "<name>"`), else None; any read error: None."""
    import os
    try:
        value = read_repo_json(root, ".sdlc/config.json").get("workbench")
    except Exception:
        return None
    return value.strip() if isinstance(value, str) and value.strip() else None


# Folders and files the workbench owns itself: a repo listed under one of these names would take them over
RESERVED = frozenset({"contract", "docs", "infras", "knowledge", "workbench.json", "claude.md", "agents.md",
                      "readme.md"})


def check_url(url):
    """The URL when it can only be a clone URL handed to git after `--`, else ValueError: no leading `-`, no
    whitespace, control or shell characters, and no `<helper>::` transport (`ext::` runs a command)."""
    import re
    bad = re.compile(r"[\s\x00-\x1f\x7f;|&$`<>()'\"]")
    if (not isinstance(url, str) or not url or url.startswith("-") or bad.search(url)
            or re.match(r"^[A-Za-z][\w+.-]*::", url)):
        raise ValueError(f"url {url!r} must be a clone URL (https://, ssh://, git@host:path or a local path; no "
                         "spaces, shell characters or <transport>:: helpers)")
    return url


def repo_dir(root, name):
    """root/<name> for a manifest or state name: a plain folder name whose folder, when it exists, is a real folder
    directly in the workbench (any link is refused, even to a sibling: a read-only repo under a writable name); else
    ValueError."""
    import os
    path = os.path.join(root, check_name(name))
    if os.path.lexists(path) and (os.path.islink(path) or os.path.normcase(os.path.realpath(path))
                                  != os.path.normcase(os.path.join(os.path.realpath(root), name))):
        raise ValueError(f"{name}/ is a link, not a repo cloned in the workbench: sdlc never follows one (outside the "
                         "workbench, or to another listed repo)")
    return path


def ignored_name(line):
    """The folder a .gitignore line ignores at the root (`api`, `api/`, `/api`, `/api/` → api), else None."""
    x = line.strip()
    return x.strip("/") if x and not x.startswith(("#", "!")) and "/" not in x.strip("/") else None


def check_branch(branch):
    """The branch name when it is one sdlc records and puts in the commands it suggests: letters, digits, '.', '_',
    '-' and '/' (no leading '-', no '..' or '//', no trailing '/', '.' or '.lock'); else ValueError."""
    import re
    ok = (isinstance(branch, str) and len(branch) <= 200 and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch)
          and ".." not in branch and "//" not in branch and not branch.endswith(("/", ".", ".lock")))
    if not ok:
        raise ValueError(f"{branch!r} isn't a branch name sdlc records (letters, digits, '.', '_', '-' and '/')")
    return branch


def check_name(name):
    """The name when it is a plain folder name, else ValueError."""
    ok = (isinstance(name, str) and 0 < len(name) <= 100 and set(name) <= _NAME_CHARS
          and name[0] not in ".-" and name not in (".", ".."))
    if not ok:
        raise ValueError(f"{name!r} is not a plain folder name (letters, digits, '.', '_', '-'; "
                         "not starting with '.' or '-')")
    return name


def _check_entry(i, entry, seen):
    where = f"not run: {WORKBENCH_FILE} repos[{i}]"
    if not isinstance(entry, dict):
        raise ValueError(f"{where} is not an object")
    try:
        name = check_name(entry.get("name"))
    except ValueError as e:
        raise ValueError(f"{where}: {e}")
    if name.lower() in seen:  # Specs and specs are one folder on macOS and Windows
        raise ValueError(f"{where}: duplicate name {name!r}")
    if name.lower() in RESERVED:
        raise ValueError(f"{where}: {name!r} is the workbench's own (reserved: {', '.join(sorted(RESERVED))})")
    seen.add(name.lower())
    url = entry.get("url")
    try:
        check_url(url)
    except ValueError as e:
        raise ValueError(f"{where} ({name}): {e}")
    role = entry.get("role")
    if role not in ROLES:
        raise ValueError(f"{where} ({name}): role must be one of {', '.join(ROLES)}")
    write = entry.get("write", False)
    if not isinstance(write, bool):
        raise ValueError(f"{where} ({name}): write must be true or false")
    if write and role != "app":
        raise ValueError(f"{where} ({name}): only an app repo can be writable")
    owner = entry.get("owner")
    if owner is not None and not isinstance(owner, str):
        raise ValueError(f"{where} ({name}): owner must be a team handle")
    contract = entry.get("contract")
    if contract is not None:
        if (not isinstance(contract, dict) or not set(contract) <= set(_CONTRACT_KEYS)
                or not all(isinstance(v, str) and v[:1] == "v" and v[1:].isdigit() for v in contract.values())):
            raise ValueError(f"{where} ({name}): contract must be {{\"provides\"|\"consumes\": \"v<N>\"}}")
    return {"name": name, "url": url, "role": role, "write": write, "owner": owner, "contract": contract or {}}


def manifest(root):
    """The repos workbench.json lists, validated: [{name, url, role, write, owner, contract}]. A missing file is an
    empty workbench; anything malformed is ValueError("not run: workbench.json …")."""
    import os
    path = os.path.join(root, WORKBENCH_FILE)
    if not os.path.exists(path):
        return []
    try:
        data = read_repo_json(root, WORKBENCH_FILE)
    except (OSError, ValueError) as e:
        raise ValueError(f"not run: {WORKBENCH_FILE} is not readable JSON ({e})")
    repos = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(repos, list):
        raise ValueError(f"not run: {WORKBENCH_FILE} needs a \"repos\" list")
    seen = set()
    return [_check_entry(i, entry, seen) for i, entry in enumerate(repos)]


def workbench_scopes(root):
    """One scope per writable repo (its folder, the commands and stack from its own .sdlc/config.json), then the
    workbench itself. `configured` False when an app has no readable config of its own yet."""
    import os
    out = []
    for repo in manifest(root):
        if not repo["write"]:
            continue
        try:
            folder = repo_dir(root, repo["name"])
        except ValueError:
            continue  # links outside the workbench: never a scope sdlc reads or runs in
        try:
            cfg = read_repo_json(folder, ".sdlc/config.json")
            cfg = cfg if isinstance(cfg, dict) else {}
            configured = True
        except (OSError, ValueError):
            cfg, configured = {}, False
        out.append({"name": repo["name"], "path": repo["name"], "stack": _dict(cfg.get("project")).get("stack"),
                    "commands": _dict(cfg.get("commands")), "accept": cfg.get("accept", {}), "named": True,
                    "repo": repo, "configured": configured})
    try:
        own = read_repo_json(root, ".sdlc/config.json")
    except (OSError, ValueError):
        own = {}
    out.append({"name": WORKBENCH_SCOPE, "path": ".", "stack": None, "commands": _dict(_dict(own).get("commands")),
                "accept": {}, "named": True, "repo": None, "configured": True})
    return out


REPOS_HEADING = "Repos"


def repo_line(name, branch=None, base=None, read=None):
    """One `## Repos` line of a workbench feature's state file: a writable repo's branch and base, or the commit of
    a read-only repo it read."""
    return f"{name}: branch {branch} base {base}" if branch else f"{name}: read {read}"


def feature_repos(state_text):
    """{name: {"branch", "base"} | {"read"}} from a state file's `## Repos` section; a line that doesn't parse, or
    names something that isn't a plain folder name or branch name, is skipped (the file is committed: never a path or
    a shell word from it)."""
    import re
    line_re = re.compile(r"^-\s+([^:\s]+):\s+(?:branch\s+(\S+)\s+base\s+([0-9a-f]{7,40})|read\s+([0-9a-f]{7,40}))\s*$")
    out = {}
    for line in _section_lines(state_text, REPOS_HEADING):
        m = line_re.match(line)
        if not m:
            continue
        try:
            name = check_name(m.group(1))
            if m.group(2):
                check_branch(m.group(2))
        except ValueError:
            continue
        out[name] = {"branch": m.group(2), "base": m.group(3)} if m.group(2) else {"read": m.group(4)}
    return out


def _section_lines(state_text, heading):
    inside = False
    for line in str(state_text or "").replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            inside = line[3:].strip() == heading
        elif inside:
            yield line


def branched_repos(root, state_text):
    """([(name, record)], [(name, why)]): the `## Repos` branch lines sdlc may act on (stage, commit, run commands),
    and those it must not: a repo the manifest doesn't list as `write: true` (another team's, or flipped since it was
    branched), one that isn't a cloned git repo (git would fall back to the workbench) or one that links outside.
    A manifest it can't read: ValueError (callers refuse, never guess)."""
    import os
    writable = {r["name"] for r in manifest(root) if r["write"]}
    kept, dropped = [], []
    for name, rec in feature_repos(state_text).items():
        if not rec.get("branch"):
            continue
        if name not in writable:
            dropped.append((name, f"{name} isn't a writable repo in {WORKBENCH_FILE} (write: true)"))
            continue
        try:
            path = repo_dir(root, name)
        except ValueError as e:
            dropped.append((name, str(e)))
            continue
        if not os.path.exists(os.path.join(path, ".git")):
            dropped.append((name, f"{name}/ isn't a cloned git repo"))
            continue
        kept.append((name, rec))
    return kept, dropped


def listed_names(root):
    """Every repo name workbench.json lists (read entry by entry), or None when it can't be read as JSON with a
    `repos` list. For the watch, which must see a writable repo's entry go too."""
    try:
        data = read_repo_json(root, WORKBENCH_FILE)
    except (OSError, ValueError):
        return None
    repos = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(repos, list):
        return None
    return {r["name"] for r in repos if isinstance(r, dict) and isinstance(r.get("name"), str)}


def read_only_names(root):
    """{name: owner} of every repo the manifest lists that isn't exactly `write: true`, read entry by entry so one
    malformed entry never unguards the others (the guard fails closed); None only when the file can't be read as
    JSON with a `repos` list."""
    import os
    try:
        data = read_repo_json(root, WORKBENCH_FILE)
    except (OSError, ValueError):
        return None
    repos = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(repos, list):
        return None
    out = {}
    for entry in repos:
        if not isinstance(entry, dict) or entry.get("write") is True:
            continue
        try:
            name = check_name(entry.get("name"))
        except ValueError:
            continue
        if name.lower() in RESERVED:  # the workbench's own folder: never another team's repo
            continue
        owner = entry.get("owner")
        out[name] = owner if isinstance(owner, str) and owner.strip() else None
    return out


def workbench_root(start, guarded=False):
    """The nearest folder at or above `start` that is a workbench (with `guarded`, guarded_workbench), else None
    (hosts without CLAUDE_PROJECT_DIR)."""
    import os
    here = os.path.abspath(start or ".")
    while True:
        if (guarded_workbench if guarded else is_workbench)(here):
            return here
        up = os.path.dirname(here)
        if up == here:
            return None
        here = up


PRS_HEADING = "PRs"


def check_pr_url(url):
    """A PR's URL (`https://<host>/<owner>/<repo>/pull/<n>`) or bare number, else ValueError: it reaches gh as an
    argument, so never anything that reads as an option."""
    import re
    if not isinstance(url, str) or not re.fullmatch(r"https://[^\s/]+/\S*/pull/\d+/?|\d+", url):
        raise ValueError(f"{url!r} is not a PR URL (https://<host>/<owner>/<repo>/pull/<n>) or number")
    return url


def pr_name(name):
    """A `## PRs` name: a plain folder name, or the workbench itself (WORKBENCH_SCOPE); else ValueError."""
    return name if name == WORKBENCH_SCOPE else check_name(name)


def feature_prs(state_text):
    """{name: url} from a workbench feature's `## PRs` section (`- <name>: <url>`); bad lines skipped."""
    import re
    out = {}
    for line in _section_lines(state_text, PRS_HEADING):
        m = re.match(r"^-\s+(\S+):\s+(\S+)\s*$", line)
        if m:
            try:
                out[pr_name(m.group(1))] = check_pr_url(m.group(2))
            except ValueError:
                continue
    return out


def merge_order(root, names):
    """`names` (WORKBENCH_SCOPE and repo names) in merge order: the workbench (its contract), then each provider,
    then each consumer, then the rest; manifest order within each group. Also {name: rank} for warnings."""
    try:
        repos = {r["name"]: r for r in manifest(root)}
    except ValueError:
        repos = {}
    def group(name):
        if name == WORKBENCH_SCOPE:
            return 0
        contract = (repos.get(name) or {}).get("contract") or {}
        return 1 if "provides" in contract else 2 if "consumes" in contract else 3
    listed = list(repos)
    return sorted(names, key=lambda n: (group(n), listed.index(n) if n in listed else len(listed), n))


def must_follow(root, before, after):
    """True when `after` must merge after `before`: the workbench before any app with a contract, a provider before
    a consumer of the same version."""
    try:
        repos = {r["name"]: r for r in manifest(root)}
    except ValueError:
        return False
    late = (repos.get(after) or {}).get("contract") or {}
    if before == WORKBENCH_SCOPE:
        return bool(late)
    early = (repos.get(before) or {}).get("contract") or {}
    return bool(early.get("provides")) and early.get("provides") == late.get("consumes")


def command_sets(root):
    """Every commands object the project at root runs: its own `commands`, each package's, and in a workbench each
    writable app repo's (from the app's own config). Unreadable config: what can be read ([] at worst)."""
    import os
    try:
        config = read_repo_json(root, ".sdlc/config.json")
    except (OSError, ValueError):
        config = {}
    config = config if isinstance(config, dict) else {}
    sets = [config.get("commands")] + [p.get("commands") for p in config.get("packages") or [] if isinstance(p, dict)]
    if is_workbench(root):
        try:
            sets += [scope["commands"] for scope in workbench_scopes(root) if scope["repo"]]
        except ValueError:
            pass
    return [s for s in sets if isinstance(s, dict)]


def root_commands(config):
    """The root `commands` beside `packages` (workspace-wide), else {}: without packages they are the root scope's."""
    cfg = _dict(config)
    return _dict(cfg.get("commands")) if packages(cfg) else {}
