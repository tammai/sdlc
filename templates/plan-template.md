# Plan: [FEATURE NAME]

**Intent:** [intent.md](intent.md) · **Spec:** [spec.md](spec.md)

<!-- How, written in Define, and what was reviewed, written in Review. Same sections at every size: S a line or two each.
     A later session works from these three files alone. -->

## How the build runs

[inline | parts in fresh sessions | parallel subagents] because [reason]

## Handoff

<!-- What the builder (or the next part's session) needs and wouldn't find in the code: decisions with their reasons,
     facts found in the code (file:line), risks and how they're proven. Updated at the end of each part. -->

- [decision, fact or risk]

## Tasks

1. **[Task]** — AC-[n]
   - Files: [paths to create or change, backticked]
   - Test first: [the failing test]
   - Then: [the change, in a sentence]

## Acceptance tests

<!-- One row per AC in spec.md: the test that proves it and a command that runs only that test. Build records each
     failing before its code (`verify.py red AC-nnn`). No test can prove it: Test `manual`, the Run cell says why. -->

| AC | Test | Run |
|---|---|---|
| AC-001 | [test file] › [test name] | `[command that runs only this test]` |

## Public Surface

<!-- Every new export, endpoint, CLI command, config key, env var and dependency, with its AC. "- none" if none. -->

- none

## Deviations

<!-- Written in Build: what changed from this plan, why, and its effect. -->

## Review

<!-- Written in Review: what was recommended and why, what was chosen and by whom, each verdict, the high findings and
     what fixed them, tickets, and lessons filed (with links). -->
