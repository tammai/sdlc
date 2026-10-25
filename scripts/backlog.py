#!/usr/bin/env python3
"""sdlc backlog: which slice of a feature's backlog.md runs next.

A slice in progress is resumed; otherwise the next one is the first `todo` row whose dependencies are all
`done <commit>`. Used by the orchestrator and autopilot.py.
Usage: python3 backlog.py next BACKLOG.md          -> {"next": "B2" | null, "done": bool}
       python3 backlog.py check BACKLOG.md B<n>    -> {"ok": true} or exit 1 with {"ok": false, "reason": ...}
An unreadable file, or one without a table with ID, Deps and Status columns: exit 2 with {"error": ...}.
Prints one JSON object. Stdlib only, Python 3.9+.
"""
import json
import re
import sys


def slices(text):
    """[{id, deps, status}] from the first table whose header has ID, Deps and Status columns."""
    rows, cols = [], None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if cols and rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cols is None:
            names = [c.lower() for c in cells]
            if {"id", "deps", "status"} <= set(names):
                cols = {n: names.index(n) for n in ("id", "deps", "status")}
            continue
        if set(line.replace("|", "").strip()) <= set("-: ") or len(cells) <= max(cols.values()):
            continue  # the separator row, or a row too short to read
        rows.append({"id": cells[cols["id"]].upper(), "deps": [d.upper() for d in re.findall(r"B\d+", cells[cols["deps"]], re.I)],
                     "status": cells[cols["status"]].lower()})
    return rows


def is_done(row):
    return row["status"].startswith("done")


def next_slice(rows):
    for r in rows:
        if r["status"].startswith("in progress"):
            return r["id"]
    done = {r["id"] for r in rows if is_done(r)}
    for r in rows:
        if r["status"].startswith("todo") and all(d in done for d in r["deps"]):
            return r["id"]
    return None


def check(rows, slice_id):
    by_id = {r["id"]: r for r in rows}
    row = by_id.get(slice_id)
    if row is None:
        return f"{slice_id} isn't in the backlog"
    if is_done(row):
        return f"{slice_id} is already {row['status']}"
    open_deps = [f"{d} ({by_id[d]['status'] if d in by_id else 'missing'})" for d in row["deps"]
                 if not (d in by_id and is_done(by_id[d]))]
    return f"{slice_id} depends on {', '.join(open_deps)}" if open_deps else None


def main(argv):
    if len(argv) < 2 or argv[0] not in ("next", "check") or (argv[0] == "check" and len(argv) < 3):
        print(json.dumps({"error": "usage: backlog.py next BACKLOG.md | check BACKLOG.md B<n>"}))
        return 2
    try:
        with open(argv[1], encoding="utf-8-sig") as f:
            rows = slices(f.read())
    except (OSError, UnicodeDecodeError) as e:
        print(json.dumps({"error": f"can't read {argv[1]}: {e}"}))
        return 2
    if not rows:  # "nothing ready" must never be how a broken backlog looks
        print(json.dumps({"error": f"no table with ID, Deps and Status columns in {argv[1]}"}))
        return 2
    if argv[0] == "next":
        print(json.dumps({"next": next_slice(rows), "done": bool(rows) and all(is_done(r) for r in rows)}))
        return 0
    reason = check(rows, argv[2].upper())
    print(json.dumps({"ok": False, "reason": reason} if reason else {"ok": True}))
    return 1 if reason else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
