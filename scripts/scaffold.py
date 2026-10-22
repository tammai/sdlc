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
import hashlib
import json
import os
import re
import shutil
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = ".sdlc/config.json"
LOCK = ".sdlc/scaffold.lock.json"
SETTINGS = ".claude/settings.json"
GITIGNORE = ".gitignore"
FILE_CLASSES = ("generated", "seeded")
DEFAULTS = "templates/project/config.defaults.json"
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*(?:\|\s*([a-z_]+)\s*)?\}\}")


class Refused(Exception):
    pass


# --- io ---------------------------------------------------------------------------

def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        raise ValueError(f"{path} is not valid JSON: {e}")


def write_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def sha256(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def rel(root, path):
    r = os.path.relpath(os.path.join(root, path), root).replace(os.sep, "/")
    if r == ".." or r.startswith("../"):
        raise ValueError(f"{path} is outside the project root")
    return r


# --- versions -----------------------------------------------------------------------

def parse_version(v):
    m = re.match(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", str(v or "").strip())
    if not m:
        raise ValueError(f"not a version: {v!r}")
    return tuple(int(x or 0) for x in m.groups())


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

class Project:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.config = read_json(self.path(CONFIG))
        self.lock = read_json(self.path(LOCK))

    def path(self, p):
        return os.path.join(self.root, p)

    def require_lock(self):
        if self.lock is None:
            raise ValueError(f"no {LOCK}; run `init` first")
        return self.lock

    def save(self):
        if self.lock is not None:
            write_json(self.path(LOCK), self.lock)
        if self.config is not None:
            write_json(self.path(CONFIG), self.config)

    def file_state(self, path, entry):
        actual = sha256(self.path(path))
        if actual is None:
            return "missing"
        return "unchanged" if actual == entry.get("sha256") else "modified"


# --- commands ----------------------------------------------------------------------------

def cmd_init(p, a):
    if p.lock is not None and not a.force:
        raise ValueError(f"{LOCK} already exists (setup started or done); use status, or --force to restart")
    version = plugin_version()
    if p.config is None:  # overrides only; everything else comes from the plugin defaults
        p.config = {"min_plugin_version": version, "project": {"kind": a.kind}}
    p.lock = {"scaffold_version": version, "files": {}, "merged": {},
              "migrations": {"applied": [], "skipped": {}},
              "setup": {"kind": a.kind, "completed_steps": [], "complete": False}}
    p.save()
    return {"initialized": True, "scaffold_version": version, "kind": a.kind}


def cmd_status(p, a):
    pv = plugin_version()
    out = {"plugin_version": pv, "configured": p.config is not None}
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
               completed_steps=setup.get("completed_steps", []),
               scaffold_version=sv, min_plugin_version=minv, drift=drift,
               pending_migrations=[m["id"] for m in pending_migrations(p)],
               files={path: {"class": e["class"], "state": p.file_state(path, e)}
                      for path, e in sorted(p.lock.get("files", {}).items())})
    return out


def cmd_config(p, a):
    return {"config": effective_config(p.config), "overrides": p.config or {}}


def cmd_step_done(p, a):
    setup = p.require_lock().setdefault("setup", {"completed_steps": [], "complete": False})
    if a.step not in setup["completed_steps"]:
        setup["completed_steps"].append(a.step)
    if a.complete:
        setup["complete"] = True
    p.save()
    return {"completed_steps": setup["completed_steps"], "complete": setup.get("complete", False)}


def cmd_record(p, a):
    files = p.require_lock().setdefault("files", {})
    recorded = {}
    for path in a.paths:
        r = rel(p.root, path)
        h = sha256(p.path(r))
        if h is None:
            raise ValueError(f"cannot record {r}: file does not exist")
        entry = files.get(r, {})
        entry.update({"class": a.cls, "sha256": h})
        if a.template:
            entry["template"] = a.template
        files[r] = entry
        recorded[r] = entry
    p.save()
    return {"recorded": recorded}


def cmd_forget(p, a):
    files = p.require_lock().setdefault("files", {})
    forgotten = [rel(p.root, x) for x in a.paths if files.pop(rel(p.root, x), None) is not None]
    p.save()
    return {"forgotten": forgotten}


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
    ctx = {"plugin_version": plugin_version(), "config": effective_config(p.config)}
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
    template = a.template.replace(os.sep, "/")
    text = render_source(template, p)
    dest = rel(p.root, a.dest)
    entry = lock.setdefault("files", {}).get(dest)
    if a.if_unchanged and entry and p.file_state(dest, entry) == "modified":
        raise Refused(f"{dest} was edited since the plugin wrote it; review the diff instead of overwriting")
    if a.if_unchanged and not entry and os.path.exists(p.path(dest)):
        raise Refused(f"{dest} exists but the plugin never wrote it; review the diff instead of overwriting")
    full = p.path(dest)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    before = sha256(full)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)
    after = sha256(full)
    lock["files"][dest] = {"class": a.cls, "sha256": after, "template": template}
    p.save()
    return {"rendered": dest, "class": a.cls, "changed": before != after}


