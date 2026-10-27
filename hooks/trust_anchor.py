#!/usr/bin/env python3
"""sdlc trust anchor: changes to what verification trusts reach the user instead of happening silently.

The files the other hooks trust (state.md, spec.md, baseline.md, config.json) are writable by the agent they
check, so this can't prevent a change; it makes one visible. For each active feature, on Stop:
  - `Track:`, `Risk:`, `Top model:`, `Base:` or `Process:` differs from the value first seen, unless the change only
    makes the process stricter (Track up, Risk low → high): that becomes the new anchor and is shown to the user
    without blocking, since they approved it already
  - `.sdlc/baseline.md` lists a failing test it didn't at the feature's `Base:` commit (it may only shrink)
  - the commands in `.sdlc/config.json` differ from those at `Base:`
  - `spec.md` changed after the feature entered Review (Stage 5)
  - the feature left Review while code differed from its last full test run, or moved past Review without a
    passing full run of the current code, at every size (sdlc 2.0: that run is Review's evidence)
  - leaving Review while the latest round of a review's report says `VERDICT: FAIL`, unless the user waived it
  - verify.py's record of its last run differs from the freshness hook's own copy (a hand-edited record)
  - a feature seen active stopped being active, other than by finishing (`Status: done`)
Only 2.0 features (`Process: 2`) are anchored; a 1.x one is finished on 1.8.1, and a 2.0 one whose `Process:`
line changes keeps its anchor, so the change is a notice. A new notice blocks the stop once, with a systemMessage so the user sees it; it doesn't block again. The user's
next prompt accepts it: the current values become the new anchor. Only a prompt clears a notice, because only
the user can send one. A damaged record is a notice too; a deleted one can't be told from a first run (Known
gaps in spec 02). State: .sdlc/.work/trust-anchor.json. Any error: no output.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

import sdlc_layout  # sibling module: where feature state and sdlc documents live
import verify_freshness as vf  # sibling hook: project root, git, worktree trees, freshness state

STATE = os.path.join(".sdlc", ".work", "trust-anchor.json")
# Base: the baseline and commands are compared at it. Process: 2 marks a 2.0 feature, the only kind the hooks act on
FIELDS = ("Track", "Risk", "Top model", "Base", "Process")
# Ordered weakest first: a move up one of these only adds checks, so it needs no second word from the user
STRICTER = {"Track": ("s", "m", "l"), "Risk": ("low", "high")}


def field(text, name):
    # Same matching as the hooks that act on these fields (model_router: re.I); every line counts, not just the first
    found = re.findall(rf"^{name}:\s*(\S+)", text, re.M | re.I)
    return ",".join(found) if found else None


def stage(text):
    m = re.search(r"^Current:\s*Stage\s*(\d+)", text, re.M | re.I)
    return int(m.group(1)) if m else None


def stricter(name, before, after):
    order = STRICTER.get(name, ())
    before, after = (before or "").lower(), (after or "").lower()
    return before in order and after in order and order.index(after) > order.index(before)


def baseline_failures(text):
    """The failing tests the baseline lists, as `package | test` keys (swapping one for another still shows)."""
    m = re.search(r"^##\s+Failing tests\s*$(.*?)(?=^##\s|\Z)", text or "", re.M | re.S)
    rows = [l for l in (m.group(1) if m else "").splitlines() if l.startswith("|") and not l.startswith("|---")]
    keys = [" | ".join(c.strip() for c in row.strip("|").split("|")[:2]) for row in rows[1:]]  # minus the header
    return sorted(set(keys))


def commands(text):
    try:
        cfg = json.loads(text or "{}")
    except ValueError:
        return None
    # docs_dir too: the freshness hook and the role guard treat that folder as non-code
    return json.dumps({"commands": cfg.get("commands"), "packages": cfg.get("packages"),
                       "docs_dir": cfg.get("docs_dir")}, sort_keys=True)


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def check(root, name, text, anchor, shown):
    """Notices for one feature; stricter field changes go to `shown`; updates `anchor` with what was seen."""
    notices = []
    intents = os.path.join(root, sdlc_layout.features(root).get(name, {}).get("intents", ""))
    for f in FIELDS:
        now = field(text, f)
        first = anchor.setdefault("fields", {}).setdefault(f, now)
        if now != first and stricter(f, first, now):
            anchor["fields"][f] = now  # the new anchor, so moving back down is still a notice
            shown.append(f"{f}: {first} → {now}")
        elif now != first:
            notices.append(f"{f}: {first} → {now}")
    base = vf.feature_base(root, name)
    if base:
        at_base = vf.git(root, "show", f"{base}:.sdlc/baseline.md")
        now = baseline_failures(read(os.path.join(root, ".sdlc", "baseline.md")))
        if at_base is not None:
            added = sorted(set(now) - set(anchor.get("baseline_ok", baseline_failures(at_base))))
            if added:
                notices.append(f"baseline.md lists failing tests it didn't at Base: {', '.join(added[:5])}")
        anchor["baseline_seen"] = now
        cmds_base = commands(vf.git(root, "show", f"{base}:.sdlc/config.json"))
        cmds_now = commands(read(os.path.join(root, ".sdlc", "config.json")))
        if cmds_base and cmds_now != anchor.get("commands_ok", cmds_base):
            notices.append("the commands or docs_dir in .sdlc/config.json differ from Base")
        anchor["commands_seen"] = cmds_now
    st = stage(text)
    spec = read(os.path.join(intents, "spec.md"))
    digest = hashlib.sha256(spec.encode("utf-8")).hexdigest() if spec is not None else None
    anchor["spec_seen"] = digest
    if st is not None and st >= 5:
        first = anchor.setdefault("spec", digest)
        if digest != first:
            notices.append("spec.md changed after the feature entered Stage 5")
    prev = anchor.get("stage")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Stops are samples: a turn can run Build, Review and Ship between two of them, so passing Review is judged by
    # its evidence, a passing full run of the current code, at every size (sdlc 2.0 has no verifier round)
    if prev is not None and prev < 5 < (st or 0) and not suite_passed(root, name):
        notices.append(f"went from Stage {prev} to Stage {st} without Stage 5")
    leaving_5 = prev == 5 and st is not None and st > 5
    if leaving_5:
        changed = changed_since_full_run(root, name)
        # Accepting covers this exact code, not these file names: new untested code in the same files is new
        anchor["untested_seen"] = vf.worktree_tree(root) if changed else None
        if changed and anchor["untested_seen"] != anchor.get("untested_ok"):
            notices.append(f"left Stage 5 for Stage {st} with code changed since the last full test run: "
                           + ", ".join(changed[:5]))
    # A review's report decides its findings: leaving Review needs the latest round's VERDICT lines to pass
    if prev is not None and st is not None and prev <= 5 < st:
        failed = failed_verdicts(root, name)
        if failed and not waived(text, failed):
            notices.append("left Stage 5 while a review's verdict is FAIL: " + ", ".join(failed))
    disagree = verify_records_disagree(root, name)
    if disagree:
        notices.append(f"verify records disagree: {disagree}")
    anchor["stage"] = st
    anchor["stop_time"] = now
    return notices


# The reviews' reports (review.md); the folder also holds the diff facts and explorer reports, with no VERDICT
CHECKER_REPORT = r"(?:code-reviewer|security|ui-reviewer|qa-tester|pr-test-analyzer)-r\d+\.md"


def failed_verdicts(root, name):
    """Review reports of the latest round in .sdlc/.work/findings/<feature>/ whose VERDICT isn't PASS.
    No reports (the in-session flow passes results back as text): nothing to check."""
    folder = os.path.join(root, ".sdlc", ".work", "findings", name)
    try:
        files = [f for f in os.listdir(folder) if re.fullmatch(CHECKER_REPORT, f)]
    except OSError:
        return []
    if not files:
        return []
    rounds = {f: int(re.search(r"-r(\d+)\.md$", f).group(1)) for f in files}
    latest = max(rounds.values())
    failed = []
    for f in sorted(files):
        if rounds[f] != latest:
            continue
        verdicts = re.findall(r"^\W*verdict:\W*(pass|fail)\b", read(os.path.join(folder, f)) or "", re.M | re.I)
        if not verdicts or verdicts[-1].lower() != "pass":
            failed.append(f)
    return failed


def waived(text, failed):
    """The user waived the round these failed reports belong to: a `waived round <N>` deviation (review.md)."""
    n = int(re.search(r"-r(\d+)\.md$", failed[0]).group(1))
    return bool(re.search(rf"^- .*\bwaived round {n}\b", text, re.M | re.I))


def verify_records_disagree(root, name):
    """verify.py's record of its last run against the freshness hook's own copy: a hand-edited, malformed or deleted
    record shows here (both files are agent-writable, so nothing in them is trusted to be well-formed)."""
    def obj(x):
        return x if isinstance(x, dict) else {}
    hook = obj(vf.load(root))
    b = obj(obj(hook.get("verify")).get("last")) if hook.get("feature") == name else {}
    if not b:
        return None
    try:
        with open(os.path.join(root, ".sdlc", ".work", "verify.json"), encoding="utf-8") as f:
            script = json.load(f)
    except (OSError, ValueError):
        script = None
    if not isinstance(script, dict) or script.get("feature") != name or not isinstance(script.get("last"), dict):
        return f"the hook saw a verify run ({b.get('result')}), but verify.json has no record of it"
    a = script["last"]
    if (a.get("tree"), a.get("result")) != (b.get("tree"), b.get("result")):
        return f"verify.json says {a.get('result')}, the hook saw {b.get('result')} (tree {str(b.get('tree'))[:12]})"
    return None


def suite_passed(root, name):
    """A full test run of this feature passed and the code hasn't changed since."""
    fresh = vf.load(root)
    scopes = (fresh.get("scopes") or {}).values() if fresh.get("feature") == name else []
    return (bool(scopes) and all(not s.get("stale") and s.get("last_result") != "fail" for s in scopes)
            and not changed_since_full_run(root, name))


