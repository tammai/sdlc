# Generated Python CI pins astral-sh/setup-uv@v10, a tag that doesn't exist

## Why

The CI workflow `/sdlc:setup` and `/sdlc:upgrade` generate for a Python repo pins `astral-sh/setup-uv@v10`. That tag doesn't exist upstream, so the `verify` job fails at "Set up job" (`Unable to resolve action astral-sh/setup-uv@v10, unable to find version v10`) on every PR and push, before lint or tests run. Every Python project set up with sdlc 3.1.0 has red CI from its first PR (seen on tammai/bug-hunter PR #1, run 42012743191; pinning `@v10.3.3` by hand made it pass).

Request (verbatim summary): "The generated workflow pins a tag that exists, so CI runs lint and tests. `astral-sh/setup-uv` publishes only full version tags (no moving `v10` major tag), so it needs a full version, e.g. `@v10.3.3`."

Proof: `scaffold.py preview builtin:ci` on a `python` stack renders `- uses: astral-sh/setup-uv@v10`; AC-001's test fails on it.

Root cause: `scripts/scaffold.py` `CI_SETUP["python"]` follows the `@v<major>` style of the `actions/*` pins, but setup-uv has no major-version tags. `tests/test_project_templates.py` asserted the same string, locking the broken pin in.

## Decisions

- Pin the full version `v10.3.3`, the latest tag upstream and the one the bug report confirmed working.
- Ruled out: a commit SHA pin (no other entry in the table uses one, and it hides the version from readers); `@main` (moves under users' feet).

## Acceptance criteria

- AC-001: the CI workflow generated for a `python` stack pins `astral-sh/setup-uv` exactly once, with a full `v<major>.<minor>.<patch>` version, and the existing generated-CI test asserts `@v10.3.3`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_project_templates.py › test_python_ci_pins_setup_uv_by_full_version | `python3 -m unittest discover -s tests -t tests -p test_project_templates.py -k test_python_ci_pins_setup_uv_by_full_version` |

## Must never break

- The other stacks' pins (`actions/*@v6/v7`, rust, dart, flutter, shell) and the generated workflow's step order.

## Out of scope

- The hand-edit conflict `/sdlc:upgrade` reports on a repo that pinned the tag by hand: upgrade's merge flow already asks about edited files, and the regenerated file now carries a working pin.
- Bumping the pin automatically when setup-uv releases.

## Review

No review ran: no trigger fired.