# --- commands contract -------------------------------------------------------------------
# The project's own commands live in config: `commands` for a single project, or `packages` (each with name,
# path, stack and commands) for a monorepo. A command set to null means "not applicable" (e.g. typecheck for
# shell scripts). Stages, the verifier, CI, the allowlist and the freshness hook all read them from here.

ROOT_SCOPE = "(root)"


def scopes(config):
    """[{name, path, stack, commands}]: one per package, or the root project when there are no packages."""
    cfg = effective_config(config)
    pkgs = cfg.get("packages") or []
    if pkgs:
        return [{"name": pk.get("name"), "path": (pk.get("path") or ".").rstrip("/") or ".",
                 "stack": pk.get("stack"), "commands": pk.get("commands") or {}} for pk in pkgs]
    return [{"name": ROOT_SCOPE, "path": ".", "stack": None, "commands": cfg.get("commands") or {}}]


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


def cmd_contract(p, a):
    cfg = effective_config(p.config)
    required = cfg.get("contract", {}).get("required", [])
    out = {"required": required, "monorepo": bool(cfg.get("packages")), "scopes": {}}
    names = set()
    for sc in scopes(p.config):
        problems = []
        if not sc["name"]:
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
    return out


def verify_plan(config):
    cfg = effective_config(config)
    order = cfg.get("verify", {}).get("order", ["lint", "typecheck", "build", "test"])
    plan = {"install": [], "verify": []}
    for sc in scopes(config):
        cmds = sc["commands"]
        if cmds.get("install"):
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
    "node": ["- uses: actions/setup-node@v4", "  with:", '    node-version: "{node_version}"', "- run: corepack enable"],
    "python": ["- uses: astral-sh/setup-uv@v6"],
    "go": ["- uses: actions/setup-go@v5", "  with:", "    go-version-file: {go_mod}"],
    "rust": ["- uses: dtolnay/rust-toolchain@stable", "  with:", "    components: clippy, rustfmt"],
    "dart": ["- uses: dart-lang/setup-dart@v1"],
    "flutter": ["- uses: subosito/flutter-action@v2", "  with:", "    channel: stable"],
    "java": ["- uses: actions/setup-java@v4", "  with:", "    distribution: temurin", '    java-version: "{java_version}"'],
    "dotnet": ["- uses: actions/setup-dotnet@v4", "  with:", '    dotnet-version: "{dotnet_version}"'],
    "shell": ["- run: sudo apt-get install -y shellcheck shfmt bats"],
}


def project_stacks(config):
    """Distinct toolchains, from each package's `stack`, else `project.stack`."""
    cfg = effective_config(config)
    raw = [sc["stack"] for sc in scopes(config) if sc["stack"]] or cfg.get("project", {}).get("stack", [])
    found = []
    for st in raw:
        st = STACK_ALIASES.get(str(st).lower(), str(st).lower())
        if st not in found:
            found.append(st)
    return found


