# CI checks the test lock and that each AC's test file exists

## Why

**Request:** "do #68 then P6": #56's P6, two checks of the record in CI, where the agent can't edit them. Since #69, an M or L feature's state file carries `## Test lock` (each test file's sha256 at its red run), and the state file is committed, but only `verify.py`, in the agent's own session, compares the hashes. `.sdlc/ci/invariants.py` checks the record's shape, not its proof.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| The lock is checked for active features and for any feature whose state file changed since `--base` | active features only | Ship sets `Status: done` in the feature's own commit, so its PR would never be checked |
| A locked file matches when its bytes, or its bytes with line endings turned to LF or CRLF, hash to the locked sha256 | raw bytes only | the lock is written on the developer's checkout (CRLF on Windows); CI checks out LF |
| A changed or deleted locked file passes when the state file has a `test-change <file> What: … Why: …` deviation | re-running `red --at` in CI | CI can't run the red step; the deviation is the record of why, and `verify.py` checked the re-red locally |
| An active feature past Define fails when an AC row's test file is missing; `manual` and `departure` rows are skipped | checking done features too | a done feature's tests may move later, legitimately |

## Acceptance criteria

- **AC-001** Given an active feature whose `## Test lock` hashes match the files (with LF or CRLF line endings), when invariants runs, then it passes; when a locked file changed or was deleted, then it fails naming the file, unless a `test-change <file> What: … Why: …` deviation names it.
- **AC-002** Given a done feature with a lock that no longer matches, when invariants runs with `--base` and the feature's state file changed since then, then it fails; when its state file didn't change since `--base`, then it isn't checked.
- **AC-003** Given an active feature past Define whose `## Acceptance tests` names a test file that doesn't exist, when invariants runs, then it fails naming the file; `manual` and `departure` rows aren't files.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_invariants.py › TestLockTest.test_the_test_lock_is_checked | `py -3.10 -m unittest discover -s tests -t tests -p test_invariants.py -k test_the_test_lock_is_checked` |
| AC-002 | tests/test_invariants.py › TestLockTest.test_a_done_feature_is_checked_in_the_push_that_finished_it | `py -3.10 -m unittest discover -s tests -t tests -p test_invariants.py -k test_a_done_feature_is_checked_in_the_push_that_finished_it` |
| AC-003 | tests/test_invariants.py › TestLockTest.test_each_ac_test_file_exists | `py -3.10 -m unittest discover -s tests -t tests -p test_invariants.py -k test_each_ac_test_file_exists` |

## Must never break

- invariants.py stays stdlib only, Python 3.9+, importing nothing from the plugin.
- A repo with no lock (S changes, features from before #69) passes as before.
- The record and baseline checks are unchanged.

## Out of scope

- #56 P7 (doctor row for required checks), P4, P8.

## Review

No review ran: low risk, no trigger fired (no Public Surface: the new helpers are internal to the generated CI script, recorded as deviations; one source file, under 300 added lines); every AC red then green (verify.py); the test file's change after red was recorded and re-red at Base. Full suite: 624 tests pass on Python 3.10.
