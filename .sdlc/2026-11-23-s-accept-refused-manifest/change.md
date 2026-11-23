# An accept says when sdlc's scripts refuse the manifest

## Why

**Request (verbatim):** "Fix all 6, then release" — the todo: "Workbench: `accept read-only <repo>` accepts a non-app repo made writable in workbench.json, which sdlc's scripts then reject (`only an app repo can be writable`), blocking every feature step until it's undone; warn at the accept — 3.15.0 smoke test K re-run".

**Proof:** `tests/test_workbench.py` › `test_an_accept_says_when_sdlc_refuses_the_manifest_it_accepts` fails: the accept message says nothing of the refusal.

**Root cause:** the watch reads `workbench.json` entry by entry (`read_only_names`, it must never fail open), while the scripts read it with `sdlc_scopes.manifest`, which refuses a writable non-app repo; the accept never checked the second.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| The accept still takes the repos, then adds the scripts' refusal to its message | refusing the accept | the accept is the user's; telling them at once is enough to fix the file |

## Acceptance criteria

- **AC-001** Accepting a `specs` repo made writable says sdlc's scripts refuse `workbench.json`, naming the reason.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › ReadOnlyBackstop.test_an_accept_says_when_sdlc_refuses_the_manifest_it_accepts | `python3 -m unittest discover -s tests -t tests -p test_workbench.py -k test_an_accept_says_when_sdlc_refuses_the_manifest_it_accepts` |

## Must never break

- The rest of ReadOnlyBackstop: a valid manifest's accept message is unchanged.

## Out of scope

- Which roles may be writable.

## Review

No review ran: no trigger fired.
