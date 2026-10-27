# Spec: [FEATURE NAME]

<!-- What must be true when it's done: no files, code structure or steps (those are plan.md's).
     Same sections at every size: S a line or two each. -->

**Intent:** [intent.md](intent.md) · **Plan:** [plan.md](plan.md) · **References:** [links to existing docs this builds on, or delete the line]

## Acceptance criteria

<!-- Each an id, AC-001 onward, and a new or changed behaviour a test can prove, so its test fails before the change.
     About 10 or fewer. Never "existing tests still pass": verify.py runs the whole suite anyway.
     A bug: AC-001 is the test that proves it today. plan.md's "## Acceptance tests" names each one's test. -->

- **AC-001** Given [state], when [action], then [outcome].
- **AC-002** Given [state], when [action], then [outcome].

## Must never break

- [an invariant this change must keep, e.g. "a killed process never leaves the store unreadable"]

## Failure modes

<!-- Only the edges that apply: concurrent use, scale or large inputs, persisted-data migration, partial failure or a
     crash mid-write, untrusted input, I/O errors. Each one is also an acceptance criterion or a must-never-break line.
     None apply: say so in one line. -->

- [failure mode] → AC-00N

## Out of scope

- [what this deliberately doesn't do, including proposals the user dropped. "None identified" only after looking]
