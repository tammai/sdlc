#!/usr/bin/env python3
"""sdlc trust anchor: changes to what verification trusts reach the user instead of happening silently.

The files the other hooks trust (state.md, spec.md, baseline.md, config.json) are writable by the agent they
check, so this can't prevent a change; it makes one visible. For each active feature, on Stop:
  - `Track:`, `Risk:`, `Flow:`, `Top model:` or `Base:` differs from the value first seen
  - `.sdlc/baseline.md` lists a failing test it didn't at the feature's `Base:` commit (it may only shrink)
  - the commands in `.sdlc/config.json` differ from those at `Base:`
  - `spec.md` changed after the feature entered Stage 5
  - the feature left Stage 5 while code differed from its last full test run, or moved past Stage 5 without it
    (a verifier dispatched in Stage 5 since the last Stop counts, since a turn can run several stages)
  - on `Flow: lite`, a Stop outside Stages 4-6 finds code that differs from the last full test run (one notice
    per set of changed files)
  - a feature seen active stopped being active, other than by finishing (`Status: done`)
A new notice blocks the stop once, with a systemMessage so the user sees it; it doesn't block again. The user's
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
# Base: the baseline and commands are compared at it. Flow: the Lite flow drops the top-tier review
FIELDS = ("Track", "Risk", "Flow", "Top model", "Base")


def field(text, name):
    # Same matching as the hooks that act on these fields (model_router: re.I); every line counts, not just the first
    found = re.findall(rf"^{name}:\s*(\S+)", text, re.M | re.I)
    return ",".join(found) if found else None


def stage(text):
    m = re.search(r"^Current:\s*Stage\s*(\d+)", text, re.M | re.I)
    return int(m.group(1)) if m else None


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


def check(root, name, text, anchor):
    """Notices for one feature; updates `anchor` with what was seen."""
    notices = []
    for f in FIELDS:
        now = field(text, f)
        first = anchor.setdefault("fields", {}).setdefault(f, now)
        if now != first:
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
    spec = read(os.path.join(root, sdlc_layout.features(root).get(name, {}).get("intents", ""), "spec.md"))
    digest = hashlib.sha256(spec.encode("utf-8")).hexdigest() if spec is not None else None
    if st is not None and st >= 5:
        first = anchor.setdefault("spec", digest)
        if digest != first:
            notices.append("spec.md changed after the feature entered Stage 5")
    prev = anchor.get("stage")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # the model router's dispatch-log format
    # Stops are samples: a Lite turn can run Stages 3 to 8 between two of them, so Stage 5 counts as passed when a
    # verifier was dispatched in it since the last Stop (the evidence the Stage 5 gate trusts)
    if prev is not None and prev < 5 < (st or 0) and not verifier_since(root, anchor.get("stop_time")):
        notices.append(f"went from Stage {prev} to Stage {st} without Stage 5")
    # The Lite flow re-verifies fixes in-session, so outside the build-verify-review loop (Stages 4-6) the code must
    # match the last full run: checked at every such Stop, since the move out of the loop may not be seen
    lite = re.search(r"^Flow:\s*lite\b", text, re.M | re.I)
    leaving_5 = prev == 5 and st is not None and st > 5
    if st is not None and prev is not None and (leaving_5 or lite and st not in (4, 5, 6)):
        changed = changed_since_full_run(root, name)
        anchor["untested_seen"] = changed
        if changed and changed != anchor.get("untested_ok"):
            where = f"left Stage 5 for Stage {st}" if leaving_5 else f"Stage {st}"  # stable text: seen once
            notices.append(f"{where} with code changed since the last full test run: " + ", ".join(changed[:5]))
    anchor["stage"] = st
    anchor["stop_time"] = now
    return notices


def verifier_since(root, since):
    try:
        with open(os.path.join(root, ".sdlc", ".work", "dispatches.jsonl"), encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return False
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if (isinstance(d, dict) and d.get("agent") == "sdlc:verifier" and not d.get("denied")
                and str(d.get("time", "")) >= (since or "")
                and any(re.match(r"Stage\s*5\b", str(s)) for s in d.get("stages") or [])):
            return True
    return False


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
    if "baseline_seen" in anchor:
        anchor["baseline_ok"] = anchor["baseline_seen"]
    if "commands_seen" in anchor:
        anchor["commands_ok"] = anchor["commands_seen"]
    if "spec_seen" in anchor:
        anchor["spec"] = anchor["spec_seen"]
    if "untested_seen" in anchor:
        anchor["untested_ok"] = anchor["untested_seen"]
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
        if status == "active":
            features[name] = text
        elif was.get("status") == "active":
            # Leaving active switches the model router and freshness hook off for it, so it's shown; finishing
            # is the one normal way out, from Stage 8 on
            if status != "done" or (was.get("stage") or 0) < 8:
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
        new = list(left)
        for name, text in features.items():
            anchor = saved.setdefault(name, {})
            anchor["status"] = "active"
            notices = check(root, name, text, anchor)
            anchor["fields_seen"] = {f: field(text, f) for f in FIELDS}
            spec = read(os.path.join(root, located[name]["intents"], "spec.md"))
            anchor["spec_seen"] = hashlib.sha256(spec.encode("utf-8")).hexdigest() if spec is not None else None
            fresh = [n for n in notices if n not in anchor.get("notices", [])]
            anchor["notices"] = notices
            new += [f"{name}: {n}" for n in fresh]
        if corrupt:
            new.append("the trust anchor's own record (.sdlc/.work/trust-anchor.json) was damaged and was reset")
        if new:
            msg = "Verification anchors changed: " + "; ".join(new) + "."
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
