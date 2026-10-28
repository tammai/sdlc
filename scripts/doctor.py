#!/usr/bin/env python3
"""sdlc doctor: read-only health check of the machine, the plugin and the current repo.

Every check returns ok | warn | fail | skip with a one-line detail and, when not ok, a fix pointer
(a runbook procedure or a command). Changes nothing. Exit 1 if any check fails, else 0.
Usage: python3 doctor.py [--root DIR] [--format json|md]
Stdlib only, Python 3.9+.
"""
import argparse
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
sys.path.insert(0, PLUGIN_ROOT)
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "hooks"))
import sdlc_layout  # noqa: E402  (hooks/: where feature state and documents live)
import scaffold  # noqa: E402  (sibling script: lock, config, commands and version logic)

CLAUDE_MD_BUDGET = 60
RUNBOOK = "docs/runbook.md"


class Report:
    def __init__(self):
        self.checks = []

    def add(self, group, name, status, detail, fix=None):
        self.checks.append({"group": group, "check": name, "status": status, "detail": detail, "fix": fix})


def run(cmd, cwd=None, timeout=10):
    try:
        p = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=timeout)
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None, ""


# --- environment -------------------------------------------------------------------------

def claude_hosted(root):
    try:
        return "claude-code" in scaffold.hosts(scaffold.Project(root))
    except ValueError:
        return True


def check_environment(r, root):
    g = "environment"
    # jq and the security reviewer serve Claude Code hooks only; other agents run none yet
    claude = claude_hosted(root)
    no_claude = "used only by Claude Code hooks, and this repo has no Claude Code host"
    v = sys.version_info
    r.add(g, "python", "ok" if v >= (3, 9) else "fail", f"{v.major}.{v.minor}.{v.micro}",
          None if v >= (3, 9) else "install Python 3.9+ (hooks and scripts need it)")
    # hooks.json starts every hook through hooks/sg-python.sh, which skips the Microsoft Store stub; if it finds no
    # Python, every guardrail fails open (Claude Code treats any exit other than 2 as non-blocking)
    bash = shutil.which("bash")
    bash = bash if bash and "system32" not in bash.lower() else None  # System32's bash is WSL, not Git Bash
    launcher = os.path.join(PLUGIN_ROOT, "hooks", "sg-python.sh")
    code, out = run([bash, launcher, "-c", "import sys; print(sys.version_info[0])"]) if bash else (None, "")
    ok = code == 0 and out.strip().endswith("3")
    r.add(g, "hook python", "ok" if ok else "fail",
          "hooks/sg-python.sh finds Python 3" if ok else
          ("no bash on PATH" if not bash else f"hooks/sg-python.sh found no working Python 3 (exit {code})"),
          None if ok else "install Python 3.10+ from python.org (not the Microsoft Store) and Git Bash on Windows")
    for tool, needed_for, status in (("git", "worktrees, freshness hook, commits", "fail"),
                                     ("gh", "/sdlc:code-review and PR commands", "warn"),
                                     ("jq", "the sdlc-extras Ralph loop's stop hook (it silently stops looping without it)", "warn")):
        found = shutil.which(tool)
        if tool == "jq" and not claude:
            r.add(g, tool, "skip", no_claude)
            continue
        r.add(g, tool, "ok" if found else status, found or f"not found (needed for {needed_for})",
              None if found else f"install {tool}")
    if not claude:
        r.add(g, "security reviewer env", "skip", no_claude)
        return
    try:
        from hooks import _base  # the security hooks' own resolver and install check
        state = _base.state_dir()
        if _base.llm_reviews_switched_off():
            r.add(g, "security reviewer env", "skip", "model reviews are switched off by environment variables")
        elif _base.agent_sdk_installed(state):
            r.add(g, "security reviewer env", "ok", os.path.join(state, "agent-sdk-venv"))
        else:
            r.add(g, "security reviewer env", "warn",
                  f"not built in {state}. A session start builds it in the background, but only when the security "
                  "hooks receive credentials (a Claude Code sign-in or ANTHROPIC_API_KEY); without them the "
                  "model reviews are skipped and pattern warnings still work",
                  f"keep a signed-in session open for about a minute · {RUNBOOK} R2")
    except ImportError as e:
        r.add(g, "security reviewer env", "skip", f"security hook modules not importable: {e}")


