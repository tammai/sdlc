# Reviewer brief (every code reviewer, every flow)

Give each reviewer:

- `intent.md`, the spec and the plan (a slice: `plan-B<n>.md`), the diff facts (`prove.md`'s `diff_stats.py` call), the plan's Review Focus and Deviations sections verbatim, and the `Ruling:` lines in the Gate log;
- the spec's **Failure modes**: which of these it says apply (concurrent use, scale or large inputs, persisted-data migration and compatibility, partial failure or a crash mid-write, untrusted input, I/O errors), each checked against the code and its tests, and any that clearly applies but the spec left out raised as a finding;
- these edges by name, each finding rated high when the spec states the behaviour:
  - **Writes:** persisted data survives a crash or a failed write (temp file flushed and synced before the rename, the temp file removed on failure, the original never overwritten by bad input).
  - **Error paths:** every failure the code can hit, I/O included (missing directory, permissions, a full disk), reaches the user in the spec's error format and exit code, never as a raw system error or stack trace.
  - **Loaded data:** anything read back from disk or the network is checked against the same rules as user input.
- the recurring defects: `recurring-defects.md` (this folder), plus `<docs>/recurring-defects.md` if the project has one (same shape; how to add is at the top of `recurring-defects.md`); each is checked, and a hit is rated as its entry says;
- simplifications as findings: needless code, abstraction or dependency, with the smaller version (there is no separate simplifier pass, so its fixes land with the others);
- scope: behaviour the spec didn't ask for (stricter validation, extra hardening, an option or message nobody requested) is a simplification finding, high when a user can see it;
- severity: unrequested public surface (an export, file, endpoint, option, config key or dependency not in the plan's Public Surface, with no stated reason) is high.
