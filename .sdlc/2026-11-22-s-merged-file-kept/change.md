# Upgrade and eject keep a file the user merged

## Why

From `.sdlc/todo.md`: "H2: upgrade overwrites a file the user merged (the merged file's hash is stored as if unedited; next upgrade lands it in replace); store the pure render's hash per entry and replace only when disk matches it — whole-plugin review (2026-11-13)". It also covers: "After `/sdlc:upgrade` applies a merge to an edited guardrail, `/sdlc:eject` deletes it; the eject dialog offered to keep it but the report said it wasn't kept — 3.8.0 smoke test H (2026-11-13)".

Proof: render a seeded file, edit it, then record the merge as the upgrade's "apply merge" step does (`scaffold.py record seeded <path> --template <tpl>`). The next upgrade plan lists the file under `replace`, which renders the plain template over the user's edits, and the eject plan lists it under `delete`, with no question. Root cause: `record` stores the merged text's hash as `sha256`, the same field a pure render uses, so `file_state` calls the merged file "unchanged", meaning the plugin's own output.

## Decisions

- `record --template` also stores `render_sha256`, the hash of the template's render at that moment. An entry whose `render_sha256` differs from its `sha256` holds the user's edits. In the upgrade plan, such a file goes under `review` when the template has changed since the merge, and is left alone when it hasn't. Eject asks about it, and `render --if-unchanged` refuses to overwrite it. A later plain render rewrites the entry without the field.
- Ruled out: changing `file_state` itself. It would put every merged file under `review` on every upgrade, even with nothing new to merge.

## Acceptance criteria

- **AC-001** A merged file whose template changed afterwards is listed under `review` in the upgrade plan, not `replace`. With the template unchanged, it's in no list.
- **AC-002** The eject plan lists a merged file under `ask`, not `delete`.
- **AC-003** A lock whose `render_sha256` isn't a string is refused with a message naming the entry, not a traceback.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_a_merged_file_is_reviewed_not_replaced | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_a_merged_file_is_reviewed_not_replaced` |
| AC-002 | tests/test_scaffold.py › ScaffoldTest.test_eject_asks_about_a_merged_file | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_eject_asks_about_a_merged_file` |
| AC-003 | tests/test_scaffold.py › ScaffoldTest.test_a_malformed_render_hash_is_refused | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_a_malformed_render_hash_is_refused` |

## Must never break

- An unedited seeded file whose template changed still goes under `replace`, and an edited one under `review` (`test_upgrade_plan_classifies_every_file`).
- Locks written before this change, with no `render_sha256`, behave as before.

## Out of scope

- The eject dialog's wording, which is the skill's text. With the file now under `ask`, the plan matches what the dialog offers.

## Review

No review ran: no trigger fired (low risk, no Public Surface, no sensitive path).
