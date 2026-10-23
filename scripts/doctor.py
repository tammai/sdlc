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

def check_environment(r):
    g = "environment"
    v = sys.version_info
    r.add(g, "python", "ok" if v >= (3, 9) else "fail", f"{v.major}.{v.minor}.{v.micro}",
          None if v >= (3, 9) else "install Python 3.9+ (hooks and scripts need it)")
    # hooks.json starts the hooks with a bare `python3`; a missing or Microsoft Store stub python3 makes every
    # hookify guardrail fail open (Claude Code treats any exit other than 2 as non-blocking)
    code, out = run(["python3", "-c", "import sys; print(sys.version_info[0])"])
    ok = code == 0 and out == "3"
    r.add(g, "python3", "ok" if ok else "fail",
          shutil.which("python3") if ok else f"`python3` is missing or does not run (exit {code}); hooks start with it",
          None if ok else "put a real python3 on PATH (on Windows, copy python.exe to python3.exe)")
    for tool, needed_for, status in (("git", "worktrees, freshness hook, commits", "fail"),
                                     ("gh", "/sdlc:code-review and PR commands", "warn"),
                                     ("jq", "the /sdlc:ralph-loop stop hook (it silently stops looping without it)", "warn")):
        found = shutil.which(tool)
        r.add(g, tool, "ok" if found else status, found or f"not found (needed for {needed_for})",
              None if found else f"install {tool}")
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
        cfg = scaffold.effective_config(p.config)
        if cfg.get("project", {}).get("kind") == "brownfield":
            b = os.path.join(root, cfg.get("baseline", ".sdlc/baseline.md"))
            r.add(g, "baseline", "ok" if os.path.exists(b) else "warn",
                  "present" if os.path.exists(b) else "brownfield repo without a baseline: old failures will fail Stage 5",
                  None if os.path.exists(b) else f"rerun the baseline step of /sdlc:setup · {RUNBOOK} R16")

    if status["setup"] == "complete" and sdlc_layout.docs_dir(root) is None:
        r.add(g, "layout", "warn", "sdlc documents are still in .sdlc/ (the layout before 1.7.0)",
              "run /sdlc:upgrade to move them to docs/sdlc or a location you choose")

    gi = os.path.join(root, ".gitignore")
    ignored = os.path.exists(gi) and ".sdlc/.work/" in open(gi, encoding="utf-8").read().split()
    if os.path.isdir(os.path.join(root, ".sdlc")):
        r.add(g, ".gitignore", "ok" if ignored else "warn",
              ".sdlc/.work/ ignored" if ignored else ".sdlc/.work/ is not git-ignored (scratch files may get committed)",
              None if ignored else "add `.sdlc/.work/` to .gitignore")

    files = repo_files(root)
    if status["setup"] == "complete":
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
    check_environment(r)
    check_plugin(r)
    check_repo(r, root)
    summary = {k: sum(1 for c in r.checks if c["status"] == k) for k in ("ok", "warn", "fail", "skip")}
    report = {"root": root, "checks": r.checks, "summary": summary}
    sys.stdout.reconfigure(encoding="utf-8")  # a cp1252 pipe (Windows) can't encode the status emoji
    print(to_markdown(report) if a.format == "md" else json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
