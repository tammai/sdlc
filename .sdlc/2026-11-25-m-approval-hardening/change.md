# Plan approval holds against a hand-edited track and a re-created feature

## Why

**Request:** "work on open issues". GitHub has none open, so this works the four approval-policy todos in `.sdlc/todo.md`, left by the reviews of `2026-11-24-m-gh-92-approval-policy` and `2026-11-24-s-gh-92-s-test-lock`:

- **N4:** editing `Track:` in the state file by hand at Define, rather than through `state.py set`, still gets an M past `approval: ml`.
- **Hardening (1):** the file tools or the shell can write `.sdlc/.work/approvals.json` and `asked.json`. Attempted, then dropped by the user's call after review round 4 (see Decisions).
- **Hardening (2):** an approval isn't tied to the feature instance. A feature deleted by hand while approved, then re-created under the same name, inherits the approval.
- **L4:** `approval()` runs `git show HEAD:.sdlc/config.json` until the trust anchor's record carries `approval`.
- **L5:** `scaffold.py approval` reports from `gate_root(session=False)`, while the gates read from the session's gate.
- **Workbench gap (R2-1(a), R2-3):** in a session started in an app repo that has its own `.sdlc`, a dialog Approve for a feature waiting at the workbench is ignored. `user_answer.py` records a question only when the project root has an active feature.

## Decisions

| Decision | Chosen | Ruled out | Why |
|---|---|---|---|
| Where the created track is kept (revised after review round 3) | An `Approval floor:` line in the state file, written by `new`. `set Track` raises it at any stage; `set` can't name it; only an approved downsize lowers it. The check takes the stricter of the floor and `Track:`. | The track in `approvals.json` (rounds 1–3) | In `.sdlc/.work`, the track was wiped by `git clean -fdX`, shared between namesakes in nested repos, and written apart from the state change. Each fix opened another route. The state file is tracked, per feature, and written in the same step as the move. |
| When `new` writes it | Only when the honoured policy covers some track (`ml`, `always`) | Every `new` | Under the default, no state file or store changes. A feature started before the policy has no floor and is judged by its track, as in 3.16. |
| Approval keys (revised after review round 6) | The feature's bare name, as in 3.16 | Per-repo keys `<repo>/<name>` (rounds 3–6); refusing namesakes (round 2) | Per-repo keys broke typed approval, dialog matching and 3.16's records, round after round, to serve namesakes in nested repos, a rare case. That case is now a todo. |
| A guard on writes to the answer records (hardening 1) | Dropped after review round 4, by the user's choice. The records stay agent-writable, as Limitations says. | The file-tool and shell-text guard of rounds 1–4 | Rounds 2–4 each found new spellings past a guard that reads command text: PowerShell and host-mapped globs, a junction, a subst drive, a glob through an in-repo link, a dangling symlink. This is the recurring defect "a guard that reads command text is the only line". |
| L4 | No change: one `git show` costs about 17 ms here, and only until the first turn end. `trust_anchor.config_notice` writes `approval` into the record whenever it lacks it. | A per-process cache of HEAD's config | A cache would go stale across commits in a long-lived caller. |

## Acceptance criteria

- **AC-001** Under `approval: ml`, an M feature at Define whose `Track:` line is edited by hand to `S` still can't advance to Build without an approval.
- **AC-003** A feature approved, then deleted by hand and re-created under the same name with `state.py new`, waits for approval again.
- **AC-004** In a workbench session started in an app repo that has its own `.sdlc`, a dialog `Approve` for a feature waiting at the workbench lets `state.py advance <f> 2` run at the workbench.
- **AC-005** `scaffold.py approval` with no value, run on a nested repo inside the session's repo, reports the policy the session's hooks honour.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_approval.py › ApprovalHardeningTest.test_a_hand_edited_track_still_needs_approval | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_a_hand_edited_track_still_needs_approval` |
| AC-003 | tests/test_approval.py › ApprovalHardeningTest.test_a_recreated_feature_starts_unapproved | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_a_recreated_feature_starts_unapproved` |
| AC-004 | tests/test_approval.py › ApprovalHardeningTest.test_a_dialog_approve_from_an_app_repo_reaches_the_workbench | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_a_dialog_approve_from_an_app_repo_reaches_the_workbench` |
| AC-005 | tests/test_approval.py › ApprovalHardeningTest.test_the_report_reads_the_sessions_gate | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_the_report_reads_the_sessions_gate` |

## Must never break

- A repo without `approval` (or with `high-risk`) gets no `approvals.json` from `state.py new`, and no advance is refused.
- An `approvals.json` written by 3.16 (entries keyed by feature name, with `by`) still approves its feature.
- Every existing approval test passes untouched.

## Out of scope

- Guarding any `.sdlc/.work` record against the agent's writes (see Decisions).
- A nested repo's feature approved from a session started in the outer repo (review round 4, R4-5, pre-existing): a ticket.
- L4 (see Decisions).

## Review

- **Fired:** code review: the diff touches more than 5 source files. Security and UI didn't fire: risk low, no sensitive, migration or UI path.
- **Ran:** the built-in `code-review` (high, all findings), seven rounds. Round 2 was the default cap. The user chose a further round at each `Review cap` stop after rounds 2–6.
- **Round 1, FAIL:** 2 high, 4 medium, 1 low.
  - H1: a junction or symlink got past the record guard.
  - H2: a nested repo's entries were pruned.
  - M1–M4: a rewrite on every prompt; `asked.json` not self-ignoring; a silent store failure; `rm -rf *` denied.
  - L1: an untested track.
  - All fixed test first.
- **Round 2, FAIL:** 5 high. A PowerShell glob bypass (added by M4's fix), a wiped store, a raise then a hand edit, namesakes, a subst drive. Fixed.
- **Round 3, FAIL:** 4 high (R3-1 to R3-4). Fixed by moving the track floor into the state file (`Approval floor:`) and keying approvals by repo.
- **Round 4, FAIL:** 4 high. Two were new routes past the text guard. The user chose to drop the record guard (old AC-002), and the remaining R4-1, R4-3 and R4-6 were fixed.
- **Round 5, FAIL:** 4 high (R5-1 to R5-4), fixed.
- **Round 6, FAIL:** 4 high, three of them from the per-repo keys. The user chose to cut back to 3.16's keys and typed `approve`. R6-3, R6-5 and R6-7 were fixed.
- **Round 7, PASS.**
  - Low bugs fixed in passing, test first: R7-1 (a raise under the default policy takes back the approval), R7-2 (an approval that can't be spent is said), R7-4 (track case).
  - R7-5 and R7-6 (wording) fixed.
  - R7-3, R7-7 and R7-8 are tickets.
- **Tickets** (`.sdlc/todo.md`): plan approval in nested repos (namesakes; R4-5); the approval records being agent-writable; the round 7 leftovers.
- **Drift:** recorded in the state file's Deviations, including AC-002's removal and each test change with its red rerun at Base.
- **Manual checks:** none.
- **Lessons filed:** [knowledge/gotchas/text-guards-dont-converge.md](../../knowledge/gotchas/text-guards-dont-converge.md)
