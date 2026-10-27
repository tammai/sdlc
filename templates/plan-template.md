# Plan: [FEATURE NAME]

**Intent:** [intent.md](intent.md) · **Spec:** [spec.md](spec.md)

<!-- How, written in Define: a working file. The permanent record is intent.md, spec.md and review.md; once the change
     is merged, /sdlc:prune may delete this. Same sections at every size: S a line or two each. -->

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

## Public Surface

<!-- Every new export, endpoint, CLI command, config key, env var and dependency, with its AC. "- none" if none. -->

- none

## Deviations

<!-- Written in Build: what changed from this plan, why, and its effect. -->
