#!/usr/bin/env python3
"""sdlc guarded changes (ADR 0032, #92 part 3): with config `guards.dependencies` or `guards.lint_config` on, the
items a feature adds since its Base that the user must allow before verify passes:
  - a dependency name new in a known manifest (a version bump isn't one);
  - a changed dependency source: a requirements option line (`--index-url`, `-e`), package.json's `overrides`,
    `resolutions` and `pnpm.overrides`, go.mod's `replace`, Cargo's `[patch.*]` and `[replace]`, or any change to
    `.npmrc`, `.yarnrc`, `.yarnrc.yml`, `pip.conf` or `pip.ini`;
  - any change to a known lint or type config file, or to its section of pyproject.toml, setup.cfg or tox.ini;
  - a suppression comment whose count in a source file grew (a removed or moved one is free).
The file names come from this list, never from the repo's config. An item's id carries its content, so a later change
asks again.

As a hook it only records the user's allow, in .sdlc/.work/guarded.json, and prints nothing:
  - PostToolUse on AskUserQuestion: the answer `Allow` (a trailing `(Recommended)` aside) to a question headed
    `Allow change`, recorded by user_answer.py, allows each item the last verify listed whose label the question
    names;
  - UserPromptSubmit: a prompt that is exactly `allow` allows every item the last verify listed for the one feature
    waiting (the active one, when an abandoned feature's items wait too).
Any error: nothing recorded.
"""
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys

import sdlc_scopes  # sibling module: the guards honoured, guarded reads and writes

HEADER = "Allow change"  # the question tool caps a header at 12 characters
EXCLUDING = re.compile(r"\b(?:except|excluding|but not|other than|apart from|without)\b", re.I)
STORE = os.path.join(".sdlc", ".work", "guarded.json")
TYPED = re.compile(r"allow[.!]?", re.I)

MANIFESTS = ("package.json", "composer.json", "pyproject.toml", "cargo.toml", "pubspec.yaml", "go.mod", "gemfile")
SOURCE_FILES = (".npmrc", ".yarnrc", ".yarnrc.yml", "pip.conf", "pip.ini")  # where packages come from, whole
LINT_FILES = ("tsconfig*.json", "jsconfig.json", ".eslintrc", ".eslintrc.*", "eslint.config.*", "biome.json",
              "biome.jsonc", "ruff.toml", ".ruff.toml", "mypy.ini", ".mypy.ini", ".flake8", ".pylintrc", "pylintrc",
              "pyrightconfig.json", ".golangci.yml", ".golangci.yaml", ".golangci.toml", ".golangci.json",
              "analysis_options.yaml", ".rubocop.yml", "phpstan.neon", "phpstan.neon.dist", "psalm.xml",
              ".swiftlint.yml", "detekt.yml", ".stylelintrc", ".stylelintrc.*", "stylelint.config.*")
LINT_SECTIONS = {"pyproject.toml": r"tool\.(ruff|mypy|pyright|pylint|flake8|basedpyright)\b",
                 "setup.cfg": r"(flake8|mypy|pylint)\b", "tox.ini": r"(flake8|mypy|pylint)\b"}
SOURCE = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".py", ".pyi", ".go", ".rs",
          ".java", ".kt", ".kts", ".rb", ".php", ".cs", ".swift", ".dart")
