# ADR 0023: Review aims for two rounds, one full review and one closing check

- **Status:** Accepted, 2026-11-08. Amends the review depths and the round rules in [ADR 0020](0020-sdlc-2-slim-process-core.md).
- **Deciders:** Tâm Mai, after features in cuti-os and bug-hunter took 3 to 9 review rounds.

## Context

Review had three code depths, a reviewer that reported only findings at confidence 80 or more in about 30 lines, and a round 2 that failed on any bug. The findings folders show where the extra rounds came from:

- **cuti-os** `claude-subscription` (5 rounds): every failing finding in rounds 2 to 4 says "added by the … fix" or "not fully gone". Each fix of a shared-state or identity bug broke the next thing. Rounds 3 and 4 were medium bugs only.
- **bug-hunter** `third-party-failures` (8 rounds, built-in review at `medium`): every high was the same class, a secret reaching the log in another encoding. It ended when one shared check covered every path. `security-pii-audit` and `more-stacks` show the same pattern: instance patches until a structural fix.
- Some rounds ran after a pass, by the user's choice.

Round 1 missed some findings, but most rounds were added by the fixes.

## Decision

1. **One code depth, the full one.** The built-in `code-review` runs as `high --max-findings all`; the plugin's reviewer runs the brief's one checklist.
2. **Round 1 reports everything:** no confidence-80 cut-off, no length limit, no limit to the diff's own files. A finding at 50–79 is `unconfirmed` and never fails the round. Each finding names its root cause, every instance, the structural fix when the class is open-ended, and what its fix must keep working.
3. **The fix pass fixes the class**, with a test that covers its variants, written first. An `unconfirmed` finding gets a test, and the test decides whether it's fixed or dropped. A finding whose fix is a design choice is decided once in `## Decisions`.
4. **Round 2 is the closing check:** full depth on the fixes and the code around them. It fails only on a high. Its medium and low bugs are fixed test first and closed by `verify.py`, with no round 3. `review_report.py` writes that verdict. The round-cap hook is unchanged: it stops for the user when round 2 fails, which now means a high.

## Consequences

- Round 1 costs more tokens and time. Fewer rounds should pay for it, but this is not yet measured against the M bar.
- A round-2 medium or low bug fix is checked by its test and `verify.py`, not by a reviewer.
- The built-in review's `--max-findings all` stays for the user's own later `/code-review` calls until they pass `--max-findings default`.
