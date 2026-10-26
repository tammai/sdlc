#!/usr/bin/env python3
"""sdlc state: every change to a feature's state in one call, so state.md and the control contract can't disagree.

state.md stays the model's view and the committed record; the hooks read it (`Current: Stage <n> – <name>`,
`Status:`, `Flow:`, `Base:`). Each call also writes the control contract, git-ignored runtime files a runner or a
control app reads without knowing the pipeline's internals (docs/specs/12-control-contract.md), beside the state
file and git-ignored (in either layout):
  .sdlc/state/<feature>.json            snapshot, derived from state.md (contract_version)
  .sdlc/state/<feature>.events.jsonl    one event per call, appended, never rewritten
  .sdlc/state/<feature>.commands/       the runner's inbox; never read or executed here
Advancing to the current stage is refused (it would tick the stage before its gate ran).
Usage: python3 state.py [--root DIR] advance FEATURE STAGE [--gate pass|fail] [--note TEXT]
                                     round FEATURE N pass|fail REASON [--commit SHA]
                                     verified FEATURE COMMIT TREE
                                     log FEATURE TEXT [--type note|review_done]
                                     deviation FEATURE TEXT
                                     slice FEATURE start|done|block B<n> [COMMIT | REASON]
                                     blocker FEATURE raise|resolve TEXT
                                     set FEATURE FIELD VALUE
                                     sync FEATURE
Everything is computed before anything is written; then backlog.md, state.md, state.json and the event are
written in that order, each file atomically. Prints one JSON object. Exit 0 ok, 1 refused (unknown feature,
malformed state.md, a failed write; nothing written unless the error says so), 2 usage. Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
import backlog  # noqa: E402  (sibling script: the backlog table)
import sdlc_layout  # noqa: E402  (where the feature's state and documents live)

CONTRACT_VERSION = 2
# Four phases, each run at one stage number (1 Define, 4 Build, 5 Prove, 8 Ship) so the hooks keep reading numbers.
# The other numbers keep their old names for features started under the 11-stage flow.
# 6 is also where a backlog slice rests once committed (Stage 8 means feature close reached Ship).
STAGES = {1: "Define", 2: "Design", 3: "Plan", 4: "Build", 5: "Prove", 6: "Review", 7: "Security",
          8: "Ship", 9: "Deploy", 10: "Operate", 11: "Learn"}
PHASES = {1: "define", 2: "define", 3: "define", 4: "build", 5: "prove", 6: "prove", 7: "prove",
          8: "ship", 9: "ship", 10: "ship", 11: "ship"}
FIELDS = ("Status", "Track", "Risk", "Flow", "Build", "Top model", "Base", "Owner", "Tool", "Slice gates")


class Refused(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):  # usage errors are one JSON object too
        print(json.dumps({"ok": False, "error": f"usage: {message}"}))
        sys.exit(2)


# --- state.md ------------------------------------------------------------------------------------------------

def field(text, name):
    m = re.search(rf"^{re.escape(name)}:[ \t]*(\S+)", text, re.M)
    return m.group(1) if m else None


def with_newline(text):
    return text if text.endswith("\n") else text + "\n"


def section(lines, heading):
    """(start, end) line indexes of the body under `## heading`, or None."""
    for i, line in enumerate(lines):
        if line.strip() == f"## {heading}":
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
            return i + 1, end
    return None


def section_items(text, heading):
    lines = text.split("\n")
    span = section(lines, heading)
    if not span:
        return []
    return [l[2:].strip() for l in lines[span[0]:span[1]]
            if l.startswith("- ") and l[2:].strip() and not l[2:].lstrip().startswith("(")]


def append_to_section(text, heading, item):
    lines = text.split("\n")
    span = section(lines, heading)
    if not span:  # a section the template has but this file lost: add it at the end
        return text.rstrip("\n") + f"\n\n## {heading}\n- {item}\n"
    start, end = span
    # Drop blanks, the empty "-" and the template's example lines ("- (oldest first …)", "- <date> Stage n: …")
    body = [l for l in lines[start:end] if l.strip() and l.strip() != "-" and not l.startswith("- (")
            and not re.match(r"- (<date>|Round 1 — <commit>)", l)]
    return with_newline("\n".join(lines[:start] + body + [f"- {item}"]
                                  + ([""] + lines[end:] if end < len(lines) else [])))


def remove_from_section(text, heading, item):
    lines = text.split("\n")
    span = section(lines, heading)
    for i in range(*span) if span else ():
        if lines[i].startswith("- ") and lines[i][2:].strip() == item:
            del lines[i]
            return with_newline("\n".join(lines)), True
    return text, False


def set_line(text, name, value):
    """`Name: value`, keeping a trailing `(comment)` the template puts after the value."""
    m = re.search(rf"^{re.escape(name)}:[^\n]*$", text, re.M)
    if m:
        comment = re.search(r"\s{2,}\(.*\)\s*$", m.group(0))
        line = f"{name}: {value}" + (comment.group(0).rstrip() if comment else "")
        return text[:m.start()] + line + text[m.end():]
    # A new field goes above Current:, with the other header fields
    return re.sub(r"^Current:", lambda c: f"{name}: {value}\n" + c.group(0), text, count=1, flags=re.M)


def set_slice_gates(text, gates):
    # The gates live inside the `Slice:` line; before the first slice there's a placeholder one
    if re.search(r"^Slice:.*Slice gates:", text, re.M):
        return re.sub(r"^(Slice:.*Slice gates:)[ \t]*[^(\n]*?(\s{2,}\(.*\))?[ \t]*$",
                      lambda m: f"{m.group(1)} {gates}" + (m.group(2) or ""), text, count=1, flags=re.M)
    return set_line(text, "Slice", f"-   Slice base: -   Slice gates: {gates}")


def tick(text, stage):
    return re.sub(rf"^- \[ \] {stage} ", f"- [x] {stage} ", text, count=1, flags=re.M)


def check(text):
    missing = [n for n in ("Status", "Current") if not re.search(rf"^{n}:", text, re.M)]
    if missing:
        raise Refused(f"state.md has no {' or '.join(n + ':' for n in missing)} line")
    m = re.search(r"^Current:\s*Stage\s*(\d+)\b", text, re.M)
    if not m:
        raise Refused("state.md's Current: line isn't `Current: Stage <n> – <name>`")
    return int(m.group(1))


# --- backlog.md -----------------------------------------------------------------------------------------------

def set_backlog_status(raw, slice_id, status):
    """backlog.md's text with the slice's Status cell set; columns found by header, like backlog.py."""
    lines = raw.split("\n")
    cols = None
    for i, line in enumerate(lines):
        stripped = line.strip().rstrip("\r")
        if not stripped.startswith("|"):
            continue
        cells = backlog.cells(stripped)
        if cols is None:
            names = [c.lower() for c in cells]
            if {"id", "status"} <= set(names):
                cols = (names.index("id"), names.index("status"))
            continue
        if len(cells) > max(cols) and cells[cols[0]].upper() == slice_id:
            cells[cols[1]] = status
            lead = line[:len(line) - len(line.lstrip())]
            lines[i] = lead + "| " + " | ".join(cells) + " |" + ("\r" if line.endswith("\r") else "")
            return "\n".join(lines)
    raise Refused(f"{slice_id} isn't a row of the backlog table")


# --- the contract ---------------------------------------------------------------------------------------------

def snapshot(feature, text, backlog_text):
    stage = check(text)
    slice_line = re.search(r"^Slice:[ \t]*(\S+)(.*)$", text, re.M)
    slice_info = None
    if slice_line:
        rest = slice_line.group(2)
        base = re.search(r"Slice base:\s*(\S+)", rest)
        gates = re.search(r"Slice gates:\s*([^(]+?)\s*(?:\(|$)", rest)
        slice_info = {"id": slice_line.group(1), "base": base.group(1) if base else None,
                      "gates": gates.group(1) if gates else None}
    verified = re.search(r"^Verified:\s*(\S+)\s+tree\s+(\S+)", text, re.M)
    gates = []
    for item in section_items(text, "Gate log"):
        m = re.match(r"(\S+) Stage (\d+): (pass|fail)\b(?:\s*—\s*(.*))?", item)
        if m:
            gates.append({"date": m.group(1), "stage": int(m.group(2)), "result": m.group(3), "note": m.group(4)})
    rounds = []
    for item in section_items(text, "Verify rounds"):
        m = re.match(r"Round (\d+) — (\S+) — (PASS|FAIL) — (.*)", item)
        if m:
            rounds.append({"round": int(m.group(1)), "commit": m.group(2), "result": m.group(3).lower(),
                           "reason": m.group(4)})
    slices = None
    if backlog_text is not None:
        slices = [{"id": r["id"], "status": r["status"]} for r in backlog.slices(backlog_text)]
    return {
        "contract_version": CONTRACT_VERSION, "feature": feature,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **{name.lower().replace(" ", "_"): field(text, name) for name in FIELDS if name != "Slice gates"},
        "current": {"stage": stage, "name": STAGES.get(stage)}, "phase": PHASES.get(stage),
        "slice": slice_info, "backlog": slices,
        "verified": {"commit": verified.group(1), "tree": verified.group(2)} if verified else None,
        "gates": gates, "verify_rounds": rounds, "open_questions": section_items(text, "Open questions"),
        "spend": None,
    }


def write_atomic(path, data):
    """Temp file in the same folder, fsync, rename: a reader or a crash never sees half a file."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(5):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:  # Windows: a reader has the target open for a moment
                if attempt == 4:
                    raise
                time.sleep(0.1)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# --- commands -------------------------------------------------------------------------------------------------