# --- plugin ---------------------------------------------------------------------------------

def check_plugin(r):
    g = "plugin"
    r.add(g, "version", "ok", scaffold.plugin_version())
    path = os.path.join(PLUGIN_ROOT, "hooks", "hooks.json")
    try:
        hooks = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        r.add(g, "hooks.json", "fail", f"unreadable: {e}", f"reinstall the plugin · {RUNBOOK} R1")
        return
    missing = []
    for groups in hooks.get("hooks", {}).values():
        for grp in groups:
            for h in grp.get("hooks", []):
                for ref in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"'\s]+)", h.get("command", "")):
                    if not os.path.exists(os.path.join(PLUGIN_ROOT, ref)):
                        missing.append(ref)
    r.add(g, "hook scripts", "fail" if missing else "ok",
          "missing: " + ", ".join(sorted(set(missing))) if missing else "all referenced scripts exist",
          f"reinstall the plugin · {RUNBOOK} R1" if missing else None)


# --- repo -------------------------------------------------------------------------------------

def expand_braces(pattern):
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    return [x for alt in m.group(1).split(",") for x in expand_braces(pattern[:m.start()] + alt + pattern[m.end():])]


def glob_matches(pattern, files):
    for p in expand_braces(pattern):
        rx = re.escape(p).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
        if any(re.fullmatch(rx, f) for f in files):
            return True
    return False