SUPPRESSIONS = (("@ts-ignore", r"@ts-ignore"), ("@ts-nocheck", r"@ts-nocheck"), ("@ts-expect-error", r"@ts-expect-error"),
                ("eslint-disable", r"eslint-disable"), ("biome-ignore", r"biome-ignore"),
                ("# type: ignore", r"#\s*type:\s*ignore"), ("# noqa", r"#\s*noqa"),
                ("# pyright: ignore", r"#\s*pyright:\s*ignore"), ("# pylint: disable", r"#\s*pylint:\s*disable"),
                ("nolint", r"\bnolint\b"), ("#[allow(", r"#!?\[allow\("), ("@Suppress(", r"@Suppress\("),
                ("@SuppressWarnings(", r"@SuppressWarnings\("), ("swiftlint:disable", r"swiftlint:disable"),
                ("// ignore:", r"//\s*ignore(?:_for_file)?:"), ("rubocop:disable", r"rubocop:disable"),
                ("@phpstan-ignore", r"@phpstan-ignore"), ("@psalm-suppress", r"@psalm-suppress"),
                ("# ruff: noqa", r"#\s*ruff:\s*noqa"), ("# flake8: noqa", r"#\s*flake8:\s*noqa"),
                ("# mypy: ignore-errors", r"#\s*mypy:\s*ignore-errors"),
                ("# pyright: config", r"#\s*pyright:\s*(?:basic\b|\w+\s*=\s*(?:false|none|information|warning)\b)"),
                ("/* eslint rule */", r"/\*\s*eslint\s+[\w@/-]+\s*:"), ("oxlint-disable", r"oxlint-disable"),
                ("deno-lint-ignore", r"deno-lint-ignore"))
NAME = re.compile(r"[A-Za-z0-9@](?:[A-Za-z0-9._/@-]*[A-Za-z0-9])?")
CONTROL = re.compile("[" + "".join(re.escape(chr(c)) for c in [*range(0x20), *range(0x7f, 0xa0), 0x200e, 0x200f,
                                                                   *range(0x202a, 0x202f), *range(0x2066, 0x206a)]) + "]")


class NotChecked(Exception):
    """Git couldn't say what changed: the guard can't vouch for anything (fail closed)."""


# --- what changed ---------------------------------------------------------------------------------------------

def git(root, *args):
    """Git's stdout as bytes, or None on any failure (a timeout included)."""
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def decode(raw):
    """Text of a file's bytes: UTF-8 with or without a BOM, or UTF-16 with its BOM (PowerShell 5's redirect)."""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def changed_files(root, base):
    """(paths changed since base, committed or not, and untracked ones; the untracked ones), relative to root, never
    .sdlc/."""
    diff = git(root, "diff", "--name-only", "-z", "--relative", base)
    new = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if diff is None or new is None:
        raise NotChecked(f"git couldn't list the changes since {base}")
    untracked = {n for n in decode(new).split("\0") if n and not n.startswith(".sdlc/")}
    names = {n for n in decode(diff).split("\0") if n and not n.startswith(".sdlc/")} | untracked
    return sorted(names), untracked


def at_base(root, base, path):
    raw = git(root, "show", f"{base}:./{path}")
    return decode(raw) if raw is not None else ""


def now(root, path):
    try:
        with open(os.path.join(root, path), "rb") as f:
            return decode(f.read())
    except OSError:
        return ""


def clean(text):
    return CONTROL.sub("?", text)