def today():
    return datetime.now().strftime("%Y-%m-%d")


def git_head(root):
    p = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"], capture_output=True,
                       encoding="utf-8", errors="replace")
    return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else "-"


def apply(a, text, backlog_raw):
    """(new state.md text, new backlog.md text or None, event or None) for one command."""
    stage = check(text)
    if a.cmd == "advance":
        if a.stage not in STAGES:
            raise Refused(f"no Stage {a.stage}")
        if a.stage == stage:  # a repeated advance would tick the stage before its gate ran
            raise Refused(f"already at Stage {stage}")
        if a.gate:
            text = append_to_section(text, "Gate log", f"{today()} Stage {stage}: {a.gate}"
                                     + (f" — {a.note}" if a.note else ""))
            if a.gate == "pass":
                text = tick(text, stage)
        text = re.sub(r"^Current:.*$", lambda _: f"Current: Stage {a.stage} – {STAGES[a.stage]}", text, count=1,
                      flags=re.M)
        return text, None, {"type": "stage_entered", "from": stage, "stage": a.stage, "gate": a.gate,
                            "note": a.note}
    if a.cmd == "round":
        text = append_to_section(text, "Verify rounds",
                                 f"Round {a.n} — {a.commit or '-'} — {a.result.upper()} — {a.reason}")
        return text, None, {"type": "verify_round", "round": a.n, "result": a.result, "commit": a.commit,
                            "reason": a.reason}
    if a.cmd == "verified":
        return set_line(text, "Verified", f"{a.commit} tree {a.tree}"), None, {
            "type": "verified", "commit": a.commit, "tree": a.tree}
    if a.cmd == "log":
        return append_to_section(text, "Gate log", f"{today()} {a.text}"), None, {"type": a.type, "text": a.text}
    if a.cmd == "deviation":  # its own section: the sdlc-invariants CI check reads Deviations
        return append_to_section(text, "Deviations", f"{today()} {a.text}"), None, {"type": "deviation_logged",
                                                                                    "text": a.text}
    if a.cmd == "slice":
        slice_id = a.id.upper()
        if not re.fullmatch(r"B\d+", slice_id):
            raise Refused(f"slice IDs are B<n>, not {a.id}")
        if backlog_raw is None:
            raise Refused("this feature has no backlog.md")
        if a.action == "start":
            head = git_head(a.root)
            gates = (re.search(r"Slice gates:\s*([^(\n]+?)\s*(?:\(|$)", text, re.M) or [None, "none"])[1]
            text = re.sub(r"^Slice:.*\n?", "", text, flags=re.M)
            text = set_line(text, "Slice", f"{slice_id}   Slice base: {head}   Slice gates: {gates}")
            return text, set_backlog_status(backlog_raw, slice_id, "in progress"), {
                "type": "slice_started", "slice": slice_id, "base": head}
        if a.action == "block":
            if not a.commit:
                raise Refused("slice block needs a reason")
            text = append_to_section(text, "Open questions", f"{slice_id} blocked: {a.commit}")
            return text, set_backlog_status(backlog_raw, slice_id, f"blocked: {a.commit}"), {
                "type": "slice_blocked", "slice": slice_id, "reason": a.commit}
        if not a.commit:
            raise Refused("slice done needs the slice's commit")
        return text, set_backlog_status(backlog_raw, slice_id, f"done {a.commit}"), {
            "type": "slice_done", "slice": slice_id, "commit": a.commit}
    if a.cmd == "blocker":
        if a.action == "raise":
            return append_to_section(text, "Open questions", a.text), None, {"type": "blocker_raised", "text": a.text}
        text, found = remove_from_section(text, "Open questions", a.text)
        if not found:
            raise Refused(f"no open question reads: {a.text}")
        return text, None, {"type": "blocker_resolved", "text": a.text}
    if a.cmd == "set":
        if a.field not in FIELDS:
            raise Refused(f"set takes one of: {', '.join(FIELDS)}")
        text = set_slice_gates(text, a.value) if a.field == "Slice gates" else set_line(text, a.field, a.value)
        if a.field == "Status" and a.value == "done":
            return text, None, {"type": "feature_done"}
        return text, None, {"type": "field_set", "field": a.field, "value": a.value}
    return text, None, None  # sync


