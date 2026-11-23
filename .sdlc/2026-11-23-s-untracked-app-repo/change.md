# An app repo with stray files tells the agent to ask the user

## Why

**Request (verbatim):** "working on the open items in todo". The item: "Workbench: `state.py repo` refuses an app repo with only untracked files (a `__pycache__`), and the guard denies removing them before the repo is branched, so the agent must ask the user; ignore untracked-only changes, or say so in the deny — 3.15.0 smoke test K4".

**Proof:** `tests/test_workbench.py` › `test_build_branches_and_verifies_each_touched_repo` fails on the refusal's text: it says "commit or stash them in web/", which the guard then denies (the repo isn't branched), and names no file.

**Root cause:** `state.py repo` refuses a repo with any `git status --porcelain` output, rightly: Ship stages untracked files too, so they'd ship in the feature's commit. But its message sends the agent to clean up, and `role_guard.unbranched_problem` denies every write there until the repo is branched, so the agent loops between the two.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Keep the refusal; name the files (up to 5) and tell the agent to ask the user to commit, stash, remove or ignore them | ignoring untracked-only changes | Ship stages untracked files, so a stray file would ship in the feature's commit |

## Acceptance criteria

- **AC-001** `state.py repo` on an app repo with an untracked file refuses, names the file, and says to ask the user.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › WorkbenchFeature.test_build_branches_and_verifies_each_touched_repo | `python3 -m unittest discover -s tests -t tests -p test_workbench.py -k test_build_branches_and_verifies_each_touched_repo` |

## Must never break

- A clean repo branches as before; nothing is recorded or branched when it refuses.

## Out of scope

- The guard's own deny text before a repo is branched (it names `state.py repo`, which is right once the repo is clean).

## Review

No review ran: no trigger fired.
