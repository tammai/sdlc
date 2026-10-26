#!/usr/bin/env python3
"""sdlc autopilot: run a feature's backlog one fresh headless Claude Code session per slice.

For a backlog too long for one session. Each slice runs as `claude -p "/sdlc:start B<n> --autopilot"`; after the last
slice, one more session runs feature close, which ends at Ship's (Stage 8) merge, PR or keep question. State is read
from backlog.md, the feature's state file and the trust anchor between runs, never from the sessions' output.
Stops when:
  - a trust-anchor notice is open (a new -p prompt would accept it without the user seeing it)
  - the feature isn't `Status: active` any more
  - a slice is `blocked: <reason>`, or nothing is ready while slices remain
  - a run exits non-zero, or leaves its slice's status unchanged (it would loop)
  - feature close ends anywhere but Stage 8 (it stopped on a failed gate)
Passes no permission-bypass flag; `--permission-mode` is handed to claude as given (without it or an allowlist,
a headless session can't edit files or run commands). Claude Code only.
Usage: python3 autopilot.py [--root DIR] [--permission-mode MODE] FEATURE
Prints one JSON object: {"stopped": <reason>, "ran": [...]}; exit 0 only once feature close has run.
Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
import backlog  # noqa: E402  (sibling script: backlog table and next-ready choice)
import sdlc_layout  # noqa: E402  (where the feature's state and documents live)


class Stop(Exception):
    pass


def read(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        raise Stop(f"can't read {path}: {e}")


def open_notices(root):
    try:
        with open(os.path.join(root, ".sdlc", ".work", "trust-anchor.json"), encoding="utf-8") as f:
            saved = json.load(f)
    except OSError:
        return []
    except ValueError:
        return ["the trust anchor's record is damaged"]
    if not isinstance(saved, dict):
        return ["the trust anchor's record is damaged"]
    return [f"{name}: {n}" for name, a in saved.items() if isinstance(a, dict) and isinstance(a.get("notices"), list)
            for n in a["notices"]]


def run(root, claude, prompt, mode):
    cmd = [claude, "-p", prompt] + (["--permission-mode", mode] if mode else [])
    print(f"autopilot: {prompt}", file=sys.stderr, flush=True)
    try:
        code = subprocess.run(cmd, cwd=root).returncode
    except OSError as e:
        raise Stop(f"couldn't start claude: {e}")
    if code != 0:
        raise Stop(f"claude exited {code} running {prompt}")


def autopilot(root, feature, mode, ran):
    claude = shutil.which("claude")
    if not claude:
        raise Stop("claude isn't on PATH")
    try:
        located = sdlc_layout.features(root)
        where = located[feature] if feature in located else sdlc_layout.paths(root, feature)
    except ValueError as e:
        raise Stop(str(e))
    path = os.path.join(root, where["intents"], "backlog.md")
    state = os.path.join(root, where["state"])
    if not os.path.isfile(path):
        raise Stop(f"no backlog: {path}")
    while True:
        notices = open_notices(root)
        if notices:
            raise Stop("trust-anchor notice open: " + "; ".join(notices))
        if not re.search(r"^Status:\s*active\b", read(state), re.M | re.I):
            raise Stop(f"{feature} isn't active: {state}")
        rows = backlog.slices(read(path))
        if not rows:
            raise Stop(f"no table with ID, Deps and Status columns in {path}")
        # IDs go into a command line (through a .cmd shim on Windows): only B<n> ever reaches it
        bad = [r["id"] for r in rows if not re.fullmatch(r"B\d+", r["id"])]
        if bad:
            raise Stop("slice IDs must be B<n>: " + ", ".join(bad))
        blocked = [f"{r['id']} {r['status']}" for r in rows if r["status"].startswith("blocked")]
        if blocked:
            raise Stop("blocked: " + "; ".join(blocked))
        if all(backlog.is_done(r) for r in rows):
            run(root, claude, "/sdlc:start --autopilot", mode)
            ran.append("feature close")
            # claude exits 0 when a session ends normally, also one that stopped on a failed gate: read the state
            stages = re.findall(r"^Current:\s*(Stage\s*\d+)", read(state), re.M | re.I)
            if not stages or not re.fullmatch(r"Stage\s*8", stages[-1], re.I):
                raise Stop(f"feature close stopped at {stages[-1] if stages else 'an unknown stage'}: see {state}")
            return "feature close ran: answer its Ship question (merge, PR or keep)"
        slice_id = backlog.next_slice(rows)
        if not slice_id:
            raise Stop("no slice is ready")
        before = next(r["status"] for r in rows if r["id"] == slice_id)
        run(root, claude, f"/sdlc:start {slice_id} --autopilot", mode)
        ran.append(slice_id)
        after = next((r["status"] for r in backlog.slices(read(path)) if r["id"] == slice_id), None)
        if after == before:
            raise Stop(f"{slice_id} is still {before} after its run")


class Parser(argparse.ArgumentParser):
    def error(self, message):  # usage errors are one JSON object too
        print(json.dumps({"stopped": f"usage: {message}", "ran": []}))
        sys.exit(2)


def main(argv=None):
    ap = Parser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--permission-mode")
    ap.add_argument("feature")
    a = ap.parse_args(argv)
    ran = []
    try:
        print(json.dumps({"stopped": autopilot(os.path.abspath(a.root), a.feature, a.permission_mode, ran), "ran": ran}))
        return 0
    except Stop as e:
        print(json.dumps({"stopped": str(e), "ran": ran}))
    except KeyboardInterrupt:
        print(json.dumps({"stopped": "interrupted", "ran": ran}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
