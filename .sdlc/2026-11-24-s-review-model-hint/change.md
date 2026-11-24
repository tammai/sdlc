# A review agent dispatched without a model is told to use opus

## Why

**Request (verbatim):** "When a review agent has no model, the first refusal could say `ui-reviewer` needs `model: opus` instead of listing the tiers" (from a downstream run: `sdlc:ui-reviewer` was denied first for having no model, then for naming one below opus, so it took three dispatches).

**Proof:** a review agent dispatched with no model is denied with only the tier list; the reason never names opus as the one model it accepts.

**Root cause:** `hooks/model_router.py` `problem()` checks for a missing model before it looks at the agent, so the always-top rule is reported only on a second refusal.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| A missing model on an always-top agent gets a reason naming `model: opus` | choosing opus for the agent (rewriting the input) | a hook that answers PreToolUse denies or allows; the agent still makes the dispatch |

## Acceptance criteria

- **AC-001** A review agent (`ui-reviewer`) dispatched with no model is denied with a reason that names it and `model: opus`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_model_router.py › ModelRouterTest.test_a_review_agent_without_a_model_is_told_to_use_opus | `py -3.10 -m unittest discover -s tests -t tests -p test_model_router.py -k test_a_review_agent_without_a_model_is_told_to_use_opus` |

## Must never break

- Any other dispatch without a model is still denied with the tier list.
- A review agent below opus is still denied.

## Out of scope

- Which tier any agent runs on.

## Review

No review ran: no trigger fired.
