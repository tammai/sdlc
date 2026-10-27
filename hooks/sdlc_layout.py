"""Where a set-up repo keeps sdlc feature state and documents.

New layout (the project's own .sdlc/config.json sets `docs_dir`): state in .sdlc/state/<name>.md, documents in
<docs_dir>/intents/<name>/, constitution and design system in <docs_dir>/. Legacy layout (no `docs_dir`):
everything under .sdlc/, a feature in .sdlc/<name>/ with its state.md. Readers accept both, so a repo keeps
working between a plugin update and the /sdlc:setting-up-projects upgrade that moves it. Paths returned are repo-relative, with `/`.
"""
import glob
import json
import os
import posixpath
import re

DOCS_DEFAULT = "docs/sdlc"
SDLC = ".sdlc"


def docs_dir(root):
    """The recorded docs location, or None for a legacy repo (also when config is missing, unreadable, or the value
    isn't a valid in-repo folder: hooks grant access by it, so a bad value must not widen anything)."""
    try:
        with open(os.path.join(root, SDLC, "config.json"), encoding="utf-8") as f:
            value = json.load(f).get("docs_dir")
    except (OSError, ValueError, AttributeError):
        return None
    try:
        return validate_docs_dir(value) if isinstance(value, str) and value else None
    except ValueError:
        return None


def validate_docs_dir(value):
    raw = str(value or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        raise ValueError(f"docs_dir {value!r} is not inside the repo: give a path relative to the repo root")
    norm = posixpath.normpath(raw)
    if norm == ".." or norm.startswith("../"):
        raise ValueError(f"docs_dir {value!r} is not inside the repo: give a path relative to the repo root")
    if norm == ".":
        raise ValueError("docs_dir can't be the repo root: name a folder")
    # Windows and macOS match names case-insensitively and Windows drops trailing dots and spaces: .GIT, ".git."
    if any(part.rstrip(". ").lower() == ".git" for part in norm.split("/")):
        raise ValueError("docs_dir can't be inside .git")
    return norm


def paths(root, name=None):
    docs = docs_dir(root)
    if docs:
        out = {"layout": "new", "docs_dir": docs, "constitution": f"{docs}/constitution.md",
               "design_system": f"{docs}/design-system.md", "intents_root": f"{docs}/intents/",
               "state_root": f"{SDLC}/state/"}
        if name:
            out.update(state=f"{SDLC}/state/{name}.md", intents=f"{docs}/intents/{name}/")
    else:
        out = {"layout": "legacy", "docs_dir": SDLC, "constitution": f"{SDLC}/constitution.md",
               "design_system": f"{SDLC}/design-system.md", "intents_root": f"{SDLC}/", "state_root": f"{SDLC}/"}
        if name:
            out.update(state=f"{SDLC}/{name}/state.md", intents=f"{SDLC}/{name}/")
    return out


def features(root):
    """Every feature in either layout: {name: {state, intents, layout}}. A name in both: the new one wins."""
    docs = docs_dir(root) or DOCS_DEFAULT
    found = {}
    for path in sorted(glob.glob(os.path.join(root, SDLC, "*", "state.md"))):
        name = os.path.basename(os.path.dirname(path))
        found[name] = {"state": f"{SDLC}/{name}/state.md", "intents": f"{SDLC}/{name}/", "layout": "legacy"}
    for path in sorted(glob.glob(os.path.join(root, SDLC, "state", "*.md"))):
        name = os.path.basename(path)[:-3]
        found[name] = {"state": f"{SDLC}/state/{name}.md", "intents": f"{docs}/intents/{name}/", "layout": "new"}
    return found


def active(root):
    """(name, state text) for each feature whose state says `Status: active`; an unreadable state is skipped."""
    for name, f in features(root).items():
        try:
            with open(os.path.join(root, f["state"]), encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        if re.search(r"^Status:\s*active\b", text, re.M | re.I):
            yield name, text
