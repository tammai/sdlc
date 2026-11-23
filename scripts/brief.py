#!/usr/bin/env python3
"""sdlc brief: everything Define reads before the code, printed in one call, so reading takes one turn, not four.

Prints, each under a `===== <path> =====` line and cut at a line limit: the feature's paths (with a name), the
project's .sdlc/config.json, .sdlc/baseline.md, knowledge/index.md, <docs>/recurring-defects.md (and, near the end,
the plugin's own list, so the builder checks what Review checks), the constitution,
the PRD, README.md, the package manifest, the tracked files, a pointer to graphify-out/graph.json (only when the
repo has that code graph: Define runs `graphify query` alongside its reads), config's `rules` for the change file, plan and review
(only when set), the objects file (only when config's `objects` is on; a spec-backed repo gets a pointer to rspec's
domain.md instead) and the plugin's change template. A missing file is one
`(none)` line. When config's `deploy.target` names one of the plugin's platform references, it also
prints that reference's `## Define checks` and the file's path; a target that isn't a plain slug names no
file. The code the change touches isn't printed: the agent reads that itself, in the same turn. Run when
sizing a new request, so the router's reading and Define's are one turn.
Spec-backed work (spec 03 S2): `--criteria ID ...` (the slice's criteria), and the IDs NAME's change file cites,
print as `cited criteria`: each criterion's line from the spec, with its level and recorded test from the lock.
Usage: python3 brief.py [--root DIR] [NAME] [--criteria ID ...]. Read-only. Exit 0; 2 usage. Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLATFORMS = "skills/orchestrator/references/platforms"
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
import sdlc_layout  # noqa: E402  (where the feature's state and documents live)
sys.path.insert(0, HERE)
import spec_lock  # noqa: E402  (the criteria an rspec spec locked)

LIMIT = 200  # lines per file: a long README or PRD is cut, and the cut says so
MANIFESTS = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Gemfile",
             "composer.json")


def section(title, text, limit=LIMIT):
    lines = text.rstrip("\n").split("\n") if text else []
    out = [f"===== {title} ====="]
    if not lines or lines == [""]:
        out.append("(none)")
    else:
        out += lines[:limit]
        if len(lines) > limit:
            out.append(f"... ({len(lines) - limit} more lines: read the file for the rest)")
    return "\n".join(out)


def read(root, rel):
    """A committed repo file's text, "" when missing or a link out of the repo or into .git (never read through it:
    the brief reaches the agent's context, and a FIFO would hang it)."""
    import sdlc_scopes  # noqa: PLC0415
    try:
        sdlc_scopes._inside(root, rel)
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def tracked(root):
    try:
        p = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return p.stdout if p.returncode == 0 else ""


def config_text(root):
    """.sdlc/config.json's text, "{}" when missing or a link out of the repo (never read through it)."""
    import sdlc_scopes  # noqa: PLC0415
    return sdlc_scopes.read_repo_text(root, ".sdlc/config.json") or "{}"


def platform(root):
    """The platform reference's Define checks for config's deploy target, as a section; None when there are none.
    Repo config is untrusted: only a plain slug may name a file in the plugin."""
    try:
        cfg = json.loads(config_text(root))
    except ValueError:
        return None
    deploy = cfg.get("deploy") if isinstance(cfg, dict) else None
    target = deploy.get("target") if isinstance(deploy, dict) else None
    if not isinstance(target, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", target):
        return None
    rel = f"{PLATFORMS}/{target}.md"
    m = re.search(r"^## Define checks\n(.*?)(?=^## |\Z)", read(os.path.dirname(HERE), rel), re.M | re.S)
    if not m:
        return None
    return section(f"platform: {target} (the rest: ${{CLAUDE_PLUGIN_ROOT}}/{rel})", m.group(1).strip())


RULE_DOCS = ("change", "plan", "review")  # the documents config's `rules` may shape


def rules(root):
    """Config's `rules` (#75) as a section: each document's rules, for whoever writes or reviews it; None when there
    are none. Instructions to the agent only, read like CLAUDE.md: nothing runs without asking because of them."""
    try:
        cfg = json.loads(config_text(root))
    except ValueError:
        return None
    given = cfg.get("rules") if isinstance(cfg, dict) else None
    if not isinstance(given, dict):
        return None
    lines = []
    for doc in RULE_DOCS:
        items = given.get(doc)
        if isinstance(items, list) and any(isinstance(x, str) and x.strip() for x in items):
            lines += [f"{doc}:"] + [f"- {x.strip()}" for x in items if isinstance(x, str) and x.strip()]
    return section("project rules (.sdlc/config.json `rules`)", "\n".join(lines)) if lines else None


GRAPH = "graphify-out/graph.json"  # a code graph the graphify tool built, when the user runs it; sdlc never builds one


def graph(root):
    """A pointer to the repo's graphify graph, when it has one: Define queries it for the files a request touches,
    alongside its reads. None when there is none, so a repo without graphify sees nothing."""
    path = os.path.join(root, GRAPH)
    if not os.path.isfile(path):
        return None
    built = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(path)))
    if shutil.which("graphify"):
        how = (f'In the same turn as the code reads, run `graphify query "<the request in a few words>" --budget 1500` '
               "and read the files it names that the request touches.")
    else:
        how = "The graphify command isn't installed here: graphify-out/GRAPH_REPORT.md summarizes the graph instead."
    return section(f"graphify graph: {GRAPH} (built {built})",
                   how + " The graph can be older than the code: where they disagree, the code wins.")


