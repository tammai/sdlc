#!/usr/bin/env python3
"""sdlc context diet: what Claude Code loads into every call for this project, as facts.

Every enabled skill, agent and command is listed by name and description in each main-session call, and
plugins can add MCP servers. This estimates that cost per source (plugins, personal skills, claude.ai-synced
plugins and skills) and reads what the project is, so the trimming-context skill can propose what to switch off.
Only two verdicts are decided here: standalone copies of plugins sdlc bundles, and LSPs by language.
Read-only. Usage: python3 context_diet.py [--home DIR] [--root DIR]
Prints one JSON object. Stdlib only, Python 3.9+.
"""
import argparse
import json
import math
import os
import subprocess
import sys

DUPLICATES = {"security-guidance", "code-review", "code-simplifier"}  # bundled in sdlc
LSP_LANGUAGES = {
    "typescript-lsp": {"typescript", "javascript"}, "pyright-lsp": {"python"}, "rust-analyzer-lsp": {"rust"},
    "gopls-lsp": {"go"}, "clangd-lsp": {"c", "cpp"}, "jdtls-lsp": {"java"}, "kotlin-lsp": {"kotlin"},
    "csharp-lsp": {"csharp"}, "php-lsp": {"php"}, "swift-lsp": {"swift"}, "lua-lsp": {"lua"}, "ruby-lsp": {"ruby"},
}
EXTENSIONS = {
    ".ts": "typescript", ".tsx": "typescript", ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".cjs": "javascript", ".py": "python", ".rs": "rust", ".go": "go", ".c": "c", ".h": "c", ".cc": "cpp",
    ".cpp": "cpp", ".hpp": "cpp", ".java": "java", ".kt": "kotlin", ".cs": "csharp", ".php": "php",
    ".swift": "swift", ".lua": "lua", ".rb": "ruby", ".dart": "dart",
}
MANIFESTS = {
    "package.json": "javascript", "tsconfig.json": "typescript", "Cargo.toml": "rust", "pyproject.toml": "python",
    "requirements.txt": "python", "setup.py": "python", "go.mod": "go", "Gemfile": "ruby", "composer.json": "php",
    "pom.xml": "java", "build.gradle": "java", "build.gradle.kts": "kotlin", "Package.swift": "swift",
    "pubspec.yaml": "dart", "CMakeLists.txt": "cpp",
}
OTHER_SIGNALS = ("wrangler.toml", "wrangler.json", "wrangler.jsonc", "playwright.config.ts", "playwright.config.js",
                 "Dockerfile", "components.json", ".mcp.json", "CLAUDE.md", "AGENTS.md")
DESIGN_EXTENSIONS = (".fig", ".sketch", ".pen", ".xd")
SKIP_DIRS = {".git", "node_modules", "vendor", "target", "dist", "build", ".venv", "venv", "__pycache__", ".next"}
MAX_FILES = 5000

problems = []


def problem(path, what):
    problems.append({"file": path.replace(os.sep, "/"), "problem": what})


def read_json(path, required=False):
    """The parsed file, or None (reported) when it's missing or malformed."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        problem(path, "not a JSON object")
    except FileNotFoundError:
        if required:
            problem(path, "missing")
    except (OSError, ValueError) as e:
        problem(path, f"unreadable: {e}")
    return None


def frontmatter(path):
    """name and description from a markdown file's frontmatter. Forgiving: folded (>) and literal (|) blocks."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    out, key = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if key and (line.startswith((" ", "\t")) or not line.strip()):
            out[key] = (out[key] + " " + line.strip()).strip()
            continue
        k, sep, v = line.partition(":")
        if not sep or line.startswith((" ", "\t", "-")):
            key = None
            continue
        k, v = k.strip(), v.strip()
        key = k if v in ("", ">", "|", ">-", "|-", ">+", "|+") else None
        out[k] = "" if key else v.strip("'\"")
    return out


def item(path, default_name, prefix):
    """One listed skill, command or agent: (name, tokens), or None when Claude Code doesn't list it."""
    fm = frontmatter(path)
    if str(fm.get("disable-model-invocation", "")).lower() == "true":
        return None
    name = fm.get("name") or default_name
    line = f"- {prefix}{name}: {fm.get('description', '')}\n"
    return name, math.ceil(len(line) / 4), fm.get("description", "")


def paths_of(base, manifest, key, default):
    extra = manifest.get(key) if manifest else None
    extra = [extra] if isinstance(extra, str) else extra if isinstance(extra, list) else []
    return [os.path.normpath(os.path.join(base, p)) for p in [default] + [p for p in extra if isinstance(p, str)]]