def generate_ci(p):
    cfg = effective_config(p.config)
    ci = cfg.get("ci", {})
    plan = verify_plan(p.config)
    if not plan["verify"]:
        raise ValueError("no commands in .sdlc/config.json to put in CI (set `commands`, or `packages[].commands`)")
    go_scope = next((sc for sc in scopes(p.config) if os.path.exists(p.path(os.path.join(sc["path"], "go.mod")))), None)
    go_mod = os.path.normpath(os.path.join(go_scope["path"] if go_scope else ".", "go.mod")).replace(os.sep, "/")
    values = {"node_version": ci.get("node_version", "22"), "java_version": ci.get("java_version", "21"),
              "dotnet_version": ci.get("dotnet_version", "8.0.x"), "go_mod": go_mod}
    pad = " " * 6
    lines = [
        f"# Managed by the sdlc plugin v{plugin_version()} (seeded: replaced on upgrade only while unedited).",
        "# Generated from the commands in .sdlc/config.json: the same commands Stage 5 runs.",
        "name: sdlc verify", "", "on:", "  pull_request:", "  push:", "    branches: [main, master]", "",
        "concurrency:", "  group: sdlc-verify-${{ github.ref }}", "  cancel-in-progress: true", "",
        "permissions:", "  contents: read", "",
        "defaults:", "  run:", "    shell: bash  # Git Bash on Windows runners: same shell everywhere", "",
        "jobs:", "  verify:", "    strategy:", "      fail-fast: false", "      matrix:",
        f"        os: {json.dumps(ci.get('os', ['ubuntu-latest']))}",
        "    runs-on: ${{ matrix.os }}", "    timeout-minutes: 30", "    steps:", pad + "- uses: actions/checkout@v4"]
    for st in project_stacks(p.config):
        if st in CI_SETUP:
            lines += [pad + x.format(**values) for x in CI_SETUP[st]]
        else:
            lines.append(pad + f"# TODO: add the toolchain setup for '{st}'")
    for step in plan["install"] + plan["verify"]:
        label = step["step"] if step["scope"] == ROOT_SCOPE else f"{step['scope']} · {step['step']}"
        lines.append(pad + f"- name: {json.dumps(label, ensure_ascii=False)}")
        if step["cwd"] != ".":
            lines.append(pad + f"  working-directory: {step['cwd']}")
        lines += [pad + "  run: |", pad + "    " + step["run"]]
    return "\n".join(lines) + "\n"


def render_source(template, p):
    if template == "builtin:ci":
        return generate_ci(p)
    with open(os.path.join(PLUGIN_ROOT, template), encoding="utf-8") as f:
        return render_text(f.read(), p)


def template_exists(template):
    return template.startswith("builtin:") or os.path.exists(os.path.join(PLUGIN_ROOT, template))


def cmd_preview(p, a):
    return {"template": a.template, "text": render_source(a.template, p)}


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
    settings_path = p.path(SETTINGS)
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


def cmd_gitignore(p, a):
    path = p.path(GITIGNORE)
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
    return {"added": added, "removed": removed, "owned": ours}


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
            if sv < parse_version(m["version"]) <= pv and m["id"] not in done]


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


def cmd_set_version(p, a):
    lock = p.require_lock()
    parse_version(a.version)
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
            "regenerate": [], "replace": [], "review": [], "restore": [], "template_gone": []}
    for path, e in sorted(lock.get("files", {}).items()):
        tpl = e.get("template")
        if not tpl:
            continue
        if not template_exists(tpl):
            plan["template_gone"].append(path)
            continue
        state = p.file_state(path, e)
        item = {"path": path, "template": tpl}
        if e["class"] == "generated":
            plan["regenerate"].append(item)
        elif state == "unchanged":
            new = render_source(tpl, p)
            if hashlib.sha256(new.encode("utf-8")).hexdigest() != e["sha256"]:
                plan["replace"].append(item)
        elif state == "modified":
            plan["review"].append(item)
        else:
            plan["restore"].append(item)  # user deleted a seeded file: offer, never force
    plan["pending_migrations"] = pending_migrations(p)
    return plan


