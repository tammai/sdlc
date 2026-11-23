# `- None` under Avoid means nothing to avoid

## Why

**Request (verbatim):** "Fix all 6, then release" — the todo: "`/sdlc:setup objects` writes `None` under `## Avoid` when nothing is avoided; `scaffold.py objects --enable` rejects it and the agent drops the section — 3.15.0 smoke test C8/P3".

**Proof:** `tests/test_objects.py` › `test_none_under_avoid_means_nothing_to_avoid` fails: `objects.py check` reports `objects_avoid_line` for `- None`.

**Root cause:** `objects.parse` takes every bullet under `## Avoid` as an Avoid line, so `- None` reads as one without `→`.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| A lone `- None`, `- n/a` or `- nothing` bullet under Avoid is no line | changing the setup instructions only | the agent writes it that way unprompted; the parser accepting the plain meaning fixes every writer |

## Acceptance criteria

- **AC-001** An objects file whose Avoid section is `- None` passes `objects.py check`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_objects.py › ObjectsTest.test_none_under_avoid_means_nothing_to_avoid | `python3 -m unittest discover -s tests -t tests -p test_objects.py -k test_none_under_avoid_means_nothing_to_avoid` |

## Must never break

- A real Avoid line without `→` is still refused.

## Out of scope

- Other sections' placeholders.

## Review

No review ran: no trigger fired.
