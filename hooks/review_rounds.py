#!/usr/bin/env python3
"""sdlc review rounds: one full review, its fixes, a closing check of them (more if config allows); then only the user decides.

A round is one set of review reports, `.sdlc/.work/findings/<feature>/<reviewer>-r<N>.md`: round 1 reviews the change
and its bugs are fixed test first, round 2 checks the fixes and fails only on a high. When an active feature's last round
(round 2 by default) still ends `VERDICT: FAIL` and the user hasn't waived it (`waived round <N>`), PreToolUse denies every edit, shell command,
subagent and skill, so the agent can only read and ask the user: one more round, waive, or stop. Writes to
`.sdlc/.work/findings/` stay open, so a round-3 reviewer still finishing its report isn't cut off, and so do the
project's test command and the plugin's verify.py, which change no code (the freshness hook asks for a run before
Review's turn ends).
The last round is config's `review_rounds` (2 to 5, default 2). It is a safety stop, so the agent's own edit to config
can only lower it. Each feature keeps a ceiling (`ceiling` in the store): it starts at the value committed at the
feature's Base, follows config down whenever config is lower, and goes up only when the user types
`/sdlc:setup review-rounds <n>`. The hook reads that number from the prompt itself and writes it into config, so it
needs no agent write the hook might deny while it holds the work.
That prompt sets the cap; it isn't also a grant. A grant allows rounds up to the one after the round it answered,
whatever the cap does later.
The user's reply grants one more round: their next prompt, or their answer to an AskUserQuestion headed `Review cap`
that user_answer.py saw asked without answers; nothing the agent writes can. The
highest round seen is kept in `.sdlc/.work/review-rounds.json`, so deleting a report doesn't reset the count.
Silent outside an active 2.0 feature; any error: no output.
"""
import json
import os
import re
import sys

import prove_budget as pb  # sibling hook: what counts as the project's own command
import sdlc_layout  # sibling module: where feature state and sdlc documents live
import trust_anchor  # sibling hook: the latest round's failed reports and the user's waiver
import user_answer  # sibling hook: an AskUserQuestion answer the user gave in the dialog
import verify_freshness as vf  # sibling hook: project root

CAP = 2  # default: the review, then the check of its fixes
MOST = 5  # beyond this the cap is no longer a stop
STATE = os.path.join(".sdlc", ".work", "review-rounds.json")
# The user's own command, as typed: /sdlc:setup, /setup, or a Codex skill's $sdlc-setup
SET = re.compile(r"\s*[/$](?:sdlc[:-])?setup\s+review-rounds\s+([0-9]{1,3})\s*$", re.I)
HEADER = "Review cap"  # the AskUserQuestion header whose answer grants a round
GUARDED = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "Monitor", "Agent", "Task", "Skill"}


def load(root):
    try:
        with open(os.path.join(root, STATE), encoding="utf-8") as f:
            saved = json.load(f)
        return saved if isinstance(saved, dict) else {}
    except (OSError, ValueError):
        return {}


def save(root, saved):
    path = os.path.join(root, STATE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2)


def configured(value):
    """A `review_rounds` value as a cap, or None unless it is a whole number from CAP to MOST (scaffold.py checks it too)."""
    return value if type(value) is int and CAP <= value <= MOST else None


def cap_in(text):
    """The cap a config.json text sets: CAP unless it is a JSON object whose `review_rounds` is valid."""
    try:
        data = json.loads(text) if text else {}
    except ValueError:
        return CAP
    return (configured(data.get("review_rounds")) if isinstance(data, dict) else None) or CAP


def user_set(prompt):
    """The cap a prompt sets (`/sdlc:setup review-rounds <n>`, n valid), else None."""
    m = SET.match(prompt or "")
    return configured(int(m.group(1))) if m else None


def record_in_config(root, n):
    """Write the cap the user typed into config, so it lasts past this feature, with scaffold.py's writer (atomic, since
    sibling hooks read config on the same event; never through a link out of the repo; mode kept; retried on Windows; its temp under
    .sdlc/.work/). False when it couldn't: config is left alone, and the ceiling then follows config's own value (held
    at 2 while config isn't a JSON object)."""
    import sdlc_scopes
    path = os.path.join(root, ".sdlc", "config.json")
    try:
        cfg = sdlc_scopes.read_repo_json(root, ".sdlc/config.json")  # refuses a link out of the repo: never written
        if not isinstance(cfg, dict):
            return False
        if configured(cfg.get("review_rounds")) == n:
            return True
        cfg["review_rounds"] = n
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
        import scaffold  # loaded only for the user's typed command
        scaffold.write_json(path, cfg, scratch=os.path.join(root, ".sdlc", ".work"))
        return True
    except Exception:  # unreadable, a refusal or a write that won't clear: config keeps its value
        return False


def at_base(root, name):
    """The cap config held at the feature's Base; the stricter CAP when git can't say."""
    base = vf.feature_base(root, name)
    try:  # ./ resolves from -C (the project root), which can sit below the git top level
        return cap_in(vf.git(root, "show", f"{base}:./.sdlc/config.json")) if base else CAP
    except Exception:  # a git timeout: the stricter cap, never no answer
        return CAP


def cap_for(root, name, rec, now):
    """The feature's cap: its ceiling, first the value at Base, lowered to config's value whenever that is lower.
    Only the user's typed number raises it (capped()). `now` None: config couldn't be read as an object this time, so
    this call holds at CAP without lowering the ceiling for good."""
    ceiling = configured(rec.get("ceiling"))
    if now is None:  # nothing stored from an unreadable config: Base is read once config reads again
        return CAP
    if ceiling is None:
        ceiling = CAP if now == CAP else at_base(root, name)  # the default needs no git call
    rec["ceiling"] = min(ceiling, now)
    return rec["ceiling"]