def changed_since_full_run(root, name):
    fresh = vf.load(root)
    if fresh.get("feature") != name:
        return []
    new_tree = vf.worktree_tree(root)
    changed = set()
    for s in (fresh.get("scopes") or {}).values():
        if s.get("stale"):
            changed.add(s.get("last_edit_file") or "(stale)")
        elif s.get("tree") and new_tree:
            changed.update(vf.changed_code_files(root, s["tree"], new_tree) or [])
    return sorted(changed)


def accept(anchor):
    """The user has seen the notices: what they flagged becomes the new anchor."""
    anchor["fields"] = anchor.get("fields_seen", anchor.get("fields", {}))
    for seen, ok in (("baseline_seen", "baseline_ok"), ("commands_seen", "commands_ok"), ("spec_seen", "spec"),
                     ("untested_seen", "untested_ok")):
        if seen in anchor:
            anchor[ok] = anchor[seen]
    anchor["notices"] = []


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name")
    root = vf.project_root(data.get("cwd"))
    if not root or event not in ("Stop", "UserPromptSubmit"):
        return
    path = os.path.join(root, STATE)
    corrupt = False
    try:
        saved = json.load(open(path, encoding="utf-8"))
        corrupt = not isinstance(saved, dict)
    except OSError:
        saved = {}
    except ValueError:
        corrupt = True
    if corrupt:  # its own record was damaged: start over, but say so
        saved = {}
    features, left = {}, []
    seen = set()
    located = sdlc_layout.features(root)
    for name, f in located.items():
        text = read(os.path.join(root, f["state"])) or ""
        seen.add(name)
        status = (field(text, "Status") or "").lower()
        was = saved.get(name, {})
        if status == "active" and (re.search(r"^Process:\s*2\b", text, re.M) or was.get("status") == "active"):
            features[name] = text  # a 2.0 feature, or one already anchored (so a changed Process: line shows)
        elif was.get("status") == "active":
            # Leaving active switches the model router and freshness hook off for it, so it's shown; finishing
            # is the one normal way out, from Stage 8 on (Ship can reach 8 and finish between two Stops)
            if status != "done" or max(stage(text) or 0, was.get("stage") or 0) < 8:
                left.append(f"{name}: Status: active → {status or 'missing'} at Stage {was.get('stage')}")
            was["status"] = status
    for name, was in saved.items():
        if was.get("status") == "active" and name not in seen:
            left.append(f"{name}: its state.md was removed while active")
            was["status"] = "removed"
    if event == "UserPromptSubmit":
        for anchor in saved.values():
            if anchor.get("notices"):
                accept(anchor)
    else:
        new, shown = list(left), []
        for name, text in features.items():
            anchor = saved.setdefault(name, {})
            anchor["status"] = "active"
            stricter_now = []
            notices = check(root, name, text, anchor, stricter_now)
            shown += [f"{name}: {n}" for n in stricter_now]
            anchor["fields_seen"] = {f: field(text, f) for f in FIELDS}
            fresh = [n for n in notices if n not in anchor.get("notices", [])]
            anchor["notices"] = notices
            new += [f"{name}: {n}" for n in fresh]
        if corrupt:
            new.append("the trust anchor's own record (.sdlc/.work/trust-anchor.json) was damaged and was reset")
        if shown and not new:
            print(json.dumps({"systemMessage": "Stricter process: " + "; ".join(shown) + "."}))
        if new:
            msg = "Verification anchors changed: " + "; ".join(new + shown) + "."
            if data.get("stop_hook_active"):
                print(json.dumps({"systemMessage": "⚠ " + msg}))
            else:
                print(json.dumps({"decision": "block", "systemMessage": "⚠ " + msg + " Your next message accepts it.",
                                  "reason": msg + " Tell the user, in your reply, what changed and why; don't undo "
                                  "or redo it on your own. Their next message accepts it."}))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        main()
    except Exception:
        pass
    sys.exit(0)
