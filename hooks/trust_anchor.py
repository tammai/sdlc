#!/usr/bin/env python3
"""sdlc trust anchor: changes to what verification trusts reach the user instead of happening silently.

The files the other hooks trust (state.md, spec.md, baseline.md, config.json) are writable by the agent they
check, so this can't prevent a change; it makes one visible. For each active feature, on Stop:
  - `Track:`, `Risk:`, `Flow:`, `Top model:` or `Base:` differs from the value first seen, unless the change only
    makes the process stricter (Track up, Risk low → high, Flow lite → full): that becomes the new anchor and is
    shown to the user without blocking, since they approved it already (it can switch off the Lite-only check);
    a backlog feature leaving Lite still blocks
  - `.sdlc/baseline.md` lists a failing test it didn't at the feature's `Base:` commit (it may only shrink)
  - the commands in `.sdlc/config.json` differ from those at `Base:`
  - `spec.md` changed after the feature entered Stage 5, or, on S (no spec), the state file's `Repro:` line
  - the feature left Stage 5 while code differed from its last full test run, or moved past Stage 5 without it
    (a verifier dispatched in Stage 5 since the last Stop counts, since a turn can run several stages; so does an
    ac-checker on a passing full run of the current code, and that passing run alone on S, M with `Flow: lite`
    or `Prove: skip`, which have no Prove)
  - verify.py's record of its last run differs from the freshness hook's own copy (a hand-edited record)
  - on `Flow: lite`, a Stop outside Stages 4-6 finds code that differs from the last full test run (one notice
    per untested state of the code)
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
FIELDS = ("Track", "Risk", "Flow", "Top model", "Base", "Prove")
# Ordered weakest first: a move up one of these only adds checks, so it needs no second word from the user
STRICTER = {"Track": ("s", "m", "l"), "Risk": ("low", "high"), "Flow": ("lite", "full"), "Prove": ("skip", "run")}


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
    # A backlog stays on Lite, and an autopilot slice session has no one to read a non-blocking message
    backlog = os.path.isfile(os.path.join(intents, "backlog.md"))
    for f in FIELDS:
        now = field(text, f)
        first = anchor.setdefault("fields", {}).setdefault(f, now)
        if now != first and stricter(f, first, now) and not (backlog and f == "Flow"):
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
    spec = read(os.path.join(root, sdlc_layout.features(root).get(name, {}).get("intents", ""), "spec.md"))
    digest = hashlib.sha256(spec.encode("utf-8")).hexdigest() if spec is not None else None
    if st is not None and st >= 5:
        first = anchor.setdefault("spec", digest)
        if digest != first:
            notices.append("spec.md changed after the feature entered Stage 5")
        # S has no spec.md: its one acceptance criterion is the state file's Repro line
        repro = "\n".join(re.findall(r"^Repro:.*$", text, re.M)) or None  # the whole line: field() keeps one word
        if anchor.setdefault("repro", repro) != repro:
            notices.append("Repro changed after the feature entered Stage 5")
    prev = anchor.get("stage")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # the model router's dispatch-log format
    # Stops are samples: a Lite turn can run Stages 3 to 8 between two of them, so Stage 5 counts as passed when a
    # verifier was dispatched in it since the last Stop (the evidence the Stage 5 gate trusts), or an ac-checker was
    # and the last full run (verify) passed on the current code (ADR 0013)
    # S and M lite have no Prove (Build's passing verify.py is their evidence), so their passing run counts on its own
    s_track = re.search(r"^Track:\s*s\b", text, re.M | re.I)
    m_lite = re.search(r"^Track:\s*m\b", text, re.M | re.I) and re.search(r"^Flow:\s*lite\b", text, re.M | re.I)
    skipped = re.search(r"^Prove:\s*skip\b", text, re.M | re.I)  # the user chose it before Build
    since = anchor.get("stop_time")
    if (prev is not None and prev < 5 < (st or 0) and not dispatched_since(root, since, "sdlc:verifier")
            and not ((s_track or m_lite or skipped or dispatched_since(root, since, "sdlc:ac-checker"))
                     and suite_passed(root, name))):
        notices.append(f"went from Stage {prev} to Stage {st} without Stage 5")
    # The Lite flow re-verifies fixes in-session, so outside the build-verify-review loop (Stages 4-6) the code must
    # match the last full run: checked at every such Stop, since the move out of the loop may not be seen
    lite = re.search(r"^Flow:\s*lite\b", text, re.M | re.I)
    leaving_5 = prev == 5 and st is not None and st > 5
    if st is not None and prev is not None and (leaving_5 or lite and st not in (4, 5, 6)):
        changed = changed_since_full_run(root, name)
        # Accepting covers this exact code, not these file names: new untested code in the same files is new
        anchor["untested_seen"] = vf.worktree_tree(root) if changed else None
        if changed and anchor["untested_seen"] != anchor.get("untested_ok"):
            where = f"left Stage 5 for Stage {st}" if leaving_5 else f"Stage {st}"  # stable text: seen once
            notices.append(f"{where} with code changed since the last full test run: " + ", ".join(changed[:5]))
    disagree = verify_records_disagree(root, name)
    if disagree:
        notices.append(f"verify records disagree: {disagree}")
    anchor["stage"] = st
    anchor["stop_time"] = now
    return notices


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


def dispatched_since(root, since, agent):
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
        if (isinstance(d, dict) and d.get("agent") == agent and not d.get("denied")
                and str(d.get("time", "")) >= (since or "")
                and any(re.match(r"Stage\s*5\b", str(s)) for s in d.get("stages") or [])):
            return True
    return False


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
        new, shown = list(left), []
        for name, text in features.items():
            anchor = saved.setdefault(name, {})
            anchor["status"] = "active"
            stricter_now = []
            notices = check(root, name, text, anchor, stricter_now)
            shown += [f"{name}: {n}" for n in stricter_now]
            anchor["fields_seen"] = {f: field(text, f) for f in FIELDS}
            spec = read(os.path.join(root, located[name]["intents"], "spec.md"))
            anchor["spec_seen"] = hashlib.sha256(spec.encode("utf-8")).hexdigest() if spec is not None else None
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
