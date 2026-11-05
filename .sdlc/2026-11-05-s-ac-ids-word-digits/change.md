# backlog.ac_ids reads digits inside words (OAuth2, B3) as AC numbers

## Why

Request (verbatim): "backlog.ac_ids reads digits inside words (OAuth2, B3) as AC numbers. `ac_ids('AC-001 (OAuth2 login)')` returns `['AC-001', 'AC-002']`, and `ac_ids('AC-001, see B3')` returns `['AC-001', 'AC-' + '003']`. `verify.later_parts()` then treats those ACs as owned by a part that hasn't started and skips them, so a real AC goes unchecked. Expected: `['AC-001']` for both cells; only `AC-nnn` tokens or standalone numbers count."

Proof: `tests/test_backlog.py › test_digits_inside_words_are_not_ac_numbers` fails before the fix.

Root cause: `AC_SPAN` in `scripts/backlog.py` has no leading boundary, so `(\d{1,3})\b` matches the digits at the end of a word such as `OAuth2` or `B3`.

## Decisions

- Add a `(?<![\w-])` lookbehind at the start of `AC_SPAN`, so a match must start at an `AC-` token or a standalone number. Ruled out: requiring the `AC-` prefix, which would break the documented `1, 2` and `2-3` forms.

## Acceptance criteria

- AC-001: `ac_ids` ignores digits that end a word: `AC-001 (OAuth2 login)` and `AC-001, see B3` both give `['AC-001']`.
- AC-002: the documented forms still parse: plain number lists, `AC-nnn` tokens, and ranges with an en dash or hyphen, with or without the `AC-` prefix and spaces around the dash.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_backlog.py › test_digits_inside_words_are_not_ac_numbers | `python3 -m unittest discover -s tests -t tests -p test_backlog.py -k test_digits_inside_words_are_not_ac_numbers` |
| AC-002 | tests/test_backlog.py › test_ac_tokens_numbers_and_ranges_still_count | `python3 -m unittest discover -s tests -t tests -p test_backlog.py -k test_ac_tokens_numbers_and_ranges_still_count` |

## Must never break

- `verify.later_parts()` and every backlog reading of the ACs column.

## Out of scope

- Forms without a hyphen such as `AC001`, which were never documented.

## Review

No review ran: no trigger fired.