def scan_items(base, manifest, prefix):
    """Every listed skill, command and agent under a plugin folder: [(name, tokens, description)]."""
    found, seen = [], set()

    def add(path, name):
        real = os.path.realpath(path)
        if real in seen:
            return
        seen.add(real)
        got = item(path, name, prefix)
        if got:
            found.append(got)

    for root in paths_of(base, manifest, "skills", "skills"):
        if os.path.isfile(os.path.join(root, "SKILL.md")):
            add(os.path.join(root, "SKILL.md"), os.path.basename(root))
        elif os.path.isdir(root):
            for d in sorted(os.listdir(root)):
                if os.path.isfile(os.path.join(root, d, "SKILL.md")):
                    add(os.path.join(root, d, "SKILL.md"), d)
    for key in ("commands", "agents"):
        for root in paths_of(base, manifest, key, key):
            if os.path.isfile(root) and root.endswith(".md"):
                add(root, os.path.basename(root)[:-3])
            for d, _, files in os.walk(root) if os.path.isdir(root) else []:
                for f in sorted(files):
                    if f.endswith(".md"):
                        rel = os.path.relpath(os.path.join(d, f[:-3]), root)
                        add(os.path.join(d, f), rel.replace(os.sep, ":"))
    return found


def mcp_servers(base, manifest):
    servers = read_json(os.path.join(base, ".mcp.json")) or {}
    servers = servers.get("mcpServers", servers)  # both forms ship: wrapped in mcpServers, or the servers at the top
    inline = (manifest or {}).get("mcpServers")
    if isinstance(inline, str):
        inline = (read_json(os.path.normpath(os.path.join(base, inline))) or {}).get("mcpServers")
    if isinstance(inline, dict):
        servers = dict(servers, **inline)
    return sorted(servers) if isinstance(servers, dict) else []


def scan_plugin(base, prefix):
    manifest = read_json(os.path.join(base, ".claude-plugin", "plugin.json"))
    items = scan_items(base, manifest, prefix)
    return {
        "tokens": sum(t for _, t, _ in items),
        "items": len(items),
        "mcp": mcp_servers(base, manifest),
        "hooks": os.path.isfile(os.path.join(base, "hooks", "hooks.json")) or bool((manifest or {}).get("hooks")),
        "about": str((manifest or {}).get("description", ""))[:200],
        "names": [n for n, _, _ in items][:25],
    }


def install_path(records, key, root):
    """The install folder for one plugin key: a project-scope install of this project wins over the user's."""
    entries = records.get(key)
    entries = [entries] if isinstance(entries, dict) else entries if isinstance(entries, list) else []
    entries = [e for e in entries if isinstance(e, dict)]
    here = os.path.normcase(os.path.realpath(root))
    for e in entries:
        if e.get("projectPath") and os.path.normcase(os.path.realpath(e["projectPath"])) == here:
            return e.get("installPath")
    for e in entries:
        if e.get("scope", "user") == "user":
            return e.get("installPath")
    return entries[0].get("installPath") if entries else None


def project_signals(root):
    languages, manifests, deps, design = set(), [], set(), []
    count = 0
    for d, dirs, files in os.walk(root):
        rel = os.path.relpath(d, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not (x.startswith(".") and x not in (".sdlc", ".claude")))
        if depth >= 4:
            dirs[:] = []
        for f in files:
            count += 1
            path = os.path.join(rel, f) if rel != "." else f
            ext = os.path.splitext(f)[1].lower()
            if ext in EXTENSIONS:
                languages.add(EXTENSIONS[ext])
            if ext in DESIGN_EXTENSIONS:
                design.append(path.replace(os.sep, "/"))
            if depth <= 2 and (f in MANIFESTS or f in OTHER_SIGNALS):
                manifests.append(path.replace(os.sep, "/"))
                if f in MANIFESTS:
                    languages.add(MANIFESTS[f])
                if f == "package.json":
                    pkg = read_json(os.path.join(d, f)) or {}
                    for k in ("dependencies", "devDependencies"):
                        if isinstance(pkg.get(k), dict):
                            deps.update(pkg[k])
        if count >= MAX_FILES:
            break
    return {
        "languages": sorted(languages),
        "manifests": manifests[:40],
        "dependencies": sorted(deps)[:80],
        "design_files": design[:10],
        "sdlc": os.path.isfile(os.path.join(root, ".sdlc", "config.json")),
    }


