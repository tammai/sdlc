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


def root_commands(config):
    """The root `commands` beside `packages` (workspace-wide), else {}: without packages they are the root scope's."""
    cfg = _dict(config)
    return _dict(cfg.get("commands")) if packages(cfg) else {}
