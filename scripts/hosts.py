#!/usr/bin/env python3
"""Build the files that let Codex, Cursor and Antigravity install this plugin, from the Claude Code sources.

The Claude Code plugin (.claude-plugin/, skills/, commands/, agents/, hooks/) is the one source. This writes:
  .codex-plugin/plugin.json       Codex manifest: the shared skills plus hosts/skills
  .agents/plugins/marketplace.json  Codex repo marketplace (`codex plugin marketplace add tammai/sdlc`)
  .cursor-plugin/plugin.json, marketplace.json   Cursor manifest; agents from hosts/cursor/agents
  plugin.json                     Antigravity manifest (root, as `agy plugin install <github url>` expects), plus hosts/skills
  hosts/cursor/agents/*.md        agents with Cursor's frontmatter: model inherit, readonly for read-only roles
  hosts/skills/<command>/SKILL.md commands as skills: Codex and Antigravity drop commands that take $ARGUMENTS
  hosts/codex/hooks.json, hosts/cursor/hooks.json   the plugin's hooks through hosts/hook.py, which adapts the payloads
  hooks.json                      the same for Antigravity, which reads it at the plugin root

Usage: python3 scripts/hosts.py [--root DIR] build | check   (check exits 1 when a file differs from a fresh build)
       python3 scripts/hosts.py dist antigravity OUT   a copy to `agy plugin install OUT`: Antigravity reads agents/
                                                       itself and skips Claude's model tiers and comma-string tools
Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import shutil
import sys

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
# Write only for their report under .sdlc/.work/findings/ (the role guard holds them to it); on Cursor they read
REPORT_WRITERS = {"code-explorer", "code-reviewer"}
# Claude Code-only commands: the Ralph loop's Stop hook runs only there; hookify rules live in .claude/, which only
# Claude Code's setup writes; context-diet trims Claude Code's own plugin config
CLAUDE_ONLY_COMMANDS = {"cancel-ralph", "ralph-loop", "ralph-help", "hookify-configure", "hookify-help",
                        "hookify-list", "context-diet"}


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
    tools = set(listed_tools(fields))
    # No tools line means every tool, so only a listed set without edit tools is read-only
    readonly = bool(tools) and not tools & EDIT_TOOLS - ({"Write"} if fields["name"] in REPORT_WRITERS else set())
    head = [f"name: {fields['name']}", f"description: {fields['description']}", "model: inherit"]
    if readonly:
        head.append("readonly: true")
    return "---\n" + "\n".join(head) + "\n---\n" + body


def listed_tools(fields):
    return [t.strip(" \"'[]") for t in fields.get("tools", "").split(",") if t.strip(" \"'[]")]


def command_skill(text, name):
    """A command as a skill: no $ARGUMENTS or !`cmd` expansion outside Claude Code, so say it in words."""
    try:
        fields, body = frontmatter(text)
    except ValueError:
        raise ValueError(f"commands/{name}.md: no frontmatter")
    body = body.replace("$ARGUMENTS", "<the user's request>")
    body = re.sub(r"!`([^`]+)`", r"run `\1`", body)
    return f"---\nname: {name}\ndescription: {fields['description']}\n---\n" + body


def antigravity_agent(text, source):
    """Antigravity rejects every model tier and wants tools as a list."""
    try:
        fields, body = frontmatter(text)
    except ValueError:
        raise ValueError(f"{source}: no frontmatter")
    head = [f"name: {fields['name']}", f"description: {fields['description']}", "model: inherit"]
    tools = listed_tools(fields)
    if tools:
        head.append("tools: [" + ", ".join(json.dumps(t) for t in tools) + "]")
    return "---\n" + "\n".join(head) + "\n---\n" + body


def dist(root, host, out):
    if host != "antigravity":
        raise ValueError(f"no dist for {host}: only Antigravity can't read agents from a generated folder")
    if os.path.exists(out) and os.listdir(out):
        raise ValueError(f"{out} is not empty")
    out_abs = os.path.abspath(out)

    def skip(folder, names):
        return [n for n in names if n in (".git", "tests", "__pycache__")
                or os.path.abspath(os.path.join(folder, n)) == out_abs]

    shutil.copytree(root, out, ignore=skip, dirs_exist_ok=True)
    for rel, text in outputs(root).items():
        os.makedirs(os.path.dirname(os.path.join(out, rel)) or out, exist_ok=True)
        with open(os.path.join(out, rel), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    for name in sorted(os.listdir(os.path.join(root, "agents"))):
        if name.endswith(".md"):
            with open(os.path.join(out, "agents", name), "w", encoding="utf-8", newline="\n") as f:
                f.write(antigravity_agent(read(root, f"agents/{name}"), f"agents/{name}"))
    return out


def codex_hooks():
    """hosts/hook.py for each event it adapts. Codex fills in ${PLUGIN_ROOT}, and runs commandWindows in cmd.exe."""
    def entry(event, matcher=None):
        script = '"${PLUGIN_ROOT}/hosts/hook.py" codex ' + event
        group = {"hooks": [{"type": "command", "command": "python3 " + script, "commandWindows": "python " + script,
                            "timeout": 60}]}
        return [dict({"matcher": matcher}, **group) if matcher else group]
    return {"hooks": {"PreToolUse": entry("PreToolUse", "^(Bash|apply_patch)$"),
                      "PostToolUse": entry("PostToolUse", "^(Bash|apply_patch)$"),
                      "UserPromptSubmit": entry("UserPromptSubmit"), "Stop": entry("Stop")}}


def cursor_hooks():
    """hosts/hook.py on Cursor's events, named by the Claude Code event it stands for."""
    def entry(event, matcher=None):
        hook = {"command": 'python3 "${CURSOR_PLUGIN_ROOT}/hosts/hook.py" cursor ' + event, "timeout": 60}
        return [dict(hook, matcher=matcher) if matcher else hook]
    return {"version": 1, "hooks": {"preToolUse": entry("PreToolUse", "^(Shell|Write|Delete)$"),
                                    "postToolUse": entry("PostToolUse", "^(Shell|Write|Delete)$"),
                                    "postToolUseFailure": entry("PostToolUseFailure", "^Shell$"),
                                    "beforeSubmitPrompt": entry("UserPromptSubmit"), "stop": entry("Stop")}}


