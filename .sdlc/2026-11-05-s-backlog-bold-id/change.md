# backlog next stalls with no error when a backlog ID is bold

## Why

Request (verbatim title): "backlog next stalls with no error when a backlog ID is bold". A row whose ID is written `**B1**` made `backlog.py next` return `{"next": null, "done": false}` with no error, which the script says a broken backlog must never look like.

Proof: `tests/test_backlog.py › test_a_bold_id_reads_as_its_plain_id` (B1 bold and done, B2 depends on B1: `next` must be B2).

Root cause: `slices()` in `scripts/backlog.py` took the ID cell as written (only uppercased), while deps were extracted with `B\d+`. So the done set held `**B1**` and B2's dep `B1` never matched.

## Decisions

- Read the ID as `B<n>` when the cell is a bare `B<n>` wrapped only in Markdown emphasis or code marks (`*`, `_`, `` ` ``, `~`). Any other cell keeps its old reading (as written, uppercased), so nothing that parsed before parses differently.
- Ruled out: the issue's suggested `re.search(r"B\d+")`, which reads `B1 & calc` as `B1` and so defeats autopilot's refusal of an ID that isn't `B<n>` before it reaches a command line (`tests/test_autopilot.py › test_a_slice_id_that_isnt_b_and_a_number_never_reaches_claude` caught it).
- Ruled out: exiting 2 on a decorated ID. Reading it as the plain ID is what the user meant, and the issue names it as the preferred outcome.

## Acceptance criteria

- AC-001: with B1's ID written `**B1**` and done, `backlog.py next` returns `{"next": "B2", "done": false}`.
- AC-002: with B1's ID written `**B1**` and done, `backlog.py check … B2` returns `{"ok": true}`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_backlog.py › test_a_bold_id_reads_as_its_plain_id | `python3 -m unittest discover -s tests -t tests -p test_backlog.py -k test_a_bold_id_reads_as_its_plain_id` |
| AC-002 | tests/test_backlog.py › test_a_slice_depending_on_a_bold_done_id_is_ready | `python3 -m unittest discover -s tests -t tests -p test_backlog.py -k test_a_slice_depending_on_a_bold_done_id_is_ready` |

## Must never break

- Plain IDs, escaped pipes in cells, and the exit-2 error for a file without a backlog table (the existing tests in `tests/test_backlog.py`).

## Out of scope

- Other markup in the Status cell (e.g. `**done**`).

## Review

No review ran: no trigger fired.