def contract_paths(root, feature):
    """(state.json, events.jsonl) as `.sdlc/state/<f>.json` and `<f>.events.jsonl` in either layout, so one set of
    ignore patterns covers them and an old-layout feature folder holds only documents (relocate moves those)."""
    base = os.path.join(root, ".sdlc", "state", feature)
    return base + ".json", base + ".events.jsonl"


def read_raw(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def run(a):
    located = sdlc_layout.features(a.root).get(a.feature)
    if not located:
        raise Refused(f"no feature named {a.feature} (no state file for it)")
    for value in vars(a).values():  # a newline in a value would add lines (a fake Current:) to state.md
        if isinstance(value, str) and ("\n" in value or "\r" in value):
            raise Refused("values can't contain line breaks")
    path = os.path.join(a.root, located["state"])
    raw = read_raw(path)
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    backlog_path = os.path.join(a.root, located["intents"], "backlog.md")
    backlog_raw = read_raw(backlog_path) if os.path.isfile(backlog_path) else None
    bom = backlog_raw is not None and backlog_raw.startswith("﻿")
    if bom:
        backlog_raw = backlog_raw[1:]
    new, new_backlog, event = apply(a, text, backlog_raw)
    check(new)
    snap = snapshot(a.feature, new, new_backlog if new_backlog is not None else backlog_raw)
    snapshot_path, events_path = contract_paths(a.root, a.feature)
    written = []
    try:
        if new_backlog is not None and new_backlog != backlog_raw:
            write_atomic(backlog_path, ("﻿" if bom else "") + new_backlog)
            written.append("backlog.md")
        if new != text:
            write_atomic(path, new.replace("\n", "\r\n") if crlf else new)
            written.append("state.md")
        os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
        write_atomic(snapshot_path, json.dumps(snap, indent=2, ensure_ascii=False))
        if event:
            event = {"ts": snap["updated"], "feature": a.feature, **event}
            with open(events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
    except OSError as e:
        done = f"; already written: {', '.join(written)} (run sync once the cause is fixed)" if written else ""
        raise Refused(f"{type(e).__name__}: {e}{done}")
    return event


def main(argv=None):
    ap = Parser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("advance"); s.add_argument("feature"); s.add_argument("stage", type=int)
    s.add_argument("--gate", choices=["pass", "fail"]); s.add_argument("--note")
    s = sub.add_parser("round"); s.add_argument("feature"); s.add_argument("n", type=int)
    s.add_argument("result", choices=["pass", "fail"]); s.add_argument("reason"); s.add_argument("--commit")
    s = sub.add_parser("verified"); s.add_argument("feature"); s.add_argument("commit"); s.add_argument("tree")
    s = sub.add_parser("log"); s.add_argument("feature"); s.add_argument("text")
    s.add_argument("--type", choices=["note", "review_done"], default="note")
    s = sub.add_parser("deviation"); s.add_argument("feature"); s.add_argument("text")
    s = sub.add_parser("slice"); s.add_argument("feature")
    s.add_argument("action", choices=["start", "done", "block"]); s.add_argument("id")
    s.add_argument("commit", nargs="?", help="done: the slice's commit; block: the reason")
    s = sub.add_parser("blocker"); s.add_argument("feature"); s.add_argument("action", choices=["raise", "resolve"])
    s.add_argument("text")
    s = sub.add_parser("set"); s.add_argument("feature"); s.add_argument("field"); s.add_argument("value")
    s = sub.add_parser("sync"); s.add_argument("feature")
    for p in sub.choices.values():
        p.error = ap.error
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    a.root = os.path.abspath(a.root)
    try:
        event = run(a)
    except Refused as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1
    except Exception as e:  # never a traceback: a caller parses stdout
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "feature": a.feature, "event": event}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
