# ship.py stages on the feature branch when origin/HEAD names it, and moves no state when it refuses

## Why

`ship.py` is Ship's one command. On a new repo whose first push was the feature branch, GitHub makes that branch the default and `origin/HEAD` names it.

**Request (verbatim, abridged):** "ship.py fails, and marks the feature done, when origin/HEAD points at the feature branch … `scripts/ship.py` refuses with `git switch: fatal: a branch named '<feature>' already exists` … by then `ship()` has already run `state.py advance … 4 --gate pass` and `state.py set … Status done`, so the state file says the feature is done and shipped while nothing was committed or branched. Expected: On a branch named after the feature, `ship.py` never tries to create that branch again: it stages on the current branch. A refusal leaves the state file as it was (no Stage 4, no `Status: done`), so the user can fix the cause and run `ship.py` again."

**Proof:** `tests/test_ship.py` › `test_on_the_feature_branch_named_by_origin_head_it_stages_there` (exit 1, `git switch: fatal: a branch named 'login' already exists`) and › `test_a_refused_branch_switch_leaves_the_state_as_it_was` (the state file says Stage 4 and `Status: done` after the refusal).

**Root cause:** `on_default_branch()` trusts `origin/HEAD` alone, so the feature branch it names is taken for the default and `ship()` runs `git switch -c <feature>` for a branch that exists; and `ship()` advances the state before that switch, so the failure isn't atomic.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `ship()` creates the branch only when the current branch isn't already named after the feature and is the default one | Changing `on_default_branch()` to ignore `origin/HEAD` | `origin/HEAD` is still the best guess at the default; only the feature's own name is certain |
| The branch is settled before the state moves: a local branch named after the feature that exists while on the default branch is refused with what to do; otherwise the switch runs before `state.py advance` | Switching to the existing branch | It may hold other work; the user decides |

## Acceptance criteria

- **AC-001** On a branch named after the feature that `origin/HEAD` names, `ship.py` stages on that branch and exits 0.
- **AC-002** When the branch can't be created (on the default branch, one named after the feature exists), `ship.py` exits 1 naming it, and the state file is still at Stage 2 without `Status: done`, nothing staged.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_ship.py › test_on_the_feature_branch_named_by_origin_head_it_stages_there | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_on_the_feature_branch_named_by_origin_head_it_stages_there` |
| AC-002 | tests/test_ship.py › test_a_refused_branch_switch_leaves_the_state_as_it_was | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_refused_branch_switch_leaves_the_state_as_it_was` |

## Must never break

- On the default branch with no feature branch yet, `ship.py` still creates the feature branch (`test_readies_the_commit_in_one_call`).
- A failing verify still moves nothing.

## Out of scope

- `on_default_branch()` itself still answers from `origin/HEAD`; fixing the remote's default is the user's (`git remote set-head origin main`).

## Review

No review ran: no trigger fired (risk low, no sensitive, migration or UI path, no public surface change).
