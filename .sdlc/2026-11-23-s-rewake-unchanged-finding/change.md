# A finding already reported on unchanged code isn't raised again on a rewake

## Why

From `.sdlc/todo.md`: "Workbench turn-end review: a rewake re-sends another repo's code the agent left unchanged after a finding, so a declined finding there may be raised again (up to the rewake cap, 3); only the first repo's baseline moves past reviewed code — code review r4 CR4-1 of 2026-11-23-m-stop-review-every-repo".

Proof: a turn whose review flags `web/b.py`, followed by a Stop with no edit (the agent declined), exits 2 again with the same finding (AC-001's test). Root cause: the other repos are diffed from the turn's start on every fire, by design (so a file the cap cut is never lost), and nothing tells the hook that the finding's code is unchanged.

## Decisions

- Each stored finding keeps `diffHash`, the hash of the diff the file was reviewed in. A later fire drops a finding whose file and category were reported on that same diff. A finding re-flagged on changed code stands, and its stored hash moves to the new code. Only the same file, category and vulnerable code, on the same diff, within the same turn (the prompt it started from) is dropped (security review SEC-1, SEC-2): a new issue in an unchanged file still blocks, and a later turn reports it again. This dedups findings, not the files sent, so a file the cap cut is still sent on a rewake. Ruled out: remembering which files were sent (the dropped `other_reviewed_at`, which lost cut files).

## Acceptance criteria

- **AC-001** A finding already reported on byte-identical code isn't raised again on a rewake, and one on changed code still is.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › StopReviewEveryRepo.test_a_declined_finding_on_unchanged_code_is_not_raised_again | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_declined_finding_on_unchanged_code_is_not_raised_again` |

## Must never break

- A new finding, or one on changed code, still blocks the turn (exit 2).

## Review

Security review fired (Risk: high), run once over both changes of branch `2026-11-23-todo-mode-tickets` (`2026-11-23-s-mode-tickets`, `2026-11-23-s-rewake-unchanged-finding`), on opus.

- **Round 1 FAIL:**
  - SEC-1, high: the drop ignored the vulnerable code. Fixed: file, category, code and diff must all match.
  - SEC-2: a hash outlived the turn. Fixed: a stored finding carries its turn.
  - SEC-4: the acceptance line named what was shown, not what's enforced. Fixed: it's built from `effective`, after the write.
  - SEC-3: Windows text mode. Fixed: `O_BINARY`.
- **Round 2 PASS:**
  - M-1: a fix reverted in the same turn was dropped. Fixed test first: a reviewed file that isn't flagged clears its stored hash.
  - L-1: fixed; a subagent's findings carry no hash.
  - L-4: the test now asserts the message.
  - M-2 and L-3 (unconfirmed) are tickets in `.sdlc/todo.md`.
- **Reports:** `.sdlc/.work/findings/2026-11-23-todo-mode-tickets/security-r1.md` and `security-r2.md`.
- **Tests:** full suite on Python 3.10. No lesson filed.
