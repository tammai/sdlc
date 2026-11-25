# ADR 0031: A repo can make plans wait for the user's approval (config `approval`)

- **Status:** Accepted, 2026-11-24. Records: `.sdlc/2026-11-24-m-gh-92-approval-policy/change.md`. Issue: #92 (part 1). Related: [0030](0030-modes-and-skips.md).
- **Deciders:** Tâm Mai.

## Context

By default only a high-risk M stops for the plan. A low-risk M builds straight away, and L approves itself when its own checks pass. That suits a solo maintainer. On a team, often nobody but the agent reads the plan: in this repo's history, 16 of 36 changes record "plan self-approved" or "not stopped for approval".

## Decision

1. **`"approval": "high-risk" | "ml" | "always"`** in `.sdlc/config.json`, set by `scaffold.py approval` (`/sdlc:setup approval …`).
   - `high-risk`, or the key absent or unknown, keeps today's flow; nothing new is checked.
   - `ml`: every M and L waits for the user's approval after Define. L still writes its self-check but doesn't approve itself.
   - `always`: S waits too.
2. **`state.py advance <f> 2` from Define enforces it.** It refuses while the policy covers the feature's track and no approval is recorded. Every track's Define ends in that call, chained before `verify.py red`, so a refusal stops the build on every host without a hook reading command text. Once approved, the Gate log line notes who approved and how.
3. **Only the user's approval counts**, recorded in `.sdlc/.work/approvals.json` by `hooks/plan_approval.py`:
   - the answer `Approve` (a trailing `(Recommended)` aside) to a question headed `Approve plan` that names the waiting feature, whose call `user_answer.py` recorded, so the agent can't pre-fill it; any other answer to it takes back an earlier approval of that feature;
   - or a prompt that is exactly `approve` (with one feature waiting) or `approve <feature>`, for hosts without the dialog.

   Any other prompt counts for nothing. Unlike the review cap, "the next message" isn't a reply here, because a resumed session's first prompt and autopilot's `claude -p` prompt would approve on their own. The hook prints nothing, so it adds no allow or deny answer other hosts must read.
4. **The policy is read like `mode` and `skip`** (`sdlc_scopes.approval`):
   - a stricter value applies at once;
   - a move to fewer stops counts only once the trust anchor has shown it and the user replied;
   - with no record, HEAD's committed config decides.

   A record from before 3.16 has no `approval` field and stays valid.
5. **An approval covers the plan the user saw.** The move to Build uses it up, so a feature sent back to Define needs a new one, and resizing a feature at Define to a track the policy doesn't cover is refused until the plan is approved.
   - Since 3.17, `state.py new` writes an `Approval floor:` line into the state file under a policy that covers some track.
   - `set Track` raises the floor at any stage, taking back the approval at Define. `set` can't name the floor itself, so only an approved downsize lowers it.
   - The check takes the stricter of the floor and `Track:`, so an edit of the `Track:` line alone can't lower it.
   - A feature started before the policy has no floor and is judged by its track.
   - `new` clears any approval left under the feature's key by a feature deleted by hand.
   - Leaving Define uses up any approval, needed or not, so a feature sent back to Define needs a new one.
6. **Autopilot never self-approves.** No one can answer in an `--autopilot` session, so it blocks the part instead.

## Consequences

- A team turns on real plan review with one config key. Solo repos see no change.
- The approval record is agent-writable like the other `.sdlc/.work` stores. It is a notice-level protection, stated in `docs/wiki/Limitations.md`. A guard on the file tools and shell commands that write it was tried in 3.17 and dropped: each review round found another spelling past it (a glob through a link, a dangling symlink, PowerShell's dot-matching wildcards).
- Headless Cursor sends no prompt event, so a typed approval can't arrive there. Under `ml` or `always`, a headless Cursor run stops at the refusal.
