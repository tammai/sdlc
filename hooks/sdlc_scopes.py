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


def workbench_of(root):
    """The workbench an app repo belongs to (its config's `"workbench": "<name>"`), else None; any read error: None."""
    import os
    try:
        value = _read_json(os.path.join(root, ".sdlc", "config.json")).get("workbench")
    except Exception:
        return None
    return value.strip() if isinstance(value, str) and value.strip() else None


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
    if name in seen:
        raise ValueError(f"{where}: duplicate name {name!r}")
    seen.add(name)
    url = entry.get("url")
    if not isinstance(url, str) or not url.strip() or url.startswith("-") or any(c in url for c in "\r\n\0"):
        raise ValueError(f"{where} ({name}): url must be a clone URL")
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
            cfg = _read_json(os.path.join(root, repo["name"], ".sdlc", "config.json"))
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
    names something that isn't a plain folder name, is skipped (the file is committed: never a path from it)."""
    import re
    out, inside = {}, False
    for line in str(state_text or "").replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            inside = line[3:].strip() == REPOS_HEADING
            continue
        m = inside and re.match(r"^-\s+([^:\s]+):\s+(?:branch\s+(\S+)\s+base\s+([0-9a-f]{7,40})|read\s+([0-9a-f]{7,40}))"
                                r"\s*$", line)
        if not m:
            continue
        try:
            name = check_name(m.group(1))
        except ValueError:
            continue
        out[name] = {"branch": m.group(2), "base": m.group(3)} if m.group(2) else {"read": m.group(4)}
    return out


PRS_HEADING = "PRs"


def _section_lines(state_text, heading):
    inside = False
    for line in str(state_text or "").replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            inside = line[3:].strip() == heading
        elif inside:
            yield line


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
                out[pr_name(m.group(1))] = m.group(2)
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
