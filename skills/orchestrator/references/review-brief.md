# Reviewer brief (every review)

The reviewer reads this file itself, with `<change>`, the state file (its plan sections and `## Deviations`; a part: also `plan-B<n>.md`) and the diff (`git diff <Base> -- . ':!.sdlc'`, one call; in a workbench, also `git -C <repo> diff <base>` for each `## Repos` branch line of the state file). Round 1 is the one full review, so it aims to leave nothing for a later round: read whatever the diff calls, whatever calls what it changed, and the state and files they share; report every finding, with no length limit; don't call an advisor.

## Coverage (round 1)

- **Every finding, in two tiers.** Confirmed: you can point at the line and say what goes wrong. Unconfirmed: plausible but not proven from reading alone (a race, a timing, an input you suspect breaks something): mark it `(unconfirmed)` with the input or probe that would settle it. An unconfirmed finding never makes the verdict FAIL: the fix pass turns it into a failing test, fixes it when the test fails and drops it when it passes.
- **Classes, not instances.** For each finding, name its root cause and list every place in the diff with the same cause. When the class is open-ended (encodings or escapes of a value, input shapes, environment variables, platforms, one setter among several sharing state), say so and name the structural fix (one shared check on every path, an allowlist, fail closed, one owner for the state) rather than the instance patch: patching one shape at a time is what makes later rounds find the next one.
- **What a fix could break.** For each high or bug, say what the obvious fix would have to keep working (identity or cache keys, other callers, shared state, error paths), so the fix pass doesn't trade one bug for the next.

## Depth (code review)

`verify.py` has already proven each acceptance criterion's test failed before the code and passes now: don't re-prove that.

One depth, the full one (a lighter first pass only moves its findings into later rounds): the must-never-break lines and each `manual` AC against the code; silent failures (swallowed errors, fallbacks that hide a failure, missing error paths); test gaps (a behaviour or failure mode the spec implies that no test would catch, rated 1–10, 8 or more is high); simplifications (needless code, abstraction or dependency, with the smaller version); security basics (injection, untrusted input reaching a shell, file path or database, secrets in the diff); and every edge below, each traced through the code and its tests.

## The edges

- The spec's **Failure modes** that apply (concurrent use, scale, persisted-data migration, partial failure or a crash mid-write, untrusted input, I/O errors), each checked against the code and its tests; one that clearly applies but the spec left out is a finding.
- **Writes:** persisted data survives a crash or a failed write (temp file synced before the rename, the temp removed on failure, the original never overwritten by bad input). A kill between a create and its write is a crash window: high when the spec says a killed process must not leave the system unusable.
- **Error paths:** every failure the code can hit, I/O included, reaches the user in the spec's error format and exit code, never as a raw error or stack trace.
- **Loaded data:** anything read back from disk or the network is checked like user input.
- **Recurring defects:** `recurring-defects.md` (this folder) and `<docs>/recurring-defects.md` if present; each checked, a hit rated as its entry says.

## Security review

Security only: injection, authz, secrets, SSRF, XSS, unsafe deserialization, dependency risk, and untrusted input reaching a shell, terminal, file path or database. Report file `security-r<N>.md`.

## Severity

- **High:** a failing or unproven acceptance criterion; wrong behaviour against the spec or a must-never-break line; data loss or corruption; a security issue; a crash window as above; an error path that breaks the spec's error format or exit code; a test gap rated 8 or more; unrequested public surface (anything not in the state file's `## Public Surface`, with no stated reason); a broken constitution MUST rule.
- **Fix in passing:** code-style rules (comments, naming, formatting, docs wording). Never high.
- **Medium / low:** everything else. Mark one that's a bug in code this change touched (wrong behaviour, a crash, an unhandled error, a missing test for something it does) `(bug)`: it's fixed before Ship like a high; the rest are ticketed.

Severity is impact, not confidence. Each finding names the requirement it breaks, if any (an AC, a must-never-break line, a section of the spec the change file links, a constitution rule): one that names one is high, whatever else you'd call it. End the report with `VERDICT: PASS` or `VERDICT: FAIL — <ids>`: in round 1, every high and every confirmed `(bug)`; from round 2, every high only.

## Round 2: the closing check

Round 2 is meant to be the last. It runs at high depth on the fixes (`git diff <round-1 commit or Verified tree>`, or the files the fixes touched), the code that calls them and the state they share, told round 1's findings and their classes. For each round-1 finding: gone, in every instance of its class? For each fix: did it add a bug (the "what a fix could break" list above)? Report everything you find, any severity. Only a high makes it FAIL; a medium or low `(bug)` is listed to fix before Ship, test first, and verify.py closes it without another round; the rest are tickets.
