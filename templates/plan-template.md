# Plan: [FEATURE NAME]

**Intent:** [intent.md](intent.md) · **Spec:** [spec.md](spec.md) · **Build:** [native | subagent | tasks]

<!-- The how, written in Define. A builder with no conversation context must be able to work from intent.md, spec.md
     and this file alone. S: 1–3 tasks. M lite: 3–6. A change confined to 1–2 files: 1–3, whatever the track. A deviation during Build is written back here, with its reason. -->

## Handoff to Build

<!-- The whole handoff: Build works from the files, never from Define's conversation. Anything the user said that
     changes what gets built goes under Decisions, or it doesn't count. -->

- Decisions: [decision] because [reason] (if [reason] is false: [what changes])
- Rejected: [option] because [reason]
- Found in the code: [fact] ([file:line])
- Must not break: [invariant]
- Builder's choice: [open call]
- Careful: [risk] -> proven by [check, with its budget]

## Tasks

1. **[Task name]** — FR-[n]
   - Files: [paths to create or change]
   - Test first: [the failing test: file and name, and what it asserts]
   - Then: [the change, in a sentence or two]
   - Run: [the command that proves it, e.g. the full suite]

<!-- A proof that the new code behaves like the old (old vs new on generated inputs) has a budget, not a count:
     about 1,000 cases or 2 minutes, whichever comes first, calling both versions in one process where the code
     allows (no process per case). It runs once, in Build; Prove reuses it unless the files it covers changed. -->

## Acceptance tests

<!-- One row per acceptance criterion (AC-nnn) in spec.md: the test that proves it and the command that runs just that
     test. Build records each test failing before its code (`verify.py red AC-nnn`), and verify.py checks the table.
     A criterion no automated test can prove: Test `manual`, and the Run cell says why. -->

| AC | Test | Run |
|---|---|---|
| AC-001 | [test file] › [test name] | `[command that runs only this test]` |

## Public Surface

<!-- Every new export, endpoint, CLI command, config key, env var and dependency, one per line with its requirement.
     Prove checks the diff against this list (diff_stats.py --plan). Keep the format; "- none" if there is none. -->

- [kind] `[name]` ([where]) — FR-[n]

## UI mapping

<!-- UI work only: each changed screen → the design-system components, tokens and patterns it uses. Delete otherwise. -->

## Review Focus

<!-- Up to five inputs or failure modes the spec implies that no task's test covers, most likely to bite first;
     each one's test then goes into the owning task. "- none found" if you checked and found none. -->

## Deviations

<!-- Written during Build, in the same commit as the drift, one line each; verify.py fails on drift with no line:
     - `[file, task N or surface name]` — What: [what drifted] · Why: [what the plan didn't foresee] · Effect: [on ACs, public surface, risk, other code] -->