def local_settings(root):
    rel = ".claude/settings.local.json"
    p = subprocess.run(["git", "-C", root, "check-ignore", "-q", rel], capture_output=True,
                       encoding="utf-8", errors="replace")
    return {"path": rel, "exists": os.path.isfile(os.path.join(root, rel)),
            "ignored": {0: True, 1: False}.get(p.returncode)}  # None: not a git repo


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--home", help="home directory to read .claude from (default: CLAUDE_CONFIG_DIR, else ~)")
    ap.add_argument("--root", default=os.getcwd(), help="project directory (default: current)")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    config = os.path.join(a.home, ".claude") if a.home else (
        os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"))

    layers = [("user", os.path.join(config, "settings.json")),
              ("project", os.path.join(root, ".claude", "settings.json")),
              ("local", os.path.join(root, ".claude", "settings.local.json"))]
    enabled, set_by = {}, {}
    for scope, path in layers:  # later scopes override earlier ones key by key
        plugins = (read_json(path, required=scope == "user") or {}).get("enabledPlugins")
        for k, v in (plugins.items() if isinstance(plugins, dict) else []):
            enabled[k], set_by[k] = v is True, scope
    records = (read_json(os.path.join(config, "plugins", "installed_plugins.json"), required=True) or {})
    records = records.get("plugins", records) if isinstance(records.get("plugins", records), dict) else {}
    sdlc_on = any(on and k.split("@")[0] == "sdlc" for k, on in enabled.items())
    signals = project_signals(root)

    sources = []
    for key in sorted(enabled):
        name = key.split("@")[0]
        src = {"kind": "plugin", "key": key, "name": name, "enabled": enabled[key], "set_by": set_by[key],
               "tokens": 0, "items": 0, "mcp": [], "verdict": None, "rule": None}
        if enabled[key]:
            base = install_path(records, key, root)
            if not base or not os.path.isdir(base):
                problem(key, "enabled but not installed (no install record or folder)")
            else:
                src.update(scan_plugin(base, name + ":"))
            if name in DUPLICATES and sdlc_on:
                src.update(verdict="duplicate", rule=f"sdlc is enabled here and bundles {name}")
            elif name in LSP_LANGUAGES:
                present = LSP_LANGUAGES[name] & set(signals["languages"])
                src.update(verdict="keep" if present else "off",
                           rule=f"{'/'.join(sorted(LSP_LANGUAGES[name]))} {'present' if present else 'not in this project'}")
        sources.append(src)

    skills = os.path.join(config, "skills")
    for d in sorted(os.listdir(skills)) if os.path.isdir(skills) else []:
        path = os.path.join(skills, d, "SKILL.md")
        got = d != "synced" and os.path.isfile(path) and item(path, d, "")
        if got:
            sources.append({"kind": "personal", "type": "skill", "name": got[0], "tokens": got[1], "items": 1,
                            "about": got[2][:200]})
    for kind in ("commands", "agents"):
        folder = os.path.join(config, kind)
        for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            got = f.endswith(".md") and item(os.path.join(folder, f), f[:-3], "")
            if got:
                sources.append({"kind": "personal", "type": kind[:-1], "name": got[0], "tokens": got[1], "items": 1,
                                "about": got[2][:200]})

    synced, seen = os.path.join(config, "plugins", "synced"), set()
    for bucket in sorted(os.listdir(synced)) if os.path.isdir(synced) else []:
        bdir = os.path.join(synced, bucket)
        for p in sorted(os.listdir(bdir)) if os.path.isdir(bdir) else []:
            base = os.path.join(bdir, p)
            if p not in seen and os.path.isfile(os.path.join(base, ".claude-plugin", "plugin.json")):
                seen.add(p)
                sources.append(dict({"kind": "synced", "name": p}, **scan_plugin(base, p + ":")))
    synced_skills, names = os.path.join(skills, "synced"), {}
    for bucket in sorted(os.listdir(synced_skills)) if os.path.isdir(synced_skills) else []:
        bdir = os.path.join(synced_skills, bucket)
        for d in sorted(os.listdir(bdir)) if os.path.isdir(bdir) else []:
            path = os.path.join(bdir, d, "SKILL.md")
            got = d not in names and os.path.isfile(path) and item(path, d, "")
            if got:
                names[d] = got[1]
    if names:
        sources.append({"kind": "synced", "name": "claude.ai skills", "tokens": sum(names.values()),
                        "items": len(names), "mcp": [], "names": sorted(names)[:25]})

    totals = {}
    for s in sources:
        totals[s["kind"]] = totals.get(s["kind"], 0) + s["tokens"]
    totals["all"] = sum(totals.values())
    sys.stdout.reconfigure(encoding="utf-8")  # descriptions carry em-dashes; a cp1252 pipe can't encode them
    print(json.dumps({"config_dir": config.replace(os.sep, "/"), "root": root.replace(os.sep, "/"),
                      "sdlc_enabled": sdlc_on, "totals": totals, "sources": sources, "project": signals,
                      "local_settings": local_settings(root), "problems": problems},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
