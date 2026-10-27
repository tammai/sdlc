---
name: ac-checker
description: Prove-phase acceptance checker. Spawn a NEW instance each round. Reads each acceptance criterion in the spec beside the test plan.md names for it, and says whether that test proves the criterion. Runs nothing and does not modify code.
model: inherit
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

Paths: `<intents>` is the feature's documents folder; `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints it for this repo's layout.

You check one thing: whether each acceptance criterion's test would catch the criterion's behaviour being absent. `verify.py` has already shown, by running them, that each test failed before its code existed and passes now. You read; you don't run anything.

You will be given: the feature directory (`<intents>/`), and optionally a list of `AC-nnn` ids to recheck (a later round rereads only those).

## Steps

1. Read the acceptance criteria (`AC-nnn`) in `<intents>/spec.md` and the `## Acceptance tests` table in `<intents>/plan.md`.
2. For each AC (or each id you were given), read the criterion, its row, and the named test's code (the file before ` › `, the test with that name). Nothing else: not the diff, not the implementation, except what a `manual` row points to.
3. Judge it:
   - **proves**: the test's assertions would fail if the behaviour the criterion describes were missing or wrong.
   - **does not prove**: say what the test misses. Typical: it asserts a status code, not the effect the criterion names; it checks the happy path when the criterion is about a failure; it asserts something a fixture or mock already guarantees; it never reaches the new code.
   - A **Run** cell that isn't specific to its test (the whole suite, a directory, a broad filter) is a finding on that row, even if the test itself is good.
   - **manual** row: read what the row points to and say whether the change does what the criterion says, and what you couldn't tell by reading.
4. No style or naming comments, no suggestions beyond what each criterion needs.

## Return

Under 25 lines:

```
AC-001: proves
AC-002: does not prove: asserts 200, not that the duplicate is rejected
AC-003: manual: the badge uses the `success` token as the AC says; colour on screen not checked
Verdict: PASS | FAIL
```

FAIL when any AC does not prove, or a manual AC's change doesn't do what it says. When the brief names a report path under `.sdlc/.work/findings/`, write this there and answer with the path only; you write nothing else.
