#!/usr/bin/env python3
"""The domain model (docs/specs/13-domain-model.md): a project's objects, their names, states and rules, in one file.

Opt-in: `"objects": true` in .sdlc/config.json (the file is <docs>/objects.md), or a path to the file inside the repo.
A spec-backed repo (an rspec criteria lock) has rspec's own `<spec>/domain.md`, so the switch does nothing there.

The file (templates/objects-template.md):
  ## Objects     one `### <Name>` per object: a line saying what it is, then `- UI name:`, `- Code:`, `- Belongs to:`,
                 `- Has:`, `- States:`, `- Actions:`, `- Shown as:` lines
  ## Rules       `- **DR-001** <rule>`: stable ids, never renumbered or reused
  ## Avoid       `- Bill, Receipt → Invoice`: names that must not appear in acceptance criteria or user-visible text
Code spans hold state names only, declared on a `States:` line, so the vendored `contracts.py --domain` reads the file
right as it is (it takes every code span as a state).

Usage: objects.py [--root DIR] check [FEATURE]. Prints one JSON object, {"ok", "problems": [...]} (scripts/problems.py
shape); exit 1 on an error, 0 with warnings only. With FEATURE, an Avoid word in its `## Acceptance criteria` is a
warning on M and an error on L. Does nothing when the switch is off. Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
sys.path.insert(0, HERE)
import sdlc_layout  # noqa: E402
import problems as P  # noqa: E402
import spec_lock  # noqa: E402

LIMIT = 200  # brief.py's cut: a longer file isn't read whole in Define
SPAN = re.compile(r"`([^`\n]+)`")  # one line, as contracts v1 reads them; a stray backtick never pairs across lines
RULE_ID = re.compile(r"^\s*[-*]\s+\*\*(DR-\d{3})\*\*\s+\S")
FIELD = re.compile(r"^\s*[-*]\s+([A-Za-z][A-Za-z ]*?):\s*(.*)$")


def setting(root):
    import sdlc_scopes  # its reader refuses a config linked out of the repo or into .git
    try:
        cfg = sdlc_scopes.read_repo_json(root, ".sdlc/config.json")
    except (OSError, ValueError):
        return None
    return cfg.get("objects") if isinstance(cfg, dict) else None


def _parts(rel):
    """A path's folder names as Windows and macOS compare them (case, trailing dots and spaces dropped)."""
    return [p.rstrip(". ").lower() for p in rel.replace("\\", "/").split("/")]


def path(root):
    """The objects file's repo-relative path, or None when the switch is off or the repo is spec-backed. Repo config
    is untrusted, so the path is judged by where it leads, links followed, on both branches: inside the repo and never
    in .git; a path config names also never in .claude or .sdlc (true keeps the old layout's .sdlc/objects.md).
    Anything else is a ValueError, and the file is never read."""
    value = setting(root)
    if value is None or value is False or spec_lock.spec_backed_repo(root):
        return None
    return target(root, value)


def target(root, value):
    """The repo-relative path config's `objects` value names (True: the default place), judged by the rules `path()`
    describes, whether or not the switch is on: setup asks it before it turns the switch on. A ValueError says why
    it can't be the objects file."""
    barred = {".git", ".claude", ".sdlc"}
    if value is True:
        try:
            rel = f"{sdlc_layout.paths(root)['docs_dir']}/objects.md"
        except ValueError as e:
            raise ValueError(str(e)) from None
        own = ".sdlc/objects.md"  # the old layout's own place, allowed only as itself, never through a link
    elif isinstance(value, str):
        try:
            rel = sdlc_layout.validate_docs_dir(value)
        except ValueError:
            raise ValueError(f"{value!r} isn't a path inside the repo: give one relative to its root, or true") from None
        own = None
    else:
        raise ValueError(f"must be true or a path to a .md file, not {value!r}")
    full = spec_lock.inside(root, rel)
    if full is None:
        raise ValueError(f"{rel!r} leads outside the repo (a link?)")
    resolved = os.path.relpath(full, os.path.realpath(root)).replace("\\", "/")
    for shown, how in ((rel, "is"), (resolved, "leads to")):  # one rule set, on the path written and where it leads
        why = _refused(shown, barred, own is not None and _parts(rel) == _parts(own) == _parts(shown))
        if why:
            raise ValueError(f"{rel!r} {how} {why}" + ("; with the old layout, set objects to true"
                                                        if _parts(rel)[:1] == [".sdlc"] and own is None else ""))
    return rel


