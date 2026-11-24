# Todo

## Open
- [ ] Brownfield: the generated `sdlc-verify.yml` fails every PR while `.sdlc/baseline.md` lists a failing test (it runs the plain test command; local Ship waives the baseline, CI can't) — 3.15.0 smoke test G (2026-11-23)
- [ ] Approval policy: a direct edit of `Track:` in the state file at Define (not `state.py set`) still gets an M past `approval: ml`; take the stricter of the track `new` recorded and the current one — code review r2 N4 of 2026-11-24-m-gh-92-approval-policy (2026-11-24)
- [ ] Approval policy: `sdlc_scopes.approval()` reads HEAD's config with `git show` on every SessionStart and `advance 2` until the trust anchor's record carries `approval`; and `scaffold.py approval` reports from `gate_root(session=False)` while the gates use the session's — code review r1 L4, L5 of 2026-11-24-m-gh-92-approval-policy (2026-11-24)

## Done
