# Doctor names the mode and expects nothing advisory skips

## Why

**Request (verbatim):** "Fix all 6, then release" — the todo: "Advisory greenfield setup ends with doctor ❌ `repo.commands` (advisory skips the stack and commands by design), `repo.guardrails` says rules were written, and doctor never names the mode — 3.15.0 smoke test D4/P1".

**Proof:** `tests/test_doctor.py` › `test_an_advisory_repo_names_its_mode_and_needs_no_commands` fails: no `mode` row, and `commands` fails on an advisory repo with none.

**Root cause:** doctor's repo checks predate advisory mode (ADR 0030): the commands check counts missing commands as a failure and the guardrails check runs for every Claude Code repo, though advisory setup records no commands and writes no guardrails.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| A `mode` row in the repo group: full with its skips, or advisory | the status line only | doctor is where a teammate checks a repo |
| In advisory, missing commands aren't a problem and the guardrails row is left out | a separate advisory report | the rest of doctor still applies |

## Acceptance criteria

- **AC-001** On an advisory repo with no commands, doctor has a `mode` row naming advisory, `commands` doesn't fail, and there is no `guardrails` row.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_doctor.py › DoctorTest.test_an_advisory_repo_names_its_mode_and_needs_no_commands | `python3 -m unittest discover -s tests -t tests -p test_doctor.py -k test_an_advisory_repo_names_its_mode_and_needs_no_commands` |

## Must never break

- A full repo's checks: missing commands still fail, unwritten guardrails still warn.

## Out of scope

- Advisory greenfield building no stack (by design, references/advisory.md).

## Review

No review ran: no trigger fired.