def latest_round(root, name):
    folder = os.path.join(root, ".sdlc", ".work", "findings", name)
    try:
        files = [f for f in os.listdir(folder) if re.fullmatch(trust_anchor.CHECKER_REPORT, f)]
    except OSError:
        return 0
    return max((int(re.search(r"-r(\d+)\.md$", f).group(1)) for f in files), default=0)


def runs_tests(root, command):
    """verify.py or the project's test command alone (Ship's call isn't one: it commits)."""
    import sdlc_scopes
    tests = [s["test"].strip() for s in sdlc_scopes.command_sets(root)
             if isinstance(s.get("test"), str) and s["test"].strip()]
    parts = [(step.strip(), sep) for step, sep in pb.split_top_level(command) or []]
    return pb.is_plugin_verify(command) or bool(tests) and not pb.is_ship_call(parts) and pb.is_project_command(command, tests)


def read_config(root):
    import sdlc_scopes  # a config linked out of the repo reads as absent
    return sdlc_scopes.read_repo_text(root, ".sdlc/config.json")


def config_cap(root):
    """config's cap now, or None when config can't be read as a JSON object (missing, mid-edit, not an object)."""
    text = read_config(root)
    try:
        return cap_in(text) if isinstance(json.loads(text or ""), dict) else None
    except ValueError:
        return None


def capped(root, saved, prompt=None):
    """{feature: round} for each active feature past its rounds, with a failing verdict the user hasn't waived. A
    prompt setting the cap records it for each active feature."""
    asked = user_set(prompt)
    if asked:
        saved["_unsaved"] = not record_in_config(root, asked)  # main() reports it and drops the key
        for rec in saved.values():  # paused features too: their ceiling is the user's number once they resume
            if isinstance(rec, dict):
                rec["ceiling"] = asked
    now = config_cap(root)  # after the write: a config that couldn't be written keeps the ceiling at its value
    out = {}
    for name, text in sdlc_layout.active(root):
        rec = saved.setdefault(name, {})
        if asked:
            rec["ceiling"] = asked
        rec["seen"] = max(int(rec.get("seen") or 0), latest_round(root, name))
        cap = cap_for(root, name, rec, now)  # every call, from round 0: a lower value is never missed
        if rec["seen"] < CAP:  # no cap can hold yet
            continue
        failed = trust_anchor.failed_verdicts(root, name)
        if "granted" in rec:  # a store from before `allowed`: its grants counted past round 2
            rec["allowed"] = max(int(rec.get("allowed") or 0), CAP + int(rec.pop("granted") or 0))
        # The user's grants allow rounds up to `allowed` whatever the cap does later; they never stack on it
        if rec["seen"] >= max(cap, int(rec.get("allowed") or 0)) and failed and not trust_anchor.waived(text, failed):
            out[name] = rec["seen"]
    return out


def say(text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}))


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name")
    root = vf.project_root(data.get("cwd"))
    if not root or event not in ("PreToolUse", "UserPromptSubmit", "PostToolUse"):
        return
    replied = event == "UserPromptSubmit" or bool(user_answer.answered(root, data, HEADER))
    if event == "PostToolUse" and not replied:
        return
    saved = load(root)
    before = json.dumps(saved, sort_keys=True)
    prompt = (data.get("prompt") or "") if event == "UserPromptSubmit" else None
    over = capped(root, saved, prompt)
    unsaved = saved.pop("_unsaved", False)
    typed = bool(prompt and SET.match(re.sub(r"[0-9]+", "0", prompt)))  # the command, whatever number it names
    if typed and not user_set(prompt):
        say(f"sdlc: review-rounds takes a whole number from {CAP} to {MOST}; nothing was set and no round was granted. "
            "Tell the user.")
    elif unsaved:
        say("sdlc: the review-rounds hook couldn't write the typed cap into .sdlc/config.json (not a JSON object, or "
            "not writable), so the cap follows config's own value. Tell the user.")
    if replied and not typed:  # the command sets the cap; it isn't also a grant
        for name in over:  # the user has answered: one more round
            saved[name]["allowed"] = saved[name]["seen"] + 1
    if json.dumps(saved, sort_keys=True) != before:  # never an empty store: setup commits before it ignores .sdlc/.work/
        save(root, saved)
    if replied:
        return
    tool = data.get("tool_name")
    if not over or tool not in GUARDED:
        return
    path = (data.get("tool_input") or {}).get("file_path") or ""
    rel = os.path.relpath(os.path.abspath(os.path.join(data.get("cwd") or root, path)), root).replace(os.sep, "/")
    if path and rel.startswith(".sdlc/.work/findings/") and not any(c in rel for c in "~:"):
        return  # a reviewer finishing its report
    if tool in ("Bash", "PowerShell", "Monitor") and runs_tests(root, (data.get("tool_input") or {}).get("command") or ""):
        return
    rounds = ", ".join(f"{n} (round {r})" for n, r in over.items())
    reason = (f"sdlc: {rounds}: the last review round allowed before the user decides still fails, so the "
              "fixing stops here. Tell the user which findings are left (the latest reports in .sdlc/.work/findings/), then ask with AskUserQuestion, "
              f"header `{HEADER}`, without `answers`: one more fix round, waive them (`waived round <N>` deviation), or "
              "stop. Their answer, or their next message, lifts this for one round (their `/sdlc:setup review-rounds <n>` "
              "sets the cap instead). In an --autopilot session no one can "
              "answer: block the part (`state.py slice <f> block`) and end instead.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        main()
    except Exception:
        pass
    sys.exit(0)
