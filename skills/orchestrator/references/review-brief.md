# Reviewer brief (every code reviewer, every flow)

Give each reviewer:

- the spec, the diff facts (the core's `diff_stats.py` call), the plan's Review Focus section verbatim if it has one, and the `Ruling:` lines in the Gate log;
- these edges by name, each finding rated high when the spec states the behaviour:
  - **Writes:** persisted data survives a crash or a failed write (temp file flushed and synced before the rename, the temp file removed on failure, the original never overwritten by bad input).
  - **Error paths:** every failure the code can hit, I/O included (missing directory, permissions, a full disk), reaches the user in the spec's error format and exit code, never as a raw system error or stack trace.
  - **Loaded data:** anything read back from disk or the network is checked against the same rules as user input.
- severity: unrequested public surface (an export, file, endpoint, option, config key or dependency not in the spec or plan, with no stated reason) is high.
