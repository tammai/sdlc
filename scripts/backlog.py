#!/usr/bin/env python3
"""sdlc backlog: which slice of a feature's backlog.md runs next.

A slice in progress is resumed; otherwise the next one is the first `todo` row whose dependencies are all
`done` (`done <commit>` from before 2.4.3). Used by the orchestrator, autopilot.py and verify.py (which ACs
belong to parts not started yet).
Usage: python3 backlog.py next BACKLOG.md          -> {"next": "B2" | null, "done": bool}
       python3 backlog.py check BACKLOG.md B<n>    -> {"ok": true} or exit 1 with {"ok": false, "reason": ...}
An unreadable file, or one without a table with ID, Deps and Status columns: exit 2 with {"error": ...}.
Prints one JSON object. Stdlib only, Python 3.9+.
"""
import json
import re
import sys


def cells(line):
    """A table row's cells; a backslash-escaped pipe is a literal pipe inside a cell, as Markdown writes it."""
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def slices(text):
    """[{id, deps, status, acs}] from the first table whose header has ID, Deps and Status columns; `acs` is the
    ACs cell as written ("" without that column)."""
    rows, cols = [], None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if cols and rows:
                break
            continue
        row = cells(line)
        if cols is None:
            names = [c.lower() for c in row]
            if {"id", "deps", "status"} <= set(names):
                cols = {n: names.index(n) for n in ("id", "deps", "status", "acs") if n in names}
            continue
        if set(line.replace("|", "").strip()) <= set("-: ") or len(row) <= max(cols[n] for n in ("id", "deps", "status")):
            continue  # the separator row, or a row too short to read
        # `**B1**` or `` `B1` `` is B1; anything else stays as written, so autopilot still refuses `B1 & calc`
        slice_id = re.fullmatch(r"[*_`~\s]*(B\d+)[*_`~\s]*", row[cols["id"]], re.I)
        rows.append({"id": (slice_id.group(1) if slice_id else row[cols["id"]]).upper(), "deps": [d.upper() for d in re.findall(r"B\d+", row[cols["deps"]], re.I)],
                     "status": row[cols["status"]].lower(),
                     "acs": row[cols["acs"]] if "acs" in cols and len(row) > cols["acs"] else ""})
    return rows


# (?<![\w-]): a match starts at an AC- token or a standalone number, never at the digits ending a word (OAuth2, B3)
AC_SPAN = re.compile(r"(?<![\w-])(?:AC-)?(\d{1,3})\b(?:\s*[–—-]\s*(?:AC-)?(\d{1,3})\b)?", re.I)


def ac_ids(cell):
    """The AC ids an ACs cell names: `1, 2`, `AC-001 AC-002` or a range such as `AC-001–004` or `2-3`."""
    out = []
    for m in AC_SPAN.finditer(cell):
        first, last = int(m.group(1)), int(m.group(2) or m.group(1))
        out += [f"AC-{n:03d}" for n in range(first, last + 1 if 0 <= last - first < 100 else first + 1)]
    return list(dict.fromkeys(out))


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
