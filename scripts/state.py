#!/usr/bin/env python3
"""sdlc state: every change to a feature's state in one call, so state.md and the control contract can't disagree.

state.md stays the model's view and the committed record; the hooks read it (`Current: Stage <n> – <name>`,
`Status:`, `Process:`, `Base:`). Each call also writes the control contract, git-ignored runtime files a runner or a
control app reads without knowing the pipeline's internals (docs/specs/12-control-contract.md), beside the state
file and git-ignored (in either layout):
  .sdlc/state/<feature>.json            snapshot, derived from state.md (contract_version)
  .sdlc/state/<feature>.events.jsonl    one event per call, appended, never rewritten
  .sdlc/state/<feature>.commands/       the runner's inbox; never read or executed here
Advancing to the current stage is refused (it would tick the stage before its gate ran).
Usage: python3 state.py [--root DIR] advance FEATURE STAGE [--gate pass|fail] [--note TEXT] [--verified [COMMIT TREE]]
                                     verified FEATURE COMMIT TREE
                                     log FEATURE TEXT [--type note|review_done]
                                     deviation FEATURE TEXT
                                     slice FEATURE start|done|block B<n> [REASON]   (done: before the part's commit)
                                     blocker FEATURE raise|resolve TEXT
                                     set FEATURE FIELD VALUE
                                     repo FEATURE NAME  (workbench: branch a writable repo from its default branch,
                                         or record a read-only repo's commit, under ## Repos; refused when dirty)
                                     pr FEATURE NAME URL  (workbench: a repo's PR under ## PRs; ship.py --status reads it)
                                     sync FEATURE
                                     new FEATURE --track S|M|L --risk low|high --task "<title> | <ACs> | <files>" ...
                                         [--criteria ID ...]   (the slice's criteria from a spec lock: Slice criteria:)
                                     lock FEATURE FILE SHA256 ...   (verify.py red: ## Test lock, first hash kept)
                                     cite FEATURE ID ...      (Define: each cited criterion's lock hash, ## Criteria)
                                     question FEATURE ID TEXT (a spec question: a finding file, the part blocked)
                                     questions FEATURE        (resolves each question whose criterion the lock changed)
                                     migrate    (every `Process: 2` state file to this version's stage numbers)
Everything is computed before anything is written; then a spec question's finding file, backlog.md, state.md,
state.json and the event are written in that order, each file atomically (a finding nothing came to name is removed
again), and last an answered question's file moves to spec-questions/resolved/. Prints one JSON object. Exit 0 ok, 1 refused (unknown feature,
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
import spec_lock  # noqa: E402  (sibling script: the criteria an rspec spec locked)

CONTRACT_VERSION = 3
# Four phases, one stage number each (sdlc 3.0; 2.x used 1, 4, 5 and 8). A backlog slice rests at Build with its row
# `done`; feature close goes on to Review.
STAGES = {sdlc_layout.DEFINE: "Define", sdlc_layout.BUILD: "Build", sdlc_layout.REVIEW: "Review",
          sdlc_layout.SHIP: "Ship"}
PHASES = {n: name.lower() for n, name in STAGES.items()}
V2_STAGES = {1: sdlc_layout.DEFINE, 4: sdlc_layout.BUILD, 5: sdlc_layout.REVIEW, 8: sdlc_layout.SHIP}  # 2.x -> now
FIELDS = ("Status", "Track", "Risk", "Top model", "Base", "Owner", "Tool", "Slice gates", "Process")


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


def is_placeholder(item):
    """The template's own example line, "(oldest first: …)". Real items may start with "(" too: they stay."""
    return item.startswith("(oldest first")


def section_items(text, heading):
    lines = text.split("\n")
    span = section(lines, heading)
    if not span:
        return []
    return [l[2:].strip() for l in lines[span[0]:span[1]]
            if l.startswith("- ") and l[2:].strip() and not is_placeholder(l[2:].strip())]


LOCK_LINE = re.compile(r"^- `([^`]+)` sha256:([0-9a-f]{64})\s*$")


def test_lock(text):
    """[(test file, sha256)] from `## Test lock` (spec 03 S4), in file order; [] without the section."""
    lines = text.replace("\r\n", "\n").split("\n")
    span = section(lines, "Test lock")
    return [m.groups() for m in (LOCK_LINE.match(l) for l in (lines[span[0]:span[1]] if span else ())) if m]


CRITERIA_LINE = re.compile(r"^- (F-[A-Z][A-Z0-9]*-[0-9]+\.AC[0-9]+) sha256:([0-9a-f]{64})\s*$")
QUESTION_LINE = re.compile(r"^- (SQ-\d{4}) (F-[A-Z][A-Z0-9]*-[0-9]+\.AC[0-9]+) sha256:([0-9a-f]{64}) (\S+)\s*$")
QUESTIONS = os.path.join(".sdlc", ".work", "spec-questions")