def repo_files(root):
    code, out = run(["git", "-C", root, "ls-files", "--cached", "--others", "--exclude-standard"])
    if code == 0:
        return out.splitlines()
    files = []
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x not in (".git", "node_modules", ".venv", "target", "dist", "build")]
        files += [os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/") for n in names]
    return files


def rule_paths(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m or "paths:" not in m.group(1):
        return None
    return [x.strip().strip("\"'") for x in re.findall(r"^\s*-\s*(.+)$", m.group(1).split("paths:", 1)[1], re.M)]


def check_repo(r, root):
    g = "repo"
    try:
        p = scaffold.Project(root)
        status = scaffold.cmd_status(p, None)
    except ValueError as e:
        r.add(g, "config and lock", "fail", str(e), f"fix the JSON or restore it from git · {RUNBOOK} R12")
        return
    if status["setup"] == "none":
        r.add(g, "setup", "warn", "not set up for sdlc", "/sdlc:setup")
    elif status["setup"] == "in_progress":
        r.add(g, "setup", "warn", f"in progress (done: {', '.join(status['completed_steps']) or 'nothing yet'})",
              f"/sdlc:setup resumes it · {RUNBOOK} R12")
    else:
        r.add(g, "setup", "ok", "complete")
        drift = status["drift"]
        detail = f"scaffold {status['scaffold_version']}, plugin {status['plugin_version']}"
        if drift == "behind":
            pend = status["pending_migrations"]
            r.add(g, "version", "warn", detail + (f"; pending migrations: {', '.join(pend)}" if pend else ""),
                  "/sdlc:upgrade")
        elif drift == "plugin_too_old":
            r.add(g, "version", "fail", detail + f"; repo needs plugin ≥ {status['min_plugin_version']}",
                  "/plugin update sdlc")
        else:
            r.add(g, "version", "ok", detail + (" (repo upgraded by a newer plugin)" if drift == "ahead" else ""))
        files = status.get("files", {})
        missing = [f for f, e in files.items() if e["state"] == "missing"]
        edited = [f for f, e in files.items() if e["state"] == "modified" and e["class"] == "seeded"]
        regen = [f for f, e in files.items() if e["state"] == "modified" and e["class"] == "generated"]
        if missing or regen:
            r.add(g, "plugin files", "warn",
                  "; ".join(x for x in (f"missing: {', '.join(missing)}" if missing else "",
                                       f"generated but hand-edited (lost on upgrade): {', '.join(regen)}" if regen else "") if x),
                  f"/sdlc:upgrade restores or regenerates them · {RUNBOOK} R14")
        else:
            r.add(g, "plugin files", "ok", f"{len(files)} tracked" + (f"; you edited: {', '.join(edited)}" if edited else ""))
        contract = scaffold.cmd_contract(p, None)
        problems, tools = [], []
        for name, sc in contract["scopes"].items():
            where = "" if name == scaffold.ROOT_SCOPE else f"{name}: "
            problems += [where + x for x in sc["problems"]]
            if sc["missing"]:
                problems.append(f"{where}no {', '.join(sc['missing'])} command")
            tools += [f"{where}{key} needs `{exe}`" for key, exe in sc["not_found"].items()]
        r.add(g, "commands", "fail" if problems else "ok",
              "; ".join(problems) if problems else
              f"defined for {len(contract['scopes'])} {'package' if contract['monorepo'] else 'project'}"
              f"{'s' if len(contract['scopes']) > 1 else ''}",
              f"set them in .sdlc/config.json · {RUNBOOK} R13" if problems else None)
        if tools:
            r.add(g, "command tools", "warn", "not found on PATH: " + "; ".join(tools),
                  f"install the tool, or fix the command in .sdlc/config.json · {RUNBOOK} R13")
        runs = contract.get("runs") or {}
        unrun = [f"{'' if name == scaffold.ROOT_SCOPE else name + ': '}{key}"
                 for name, sc in contract["scopes"].items() for key in scaffold.verify_steps(p.config, name)
                 if not (runs.get(name, {}).get(key) or {}).get("ran")]
        if status["setup"] == "complete" and unrun:
            r.add(g, "commands run", "warn", "never run successfully since recorded: " + ", ".join(unrun),
                  f"python3 scripts/scaffold.py run-commands · {RUNBOOK} R13")
        try:
            agents, cut = scaffold.agents_state(p), scaffold.codex_cut(p)
            if cut:
                r.add(g, "AGENTS.md", "warn", cut, "python3 scripts/scaffold.py agents after shortening")
            elif agents != "off":
                r.add(g, "AGENTS.md", "ok" if agents == "in_sync" else "warn",
                      f"the sdlc block matches its sources (hosts: {', '.join(scaffold.hosts(p))})"
                      if agents == "in_sync" else
                      "the sdlc block or its Claude Code mirror is out of date: some agents follow old instructions",
                      None if agents == "in_sync" else "python3 scripts/scaffold.py agents")
        except ValueError as e:
            r.add(g, "AGENTS.md", "fail", str(e), "fix the line, then python3 scripts/scaffold.py agents")
        cfg = scaffold.effective_config(p.config)
        if cfg.get("project", {}).get("kind") == "brownfield":
            b = os.path.join(root, cfg.get("baseline", ".sdlc/baseline.md"))
            r.add(g, "baseline", "ok" if os.path.exists(b) else "warn",
                  "present" if os.path.exists(b) else "brownfield repo without a baseline: old failures will fail Review",
                  None if os.path.exists(b) else f"rerun the baseline step of /sdlc:setup · {RUNBOOK} R16")

    if status["setup"] == "complete" and sdlc_layout.docs_dir(root) is None:
        r.add(g, "layout", "warn", "sdlc documents are still in .sdlc/ (the layout before 1.7.0)",
              "run /sdlc:upgrade to move them to docs/sdlc or a location you choose")

    gi = os.path.join(root, ".gitignore")
    lines = open(gi, encoding="utf-8").read().split() if os.path.exists(gi) else []
    # The control contract's runtime files (state.py, spec 12): setup adds these; repos set up before get them
    # from /sdlc:upgrade, which re-runs the gitignore step
    contract = [x for x in (".sdlc/state/*.json", ".sdlc/state/*.events.jsonl", ".sdlc/state/*.commands/")
                if x not in lines]
    if os.path.isdir(os.path.join(root, ".sdlc")):
        if ".sdlc/.work/" not in lines:
            r.add(g, ".gitignore", "warn", ".sdlc/.work/ is not git-ignored (scratch files may get committed)",
                  "add `.sdlc/.work/` to .gitignore")
        elif contract:
            r.add(g, ".gitignore", "warn", "the control contract's files aren't git-ignored: "
                  + ", ".join(contract), "run /sdlc:upgrade (it re-runs setup's gitignore step)")
        else:
            r.add(g, ".gitignore", "ok", ".sdlc/.work/ and the control contract ignored", None)

    files = repo_files(root)
    if status["setup"] == "complete":
        prd = sdlc_layout.prd(root)
        has_prd = os.path.isfile(os.path.join(root, prd))
        r.add(g, "PRD", "ok" if has_prd else "warn",
              prd if has_prd else f"no product doc ({prd}): Define has no goals, non-goals or audience to start from",
              None if has_prd else "run the prd step of /sdlc:setup (or /sdlc:upgrade)")
        enabled = scaffold.read_json(os.path.join(root, scaffold.LOCAL_SETTINGS), {}).get("enabledPlugins")
        enabled = enabled if isinstance(enabled, dict) else {}
        on = [c["id"] for c in scaffold.companions(p) if enabled.get(c["id"]) is True]
        if on:
            missing = [i for i in on if not scaffold.installed_plugins().get(i)]
            r.add(g, "companions", "warn" if missing else "ok",
                  f"enabled here but not installed: {', '.join(missing)}" if missing else ", ".join(on),
                  f"claude plugin install {missing[0]}" if missing else None)
        clash = {c["plugin"]: c for c in scaffold.conflicts() if c.get("plugin")}
        still_on = [i for i in scaffold.enabled_elsewhere(p)
                    if i.split("@", 1)[0] in clash and enabled.get(i) is not False]
        in_repo = scaffold.conflicts_in_repo(p)
        if still_on or in_repo:
            r.add(g, "conflicts", "warn",
                  "; ".join([f"{i} is on for this repo: {clash[i.split('@', 1)[0]]['why']}" for i in still_on]
                            + [f"{c['name']} ({', '.join(c['found'])}): {c['why']}" for c in in_repo]),
                  "python3 scripts/scaffold.py enable-plugin turns the plugin off for this repo only"
                  if still_on else "keep it, or remove its files from the repo (the team's call)")
        ui = scaffold.effective_config(p.config).get("areas", {}).get("ui", [])
        if any(glob_matches(x, files) for x in ui):
            design_system = sdlc_layout.paths(root)["design_system"]
            ds = os.path.exists(os.path.join(root, design_system))
            r.add(g, "design system", "ok" if ds else "warn",
                  design_system if ds else f"the repo has UI files but no {design_system}: UI work has no system to follow",
                  None if ds else "run the design-system step of /sdlc:setup (or /sdlc:upgrade)")

    dead = []
    for path in sorted(glob.glob(os.path.join(root, ".claude", "rules", "*.md"))):
        if os.path.basename(path).startswith("sdlc"):
            continue  # plugin policy rules wait for files to exist (e.g. no migrations yet); not a problem
        paths = rule_paths(open(path, encoding="utf-8").read())
        if paths and not any(glob_matches(x, files) for x in paths):
            dead.append(os.path.basename(path))
    if os.path.isdir(os.path.join(root, ".claude", "rules")):
        r.add(g, "rules paths", "warn" if dead else "ok",
              "match no files (never load): " + ", ".join(dead) if dead else "every scoped rule matches files",
              "fix the rule's `paths:`" if dead else None)

    bad = []
    try:
        from core.config_loader import load_rule_file, rule_problems
        for path in sorted(glob.glob(os.path.join(root, ".claude", "hookify.*.local.md")) +
                           glob.glob(os.path.join(root, ".claude", "hookify", "*.md"))):
            rule = load_rule_file(path)
            rel = os.path.relpath(path, root)
            if not rule:
                bad.append(f"{rel} (no valid frontmatter)")
                continue
            if rule.enabled:
                bad.extend(f"{rel} ({p})" for p in rule_problems(rule))
        n = len(glob.glob(os.path.join(root, ".claude", "hookify.*.local.md")) +
                glob.glob(os.path.join(root, ".claude", "hookify", "*.md")))
        if n:
            r.add(g, "hookify rules", "fail" if bad else "ok", "; ".join(bad) if bad else f"{n} rules parse",
                  f"{RUNBOOK} R7" if bad else None)
    except ImportError as e:
        r.add(g, "hookify rules", "skip", f"hookify engine not importable: {e}")

    cm = os.path.join(root, "CLAUDE.md")
    if os.path.exists(cm):
        n = len(open(cm, encoding="utf-8").read().splitlines())
        r.add(g, "CLAUDE.md size", "ok" if n <= CLAUDE_MD_BUDGET else "warn", f"{n} lines (budget {CLAUDE_MD_BUDGET})",
              None if n <= CLAUDE_MD_BUDGET else "/sdlc:knowledge-audit")

    idx = os.path.join(root, "knowledge", "index.md")
    if os.path.isdir(os.path.join(root, "knowledge")):
        if not os.path.exists(idx):
            r.add(g, "knowledge index", "warn", "knowledge/ has no index.md: tier-3 docs are invisible",
                  "sdlc:managing-knowledge")
        else:
            links = re.findall(r"\]\(([^)#\s]+)", open(idx, encoding="utf-8").read())
            broken = [l for l in links if not re.match(r"[a-z]+:", l) and
                      not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(idx), l)))]
            r.add(g, "knowledge index", "warn" if broken else "ok",
                  "broken links: " + ", ".join(broken) if broken else f"{len(links)} links resolve",
                  "fix or remove the links" if broken else None)

    states = sdlc_layout.features(root)
    if states:
        active, malformed = [], []
        for name, f in sorted(states.items()):
            text = open(os.path.join(root, f["state"]), encoding="utf-8").read()
            if not re.search(r"^Status:\s*\S", text, re.M) or not re.search(r"^Current:\s*Stage\s*\d", text, re.M):
                malformed.append(name)
            elif re.search(r"^Status:\s*active\b", text, re.M | re.I):
                active.append(name)
        r.add(g, "features", "warn" if malformed or len(active) > 1 else "ok",
              "; ".join(x for x in (f"{len(states)} features, active: {', '.join(active) or 'none'}",
                                    f"missing Status/Current: {', '.join(malformed)}" if malformed else "") if x),
              f"{RUNBOOK} R8/R9" if malformed or len(active) > 1 else None)
    fresh = os.path.join(root, ".sdlc", ".work", "verify-freshness.json")
    if os.path.exists(fresh):
        try:
            st = json.load(open(fresh, encoding="utf-8"))
            scopes = st.get("scopes") or {"": st}
            stale = [(n + ": " if n not in ("", "(root)") else "") + s.get("reason", "")
                     for n, s in scopes.items() if s.get("stale")]
            r.add(g, "verify freshness", "ok", f"{st.get('feature')}: " + ("stale: " + "; ".join(stale)
                                                                        if stale else "fresh"))
        except ValueError:
            r.add(g, "verify freshness", "warn", "state file is corrupt (the hook recovers on the next full run)",
                  f"delete .sdlc/.work/verify-freshness.json · {RUNBOOK} R4")
    error = os.path.join(root, ".sdlc", ".work", "verify-freshness.error")
    if os.path.exists(error):
        with open(error, encoding="utf-8", errors="replace") as f:
            r.add(g, "verify freshness hook", "warn", "its last run failed, so it didn't guard that turn: "
                  + f.read().strip()[:200], "report it with the file's contents; the next clean run clears it")


def to_markdown(report):
    icon = {"ok": "✅", "warn": "⚠️", "fail": "❌", "skip": "·"}
    lines = ["| | Check | Detail | Fix |", "|---|---|---|---|"]
    for c in report["checks"]:
        lines.append(f"| {icon[c['status']]} | {c['group']} · {c['check']} | {c['detail']} | {c['fix'] or ''} |")
    s = report["summary"]
    lines += ["", f"**{s['fail']} failing, {s['warn']} warnings, {s['ok']} ok.**"]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--format", choices=["json", "md"], default="json")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    r = Report()
    check_environment(r, root)
    check_plugin(r)
    check_repo(r, root)
    summary = {k: sum(1 for c in r.checks if c["status"] == k) for k in ("ok", "warn", "fail", "skip")}
    report = {"root": root, "checks": r.checks, "summary": summary}
    sys.stdout.reconfigure(encoding="utf-8")  # a cp1252 pipe (Windows) can't encode the status emoji
    print(to_markdown(report) if a.format == "md" else json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
