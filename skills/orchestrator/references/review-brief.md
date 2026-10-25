# Reviewer brief (every code reviewer, every flow)

Give each reviewer:

- the spec, the diff facts (the core's `diff_stats.py` call), the plan's Review Focus section verbatim if it has one, and the `Ruling:` lines in the Gate log;
- the spec's **Failure modes** (the production edges it says apply), each to be checked against the code and its tests;
- these edges by name, each finding rated high when the spec states the behaviour:
  - **Writes:** persisted data survives a crash or a failed write (temp file flushed and synced before the rename, the temp file removed on failure, the original never overwritten by bad input).
  - **Error paths:** every failure the code can hit, I/O included (missing directory, permissions, a full disk), reaches the user in the spec's error format and exit code, never as a raw system error or stack trace.
  - **Loaded data:** anything read back from disk or the network is checked against the same rules as user input.
- the recurring defects: `recurring-defects.md` (this folder), plus `<docs>/recurring-defects.md` if the project has one (same shape; how to add is at the top of `recurring-defects.md`); each is checked, and a hit is rated as its entry says;
- simplifications as findings: needless code, abstraction or dependency, with the smaller version (there is no separate simplifier pass, so its fixes land with the others);
- severity: unrequested public surface (an export, file, endpoint, option, config key or dependency not in the spec or plan, with no stated reason) is high.