def antigravity_hooks():
    """hosts/hook.py under one named hook. Antigravity runs a command in the plugin folder through cmd or sh, with no
    Windows variant, so it falls back from python3 to python; a hook that fails denies the tool call."""
    def entry(event):
        script = "hosts/hook.py antigravity " + event
        return {"type": "command", "command": f"python3 {script} || python {script}", "timeout": 60}
    # by verb, not a list: a write tool Antigravity adds later is checked too (multi_replace_file_content, edit_notebook)
    tools = "^(run_command|.*(edit|write|replace|create|delete|patch|move|rename|notebook).*)$"
    return {"sdlc": {"PreToolUse": [{"matcher": tools, "hooks": [entry("PreToolUse")]}],
                     "PostToolUse": [{"matcher": tools, "hooks": [entry("PostToolUse")]}],
                     "PreInvocation": [entry("UserPromptSubmit")], "Stop": [entry("Stop")]}}


def outputs(root):
    plugin = json.loads(read(root, ".claude-plugin/plugin.json"))
    market = json.loads(read(root, ".claude-plugin/marketplace.json"))
    common = {k: plugin[k] for k in ("name", "version", "description", "author", "license", "keywords") if k in plugin}
    repo = "https://github.com/tammai/sdlc"
    files = {
        ".codex-plugin/plugin.json": dump(dict(common, homepage=repo, repository=repo,
                                               skills=["./skills/", "./hosts/skills/"],
                                               # a folder that doesn't exist: else Codex converts commands/ too
                                               commands="./hosts/codex/commands/",
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
        "plugin.json": dump(dict({k: common[k] for k in ("name", "version", "description") if k in common},
                                 skills="./hosts/skills/")),
        "hosts/codex/hooks.json": dump(codex_hooks()),
        "hosts/cursor/hooks.json": dump(cursor_hooks()),
        "hooks.json": dump(antigravity_hooks()),
    }
    for name in sorted(os.listdir(os.path.join(root, "agents"))):
        if name.endswith(".md"):
            files[f"hosts/cursor/agents/{name}"] = cursor_agent(read(root, f"agents/{name}"), f"agents/{name}")
    commands = os.path.join(root, "commands")
    for name in sorted(os.listdir(commands)) if os.path.isdir(commands) else []:
        cmd = name[:-3]
        if name.endswith(".md") and cmd not in CLAUDE_ONLY_COMMANDS:
            files[f"hosts/skills/{cmd}/SKILL.md"] = command_skill(read(root, f"commands/{name}"), cmd)
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
    skills = os.path.join(root, "hosts", "skills")
    existing = sorted(os.listdir(skills)) if os.path.isdir(skills) else []
    out += [f"hosts/skills/{n}/SKILL.md" for n in existing if f"hosts/skills/{n}/SKILL.md" not in files]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hosts.py", description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("cmd", choices=["build", "check", "dist"])
    ap.add_argument("host", nargs="?")
    ap.add_argument("out", nargs="?")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if a.cmd == "dist":
        if not (a.host and a.out):
            ap.error("dist needs a host and an output folder")
        try:
            print(json.dumps({"dist": dist(a.root, a.host, a.out)}))
        except (ValueError, KeyError, OSError) as e:
            print(json.dumps({"error": str(e)}))
            return 1
        return 0
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
            if os.path.dirname(rel).startswith("hosts/skills/") and not os.listdir(os.path.dirname(full)):
                os.rmdir(os.path.dirname(full))
    print(json.dumps({"written": changed}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
