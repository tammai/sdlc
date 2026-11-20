# Configurable review round cap

## Why

> where is review max rounds set? … i want to config it when setup and anytime during working time

The review round cap is hard-coded (`CAP = 2` in `hooks/review_rounds.py`), so a team that wants one more automatic fix round before the hook stops for the user has to edit the plugin. This change makes it a repo setting that setup asks for and `/sdlc:setup review-rounds` changes at any time. The cap is a safety stop, so the user chose a guarded setting (asked 2026-11-20, "Bounded, user-applied"): a whole number in a fixed range, where a lower value applies at once and a higher one only on the user's next prompt.

## Acceptance criteria

- **AC-001** `scaffold.py review-rounds` prints the repo's cap (2 when none is set). `scaffold.py review-rounds <n>` records `review_rounds: <n>` in `.sdlc/config.json` for n from 2 to 5. Any other value is refused with exit 2 and leaves the config unchanged.
- **AC-002** With `review_rounds: 3` applied, a failing round 2 doesn't stop the work. A failing round 3 does, and the deny message names round 3.
- **AC-003** A higher value in config doesn't take effect until the user's next prompt (UserPromptSubmit); until then the old cap holds. A lower value takes effect at the next tool call.
- **AC-004** A `review_rounds` that isn't a whole number from 2 to 5 (`null`, a string, a bool, a float, 1, 6), or a config that isn't a JSON object, leaves the cap at 2.
- **AC-005** Setup asks for the cap as a hard stop (step `review-rounds`, recorded with `$S review-rounds <n>`), and `/sdlc:setup review-rounds` runs only that step at any time. (manual: skill and command text, checked in Review)

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_review_rounds_records_and_refuses_out_of_range | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_review_rounds_records_and_refuses_out_of_range` |
| AC-002 | tests/test_review_rounds.py › ReviewRoundsTest.test_a_configured_cap_moves_the_stop | `python3.10 -m unittest discover -s tests -t tests -p test_review_rounds.py -k test_a_configured_cap_moves_the_stop` |
| AC-003 | tests/test_review_rounds.py › ReviewRoundsTest.test_a_raise_waits_for_the_users_prompt_a_lower_cap_applies_at_once | `python3.10 -m unittest discover -s tests -t tests -p test_review_rounds.py -k test_a_raise_waits_for_the_users_prompt_a_lower_cap_applies_at_once` |
| AC-004 | tests/test_review_rounds.py › ReviewRoundsTest.test_a_bad_value_keeps_the_cap_at_two | `python3.10 -m unittest discover -s tests -t tests -p test_review_rounds.py -k test_a_bad_value_keeps_the_cap_at_two` |
| AC-005 | manual | manual: instructions in `skills/setting-up-projects/SKILL.md` and `commands/setup.md`; no test can run a skill's question |

## Must never break

- With no `review_rounds` set, the hook behaves exactly as before: round 2 failing stops the work, and each user reply grants one round (the existing `test_review_rounds` tests pass unchanged).
- Nothing the agent writes can raise the cap within a turn. Committed config can raise it only up to 5, and only once the user speaks.
- `stuck_turn.py`'s call `review_rounds.capped(root, review_rounds.load(root))` still works.
- With no active feature, the hook writes no file.

## Decisions

| Decision | Chosen | Ruled out |
|---|---|---|
| Where the value lives | `review_rounds` at the top level of `.sdlc/config.json` (committed, shared by the team) | a gitignored local file (the user chose committed and bounded) |
| Range | 2 to 5 | 1, which would stop on round 1's findings, which the flow fixes without asking; more than 5, which is no longer a stop |
| How a raise applies | the applied cap is kept in `.sdlc/.work/review-cap.json`; on UserPromptSubmit, or the user's answer to a `Review cap` question, it becomes the configured value; at any other event it only goes down | applying at once (lets the agent edit config to buy rounds) |
| The applied cap's store | its own file, not a key in `review-rounds.json` | a reserved key beside feature names (the "two report families share one key" recurring defect) |
| One validity check | `review_rounds.configured()` in the hook; `scaffold.py` imports it | a second copy of the range in `scaffold.py` |

## Failure modes

- Malformed config read back from disk (wrong type, `null`, not an object) → AC-004.
- Repo config relaxing a safety stop (recurring defect) → bounded at 5 and applied only on the user's prompt: AC-003, AC-004.

## Out of scope

- A per-feature cap. The setting applies to the whole repo.
- An upgrade migration: repos without the key keep 2, and `/sdlc:setup review-rounds` sets it.

## Review

- **Fired:** code review, because `## Public Surface` adds a command and a config key. Risk is low, so it ran without asking. Reviewer: the built-in `code-review high --max-findings all`, findings rated by the orchestrator.
- **Round 1, FAIL:** F2 (high) an agent-written config raise applied on any user reply; F4 (high) a fresh `.sdlc/.work` ignored the configured cap; F3, F5, F6 bugs; F7 docs; F1 and F8 tickets. Fix: the cap is bounded by config at Base, and the store was dropped.
- **Round 2, FAIL:** R1–R4 (high) under the "raise window" design: a raise lost, a deadlock while held, an agent's earlier raise accepted, Base read from the git top level. The user granted round 3. Fix: the number is read from the user's own `/sdlc:setup review-rounds <n>` prompt, and `./` paths are used.
- **Round 3, FAIL:** T1 (raised to high, since it broke AC-003) a typed cap beat a later lower config. The user granted round 4. Fix: the hook writes the typed number into config. Grants became `allowed` rounds. `trust_anchor.py` also gets `./` paths (pre-existing, fixed in passing, with a test).
- **Round 4, FAIL:** U1 (high) the agent could climb back above a lower value. The user granted round 5. Fix: a per-feature ceiling that only the user's typed number raises (ADR 0029). The config write is atomic.
- **Round 5, FAIL:** V1 (high) the ceiling wasn't tracked before round 2. The user granted round 6. Fix: tracked on every call. The config write uses `scaffold.write_json`, and an unreadable config holds 2 for one call only.
- **Round 6, PASS:** W1–W6 (medium and low) fixed test first without another round: no ceiling stored from an unreadable first read; a typed cap reaches paused features; an out-of-range typed number is named and not granted; an unsaved cap is reported; setup text.
- **Tickets:** the store `.sdlc/.work/review-rounds.json` can be written by the agent's shell (pre-existing, now holds the ceiling too). A nested `claude -p` prompt counts as the user's. A raise the agent commits during one feature becomes the next feature's Base value with no notice beyond its PR diff. Headless Cursor never sends prompts to hooks. All are in spec 03's Known gaps.
- **Manual:** AC-005 checked by reading `skills/setting-up-projects/SKILL.md` (the `review-rounds` step and the hard-stop list) and `commands/setup.md` (the argument, the held case, the commit with no active feature).
- **Drift:** recorded in the state file's Deviations, including ADR 0029, the trust-anchor paths and the regenerated host copy.
- **Lessons filed:** `.sdlc/recurring-defects.md` (a safety cap the agent can raise by some route).
