#!/usr/bin/env python3
"""The living spec (#73): what the system does now, one file per capability, grown from each change's ACs at Ship.

Opt-in: `"living_spec": true` in .sdlc/config.json (or a folder path instead of true). Files live in
<docs>/capabilities/<name>.md (the legacy layout: .sdlc/capabilities/). A spec-backed repo (an rspec criteria lock)
has its spec already, so this does nothing there.

A change says what it does to them in its `## Capabilities` section, one line each:
  - add <name>: AC-001 AC-002            each AC becomes a new requirement (R-nnn) of <name>
  - add <name>: AC-001 — <purpose>       a capability that doesn't exist yet needs its purpose, after ` — `
  - replace <name> R-003: AC-004         R-003's text and test become AC-004's; it keeps its id
  - remove <name> R-005: <why>           R-005 is dropped
  - retire <name>: <why>                 the capability's file is deleted (needed when removals would empty it)
  - none: <why>                          no behaviour a capability describes changed
M and L need the section (a `none:` line says so on purpose); S may leave it out. Names are kebab-case.

A capability file:
  # <name>
  <purpose>
  ## Requirements
  ### R-001
  <the AC's text>
  - Test: <file › name>
  - From: <feature> AC-001

Usage: capabilities.py [--root DIR] check|merge FEATURE   (merge writes; check only plans). Prints one JSON object:
{"ok", "files": [paths written or deleted], "problems": [...] (scripts/problems.py shape)}; exit 1 on a problem.
ship.py runs check before anything moves and merge after verify, so the files go into Ship's commit.
Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
sys.path.insert(0, HERE)
import sdlc_layout  # noqa: E402
import problems as P  # noqa: E402
import spec_lock  # noqa: E402
import verify  # noqa: E402  (the change file's sections, ACs and test rows)

NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
LINE = re.compile(rf"^\s*[-*]\s+(?:(?P<op>add|replace|remove|retire)\s+(?P<name>{NAME})(?:\s+(?P<req>R-\d{{3,}}))?"
                  rf"\s*:\s*(?P<rest>.*)|none\s*:\s*(?P<why>.*))$")
REQ = re.compile(r"^### (R-\d{3,})\s*$", re.M)
LAST = re.compile(r"<!-- last id: R-(\d{3,}) -->\n?")  # a removed requirement's id is never given again


def config(root):
    try:
        with open(os.path.join(root, ".sdlc", "config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return None
    return cfg.get("living_spec") if isinstance(cfg, dict) else None


def folder(root):
    """The capabilities folder, or None when the living spec is off (or the repo is spec-backed)."""
    value = config(root)
    if not value or spec_lock.spec_backed_repo(root):
        return None
    if isinstance(value, str):
        return sdlc_layout.validate_docs_dir(value)  # in-repo, relative: a bad value is a ValueError
    return f"{sdlc_layout.paths(root)['docs_dir']}/capabilities"


def parse_file(text):
    """(purpose, {R-id: block}, the highest id it ever gave) of a capability file, the blocks in file order."""
    head, _, body = text.replace("\r\n", "\n").partition("\n## Requirements\n")
    last = LAST.search(body)
    body = LAST.sub("", body)
    reqs, parts = {}, REQ.split(body)[1:]
    for rid, block in zip(parts[0::2], parts[1::2]):
        reqs[rid] = block.strip("\n")
    top = max([int(r[2:]) for r in reqs] + [int(last.group(1)) if last else 0])
    return "\n".join(head.strip("\n").split("\n")[1:]).strip(), reqs, top


def render(name, purpose, reqs, last):
    out = [f"# {name}", "", purpose, "", "## Requirements", "", f"<!-- last id: R-{last:03d} -->", ""]
    for rid, block in reqs.items():
        out += [f"### {rid}", block, ""]
    return "\n".join(out).rstrip("\n") + "\n"


def requirement(feature, ac, text, row):
    body = re.sub(r"^\s*[-*]\s+\**AC-\d{3}\**\s*", "", text.strip()).strip()
    test = (row or {}).get("test", "").strip("`").strip() or "none named"
    return f"{body}\n- Test: {test}\n- From: {feature} {ac}"


def plan(root, feature):
    """({path: new text or None to delete}, problems): what merge would write, or why it can't."""
    base = folder(root)
    if base is None:
        return {}, []
    paths = sdlc_layout.paths(root, feature)
    change = verify.read(os.path.join(root, paths["change"])) or ""
    state = verify.read(os.path.join(root, paths["state"])) or ""
    section = verify.section(change, "Capabilities")
    section = None if section is None else re.sub(r"<!--.*?-->", "", section, flags=re.S)
    track = (re.search(r"^Track:[ \t]*([A-Za-z]+)", state, re.M) or [None, ""])[1]
    if section is None:
        if track in ("M", "L"):
            return {}, [P.problem("capabilities_missing", f"{paths['change']}: the living spec is on, but there's no "
                                  "`## Capabilities` section saying what this change does to it", target=paths["change"],
                                  fix="add `## Capabilities` with `- add <name>: AC-001`, or `- none: <why>`")]
        return {}, []
    entries = verify.ac_entries(change)
    rows = {r["ac"]: r for r in verify.test_rows(verify.acceptance_map(change) or [])}
    files, problems, loaded = {}, [], {}

    def load(name):
        if name not in loaded:
            rel = f"{base}/{name}.md"
            text = verify.read(os.path.join(root, rel))
            loaded[name] = [rel, *(parse_file(text) if text is not None else (None, None, 0))]
        return loaded[name]

    for line in section.splitlines():
        if not line.strip():
            continue
        m = LINE.match(line)
        if not m:
            problems.append(P.problem("capability_line_invalid", f"## Capabilities: can't read `{line.strip()}`",
                                      fix="use add, replace, remove, retire or none (capabilities.py's docstring)"))
            continue
        if m.group("why") is not None:
            continue
        op, name, rid, rest = m.group("op"), m.group("name"), m.group("req"), m.group("rest").strip()
        rel, purpose, reqs, _ = load(name)
        if reqs == "retired":
            problems.append(P.problem("capability_retired", f"{op} {name}: this change retires it", target=name))
        elif op == "add":
            acs, _, new_purpose = rest.partition(" — ")
            if reqs is None:
                if not new_purpose.strip():
                    problems.append(P.problem("capability_needs_purpose", f"{name} is a new capability: its add line "
                                              "needs its purpose after ` — `", target=name,
                                              fix=f"- add {name}: {acs.strip()} — <what this capability is for>"))
                    continue
                purpose, reqs = new_purpose.strip(), {}
                loaded[name][1:3] = [purpose, reqs]
            for ac in verify.AC_ID.findall(acs) or [None]:
                if ac not in entries:
                    problems.append(P.problem("capability_ac_unknown", f"add {name}: {ac or 'no AC named'} isn't an "
                                              "AC of this change", target=name))
                    continue
                loaded[name][3] += 1
                reqs[f"R-{loaded[name][3]:03d}"] = requirement(feature, ac, entries[ac], rows.get(ac))
        elif reqs is None:
            problems.append(P.problem("capability_unknown", f"{op} {name}: there's no {rel}", target=name,
                                      fix=f"`add {name}: <ACs> — <purpose>` creates it"))
        elif op == "retire":
            loaded[name][2] = "retired"
        elif rid is None or rid not in reqs:
            problems.append(P.problem("requirement_unknown", f"{op} {name} {rid or '(no R-nnn)'}: not in {rel}",
                                      target=f"{name} {rid}"))
        elif op == "replace":
            ac = (verify.AC_ID.findall(rest) or [None])[0]
            if ac not in entries:
                problems.append(P.problem("capability_ac_unknown", f"replace {name} {rid}: {ac or 'no AC named'} "
                                          "isn't an AC of this change", target=f"{name} {rid}"))
            else:
                reqs[rid] = requirement(feature, ac, entries[ac], rows.get(ac))
        else:  # remove
            del reqs[rid]
    for name, (rel, purpose, reqs, last) in loaded.items():
        if reqs == "retired":
            files[rel] = None
        elif reqs is not None and not reqs:
            problems.append(P.problem("capability_emptied", f"{name}: this change removes its last requirement; "
                                      "deleting the file needs a `retire` line", target=name,
                                      fix=f"- retire {name}: <why>"))
        elif reqs is not None:
            files[rel] = render(name, purpose, reqs, last)
    return ({} if problems else files), problems


def merge(root, feature):
    files, problems = plan(root, feature)
    if problems:
        return [], problems
    for rel, text in files.items():
        path = os.path.join(root, rel)
        if text is None:
            if os.path.exists(path):
                os.remove(path)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return sorted(files), []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("action", choices=["check", "merge"])
    ap.add_argument("feature")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    try:
        files, problems = (merge if a.action == "merge" else plan)(root, a.feature)
    except ValueError as e:
        files, problems = [], [P.problem("living_spec_folder_invalid", f"living_spec: {e}")]
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"ok": not problems, "files": sorted(files),
                      "problems": [P.as_dict(p) for p in problems]}, ensure_ascii=False))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
