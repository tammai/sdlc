#!/usr/bin/env python3
"""Build the files that let Codex, Cursor and Antigravity install this plugin, from the Claude Code sources.

The Claude Code plugin (.claude-plugin/, skills/, commands/, agents/, hooks/) is the one source. This writes:
  .codex-plugin/plugin.json       Codex manifest: the shared skills (Codex turns commands/ into skills itself)
  .agents/plugins/marketplace.json  Codex repo marketplace (`codex plugin marketplace add tammai/sdlc`)
  .cursor-plugin/plugin.json, marketplace.json   Cursor manifest; agents from hosts/cursor/agents
  plugin.json                     Antigravity manifest (root, as `agy plugin install <github url>` expects)
  hosts/cursor/agents/*.md        agents with Cursor's frontmatter: model inherit, readonly for read-only roles
  hosts/<host>/hooks.json         no hooks yet: the plugin's hooks read Claude Code payloads only

Usage: python3 scripts/hosts.py [--root DIR] build | check   (check exits 1 when a file differs from a fresh build)
Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import sys

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return f.read()


def dump(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text.replace("\r\n", "\n"), re.S)
    if not m:
        raise ValueError("no frontmatter")
    fields = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        fields[k.strip()] = v.strip()
    return fields, text.replace("\r\n", "\n")[m.end():]


def cursor_agent(text, source):
    """Cursor reads name, description, model and readonly; Claude's model tiers aren't Cursor model ids."""
    try:
        fields, body = frontmatter(text)
    except ValueError:
        raise ValueError(f"{source}: no frontmatter")
    tools = {t.strip(" \"'[]") for t in fields.get("tools", "").split(",") if t.strip(" \"'[]")}
    # No tools line means every tool, so only a listed set without edit tools is read-only
    readonly = bool(tools) and not tools & EDIT_TOOLS
    head = [f"name: {fields['name']}", f"description: {fields['description']}", "model: inherit"]
    if readonly:
        head.append("readonly: true")
    return "---\n" + "\n".join(head) + "\n---\n" + body


def outputs(root):
    plugin = json.loads(read(root, ".claude-plugin/plugin.json"))
    market = json.loads(read(root, ".claude-plugin/marketplace.json"))
    common = {k: plugin[k] for k in ("name", "version", "description", "author", "license", "keywords") if k in plugin}
    repo = "https://github.com/tammai/sdlc"
    files = {
        ".codex-plugin/plugin.json": dump(dict(common, homepage=repo, repository=repo, skills="./skills/",
                                               hooks="./hosts/codex/hooks.json",
                                               interface={"displayName": plugin.get("displayName", "SDLC"),
                                                          "category": "Developer Tools"})),
        ".agents/plugins/marketplace.json": dump({"name": market["name"], "plugins": [
            {"name": plugin["name"], "source": {"source": "local", "path": "./"},
             "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Developer tools"}]}),
        ".cursor-plugin/plugin.json": dump(dict(common, homepage=repo, repository=repo, skills="./skills/",
                                                commands="./commands/", agents="./hosts/cursor/agents/",
                                                hooks="./hosts/cursor/hooks.json")),
        ".cursor-plugin/marketplace.json": dump({"name": market["name"], "owner": market.get("owner"), "plugins": [
            {"name": plugin["name"], "source": "./", "description": plugin["description"]}]}),
        "plugin.json": dump({k: common[k] for k in ("name", "version", "description") if k in common}),
        "hosts/codex/hooks.json": dump({"hooks": {}}),
        "hosts/cursor/hooks.json": dump({"version": 1, "hooks": {}}),
    }
    for name in sorted(os.listdir(os.path.join(root, "agents"))):
        if name.endswith(".md"):
            files[f"hosts/cursor/agents/{name}"] = cursor_agent(read(root, f"agents/{name}"), f"agents/{name}")
    return files


def stale(root, files):
    out = []
    for rel, text in sorted(files.items()):
        try:
            same = read(root, rel).replace("\r\n", "\n") == text
        except FileNotFoundError:
            same = False
        if not same:
            out.append(rel)
    agents = os.path.join(root, "hosts", "cursor", "agents")
    existing = sorted(os.listdir(agents)) if os.path.isdir(agents) else []
    out += [f"hosts/cursor/agents/{n}" for n in existing if f"hosts/cursor/agents/{n}" not in files]  # agent removed
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hosts.py", description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("cmd", choices=["build", "check"])
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        files = outputs(a.root)
    except (ValueError, KeyError, OSError) as e:
        print(json.dumps({"error": str(e)}))
        return 1
    changed = stale(a.root, files)
    if a.cmd == "check":
        print(json.dumps({"stale": changed}, indent=2))
        return 1 if changed else 0
    for rel in changed:
        full = os.path.join(a.root, rel)
        if rel in files:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8", newline="\n") as f:
                f.write(files[rel])
        else:
            os.remove(full)
    print(json.dumps({"written": changed}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
