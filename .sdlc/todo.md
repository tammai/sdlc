# Todo

## Open
- [ ] Brownfield: the generated `sdlc-verify.yml` fails every PR while `.sdlc/baseline.md` lists a failing test (it runs the plain test command; local Ship waives the baseline, CI can't) — 3.15.0 smoke test G (2026-11-23)
- [ ] Approval policy: a direct edit of `Track:` in the state file at Define (not `state.py set`) still gets an M past `approval: ml`; take the stricter of the track `new` recorded and the current one — code review r2 N4 of 2026-11-24-m-gh-92-approval-policy (2026-11-24)
- [ ] Approval policy: `sdlc_scopes.approval()` reads HEAD's config with `git show` on every SessionStart and `advance 2` until the trust anchor's record carries `approval`; and `scaffold.py approval` reports from `gate_root(session=False)` while the gates use the session's — code review r1 L4, L5 of 2026-11-24-m-gh-92-approval-policy (2026-11-24)
- [ ] Approval policy hardening (push security review of PR for #92 part 1, 2026-11-24): (1) `.sdlc/.work/approvals.json` is agent-writable (documented in Limitations); consider a role-guard deny on it and `asked.json`, or a store in plugin data; (2) an approval isn't bound to the feature instance: a feature deleted by hand while approved and re-created under the same name inherits it; drop entries for names no longer waiting and on `state.py new` (2026-11-24)

## Done