def _odd(text):
    """Whether a name has a control or format character, which could fake a brief section or hide a name."""
    return any(unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") for c in text)


def _refused(rel, barred, legacy):
    """Why a repo-relative path can't be the objects file, or None: a control or format character, not a .md file,
    or a part in .git, .claude or .sdlc (bar the old layout's own .sdlc/objects.md, `legacy`)."""
    if _odd(rel):
        return "a name with a control or format character"
    if not rel.lower().endswith(".md"):
        return "a file that isn't .md"
    import sdlc_scopes  # its one dot-folder rule: case, trailing dots and spaces, NTFS streams, 8.3 names (GIT~1)
    hit = {name for name in barred if any(sdlc_scopes.dot_segment(p, name) for p in rel.replace("\\", "/").split("/"))}
    if hit and not legacy:
        return f"a file in {', '.join(sorted(hit))}, where sdlc's own files live"
    return None


def rspec_domain(root):
    """rspec's domain file for each spec this spec-backed repo locks (`<spec>/domain.md`), when it exists."""
    out = []
    for rel in spec_lock.lock_paths(root):
        try:
            with open(spec_lock.inside(root, rel) or "", encoding="utf-8") as f:
                spec = json.load(f).get("spec")
        except (OSError, ValueError, AttributeError):
            continue
        found = f"{spec}/domain.md" if isinstance(spec, str) and not _odd(spec) else None
        if found and spec_lock.inside(root, found) and os.path.isfile(os.path.join(root, found)):
            out.append(found)
    return sorted(set(out))


def sections(text):
    """{`## heading`: [lines]}, every section of that heading joined in file order."""
    out, current = {}, None
    for line in text.split("\n"):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            current = out.setdefault(m.group(1).strip().lower(), [])
        elif current is not None:
            current.append(line)
    return out


def parse(text):
    """(objects [(name, {field: value})], rule lines, avoid lines) of an objects file."""
    parts = sections(text)
    objects, current = [], None
    for line in parts.get("objects", []):
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            current = (m.group(1).strip(), {})
            objects.append(current)
            continue
        f = FIELD.match(line)
        if current and f:
            current[1][f.group(1).strip().lower()] = f.group(2).strip()
    rules = [l for l in parts.get("rules", []) if re.match(r"^\s*[-*]\s+", l)]
    avoid = [l for l in parts.get("avoid", []) if re.match(r"^\s*[-*]\s+", l)]
    return objects, rules, avoid


ARROW = re.compile(r"\s*(?:→|->)\s*")


def avoided(avoid_lines):
    """({avoided word: the name to use}, [lines that aren't `- Bill, Receipt → Invoice`]); `->` works as the arrow."""
    out, bad = {}, []
    for line in avoid_lines:
        parts = ARROW.split(re.sub(r"^\s*[-*]\s+", "", line).strip(), maxsplit=1)
        words = [w.strip() for w in parts[0].split(",") if w.strip()]
        if len(parts) != 2 or not parts[1].strip() or not words:
            bad.append(line.strip())
            continue
        for w in words:
            out[w] = parts[1].strip()
    return out, bad


def ui_files(root):
    """Whether the repo has files config's `areas.ui` (defaults included) matches; a malformed `areas` or `ui`
    (not an object, not a list of strings) counts as none."""
    import doctor  # only here: doctor imports this module too
    import scaffold
    import sdlc_scopes
    try:
        cfg = scaffold.effective_config(sdlc_scopes.read_repo_json(root, ".sdlc/config.json"))
    except (OSError, ValueError, TypeError, AttributeError):
        return False
    areas = cfg.get("areas") if isinstance(cfg, dict) else None
    ui = areas.get("ui") if isinstance(areas, dict) else None
    if not isinstance(ui, list):
        return False
    files = doctor.repo_files(root)
    return any(isinstance(x, str) and doctor.glob_matches(x, files) for x in ui)


def file_problems(root, rel, text):
    objects, rules, avoid = parse(text)
    out = []
    declared = set()
    for line in text.split("\n"):
        if re.match(r"^\s*[-*]\s+States:", line):
            declared.update(SPAN.findall(line))
    for span in dict.fromkeys(SPAN.findall(text)):
        if span not in declared:
            out.append(P.problem("objects_state_undeclared", f"{rel}: `{span}` is in a code span but no `States:` line "
                                 "declares it (code spans hold state names only)", target=span,
                                 fix=f"declare it on its object's States line, or write {span} as plain text"))
    names = [n for n, _ in objects]
    for n in sorted({n for n in names if names.count(n) > 1}):
        out.append(P.problem("objects_duplicate", f"{rel}: the object {n} is listed twice", target=n))
    words, bad = avoided(avoid)
    for line in bad:
        out.append(P.problem("objects_avoid_line", f"{rel}: an Avoid line without `→ <name to use>`: {line[:80]}",
                             fix="write it as - Bill, Receipt → Invoice"))
    lowered = {w.lower() for w in words}
    for n in sorted({n for n in names if n.lower() in lowered}):
        out.append(P.problem("objects_avoided_name", f"{rel}: {n} is an object and also a name to avoid", target=n))
    ids = []
    for line in rules:
        m = RULE_ID.match(line)
        if not m:
            out.append(P.problem("objects_rule_id", f"{rel}: a rule without a `**DR-nnn**` id: {line.strip()[:80]}",
                                 fix="start it with the next unused id, e.g. - **DR-002** …"))
        else:
            ids.append(m.group(1))
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        out.append(P.problem("objects_rule_id", f"{rel}: {i} is used twice (ids are never reused)", target=i))
    if len(text.rstrip("\n").split("\n")) > LIMIT:
        out.append(P.problem("objects_too_long", f"{rel} is over {LIMIT} lines: Define reads only the first {LIMIT}",
                             target=rel, severity="warning"))
    if objects and ui_files(root):
        for n, fields in objects:
            missing = [k for k in ("ui name", "shown as") if not fields.get(k)]
            if missing:
                out.append(P.problem("objects_ui_fields", f"{rel}: {n} has no {' or '.join(missing).replace('ui', 'UI')} "
                                     "line, and the repo has UI files", target=n, severity="warning"))
    return out


def _read_text(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")
    except (OSError, UnicodeDecodeError):
        return None


def feature_problems(root, feature, text):
    """An Avoid word in the feature's ACs: a warning on M, an error on L or when the track can't be read (fail
    closed). A feature the check can't find, in either layout, or whose change file it can't read, is an error."""
    where = sdlc_layout.features(root).get(feature)
    change = _read_text(root, where["change"]) if where else None
    if change is None:
        return [P.problem("objects_feature_missing", f"{feature}: no change file to check (is the name right, and is "
                          "the state file written? run the check after `state.py new`)", target=feature)]
    state = _read_text(root, where["state"]) or ""
    m = re.search(r"^## Acceptance criteria\s*$(.*?)(?=^## |\Z)", change, re.M | re.S)
    criteria = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S) if m else ""
    track = (re.search(r"^Track:[ \t]*([A-Za-z]+)", state, re.M) or [None, ""])[1]
    out = []
    for word, use in avoided(parse(text)[2])[0].items():
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", criteria, re.I):
            out.append(P.problem("objects_avoid_word", f"{feature}: the acceptance criteria say {word!r}; the objects "
                                 f"file says to use {use!r}", target=word, fix=f"write {use} instead",
                                 severity="warning" if track == "M" else "error"))
    return out


def check(root, feature=None):
    try:
        rel = path(root)
    except ValueError as e:
        return [P.problem("objects_path_invalid", f"objects: {e}", target=".sdlc/config.json")]
    if rel is None:
        return []
    return check_file(root, rel, feature)


def check_file(root, rel, feature=None):
    """The file rules on the objects file at `rel` (a path `path()` gave), whether or not the switch is on yet:
    setup checks a draft before it turns the switch on."""
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            text = f.read().replace("\r\n", "\n")
    except FileNotFoundError:
        return [P.problem("objects_missing", f"there's no {rel}", target=rel,
                          fix=f"write {rel} from the plugin's templates/objects-template.md, or turn the switch off")]
    except (OSError, UnicodeDecodeError) as e:
        return [P.problem("objects_unreadable", f"{rel} can't be read as UTF-8 text ({type(e).__name__})", target=rel)]
    out = file_problems(root, rel, text)
    if feature:
        out += feature_problems(root, feature, text)
    return out


def unused_code_names(root):
    """Objects whose `Code:` name (the line's first word) is in no tracked file but the objects file: doctor's
    stale-object warning. [] when the switch is off or the file can't be read."""
    try:
        rel = path(root)
        with open(os.path.join(root, rel or ""), encoding="utf-8") as f:
            objects = parse(f.read().replace("\r\n", "\n"))[0]
    except (ValueError, OSError, UnicodeDecodeError, TypeError):
        return []
    names = {(fields.get("code") or "").split(" ")[0] for _, fields in objects} - {""}
    if not names:
        return []
    # git prints the matched words themselves (-o -h), so no path is parsed and no file is opened (a link is git's
    # blob, never followed); git missing, slow or not a work tree is no answer, never "unused"
    # the file is left out however config spells it (case) and wherever a link leads (its target)
    real = os.path.relpath(os.path.realpath(os.path.join(root, rel)), os.path.realpath(root)).replace("\\", "/")
    leave_out = [f":(exclude,literal,icase){p}" for p in dict.fromkeys((rel, real))]
    try:
        p = subprocess.run(["git", "-C", root, "grep", "-I", "-o", "-h", "-w", "-F",
                            *sum((["-e", n] for n in sorted(names)), []), "--", ".", *leave_out],
                           capture_output=True, encoding="utf-8", errors="replace", timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if p.returncode not in (0, 1):
        return []
    return sorted(names - set(p.stdout.split()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("action", choices=["check"])
    ap.add_argument("feature", nargs="?")
    a = ap.parse_args(argv)
    found = check(os.path.abspath(a.root), a.feature)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"ok": not found, "problems": [P.as_dict(p) for p in found]}, ensure_ascii=False))
    return 1 if any(p.severity == "error" for p in found) else 0


if __name__ == "__main__":
    sys.exit(main())