def section_lines(text, heading, pattern):
    lines = text.replace("\r\n", "\n").split("\n")
    span = section(lines, heading)
    return [m.groups() for m in (pattern.match(l) for l in (lines[span[0]:span[1]] if span else ())) if m]


def question_line(qid, cid, sha, part):
    return f"- {qid} {cid} sha256:{sha} {part}"


def criteria_hashes(text):
    """{criterion ID: the lock's text_sha256 recorded at Define} from `## Criteria` (spec 03 S2)."""
    return dict(section_lines(text, "Criteria", CRITERIA_LINE))


def set_section(text, heading, body):
    """`## heading` holding exactly `body` (lines), added before Gate log when missing; an empty body drops it."""
    lines = text.split("\n")
    span = section(lines, heading)
    if span:
        start = span[0] - 1
        lines[start:span[1]] = ([f"## {heading}"] + body + [""]) if body else []
        return with_newline("\n".join(lines))
    if not body:
        return text
    block = f"## {heading}\n" + "\n".join(body) + "\n\n"
    if re.search(r"^## Gate log$", text, re.M):
        return re.sub(r"^## Gate log$", lambda m: block + m.group(0), text, count=1, flags=re.M)
    return text.rstrip("\n") + "\n\n" + block


def append_to_section(text, heading, item):
    lines = text.split("\n")
    span = section(lines, heading)
    if not span:  # a section the template has but this file lost: add it at the end
        return text.rstrip("\n") + f"\n\n## {heading}\n- {item}\n"
    start, end = span
    # Drop blanks, the empty "-" and the template's example lines ("- (oldest first …)", "- <date> Stage n: …")
    body = [l for l in lines[start:end] if l.strip() and l.strip() != "-"
            and not (l.startswith("- ") and is_placeholder(l[2:].strip()))
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
    if not sdlc_layout.PROCESS_RE.search(text):
        if re.search(r"^Process:\s*2\b", text, re.M):
            raise Refused("started under sdlc 2.x (`Process: 2`, stages 1, 4, 5, 8): run `/sdlc:upgrade`, or "
                          "`python3 state.py migrate`, to renumber it")
        raise Refused("started under sdlc 1.x (no `Process: 3`): finish it with sdlc 1.8.1, or archive it")
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


def backlog_status(raw, slice_id):
    """The slice's Status cell as written (backlog.slices lowercases it), or None."""
    cols = None
    for line in (raw or "").split("\n"):
        stripped = line.strip().rstrip("\r")
        if not stripped.startswith("|"):
            continue
        cells = backlog.cells(stripped)
        if cols is None:
            names = [c.lower() for c in cells]
            if {"id", "status"} <= set(names):
                cols = (names.index("id"), names.index("status"))
            continue
        if len(cells) > max(cols) and re.sub(r"[*_`~\s]", "", cells[cols[0]]).upper() == slice_id:
            return cells[cols[1]]
    return None


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
        if a.verified:  # a phase's end records its passing verify in the same call
            text = set_line(text, "Verified", f"{a.verified[0]} tree {a.verified[1]}")
        if a.gate:
            text = append_to_section(text, "Gate log", f"{today()} Stage {stage}: {a.gate}"
                                     + (f" — {a.note}" if a.note else ""))
            if a.gate == "pass":
                text = tick(text, stage)
        text = re.sub(r"^Current:.*$", lambda _: f"Current: Stage {a.stage} – {STAGES[a.stage]}", text, count=1,
                      flags=re.M)
        return text, None, {"type": "stage_entered", "from": stage, "stage": a.stage, "gate": a.gate,
                            "note": a.note, **({"commit": a.verified[0], "tree": a.verified[1]} if a.verified else {})}
    if a.cmd == "verified":
        return set_line(text, "Verified", f"{a.commit} tree {a.tree}"), None, {
            "type": "verified", "commit": a.commit, "tree": a.tree}
    if a.cmd == "log":
        return append_to_section(text, "Gate log", f"{today()} {a.text}"), None, {"type": a.type, "text": a.text}
    if a.cmd == "lock":  # spec 03 S4: the hash of each test file a red run recorded failing
        pairs = list(zip(a.entries[::2], a.entries[1::2]))
        if len(a.entries) % 2 or not pairs or not all(re.fullmatch(r"[0-9a-f]{64}", sha) for _, sha in pairs):
            raise Refused("lock takes <file> <sha256> pairs")
        if any(re.search(r"[`\r\n]", f) or not f.strip() for f, _ in pairs):
            raise Refused("a locked file name can't hold a backtick or a line break")
        locked = dict(test_lock(text))
        for f, sha in pairs:  # the first red run's hash stays: a later one can't re-lock a weakened test
            locked.setdefault(f, sha)
        body = [f"- `{f}` sha256:{sha}" for f, sha in sorted(locked.items())]
        lines = text.split("\n")
        span = section(lines, "Test lock")
        if span:
            lines[span[0]:span[1]] = body + [""]
            text = "\n".join(lines)
        else:  # before Gate log, with the plan's sections
            text = re.sub(r"^## Gate log$", lambda m: "## Test lock\n" + "\n".join(body) + "\n\n" + m.group(0),
                          text, count=1, flags=re.M) if re.search(r"^## Gate log$", text, re.M) else \
                text.rstrip("\n") + "\n\n## Test lock\n" + "\n".join(body) + "\n"
        return with_newline(text), None, {"type": "tests_locked", "files": [f for f, _ in pairs]}
    if a.cmd == "cite":  # spec 03 S2: the lock's hash of each criterion the change cites, as Define saw it
        locked, problems = spec_lock.load(a.root)
        unknown = [cid for cid in a.ids if cid not in locked]
        if unknown or not a.ids:
            raise Refused(f"not in the lock: {', '.join(unknown)}" + (f" ({'; '.join(problems)})" if problems else "")
                          if unknown else "cite needs criterion IDs")
        hashes = criteria_hashes(text)
        hashes.update({cid: locked[cid]["text_sha256"] for cid in a.ids})
        text = set_section(text, "Criteria", [f"- {cid} sha256:{sha}" for cid, sha in hashes.items()])
        return text, None, {"type": "criteria_cited", "criteria": a.ids}
    if a.cmd == "question":  # spec 03 S10: a cited criterion is ambiguous, wrong or untestable as written
        if not a.text.strip():
            raise Refused("a spec question needs its question")
        locked, problems = spec_lock.load(a.root)
        if a.criterion not in locked:
            raise Refused(f"{a.criterion}: {'; '.join(problems)}" if problems else
                          f"{a.criterion} is not in the lock: a standalone question goes to the user")
        open_qs = section_lines(text, "Spec questions", QUESTION_LINE)
        if any(q[1] == a.criterion for q in open_qs):
            raise Refused(f"{a.criterion} already has an open spec question: one amend answers both")
        folder = os.path.join(a.root, QUESTIONS)
        taken = [int(m.group(1)) for d in (folder, os.path.join(folder, "resolved")) if os.path.isdir(d)
                 for m in (re.fullmatch(rf"{re.escape(a.feature)}-SQ-(\d{{4}})\.json", n) for n in os.listdir(d)) if m]
        qid = f"SQ-{max(taken, default=0) + 1:04d}"
        finding = {"id": qid, "source": "sdlc-question", "class": "spec-gap", "severity": "medium",
                   "criterion": a.criterion, "rule": None, "repro": None, "observed": None, "route": "rspec",
                   "question": a.text, "verified_by": {"agent": None, "result": "not run: spec question"}}
        part = (re.search(r"^Slice:\s*(B\d+)", text, re.M) or [None, None])[1]
        row = next((r for r in backlog.slices(backlog_raw) if r["id"] == part), None) if part and backlog_raw else None
        if not row or not row["status"].startswith(("in progress", "blocked")):
            part = None  # no part is running (the Slice: line names one already done): the question is a blocker
        reason = f"spec question {qid} on {a.criterion}"
        new_backlog = None
        if part:
            status = backlog_status(backlog_raw, part) or row["status"]
            new_backlog = set_backlog_status(backlog_raw, part, f"{status}; {reason}"
                                             if status.lower().startswith("blocked") else f"blocked: {reason}")
            text = append_to_section(text, "Open questions", f"{part} blocked: {reason}")
        else:
            text = append_to_section(text, "Open questions", f"{reason}: {a.text}")
        text = set_section(text, "Spec questions", [question_line(*q) for q in open_qs] +
                           [question_line(qid, a.criterion, locked[a.criterion]['text_sha256'], part or '-')])
        return text, new_backlog, {"type": "spec_question", "id": qid, "criterion": a.criterion, "part": part,
                                   "_write": {os.path.join(QUESTIONS, f"{a.feature}-{qid}.json"): finding}}
    if a.cmd == "questions":  # spec 03 S10: the part unblocks when the lock shows the criterion's new hash
        locked, _ = spec_lock.load(a.root)
        still, resolved, moves = [], [], []
        hashes = criteria_hashes(text)
        new_backlog = backlog_raw
        for qid, cid, sha, part in section_lines(text, "Spec questions", QUESTION_LINE):
            now = (locked.get(cid) or {}).get("text_sha256")
            if not now or now == sha:
                still.append((qid, cid, sha, part))
                continue
            resolved.append(qid)
            moves.append((os.path.join(QUESTIONS, f"{a.feature}-{qid}.json"),
                          os.path.join(QUESTIONS, "resolved", f"{a.feature}-{qid}.json")))
            if cid in hashes:
                hashes[cid] = now  # the amended text is the one the change now cites
            for item in section_items(text, "Open questions"):
                if f"spec question {qid} " in item + " ":
                    text = remove_from_section(text, "Open questions", item)[0]
        text = set_section(text, "Spec questions", [question_line(*q) for q in still])
        # A row blocked by a question no open line holds (answered, or its state write never landed) unblocks
        open_ids = {q[0] for q in still}
        for row in backlog.slices(new_backlog) if new_backlog else ():
            status = backlog_status(new_backlog, row["id"]) or ""
            if not status.lower().startswith("blocked") or ":" not in status:  # a hand-written block, no reasons
                continue
            reasons = [r.strip() for r in status.split(":", 1)[1].split(";") if r.strip()]
            rest = [r for r in reasons if not (re.match(r"spec question (SQ-\d{4}) ", r, re.I)
                                               and re.match(r"spec question (SQ-\d{4})", r, re.I).group(1).upper()
                                               not in open_ids)]
            if rest != reasons:
                new_backlog = set_backlog_status(new_backlog, row["id"], f"{status.split(':', 1)[0]}: "
                                                 + "; ".join(rest) if rest else "todo")
        # A file no open question names: answered with its move undone, or written by a run killed before its state
        # (the question was never asked): filed away either way, so nothing waits on it
        folder = os.path.join(a.root, QUESTIONS)
        for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else ():
            m = re.fullmatch(rf"{re.escape(a.feature)}-(SQ-\d{{4}})\.json", name)
            if m and m.group(1) not in open_ids and m.group(1) not in resolved:
                moves.append((os.path.join(QUESTIONS, name), os.path.join(QUESTIONS, "resolved", name)))
        if hashes:
            text = set_section(text, "Criteria", [f"- {cid} sha256:{h}" for cid, h in hashes.items()])
        return text, (new_backlog if new_backlog != backlog_raw else None), {
            "type": "spec_questions_checked", "resolved": resolved, "open": [q[0] for q in still], "_move": moves}
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
        # Run before the part's commit, so the row goes into that commit; a commit given (as before 2.4.3) is kept
        return text, set_backlog_status(backlog_raw, slice_id, f"done {a.commit}" if a.commit else "done"), {
            "type": "slice_done", "slice": slice_id, "commit": a.commit or None}
    if a.cmd == "blocker":
        if a.action == "raise":
            return append_to_section(text, "Open questions", a.text), None, {"type": "blocker_raised", "text": a.text}
        text, found = remove_from_section(text, "Open questions", a.text)
        if not found:
            raise Refused(f"no open question reads: {a.text}")
        return text, None, {"type": "blocker_resolved", "text": a.text}
    if a.cmd == "repo":
        return record_repo(a.root, a.name, text)
    if a.cmd == "pr":
        import sdlc_scopes  # noqa: PLC0415
        try:
            sdlc_scopes.pr_name(a.name)
            sdlc_scopes.check_pr_url(a.url)  # it reaches gh as an argument: never something read as an option
        except ValueError as e:
            raise Refused(str(e))
        prs = sdlc_scopes.feature_prs(text)
        prs[a.name] = a.url
        text = set_section(text, sdlc_scopes.PRS_HEADING, [f"- {n}: {u}" for n, u in prs.items()])
        return text, None, {"type": "pr_recorded", "repo": a.name, "url": a.url}
    if a.cmd == "set":
        if a.field not in FIELDS:
            raise Refused(f"set takes one of: {', '.join(FIELDS)}")
        text = set_slice_gates(text, a.value) if a.field == "Slice gates" else set_line(text, a.field, a.value)
        if a.field == "Status" and a.value == "done":
            return text, None, {"type": "feature_done"}
        return text, None, {"type": "field_set", "field": a.field, "value": a.value}
    return text, None, None  # sync


def git_run(cwd, *args):
    """(exit code, stdout, stderr) of one git command in cwd."""
    try:
        p = subprocess.run(["git", "-C", cwd, *args], capture_output=True, encoding="utf-8", errors="replace")
    except OSError as e:
        return 1, "", str(e)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def default_branch(repo):
    """The ref a feature branch starts from in a repo: its default branch (origin/HEAD's name, else main or master),
    origin's when it exists, else the local one; else None."""
    code, out, _ = git_run(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    names = [out.split("/", 1)[1]] if code == 0 and "/" in out else []
    for name in names + ["main", "master"]:
        for ref in (f"refs/remotes/origin/{name}", f"refs/heads/{name}"):  # origin's first: a local one can be stale
            if git_run(repo, "rev-parse", "--verify", "-q", ref + "^{commit}")[0] == 0:
                return ref
    return None


def record_repo(root, name, text):
    """`repo`: in a workbench, the first time Build touches a repo. A writable one gets the feature branch (the
    workbench's current branch name) from its default branch, and `## Repos` records branch and base; a read-only one
    records the commit read. Already recorded: unchanged. A dirty writable repo is refused, naming it."""
    import sdlc_scopes  # noqa: PLC0415
    if not sdlc_scopes.is_workbench(root):
        raise Refused("repo works in a workbench only (.sdlc/config.json `\"workbench\": true` and workbench.json)")
    try:
        sdlc_scopes.check_name(name)
        entry = next((r for r in sdlc_scopes.manifest(root) if r["name"] == name), None)
    except ValueError as e:
        raise Refused(str(e))
    if not entry:
        raise Refused(f"{name} isn't listed in workbench.json (scaffold.py workbench add)")
    if name in sdlc_scopes.feature_repos(text):
        return text, None, {"type": "repo_recorded", "repo": name, "already": True}
    try:
        repo = sdlc_scopes.repo_dir(root, name)
    except ValueError as e:
        raise Refused(str(e))
    if not os.path.exists(os.path.join(repo, ".git")):
        raise Refused(f"{name}/ isn't cloned: run scaffold.py workbench clone {name}")
    if not entry["write"]:
        code, head, err = git_run(repo, "rev-parse", "HEAD")
        if code:
            raise Refused(f"{name}: no commit to record ({err})")
        line = sdlc_scopes.repo_line(name, read=head)
        return append_to_section(text, sdlc_scopes.REPOS_HEADING, line), None, {
            "type": "repo_recorded", "repo": name, "read": head}
    code, dirty, err = git_run(repo, "status", "--porcelain")
    if code:
        raise Refused(f"{name}: git status failed ({err})")
    if dirty:
        raise Refused(f"{name} has uncommitted changes: commit or stash them in {name}/ before the feature branches "
                      "there")
    code, branch, _ = git_run(root, "rev-parse", "--abbrev-ref", "HEAD")
    if code or not branch or branch == "HEAD":
        raise Refused("the workbench isn't on a branch: check out the feature's branch there first")
    start = default_branch(repo)
    if not start:
        raise Refused(f"{name}: no default branch found (origin/HEAD, main or master)")
    own = default_branch(root)
    defaults = {start.rsplit("/", 1)[-1]} | ({own.rsplit("/", 1)[-1]} if own else set())
    if branch in defaults:
        raise Refused(f"the workbench is on {branch}, a default branch: the feature's branch is named after the "
                      "workbench's, so check out the feature's branch in the workbench first")
    base = git_run(repo, "rev-parse", start + "^{commit}")[1]
    if git_run(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}")[0] == 0:
        # Left by a run that branched but didn't get to record it: adopted when checked out and grown from the base
        current = git_run(repo, "branch", "--show-current")[1]
        if current != branch or git_run(repo, "merge-base", "--is-ancestor", base, branch)[0] != 0:
            raise Refused(f"{name} already has a branch {branch} that isn't checked out or doesn't start from {start}: "
                          f"check it out in {name}/ to use it, or rename it, then run this again")
    else:
        code, _, err = git_run(repo, "checkout", "-q", "--no-track", "-b", branch, start)
        if code:
            raise Refused(f"{name}: couldn't create branch {branch} ({err})")
    line = sdlc_scopes.repo_line(name, branch=branch, base=base)
    return append_to_section(text, sdlc_scopes.REPOS_HEADING, line), None, {
        "type": "repo_recorded", "repo": name, "branch": branch, "base": base}


def contract_paths(root, feature):
    """(state.json, events.jsonl) as `.sdlc/state/<f>.json` and `<f>.events.jsonl` in either layout, so one set of
    ignore patterns covers them and an old-layout feature folder holds only documents (relocate moves those)."""
    base = os.path.join(root, ".sdlc", "state", feature)
    return base + ".json", base + ".events.jsonl"


def read_raw(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def git_line(root, *args):
    try:
        out = subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def test_command(root):
    try:
        with open(os.path.join(root, ".sdlc", "config.json"), encoding="utf-8") as f:
            commands = json.load(f).get("commands") or {}
    except (OSError, ValueError, AttributeError):
        return ""
    return commands.get("test") or "" if isinstance(commands, dict) else ""


def task_lines(specs):
    """`--task "<title> | <ACs> | <files>"` → the numbered `## Tasks` entries (files space- or comma-separated)."""
    out = []
    for n, spec in enumerate(specs, 1):
        parts = [p.strip() for p in spec.split("|")]
        if len(parts) != 3 or not parts[0] or not parts[2]:
            raise Refused(f"--task is \"<title> | <ACs> | <files>\", not {spec!r}")
        title, acs, files = parts
        out.append(f"{n}. **{title}**" + (f" — {acs}" if acs else ""))
        out.append("   - Files: " + ", ".join(f"`{f}`" for f in re.split(r"[,\s]+", files) if f))
    return out


# `--surface "<kind> <name> — <AC>"`: what diff_stats' drift check reads (SURFACE_LINE), the name backticked
SURFACE = re.compile(r"^(export|endpoint|command|config|env|dependency)\s+`?([^`]+?)`?(?:\s+[\u2014\u2013-]\s+(\S.*))?$", re.I)


def surface_lines(specs):
    """`--surface` → the `## Public Surface` entries, refusing free text the drift check couldn't read."""
    out = []
    for spec in specs:
        m = SURFACE.match(spec.strip())
        if not m:
            raise Refused(f"--surface is \"<kind> <name> — <AC>\" with kind export, endpoint, command, config, env or "
                          f"dependency (e.g. \"export div — AC-001\"), not {spec!r}")
        out.append(f"- {m.group(1).lower()} `{m.group(2).strip()}`" + (f" \u2014 {m.group(3)}" if m.group(3) else ""))
    return out


def new_state(a):
    """The state file's text from Define's answers: the header lines (Base, Owner, the test command and the date looked
    up here) and the plan sections, so the agent writes only the change file."""
    paths = sdlc_layout.paths(a.root, a.feature)
    footprint = f"footprint: {a.footprint} files" if a.footprint is not None else "footprint: ? files"
    risk = f"Risk: {a.risk}" + (f"   ({a.risk_why})" if a.risk_why else "")
    tasks = task_lines(a.task)
    surface = surface_lines(a.surface) or ["- none"]
    head = [f"# {a.feature}", "Status: active", f"Process: {sdlc_layout.PROCESS}"]
    if a.criteria:  # spec 03 S2: the criteria assigned to this slice, each cited or set aside in ## Out of scope
        head.append("Slice criteria: " + " ".join(a.criteria))
    if a.track == "S":
        head += [f"Track: S   ({footprint})", risk, "Top model: opus",
                 f"Base: {git_line(a.root, 'rev-parse', '--short', 'HEAD')}",
                 f"Owner: {git_line(a.root, 'config', 'user.email')}", f"Tool: {a.tool}", "Current: Stage 1 – Define"]
        body = ["## Tasks", *tasks, "", "## Public Surface", *surface]
    else:
        test = test_command(a.root)
        head += [f"Change: {paths['change']}   (this feature's record for people)",
                 f"Track: {a.track}   (sized up because: {a.sized or '—'}; {footprint})", risk,
                 "Top model: opus   (fable only if the user chose it)",
                 f"Commands: test: `{test}`" if test else "Commands: test: (none recorded)",
                 f"Started: {datetime.now().strftime('%Y-%m-%d')}",
                 f"Base: {git_line(a.root, 'rev-parse', '--short', 'HEAD')}",
                 f"Owner: {git_line(a.root, 'config', 'user.email')}", f"Tool: {a.tool}",
                 "Current: Stage 1 – Define", "", "## Stages",
                 "- [ ] 1 Define   — the change file, the plan sections below", "- [ ] 2 Build",
                 "- [ ] 3 Review   — the change file's ## Review",
                 "- [ ] 4 Ship     — PR: (Learn: knowledge, recurring-defects.md)"]
        body = ["## How the build runs", a.build, "", "## Handoff", *([f"- {h}" for h in a.handoff] or ["-"]), "",
                "## Tasks", *tasks, "", "## Public Surface", *surface]
    tail = ["## Gate log", "- (oldest first: each new line goes at the bottom of this list)", "", "## Deviations", "-",
            "", "## Open questions", "-"]
    return paths["state"], "\n".join(head + [""] + body + [""] + tail) + "\n"


def create(a):
    import sdlc_scopes  # noqa: PLC0415
    workbench = sdlc_scopes.workbench_of(a.root)
    if workbench:  # an app repo of a workbench: its features are recorded once, in the workbench
        parent = os.path.dirname(a.root)
        where = f" ({parent})" if sdlc_scopes.is_workbench(parent) else ""
        raise Refused(f"{a.root} is an app repo of the workbench {workbench}: features live in the workbench, "
                      f"never in an app repo. Start it from the workbench{where} with /sdlc:start.")
    if not a.task:
        raise Refused("new needs at least one --task")
    bad = [c for c in a.criteria if not spec_lock.CRITERION_ID.fullmatch(c)]
    if bad:
        raise Refused(f"--criteria takes criterion IDs (F-ISS-01.AC2), not {', '.join(bad)}")
    for value in [a.feature, a.risk_why, a.sized, a.build, *a.task, *a.surface, *a.handoff]:
        if isinstance(value, str) and ("\n" in value or "\r" in value):
            raise Refused("values can't contain line breaks")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", a.feature):
        raise Refused("a feature name is lowercase letters, digits and dashes")
    if a.feature in sdlc_layout.features(a.root):
        raise Refused(f"{a.feature} already has a state file: pick another name (add -2) or resume it")
    rel, text = new_state(a)
    path = os.path.join(a.root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_atomic(path, text)
    a.cmd = "sync"  # the control contract, as every call writes it
    run(a)
    event = {"type": "feature_started", "state": rel}
    with open(contract_paths(a.root, a.feature)[1], "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "feature": a.feature,
                            **event}, ensure_ascii=False) + "\n")
    return event


def current_verified(root, feature):
    """[head, tree] of the passing verify run the code still matches (verify.py status), else Refused with why."""
    import verify  # noqa: PLC0415  (only this path needs it; it pulls in the whole verify plan)
    st = verify.status(root, feature)
    if not st["reuse"]:
        raise Refused(f"no current passing verify to record ({st['reason']}): run verify.py, or pass --verified <commit> <tree>")
    return [st["head"], st["tree"]]


def run(a):
    located =sdlc_layout.features(a.root).get(a.feature)
    if not located:
        raise Refused(f"no feature named {a.feature} (no state file for it)")
    for value in vars(a).values():  # a newline in a value would add lines (a fake Current:) to state.md
        if isinstance(value, str) and ("\n" in value or "\r" in value):
            raise Refused("values can't contain line breaks")
    path = os.path.join(a.root, located["state"])
    raw = read_raw(path)
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    backlog_path = os.path.join(a.root, located["work"], "backlog.md")  # before 2.0: the documents folder
    if not os.path.isfile(backlog_path):
        backlog_path = os.path.join(a.root, located["intents"], "backlog.md")
    backlog_raw = read_raw(backlog_path) if os.path.isfile(backlog_path) else None
    bom = backlog_raw is not None and backlog_raw.startswith("﻿")
    if bom:
        backlog_raw = backlog_raw[1:]
    if a.cmd == "advance" and a.verified == []:  # bare --verified: what verify.py recorded, not what the caller guesses
        a.verified = current_verified(a.root, a.feature)
    new, new_backlog, event = apply(a, text, backlog_raw)
    check(new)
    effects = {k: event.pop(k) for k in ("_write", "_move") if event and k in event}
    snap = snapshot(a.feature, new, new_backlog if new_backlog is not None else backlog_raw)
    snapshot_path, events_path = contract_paths(a.root, a.feature)
    written, findings = [], []
    try:
        for rel, data in effects.get("_write", {}).items():  # a spec question's finding, before the state naming it
            dest = os.path.join(a.root, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            write_atomic(dest, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            findings.append(dest)
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
        if not written:  # nothing names the finding: it goes, so no question waits unasked
            for path in findings:
                try:
                    os.remove(path)
                except OSError:
                    pass
        done = f"; already written: {', '.join(written)} (run sync once the cause is fixed)" if written else ""
        raise Refused(f"{type(e).__name__}: {e}{done}")
    try:  # answered questions' files, after the state that resolves them; one left behind is filed next time
        for src, dst in effects.get("_move", []):
            if os.path.exists(os.path.join(a.root, src)):
                os.makedirs(os.path.dirname(os.path.join(a.root, dst)), exist_ok=True)
                os.replace(os.path.join(a.root, src), os.path.join(a.root, dst))
    except OSError as e:
        raise Refused(f"state written, but an answered question's file wasn't filed away ({type(e).__name__}: {e});"
                      " the next `questions` run files it")
    return event


def migrate_text(text):
    """A `Process: 2` state file's text with sdlc 3.0's stage numbers (2.x used 1, 4, 5 and 8): the Current: line, the
    Stages checklist and the Gate log. Raises Refused on a stage number it has no mapping for."""
    def new(n):
        if int(n) not in V2_STAGES:
            raise Refused(f"Stage {n} has no sdlc 3.0 equivalent")
        return V2_STAGES[int(n)]

    text = re.sub(r"^Process:[ \t]*2\b", f"Process: {sdlc_layout.PROCESS}", text, count=1, flags=re.M)
    text = re.sub(r"^Current:[ \t]*Stage[ \t]*(\d+)\b[^\n]*$",
                  lambda m: f"Current: Stage {new(m.group(1))} – {STAGES[new(m.group(1))]}", text, count=1,
                  flags=re.M)
    lines = text.split("\n")
    for heading, pattern in (("Stages", r"^(- \[[ x]\] )(\d+)( )"), ("Gate log", r"^(- \S+ Stage )(\d+)(: )")):
        span = section(lines, heading)
        if span:
            for i in range(*span):
                lines[i] = re.sub(pattern, lambda m: f"{m.group(1)}{new(m.group(2))}{m.group(3)}", lines[i])
    return "\n".join(lines)


def migrate(root):
    """Renumber every `Process: 2` feature (any status) in place, and drop the trust anchor's remembered stage for it
    (a git-ignored runtime file), so no hook reads a stale number as a move. Skips a file it can't map and says why."""
    done, skipped = [], {}
    for name, located in sorted(sdlc_layout.features(root).items()):
        path = os.path.join(root, located["state"])
        try:
            raw = read_raw(path)
        except OSError as e:
            skipped[name] = f"unreadable: {e}"
            continue
        text = raw.replace("\r\n", "\n")
        if not re.search(r"^Process:[ \t]*2\b", text, re.M):
            continue
        try:
            new = migrate_text(text)
            write_atomic(path, new.replace("\n", "\r\n") if "\r\n" in raw else new)
            run(argparse.Namespace(root=root, feature=name, cmd="sync"))  # the contract snapshot, in the new numbers
        except (Refused, OSError) as e:
            skipped[name] = str(e)
            continue
        done.append(name)
    anchor = os.path.join(root, ".sdlc", ".work", "trust-anchor.json")
    try:
        with open(anchor, encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved, dict) and any(saved.pop(n, None) is not None for n in done):
            write_atomic(anchor, json.dumps(saved, indent=2))
    except (OSError, ValueError):
        pass
    return {"ok": True, "migrated": done, "skipped": skipped}


def main(argv=None):
    ap = Parser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("advance"); s.add_argument("feature"); s.add_argument("stage", type=int)
    s.add_argument("--gate", choices=["pass", "fail"]); s.add_argument("--note")
    s.add_argument("--verified", nargs="*", metavar="COMMIT TREE",
                   help="the commit and tree verify passed on; with neither, the last passing run's (verify.py status)")
    s = sub.add_parser("verified"); s.add_argument("feature"); s.add_argument("commit"); s.add_argument("tree")
    s = sub.add_parser("log"); s.add_argument("feature"); s.add_argument("text")
    s.add_argument("--type", choices=["note", "review_done"], default="note")
    s = sub.add_parser("deviation"); s.add_argument("feature"); s.add_argument("text")
    s = sub.add_parser("cite", help="record each cited criterion's lock hash under ## Criteria (Define)")
    s.add_argument("feature"); s.add_argument("ids", nargs="+")
    s = sub.add_parser("question", help="ask the spec's owner: a spec-gap finding, the running part blocked")
    s.add_argument("feature"); s.add_argument("criterion"); s.add_argument("text")
    s = sub.add_parser("questions", help="resolve each spec question whose criterion the lock has changed")
    s.add_argument("feature")
    s = sub.add_parser("lock", help="record test files' sha256 under ## Test lock (verify.py red does this)")
    s.add_argument("feature"); s.add_argument("entries", nargs="+", metavar="FILE SHA256")
    s = sub.add_parser("slice"); s.add_argument("feature")
    s.add_argument("action", choices=["start", "done", "block"]); s.add_argument("id")
    s.add_argument("commit", nargs="?", help="done: the slice's commit; block: the reason")
    s = sub.add_parser("blocker"); s.add_argument("feature"); s.add_argument("action", choices=["raise", "resolve"])
    s.add_argument("text")
    s = sub.add_parser("repo", help="workbench: branch a writable repo, or record a read-only one's commit")
    s.add_argument("feature"); s.add_argument("name")
    s = sub.add_parser("pr", help="workbench: record a repo's PR (the workbench itself: \"(workbench)\")")
    s.add_argument("feature"); s.add_argument("name"); s.add_argument("url")
    s = sub.add_parser("set"); s.add_argument("feature"); s.add_argument("field"); s.add_argument("value")
    s = sub.add_parser("sync"); s.add_argument("feature")
    sub.add_parser("migrate")
    s = sub.add_parser("new"); s.add_argument("feature")
    s.add_argument("--track", choices=["S", "M", "L"], required=True)
    s.add_argument("--risk", choices=["low", "high"], required=True); s.add_argument("--risk-why")
    s.add_argument("--sized", help="M/L: the signal that sized it up"); s.add_argument("--footprint", type=int)
    s.add_argument("--tool", default="claude-code")
    s.add_argument("--build", default="inline: this session builds it, one part")
    s.add_argument("--handoff", action="append", default=[])
    s.add_argument("--task", action="append", default=[], help='"<title> | <ACs> | <files>"')
    s.add_argument("--criteria", nargs="+", default=[], metavar="ID", help="the slice's criteria from a spec lock")
    s.add_argument("--surface", action="append", default=[], help='"<kind> <name> — <AC>", kind export|endpoint|command|config|env|dependency')
    for p in sub.choices.values():
        p.error = ap.error
    a = ap.parse_args(argv)
    if a.cmd == "advance" and a.verified is not None and len(a.verified) not in (0, 2):
        ap.error("--verified takes a commit and a tree, or neither")
    sys.stdout.reconfigure(encoding="utf-8")
    a.root = os.path.abspath(a.root)
    if a.cmd == "migrate":
        print(json.dumps(migrate(a.root), ensure_ascii=False))
        return 0
    try:
        event = create(a) if a.cmd == "new" else run(a)
    except Refused as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1
    except Exception as e:  # never a traceback: a caller parses stdout
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 1
    extra = {k: event[k] for k in ("resolved", "open")} if a.cmd == "questions" and event else {}
    print(json.dumps({"ok": True, "feature": a.feature, "event": event, **extra}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
