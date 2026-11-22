# The JSON loaders refuse a config, lock or manifest linked out of the repo

## Why

From `.sdlc/todo.md`: "The shared JSON loaders read `.sdlc/config.json`, `.sdlc/scaffold.lock.json` and `workbench.json` through a committed link (`scaffold.Project`/`read_json`, `sdlc_layout.docs_dir`/`prd`, `objects.setting`, `sdlc_scopes.manifest`), so doctor and the scripts can hang on one or take its values from an outside file; one guarded reader, extending `read_fixed_json` — security review M2 of 2026-11-22-s-doctor-reads-no-links, predates it".

Proof: with `.sdlc/config.json` linked to a file outside the repo, `scaffold.py status` reads it and exits 0, and `init` with `.sdlc` linked outside writes the config there; the hooks' `docs_dir`, `prd`, `is_workbench` and `objects.setting` take its values (the AC tests fail). Root cause: these loaders open the fixed paths with no containment check.

## Decisions

- **scripts:** `scaffold.Project` refuses (ValueError, exit 1, naming the file) when the config or the lock is a link (or under one) out of the repo or into `.git`, through `link_problem`, before it reads or ever writes either. Refusing rather than reading as absent: an absent config would let `init` or `save` write through the link.
- **hooks:** one reader, `sdlc_scopes.read_repo_json(base, rel)`, raises OSError for such a link; every config and `workbench.json` read in `sdlc_scopes`, `sdlc_layout.docs_dir`/`prd` and `objects.py` goes through it, so the hooks read the file as absent (their existing error paths: legacy layout, not a workbench, manifest not run).
- A link that stays inside the repo, outside `.git`, is still followed.

## Acceptance criteria

- **AC-001** `scaffold.py status` exits 1 naming `.sdlc/config.json` or `.sdlc/scaffold.lock.json` when it links outside the repo or into `.git`; `init` with `.sdlc` linked outside writes nothing there.
- **AC-002** A config linked outside or into `.git` gives no value to `docs_dir`, `prd`, `is_workbench`, `workbench_of` or `objects.setting`; a linked `workbench.json` makes `manifest` refuse; a plain config still reads.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_config_and_lock_linked_out_of_the_repo_are_refused | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_config_and_lock_linked_out_of_the_repo_are_refused` |
| AC-002 | tests/test_sdlc_layout.py › LinkedConfigTest.test_config_and_manifest_linked_out_of_the_repo_read_as_absent | `python3.10 -m unittest discover -s tests -t tests -p test_sdlc_layout.py -k test_config_and_manifest_linked_out_of_the_repo_read_as_absent` |

## Must never break

- Plain config, lock and manifest read as before: the scaffold, layout, workbench, objects and doctor tests pass.

## Failure modes

- Untrusted input reaching a file path: a committed link; checked on the resolved path.

## Out of scope

- `objects.py`'s reads of the objects file and spec lock (already go through `spec_lock.inside` or a path check).

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.