def eject_plan(p):
    lock = p.require_lock()
    plan = {"delete": [], "ask": [], "already_gone": [], "unmerge": lock.get("merged", {}),
            "keep": [CONFIG, ".sdlc/constitution.md", ".sdlc/baseline.md", "knowledge/", ".sdlc/<feature>/"]}
    for path, e in sorted(lock.get("files", {}).items()):
        state = p.file_state(path, e)
        if state == "missing":
            plan["already_gone"].append(path)
        elif e["class"] == "generated" or state == "unchanged":
            plan["delete"].append(path)
        else:
            plan["ask"].append(path)
    return plan


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
    allow = plan["unmerge"].get(SETTINGS, [])
    if allow:
        cmd_allow(p, argparse.Namespace(add=[], remove=list(allow)))
    ignore = plan["unmerge"].get(GITIGNORE, [])
    if ignore:
        cmd_gitignore(p, argparse.Namespace(add=[], remove=list(ignore)))
    os.remove(p.path(LOCK))
    p.lock = None
    return {"deleted": deleted, "kept_edited": [x for x in plan["ask"] if x not in extra],
            "unmerged": {SETTINGS: allow, GITIGNORE: ignore}, "lock_removed": True}


# --- cli ----------------------------------------------------------------------------------

def build_parser():
    ap = argparse.ArgumentParser(prog="scaffold.py", description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="start setup: write lock (and a default config if none)")
    s.add_argument("--kind", choices=["greenfield", "brownfield"], required=True)
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_init)

    sub.add_parser("status", help="setup state, drift, pending migrations, file states").set_defaults(fn=cmd_status)
    sub.add_parser("config", help="effective config (plugin defaults + project overrides)").set_defaults(fn=cmd_config)

    s = sub.add_parser("step-done", help="mark a setup step complete (resumable setup)")
    s.add_argument("step")
    s.add_argument("--complete", action="store_true", help="also mark the whole setup complete")
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
    s.add_argument("template", help="plugin-relative, e.g. templates/project/rules/sdlc.md, or builtin:ci")
    s.add_argument("dest")
    s.add_argument("--class", dest="cls", choices=FILE_CLASSES, default="generated")
    s.add_argument("--if-unchanged", action="store_true", help="refuse (exit 2) if the user edited the file")
    s.set_defaults(fn=cmd_render)

    sub.add_parser("contract", help="check the project's commands in config (per package in a monorepo)") \
        .set_defaults(fn=cmd_contract)
    sub.add_parser("commands", help="scopes and the install/verify plan (what Stage 5 and CI run)") \
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

    s = sub.add_parser("migrations", help="pending migrations in apply order")
    s.add_argument("--revisit", action="store_true", help="also list skipped ones")
    s.set_defaults(fn=cmd_migrations)

    s = sub.add_parser("migration", help="record a migration as applied or skipped")
    s.add_argument("id")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--applied", action="store_true")
    g.add_argument("--skipped", metavar="REASON")
    s.set_defaults(fn=cmd_migration)

    s = sub.add_parser("set-version", help="set scaffold_version (and raise min_plugin_version)")
    s.add_argument("version")
    s.add_argument("--min-plugin")
    s.set_defaults(fn=cmd_set_version)

    sub.add_parser("upgrade-plan", help="what an upgrade would regenerate/replace/review").set_defaults(fn=cmd_upgrade_plan)

    s = sub.add_parser("eject", help="show the eject plan; --apply to carry it out")
    s.add_argument("--apply", action="store_true")
    s.add_argument("--also", nargs="+", help="edited files from 'ask' the user agreed to delete")
    s.set_defaults(fn=cmd_eject)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        result = a.fn(Project(a.root), a)
        code = 0
    except Refused as e:
        result, code = {"refused": str(e)}, 2
    except (ValueError, OSError) as e:
        result, code = {"error": str(e)}, 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
