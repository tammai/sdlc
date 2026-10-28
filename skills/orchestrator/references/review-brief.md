# Reviewer brief (every review)

The reviewer reads this file itself, with `<change>`, the state file (its plan sections and `## Deviations`; a part: also `plan-B<n>.md`) and the diff (`git diff <Base> -- . ':!.sdlc'`, one call). Budget: open other files only to follow a call the diff makes; don't call an advisor; keep the report to about 30 lines.

## Depth (code review)

- **Low:** correctness only: does the code do what each acceptance criterion and must-never-break line says, do the tests prove it, and do its error paths hold (of The edges below, error paths only). Read the diff, `<change>` and the tests it names; open another file only to follow a call the diff makes. Report in a few lines.
- **Default:** low, plus in one pass: silent failures (swallowed errors, fallbacks that hide a failure, missing error paths); test gaps (a behaviour or failure mode the spec implies that no test would catch, rated 1–10, 8 or more is high); simplifications (needless code, abstraction or dependency, with the smaller version); and security basics (injection, untrusted input reaching a shell, file path or database, secrets in the diff).
- **High:** default, plus a deeper pass on each failure mode the spec names and the edges below, tracing each through the code and its tests.

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
- **Medium / low:** everything else; ticketed.

Severity is impact, not confidence. End the report with `VERDICT: PASS` or `VERDICT: FAIL — <high ids>`.
