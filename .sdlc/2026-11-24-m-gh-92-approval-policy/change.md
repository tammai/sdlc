# Approval policy: a repo can make every M and L (or every change) stop for plan approval

## Why

**Request:** GitHub issue #92, part 1 of 4 ("Team-ready gates"), gap 1: "Plan approval is skipped by default. Only high-risk M stops; low-risk M builds straight away and L self-approves when its checks pass." The issue proposes config `approval`: `high-risk` · `ml` · `always`, with today's behaviour as the default; under `ml` every M and L stops after Define with the question tool (`Approve` / `Change something`), under `always` S does too; autopilot blocks the part instead of self-approving; the Gate log records who approved.

For a team, a plan nobody but the agent read is the gap: in this repo's own history 16 of 36 changes record "plan self-approved" or "not stopped for approval".

## Decisions

| Decision | Chosen | Ruled out | Why |
|---|---|---|---|
| Where the stop is enforced | `state.py advance <f> 2` from Define refuses without a recorded approval | a hook reading `verify.py red` in command text | every track's Define ends in that one call (`new && advance 2 && red`), so a refusal stops the red step too, on every host, without widening a parser |
| What counts as approval | the dialog answer `Approve` to a question headed `Approve plan` that `user_answer.py` recorded, or a typed prompt that is exactly `approve` or `approve <feature>` | any next prompt (the review cap's rule) | a resumed session's first prompt and autopilot's `claude -p` prompt are prompts too and would approve on their own |
| Default | `high-risk` (key absent): no check at all, today's behaviour | enforcing today's high-risk stop | that stop is instruction-only now; enforcing it would change every repo on upgrade |
| Policy source | the effective value through `sdlc_scopes`, beside `mode` and `skip`: a move toward fewer stops waits for the trust anchor, a stricter one applies at once | reading config directly | the key is agent-editable config (`repo-config-is-untrusted`) |
| Record | `.sdlc/.work/approvals.json`, written by a new hook `hooks/plan_approval.py`; the hook prints nothing | a deny/allow hook | adds no answer other hosts must understand (`host-hook-answers`) |

The record is agent-writable like the other `.sdlc/.work` stores; this is stated in `docs/wiki/Limitations.md`, not guarded. Headless Cursor sends no prompt event, so a typed approval can't arrive there.

## Acceptance criteria

- **AC-001** With `approval: ml` accepted, `state.py advance <f> 2` for a low-risk M at Define is refused with a message naming the `Approve plan` question, and the state file is unchanged.
- **AC-002** After the user answers `Approve` to a recorded question headed `Approve plan`, the same advance goes ahead and the Gate log line says the plan was approved by the user.
- **AC-003** The answer `Change something` (or any answer but `Approve`), a question naming a feature that isn't waiting, or a prompt other than `approve` / `approve <feature>`, approves nothing.
- **AC-008** An approval holds only for the plan and track the user saw: a later `Change something` takes it back, and resizing a feature at Define to a track the policy doesn't cover is refused until it is approved.
- **AC-004** A typed prompt `approve` approves the one feature waiting at Define; `approve <feature>` approves that feature.
- **AC-005** With `approval: always`, an S feature's advance needs the approval too; with the key absent or `high-risk`, no advance is refused.
- **AC-006** A change to a policy with fewer stops (`ml` → `high-risk`) raises a trust-anchor notice and isn't honoured until the user accepts it; a stricter one (`high-risk` → `ml`) is honoured at once.
- **AC-007** `scaffold.py approval ml` writes the key and refuses an unknown value; the session status line shows `approval ml`, or that it was asked and not yet accepted.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_approval.py › ApprovalTest.test_ml_refuses_the_build_until_approved | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_ml_refuses_the_build_until_approved` |
| AC-002 | tests/test_approval.py › ApprovalTest.test_the_dialog_approve_lets_the_build_start | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_the_dialog_approve_lets_the_build_start` |
| AC-003 | tests/test_approval.py › ApprovalTest.test_other_answers_and_prompts_approve_nothing | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_other_answers_and_prompts_approve_nothing` |
| AC-008 | tests/test_approval.py › ApprovalTest.test_an_approval_holds_only_for_the_plan_and_track_shown | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_an_approval_holds_only_for_the_plan_and_track_shown` |
| AC-004 | tests/test_approval.py › ApprovalTest.test_a_typed_approve_approves_the_waiting_feature | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_a_typed_approve_approves_the_waiting_feature` |
| AC-005 | tests/test_approval.py › ApprovalTest.test_always_covers_s_and_the_default_refuses_nothing | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_always_covers_s_and_the_default_refuses_nothing` |
| AC-006 | tests/test_approval.py › ApprovalTest.test_fewer_stops_wait_for_the_trust_anchor | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_fewer_stops_wait_for_the_trust_anchor` |
| AC-007 | tests/test_approval.py › ApprovalTest.test_scaffold_sets_it_and_the_status_line_shows_it | `py -3.10 -m unittest discover -s tests -t tests -p test_approval.py -k test_scaffold_sets_it_and_the_status_line_shows_it` |

## Must never break

- A repo without `approval` behaves exactly as in 3.15: the existing suite passes untouched.
- `mode` and `skip` acceptance through the trust anchor work as before; a record written by 3.15 (no `approval` field) stays valid.
- A pre-filled `answers` still approves nothing (`user_answer.py` denies it).

## Out of scope

- Parts 2–4 of #92 (S test lock, guarded changes, UI evidence) and the setup profile question.
- Asking for the policy during `/sdlc:setup`'s interview (it is set with `/sdlc:setup approval <value>`).

## Review

- **Fired:** code review, because `## Public Surface` lists the `approval` config key and the `scaffold.py approval` command. Security and UI review didn't fire: risk low, no sensitive, migration or UI path.
- **Ran:** `sdlc:code-reviewer` on opus, two rounds.
- **Round 1:** FAIL, with M1–M6 medium. Fixed test first:
  - M1: only a plain `Approve` counts.
  - M2: the question must name the one waiting feature.
  - M3: the stored `by` is checked.
  - M4: resizing down at Define is refused.
  - M5: the hook records where `state.py` reads.
  - M6: another answer, or the move to Build, takes the approval back.
  - Also fixed: L1–L3 and F1–F3.
- **Round 2:** PASS. Its N1–N3 were fixed test first without another round:
  - N1: every way out of Define is checked, not just `advance 2`.
  - N2: the approval is spent only once the move is written.
  - N3: a typed change request takes the approval back.
  - Also fixed: N5 (one root for the store) and F4, F5.
- **Tickets:** N4, L4 and L5 are in `.sdlc/todo.md`.
- **Manual checks:** none.
- **Lessons filed:** [knowledge/gotchas/review-budget-kills-the-suite-here.md](../../knowledge/gotchas/review-budget-kills-the-suite-here.md)