def living_spec(root):
    """The living spec's capabilities (#73), when config turns it on: each file's name and purpose, so Define reuses
    a name instead of starting a near-duplicate. None when it's off."""
    import capabilities  # only here: it loads verify.py
    try:
        base = capabilities.folder(root)
    except ValueError as e:
        return section("living spec", f"living_spec: {e}")
    if base is None:
        return None
    try:
        names = sorted(n[:-3] for n in os.listdir(os.path.join(root, base)) if n.endswith(".md"))
    except OSError:
        names = []
    lines = []
    for n in names:
        purpose = capabilities.parse_file(read(root, f"{base}/{n}.md"))[0]
        lines.append(f"{n}: {(purpose.splitlines() or [''])[0]}")
    return section(f"living spec: {base}/ (write ## Capabilities: "
                   "${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/living-spec.md)",
                   "\n".join(lines) or "no capabilities yet")


def domain(root):
    """The domain model (spec 13): the objects file when config turns it on, so Define uses its names, states and
    rules; in a spec-backed repo, a pointer to rspec's `<spec>/domain.md` instead (read-only, D5). None when off."""
    import objects  # only here: it loads spec_lock and, for UI checks, doctor
    try:
        rel = objects.path(root)
    except ValueError:  # Define still sees an objects section, so its gate runs the check, which says why
        return section("objects: invalid (objects.py check says why)", "The objects file can't be read as config "
                       "names it; fix `objects` in .sdlc/config.json.")
    if rel is not None:
        text = read(root, rel)
        if not text:
            text = "(empty)" if os.path.isfile(os.path.join(root, rel)) else f"(not readable: {rel}; objects.py check says why)"
        return section(f"objects: {rel}", text)
    if objects.setting(root) and spec_lock.spec_backed_repo(root):
        found = objects.rspec_domain(root)
        if found:
            return "\n\n".join(section(f"domain (rspec, read-only): {p}", "The spec's roles, enumerations, limits and "
                                       "identifiers: use its names in ACs and copy; sdlc never writes it.")
                               for p in found)
    return None


def criteria_text(root, ids):
    """One line per criterion ID: its text from the spec, its level and recorded test; or why it can't be shown."""
    locked, problems = spec_lock.load(root)
    out = list(problems)
    for cid in dict.fromkeys(ids):
        entry = locked.get(cid)
        if entry is None:
            out.append(f"{cid}: not in the lock")
            continue
        line = spec_lock.criterion_line(root, entry)
        out.append(f"{line or cid + ': (its line is not in ' + entry.get('file', '?') + ')'}"
                   f"   [level {entry.get('level')}; test: {entry.get('test') or 'none recorded'}]")
    return "\n".join(out)


def brief(root, name=None, criteria=()):
    docs = sdlc_layout.docs_dir(root) or sdlc_layout.SDLC
    parts = []
    ids = list(criteria)
    if name:
        parts.append(section("paths", json.dumps(sdlc_layout.paths(root, name), indent=1)))
        change = read(root, sdlc_layout.paths(root, name)["change"])
        if spec_lock.spec_backed_repo(root):  # a standalone repo's brief stays as in 3.4.0
            ids += [cid for found in spec_lock.cited(spec_lock.entries(change)).values() for cid in found]
    if ids:
        parts.append(section("cited criteria", criteria_text(root, ids)))
    for rel in (".sdlc/config.json", ".sdlc/baseline.md", "knowledge/index.md", f"{docs}/recurring-defects.md",
                f"{docs}/constitution.md", sdlc_layout.prd(root), "README.md"):
        parts.append(section(rel, read(root, rel)))
    checks = platform(root)
    if checks:
        parts.append(checks)
    pointer = graph(root)
    if pointer:
        parts.append(pointer)
    manifest = next((m for m in MANIFESTS if os.path.isfile(os.path.join(root, m))), None)
    parts.append(section(manifest or "package manifest", read(root, manifest) if manifest else "", 80))
    parts.append(section("git ls-files", tracked(root), 300))
    parts.append(section("plugin recurring defects", read(os.path.dirname(HERE), os.path.join(
        "skills", "orchestrator", "references", "recurring-defects.md"))))
    given = rules(root)
    if given:
        parts.append(given)
    import sdlc_scopes  # noqa: PLC0415
    done, problem = sdlc_scopes.done_config(root)
    if problem:
        parts.append(section("definition of done (.sdlc/config.json `done`)",
                             f"isn't valid, so Ship refuses until it is fixed: {problem}"))
    if done:
        parts.append(section("definition of done (.sdlc/config.json `done`): copy into the change file's "
                             "## Definition of Done; tick each with its evidence before Ship",
                             "\n".join(f"- [ ] {x}" for x in done)))
    living = living_spec(root)
    if living:
        parts.append(living)
    model = domain(root)
    if model:
        parts.append(model)
    parts.append(section("change template", read(os.path.dirname(HERE), os.path.join("templates", "change-template.md"))))
    return "\n\n".join(parts) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--criteria", nargs="+", default=[], metavar="ID", help="criterion IDs to print from the lock")
    a = ap.parse_intermixed_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(brief(os.path.abspath(a.root), a.name, a.criteria))
    return 0


if __name__ == "__main__":
    sys.exit(main())
