#!/usr/bin/env python3
"""The criteria an rspec spec locked (contracts C3, `criteria.lock.json`), for spec-backed changes (spec 03 S2, S10).

Where the lock is: `.sdlc/config.json` → `spec_lock` when set, else every git-tracked `criteria.lock.json` (outside a
vendored contracts folder's fixtures). Its `spec` is relative to the repo, each criterion's `file` to `spec`
(contracts 1.1.0). A change file cites criteria by ID: `- **AC-003** → F-ISS-01.AC2[, F-ISS-01.AC3]` (or `->`).
Used by verify.py (trace), state.py (cite, question, questions) and brief.py. Stdlib only, Python 3.9+.
"""
import json
import os
import re
import subprocess

CRITERION_ID = re.compile(r"\bF-[A-Z][A-Z0-9]*-[0-9]+\.AC[0-9]+\b")
# `- **AC-003** → F-ISS-01.AC2, F-ISS-01.AC3`: the IDs after the arrow
CITE = re.compile(r"^\s*[-*]\s+\**(AC-\d{3})\**\s*(?:→|->)\s*(.+)$")
FIXTURES = re.compile(r"(^|/)contracts/v\d+/fixtures/")


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def lock_paths(root):
    """Repo-relative paths of the locks to read: config `spec_lock`, else every tracked criteria.lock.json."""
    try:
        config = json.loads(_read(os.path.join(root, ".sdlc", "config.json")) or "{}")
    except ValueError:
        config = {}
    if isinstance(config, dict) and isinstance(config.get("spec_lock"), str) and config["spec_lock"]:
        return [config["spec_lock"]]  # checked against the repo in load()
    p = subprocess.run(["git", "-C", root, "ls-files", "--", "*criteria.lock.json"], capture_output=True,
                       encoding="utf-8", errors="replace")
    return sorted(f for f in p.stdout.splitlines()
                  if os.path.basename(f) == "criteria.lock.json" and not FIXTURES.search(f))


def spec_backed_repo(root):
    """sdlc 3.5's one switch: a repo with a criteria lock (config `spec_lock`, or a tracked criteria.lock.json) or an
    acceptance bundle (acceptance/manifest.json) is spec-backed, and only there do the test lock, `red --at`, the
    accept.* keys and their doctor row apply. Without either, sdlc behaves as 3.4.0."""
    return bool(lock_paths(root)) or os.path.isfile(os.path.join(root, "acceptance", "manifest.json"))


def load(root):
    """({ID: entry with `spec` and `lock` added}, problems): every criterion of every lock; the first lock by path
    wins an ID two locks hold, and the clash is a problem."""
    found, problems = {}, []
    for rel in lock_paths(root):
        try:
            lock = json.loads(_read(inside(root, rel) or "") or "")
        except (ValueError, OSError):
            lock = None
        bad = lock_problem(root, lock)
        if bad:
            problems.append(f"not run: {rel} isn't a criteria lock ({bad})")
            continue
        for c in lock["criteria"]:
            if c["id"] in found:
                problems.append(f"{c['id']} is in two locks: {found[c['id']]['lock']} and {rel}")
                continue
            found[c["id"]] = dict(c, spec=lock["spec"], lock=rel)
    return found, problems


def inside(root, rel):
    """The path, when it stays inside the repo; else None."""
    if not isinstance(rel, str) or not rel or os.path.isabs(rel) or re.match(r"^[A-Za-z]:", rel):
        return None
    base = os.path.realpath(root)
    full = os.path.realpath(os.path.join(base, rel))
    return full if full == base or full.startswith(base + os.sep) else None


def lock_problem(root, lock):
    """Why a lock can't be read (the C3 fields sdlc uses), or None."""
    if not isinstance(lock, dict) or not isinstance(lock.get("criteria"), list):
        return "not a JSON object with criteria"
    if not isinstance(lock.get("spec"), str) or inside(root, lock["spec"]) is None:
        return "its spec path isn't a folder in the repo"
    for c in lock["criteria"]:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not CRITERION_ID.fullmatch(c["id"]):
            return f"a criterion without an ID: {str(c)[:60]}"
        if not isinstance(c.get("text_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", c["text_sha256"]):
            return f"{c['id']} has no text_sha256"
        if not isinstance(c.get("file"), str) or inside(root, os.path.join(lock["spec"], c["file"])) is None:
            return f"{c['id']}'s file isn't in the repo"
    return None


def criterion_line(root, entry):
    """The criterion's line in its story file, without the list marker and checkbox; None when it can't be found."""
    path = inside(root, os.path.join(entry.get("spec") or "", entry.get("file") or ""))
    text = _read(path) if path else None
    for line in (text or "").splitlines():
        m = re.match(r"^\s*[-*]\s+(?:\[[ xX]\]\s+)?(\*\*([^*]+)\*\*.*)$", line)
        if m and m.group(2) == entry["id"]:
            return m.group(1).strip()
    return None


AC_ENTRY = re.compile(r"^\s*[-*]\s+\**(AC-\d{3})")


def entries(change_text):
    """{AC: its text} for each `- **AC-nnn** …` entry under `## Acceptance criteria`; a blank line ends an entry, so
    a citation wrapped onto the next line belongs to its AC."""
    m = re.search(r"^##\s+Acceptance criteria\s*$(.*?)(?=^##\s|\Z)", change_text or "", re.M | re.S)
    out, current = {}, None
    for line in (m.group(1) if m else "").splitlines():
        a = AC_ENTRY.match(line)
        if a:
            current = a.group(1)
            out[current] = line
        elif current and line.strip():
            out[current] += "\n" + line
        else:
            current = None
    return out


def cited(ac_entries):
    """{AC: [criterion IDs]} for each AC entry that cites criteria (`→ F-…ACn`)."""
    out = {}
    for ac, text in ac_entries.items():
        m = CITE.match(" ".join(part.strip() for part in text.splitlines()))
        if m:
            ids = CRITERION_ID.findall(m.group(2))
            if ids:
                out[ac] = ids
    return out