def short(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


# --- dependency names -----------------------------------------------------------------------------------------

class Unreadable(Exception):
    pass


def _json_names(text, sections):
    if not text.strip():
        return set()
    try:
        data = json.loads(text)
    except ValueError:
        raise Unreadable()
    return {k for s in sections if isinstance(data.get(s), dict) for k in data[s]} if isinstance(data, dict) else set()


def _req_name(s):
    m = NAME.match(s.strip().strip("\"',"))
    return m.group(0) if m else None


def _toml_lines(text):
    """(line without its comment, the quoted strings in it, bracket depth change outside quotes) per line."""
    for line in text.splitlines():
        out, quoted, depth, quote, buf = [], [], 0, None, ""
        for ch in line:
            if quote:
                if ch == quote:
                    quoted.append(buf)
                    quote, buf = None, ""
                else:
                    buf += ch
                out.append(ch)
                continue
            if ch == "#":
                break
            if ch in "\"'":
                quote = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            out.append(ch)
        yield "".join(out).strip(), quoted, depth


def _toml_names(text):
    """Dependency names in a pyproject.toml or Cargo.toml: keys in a table whose name ends in a dependencies word,
    the name of a dotted `[dependencies.<name>]` table, and the requirements quoted in a dependencies array, at any
    bracket depth. Over-flags rather than misses."""
    names, table, array = set(), "", 0
    for s, quoted, delta in _toml_lines(text):
        if not s:
            continue
        if array > 0:
            names |= {n for n in (_req_name(q) for q in quoted) if n}
            array += delta
            continue
        m = re.match(r"\[\[?\s*([^\]]+?)\s*\]\]?$", s)
        if m:
            table = m.group(1)
            parts = [p.strip().strip("\"'") for p in table.split(".")]
            if len(parts) > 1 and "depend" in parts[-2].lower():
                names.add(parts[-1])  # [dependencies.serde], [target.x.dev-dependencies.serde]
            continue
        key, eq, value = s.partition("=")
        if not eq:
            continue
        key = key.strip().strip("\"'")
        parts = [p.strip().strip("\"'") for p in table.split(".")] if table else []
        dep_table = bool(parts) and "depend" in parts[-1].lower()
        dotted_dep = len(parts) > 1 and "depend" in parts[-2].lower()
        if dotted_dep:
            continue  # the keys of [dependencies.serde] are its settings
        if value.strip().startswith("[") and ("depend" in key.lower() or dep_table):
            names |= {n for n in (_req_name(q) for q in quoted) if n}
            array = delta
        elif value.strip().startswith("{") and "depend" in key.lower() and not dep_table:
            names |= {n for n in (_req_name(q) for q in quoted) if n}  # optional-dependencies = { dev = [...] }
        elif dep_table and key and key.lower() != "python":
            names.add(key.split(".")[0])
    return names


def _pubspec_names(text):
    names, section, child = set(), False, None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            key = line.split(":", 1)[0].strip()
            section, child = key.endswith("dependencies") or key == "dependency_overrides", None
        elif section:
            child = indent if child is None else child
            if indent == child and ":" in line:
                names.add(line.split(":", 1)[0].strip())
    return names


def _gomod_names(text):
    names, block = set(), False
    for line in text.splitlines():
        s = line.split("//", 1)[0].strip()
        if block:
            if s.startswith(")"):
                block = False
            elif s:
                names.add(s.split()[0])
        elif re.match(r"require\s*\($", s):
            block = True
        elif s.startswith("require "):
            parts = s.split()
            if len(parts) > 1:
                names.add(parts[1])
    return names


def _gemfile_names(text):
    return set(re.findall(r"^[ \t]*gem[ \t]+[\"']([^\"'\n]+)[\"']", text, re.M))


def is_requirements(path):
    """requirements.txt and its kin: requirements-dev.txt, dev-requirements.txt, requirements.in (pip-tools), and
    any .txt or .in in a requirements/ folder."""
    base = os.path.basename(path).lower()
    return bool(re.match(r"(?:.*[-_.])?requirements.*\.(?:txt|in)$", base)) or (
        base.endswith((".txt", ".in")) and os.path.basename(os.path.dirname(path)).lower() == "requirements")


def dependency_names(path, text):
    base = os.path.basename(path).lower()
    if base == "package.json":
        return _json_names(text, ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"))
    if base == "composer.json":
        return _json_names(text, ("require", "require-dev"))
    if base in ("pyproject.toml", "cargo.toml"):
        return _toml_names(text)
    if base == "pubspec.yaml":
        return _pubspec_names(text)
    if base == "go.mod":
        return _gomod_names(text)
    if base == "gemfile":
        return _gemfile_names(text)
    if is_requirements(path):
        return {n for n in (_req_name(l) for l in text.splitlines() if l.strip() and not l.lstrip().startswith(("#", "-")))
                if n}
    return set()


def source_part(path, text):
    """The part of a manifest or config that says where dependencies come from, as text to compare; "" when it has
    none, or can't be read (an unreadable package.json is its own item)."""
    base = os.path.basename(path).lower()
    if base in SOURCE_FILES:
        return text
    if is_requirements(path):
        return "\n".join(l.strip() for l in text.splitlines() if l.strip().startswith("-"))
    if base == "package.json":
        try:
            data = json.loads(text) if text.strip() else {}
        except ValueError:
            return ""
        if not isinstance(data, dict):
            return ""
        pnpm = data.get("pnpm") if isinstance(data.get("pnpm"), dict) else {}
        part = {k: data[k] for k in ("overrides", "resolutions") if k in data}
        if "overrides" in pnpm:
            part["pnpm.overrides"] = pnpm["overrides"]
        return json.dumps(part, sort_keys=True) if part else ""
    if base == "go.mod":
        out, block = [], False
        for line in text.splitlines():
            s = line.split("//", 1)[0].strip()
            if block:
                block = not s.startswith(")")
                out += [s] if block and s else []
            elif re.match(r"replace\s*\($", s):
                block = True
            elif s.startswith("replace "):
                out.append(s)
        return "\n".join(out)
    if base == "cargo.toml":
        return _sections(text, r"(patch(\..*)?|replace)$")
    return ""


# --- lint config and suppressions -----------------------------------------------------------------------------

def _sections(text, pattern, ini=False):
    """The text of each INI/TOML section whose name matches pattern (a header may carry a trailing comment; an
    indented bracket line is a value, not a header). In an INI file any column-0 bracket line is a header
    (`[mypy-pkg.*]`, `[testenv:py{38,39}]`): INI has no arrays to mistake for one."""
    out, keep = [], False
    header = r"\[([^\]]+)\]\s*(?:[#;].*)?$" if ini else r"\[+\s*([A-Za-z0-9_.:\"' -]+?)\s*\]+\s*(?:[#;].*)?$"
    for line in text.splitlines():
        m = re.match(header, line)
        if m:
            keep = bool(re.match(pattern, m.group(1).strip()))
        if keep:
            out.append(line.rstrip())
    return "\n".join(out)


def _count(text):
    counts = {}
    for line in text.split("\n"):
        for name, pattern in SUPPRESSIONS:
            if re.search(pattern, line):
                counts[name] = counts.get(name, 0) + 1
    return counts


def suppression_counts(root, base, sources):
    """{(path, name): net count added since base} for the tracked source files given, from one diff with fixed
    prefixes and unquoted paths whatever the user's git config (a moved line is free). A file the diff didn't name
    is counted from both versions instead (fail closed)."""
    counts, seen = {}, set()
    raw = git(root, "-c", "core.quotePath=false", "diff", "-U0", "-M", "--relative", "--no-color", "--no-ext-diff",
              "--src-prefix=a/", "--dst-prefix=b/", base)
    if raw is None:
        raise NotChecked(f"git couldn't diff against {base}")
    path, header = None, False
    for line in decode(raw).split("\n"):
        line = line[:-1] if line.endswith("\r") else line
        if line.startswith("diff --git "):  # a file's header runs from here to its first hunk
            path, header = None, True
            continue
        if header:
            if line.startswith("@@"):
                header = False
            elif line.startswith("+++ "):
                name = line[4:].rstrip("\t")
                path = name[2:] if name.startswith("b/") else None  # a name git still quoted is counted below
                seen.add(path)
            elif line.startswith("rename to "):  # a file moved as it is has no hunk: nothing added
                seen.add(line[len("rename to "):])
            continue
        if not line or not path or path not in sources or line[0] not in "+-":
            continue
        sign = 1 if line[0] == "+" else -1
        for name, pattern in SUPPRESSIONS:
            if re.search(pattern, line[1:]):
                counts[(path, name)] = counts.get((path, name), 0) + sign
    for path in sources - seen:  # changed, but no hunk header named it: compare both versions
        new, old = _count(now(root, path)), _count(at_base(root, base, path))
        for name in new:
            if new[name] > old.get(name, 0):
                counts[(path, name)] = new[name] - old.get(name, 0)
    return counts


def items(root, base, guards, prefix=""):
    """[(id, label)] the feature adds since base under the guards given (a list of guard keys). Raises NotChecked
    when git can't say what changed."""
    found = []
    changed, untracked = changed_files(root, base)
    for path in changed:
        name = os.path.basename(path).lower()
        shown = clean(prefix + path)
        if "dependencies" in guards and (name in MANIFESTS or name in SOURCE_FILES or is_requirements(path)):
            new, old = now(root, path), at_base(root, base, path)
            try:
                new_names = dependency_names(path, new)
            except Unreadable:
                found.append((f"manifest:{shown}:{short(new)}", f"manifest {shown} unreadable ({short(new)})"))
                new_names = set()
            try:
                old_names = dependency_names(path, old)
            except Unreadable:  # a Base that can't be read: each dependency named now is new (fail closed)
                old_names = set()
            added = new_names - old_names
            part = source_part(path, new)
            if part != source_part(path, old):
                found.append((f"source:{shown}:{short(part)}", f"dependency source {shown} ({short(part)})"))
            for dep in sorted(added):
                if NAME.fullmatch(dep):
                    found.append((f"dependency:{shown}:{dep}", f"dependency {dep} ({shown})"))
                else:
                    h = short(dep)
                    found.append((f"dependency:{shown}:?{h}", f"dependency with an unusual name in {shown} ({h})"))
        if "lint_config" not in guards:
            continue
        if any(fnmatch.fnmatchcase(name, p.lower()) for p in LINT_FILES):
            new = now(root, path)
            if new != at_base(root, base, path):
                found.append((f"config:{shown}:{short(new)}", f"lint config {shown} ({short(new)})"))
        elif name in LINT_SECTIONS:
            new = now(root, path)
            ini = name != "pyproject.toml"
            part = _sections(new, LINT_SECTIONS[name], ini)
            if part != _sections(at_base(root, base, path), LINT_SECTIONS[name], ini):
                found.append((f"config:{shown}#lint:{short(part)}",
                              f"lint config {shown}, its lint sections ({short(part)})"))
    if "lint_config" in guards:
        sources = {p for p in changed if p.lower().endswith(SOURCE)}
        counts = suppression_counts(root, base, {p for p in sources - untracked if os.path.isfile(os.path.join(root, p))})
        gone = [p for p in sources - untracked if not os.path.lexists(os.path.join(root, p))]
        for path in sources & untracked:  # untracked: everything in it is added, unless it's a deleted file moved here
            was = [g for g in gone if os.path.basename(g) == os.path.basename(path)]
            old = _count(at_base(root, base, was[0])) if len(was) == 1 else {}
            for sname, n in _count(now(root, path)).items():
                if n > old.get(sname, 0):
                    counts[(path, sname)] = n - old.get(sname, 0)
        for (path, sname), n in sorted(counts.items()):
            if n > 0:
                shown = clean(prefix + path)
                found.append((f"suppression:{shown}:{sname}:{n}", f"suppression {sname} in {shown} (now +{n})"))
    return found


# --- the user's allow ------------------------------------------------------------------------------------------

def load(root):
    try:
        with sdlc_scopes.open_regular(sdlc_scopes._inside(root, STORE)) as f:
            data = json.load(f)
    except Exception:
        data = {}
    data = data if isinstance(data, dict) else {}
    pending = data.get("pending") if isinstance(data.get("pending"), dict) else {}
    allowed = data.get("allowed") if isinstance(data.get("allowed"), dict) else {}
    return {"pending": {f: {k: v for k, v in items_.items() if isinstance(k, str) and isinstance(v, str)}
                        for f, items_ in pending.items() if isinstance(f, str) and isinstance(items_, dict)},
            "allowed": {f: [x for x in ids if isinstance(x, str)]
                        for f, ids in allowed.items() if isinstance(f, str) and isinstance(ids, list)}}


def is_allowed(item_id, allowed):
    """Allowed as is, or (a suppression) with an allowed count at least as high: taking one back stays allowed."""
    if item_id in allowed:
        return True
    m = re.match(r"(suppression:.+:)(\d+)$", item_id)
    return bool(m) and any(a.startswith(m.group(1)) and a[len(m.group(1)):].isdigit()
                           and int(a[len(m.group(1)):]) >= int(m.group(2)) for a in allowed)


def unallowed(root, base, guards, feature, repos=()):
    """[(id, label)] not allowed yet, the workbench's and each branched repo's ([(name, base)]); also records them
    as the feature's pending items an allow can name. Raises NotChecked."""
    store_root = sdlc_scopes.gate_root(root) or root
    found = items(root, base, guards) if base else []
    for name, repo_base in repos:
        found += items(os.path.join(root, name), repo_base, guards, prefix=f"{name}/")
    data = load(store_root)
    left = [(i, label) for i, label in found if not is_allowed(i, data["allowed"].get(feature, []))]
    if {i: label for i, label in left} != data["pending"].get(feature, {}):
        data["pending"][feature] = {i: label for i, label in left}
        if not data["pending"][feature]:
            data["pending"].pop(feature)
        sdlc_scopes.write_record(store_root, STORE, data)
    return left


def allowed_labels(root, base, guards, feature, repos=()):
    """Labels of this feature's items the user has allowed for it (for the Gate log). Raises NotChecked."""
    data = load(sdlc_scopes.gate_root(root) or root)
    found = items(root, base, guards) if base else []
    for name, repo_base in repos:
        found += items(os.path.join(root, name), repo_base, guards, prefix=f"{name}/")
    return [label for i, label in found if is_allowed(i, data["allowed"].get(feature, []))]


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name")
    if event not in ("PostToolUse", "UserPromptSubmit"):
        return
    import verify_freshness as vf  # noqa: PLC0415
    project = vf.project_root(data.get("cwd"))  # where user_answer.py records the questions asked
    root = (sdlc_scopes.gate_root(project) or project) if project else project
    if not root:
        return
    store = load(root)
    if not store["pending"] or sdlc_scopes.advisory_from(root):  # nothing waits: no further reads
        return
    if event == "PostToolUse":
        import user_answer  # noqa: PLC0415  (sibling hook: a question-tool answer the agent didn't write)
        if not user_answer.answered(project, data, HEADER):  # also checks the call was recorded, not pre-filled
            return
        response = data.get("tool_response") if isinstance(data.get("tool_response"), dict) else {}
        answers = response.get("answers") or (data.get("tool_input") or {}).get("answers") or {}
        allowing = []  # each question's own answer: an Allow covers only the labels its own question names
        for q in (data.get("tool_input") or {}).get("questions") or []:
            if not isinstance(q, dict) or (q.get("header") or "").strip().lower() != HEADER.lower():
                continue
            answer = answers.get(q.get("question")) if isinstance(answers, dict) else None
            text = str(q.get("question") or "")
            if EXCLUDING.search(text):
                continue  # "all except X": allows nothing; the question names only what it allows
            if isinstance(answer, str) and re.sub(r"\s*\(recommended\)\s*$", "", answer, flags=re.I).strip().lower() == "allow":
                allowing.append(text)
        import sdlc_layout  # noqa: PLC0415
        active = {name for name, _ in sdlc_layout.active(root)}
        live = [f for f in store["pending"] if f in active] or list(store["pending"])  # an abandoned one aside
        chosen = {}
        for text in allowing:
            named = [f for f in store["pending"] if re.search(rf"(?<![\w-]){re.escape(f)}(?![\w-])", text)]
            for f in named or live:  # the feature the question names, else the live ones
                for i, label in store["pending"][f].items():
                    shared = sum(label in store["pending"][g].values() for g in live) > 1
                    if label in text and (named or not shared):  # several features wait on it: say which
                        chosen.setdefault(f, []).append(i)
    else:
        if not TYPED.fullmatch((data.get("prompt") or "").strip()):
            return
        import sdlc_layout  # noqa: PLC0415
        active = {name for name, _ in sdlc_layout.active(root)}
        waiting = [f for f in store["pending"] if f in active] or list(store["pending"])  # an abandoned one aside
        if len(waiting) != 1:
            return  # several features waiting: the typed form can't say which
        chosen = {waiting[0]: list(store["pending"][waiting[0]])}
    if any(chosen.values()):
        for f, ids in chosen.items():  # an allow belongs to the feature that asked: a later one asks again
            store["allowed"][f] = sorted(set(store["allowed"].get(f, [])) | set(ids))
        store["pending"] = {f: {i: label for i, label in p.items() if not (f in chosen and i in chosen[f])}
                            for f, p in store["pending"].items()}
        store["pending"] = {f: p for f, p in store["pending"].items() if p}
        sdlc_scopes.write_record(root, STORE, store)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        main()
    except Exception:
        pass
    sys.exit(0)
