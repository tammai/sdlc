# Plan: [FEATURE NAME]

**Intent:** [intent.md](intent.md) · **Spec:** [spec.md](spec.md) · **Build:** [native | subagent | tasks]

<!-- The how, written in Define. A builder with no conversation context must be able to work from intent.md, spec.md
     and this file alone. S: 1–3 tasks. M lite: 3–6. A deviation during Build is written back here, with its reason. -->

## Tasks

1. **[Task name]** — FR-[n]
   - Files: [paths to create or change]
   - Test first: [the failing test: file and name, and what it asserts]
   - Then: [the change, in a sentence or two]
   - Run: [the command that proves it, e.g. the full suite]

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
