# [FEATURE NAME]

<!-- The change's record for people: why it exists, what must be true, and what was checked after the build. Kept for
     good and committed with the code. Same headings at every size: S a line or two each, M about a page, L the full
     interview's design. A heading that doesn't apply: one line saying so. How it's built (tasks, files, surface,
     deviations) is the agent's, in the state file. Define writes everything above `## Review`; Review writes that. -->

## Why

**Request (verbatim):** [the request or ticket text, unedited]

[What the user wants, who it serves, what changes for them when it's done, and what prompted it now.]

**The user's words:** [answers to the questions asked in Define, and anything else that shaped what gets built; "None asked" if none]

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| [the chosen approach, or a choice inside it] | [the alternative] | [why this one] |

<!-- On L the design lives here too: structure, data flow, what stays untouched. -->

**Bug:** [a bug only: the failing test or exact steps that show it, and the root cause (not the symptom). Otherwise delete this line.]

**Proposals not asked for:** [anything you'd add that neither the request nor a failure mode calls for; dropped unless the user keeps it. "None" if none]

## Acceptance criteria

<!-- Each an id, AC-001 onward, and a new or changed behaviour a test can prove, so its test fails before the change.
     About 10 or fewer. Never "existing tests still pass": verify.py runs the whole suite anyway.
     A bug: AC-001 is the test that proves it today. -->

- **AC-001** Given [state], when [action], then [outcome].

## Acceptance tests

<!-- One row per AC: the test that proves it and a command that runs only that test. Build records them failing
     before their code (`verify.py red AC-001 AC-002 …`), and verify.py checks this table. No test can prove it:
     Test `manual`, the Run cell says why. -->

| AC | Test | Run |
|---|---|---|
| AC-001 | [test file] › [test name] | `[command that runs only this test]` |

## Must never break

- [an invariant this change must keep, e.g. "a killed process never leaves the store unreadable"]

## Failure modes

<!-- Only the edges that apply: concurrent use, scale or large inputs, persisted-data migration, partial failure or a
     crash mid-write, untrusted input, I/O errors. Each one is also an acceptance criterion or a must-never-break line.
     None apply: say so in one line. -->

- [failure mode] → AC-00N

## Out of scope

- [what this deliberately doesn't do, including proposals the user dropped. "None identified" only after looking]

## Review

<!-- Written once, in Review (S: at its review step). Keep it last: what's above it is fixed once Review starts. -->

- **Recommended and chosen:** [security | code default/high | UI | advisor | none], because [the trigger that fired, or none]; chosen by [the user | the trigger list (S) | the recommendation (autopilot)]
- **Verdicts:** [review → `.sdlc/.work/findings/<feature>/<agent>-r1.md` → PASS / FAIL — high ids; or "none ran"]
- **Fixed:** [each high finding: what and where, and the test that now proves it; "None"]
- **Tickets:** [medium and low findings left for later; "None"]
- **Drift and manual checks:** [each Deviations line from the state file, and each `manual` AC with how it was checked; "None"]
- **Security:** [only when a security review ran: findings, the dependency audit, the hooks' findings; else delete this line]
- **Lessons filed:** [links to the knowledge or rule each lesson went into; "None"]
