# ADR 0032: Opt-in guards in config `guards`, turned off only with the user's acceptance

- **Status:** Accepted, 2026-11-24. Records: `.sdlc/2026-11-24-s-gh-92-s-test-lock/change.md`. Issue: #92 (part 2; part 3 adds more guards). Related: [0030](0030-modes-and-skips.md), [0031](0031-approval-policy.md).
- **Deciders:** Tâm Mai.

## Context

S is the most common track and usually gets no review. Since #56 P3, the red step locks the test files only on M and L, so on S a test can be weakened after it was recorded failing and nothing notices. Issue #92 proposed locking S always. The user chose an opt-in lock instead, so that no repo's behaviour changes on upgrade.

## Decision

1. **`"guards": {"s_tests": true}`** in `.sdlc/config.json`, set by `scaffold.py guard s-tests on|off` (`/sdlc:setup guard …`).
   - With it on, an S feature's `verify.py red` locks its test files, as on M and L.
   - A locked test that changes fails `verify.py` until a `test-change` deviation names it and `red --at <Base>` shows it still fails without the feature.
   - An unknown key, or a value other than `true`, counts as off.
2. **A guard is read like `mode`, `skip` and `approval`** (`sdlc_scopes.guards`):
   - turning a guard on counts at once;
   - turning one off counts only once the trust anchor has shown it and the user replied;
   - with no record, HEAD's committed config decides.

   A trust-anchor record without `guards` stays valid.
3. **Part 3 of #92 adds its guards here**, under the same key and the same acceptance rule.

## Consequences

- A team can make S as tamper-evident as M and L with one config key. Repos without it see no change.
- As with the other config the trust anchor reads, a guard turned off and committed with the anchor's record removed is honoured without a notice (`docs/wiki/Limitations.md`).
