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


def _read_json(path):
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_workbench(root, need_manifest=True):
    """True when root's own config says `"workbench": true` and (unless need_manifest is False, for the command that
    writes the first entry) workbench.json exists beside it. Any read error: False (never a guess)."""
    import os
    try:
        declared = _read_json(os.path.join(root, ".sdlc", "config.json")).get("workbench") is True
    except Exception:
        return False
    return declared and (not need_manifest or os.path.isfile(os.path.join(root, WORKBENCH_FILE)))


def guarded_workbench(root):
    """For the write guards: a workbench (is_workbench), or a folder holding workbench.json whose .sdlc/config.json
    exists but can't be read as an object (a merge-conflict marker, a bad edit). The guards fail closed there."""
    import os
    if is_workbench(root):
        return True
    config = os.path.join(root, ".sdlc", "config.json")
    if not os.path.isfile(os.path.join(root, WORKBENCH_FILE)) or not os.path.exists(config):
        return False
    try:
        return not isinstance(_read_json(config), dict)
    except Exception:
        return True


def workbench_of(root):
    """The workbench an app repo belongs to (its config's `"workbench": "<name>"`), else None; any read error: None."""
    import os
    try:
        value = _read_json(os.path.join(root, ".sdlc", "config.json")).get("workbench")
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
        data = _read_json(path)
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
            cfg = _read_json(os.path.join(folder, ".sdlc", "config.json"))
            cfg = cfg if isinstance(cfg, dict) else {}
            configured = True
        except (OSError, ValueError):
            cfg, configured = {}, False
        out.append({"name": repo["name"], "path": repo["name"], "stack": _dict(cfg.get("project")).get("stack"),
                    "commands": _dict(cfg.get("commands")), "accept": cfg.get("accept", {}), "named": True,
                    "repo": repo, "configured": configured})
    try:
        own = _read_json(os.path.join(root, ".sdlc", "config.json"))
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


def read_only_names(root):
    """{name: owner} of every repo the manifest lists that isn't exactly `write: true`, read entry by entry so one
    malformed entry never unguards the others (the guard fails closed); None only when the file can't be read as
    JSON with a `repos` list."""
    import os
    try:
        data = _read_json(os.path.join(root, WORKBENCH_FILE))
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


def root_commands(config):
    """The root `commands` beside `packages` (workspace-wide), else {}: without packages they are the root scope's."""
    cfg = _dict(config)
    return _dict(cfg.get("commands")) if packages(cfg) else {}
