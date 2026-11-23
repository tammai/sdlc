# A waiver refused for another failure still names the unlisted test

## Why

**Request (verbatim):** "Fix all 6, then release", applied to what the 3.15.0 smoke test (part G) then found: "when a new failing test file also counts as drift (no Deviations entry), `ship.py --waive-baseline` refuses with `verify_failed` + `drift_unrecorded`. Its fix still says "rerun with --waive-baseline", which was already passed, and it never names the test the baseline doesn't list."

**Proof:** `tests/test_ship.py` › `test_a_waiver_refused_for_another_step_still_names_an_unlisted_test` fails: with lint failing beside the tests, `--waive-baseline` says "rerun with --waive-baseline" and names no unlisted test.

**Root cause:** `ship.verified` matches the failing tests against the baseline only when every failure is a test step; otherwise it falls through to the plain refusal, whose hint suggests the flag whether or not it was given.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| With the flag given and another step failing, the refusal says the waiver covers only baselined test failures, and runs the baseline match on the test failures alone to name any unlisted test | waiving the test step while refusing the rest | the gate still refuses; the message only tells the agent everything there is to fix in one round |

## Acceptance criteria

- **AC-001** With lint failing and a test failing that the baseline doesn't list, `ship.py --waive-baseline` refuses without suggesting the flag again and names the unlisted test.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_ship.py › ShipTest.test_a_waiver_refused_for_another_step_still_names_an_unlisted_test | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_waiver_refused_for_another_step_still_names_an_unlisted_test` |

## Must never break

- The other waiver tests: a baselined test failure alone ships with the flag and is logged; without the flag, the hint names it.

## Out of scope

- A failing baseline test keeping verify from ever recording a passing run (by design, flow.md).

## Review

No review ran: no trigger fired.
