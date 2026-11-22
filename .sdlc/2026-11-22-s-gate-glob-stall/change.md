# The commit review and doctor match committed globs in bounded time

## Why

Follow-up to the ReDoS todo ("Check the security patterns (`hooks/patterns.py`) and the area globs … for regexes that backtrack badly (ReDoS) on long input"), which 2026-11-22-s-rule-paths-stall closed after probing `patterns.py`, fnmatch and doctor only.

Proof: `sdlc_review_gate._glob_re`, which turns the `areas.sensitive` / `areas.migrations` globs of a committed `.sdlc/config.json` into regexes, takes over 10 s to match `*` × 30 + `z` or `*a` × 20 + `z` against a 60-character path. The commit review runs it on every commit's files, so a committed config can stall it. Doctor's `glob_regex` (from 6490f0c) capped stars at 6, which still leaves a polynomial blow-up on a long path. AC-001's test stalls past its 10 s limit on the old gate.

## Decisions

- **One matcher, `hooks/globmatch.py`,** for the gate and doctor. It compares the glob and the path segment by segment, each segment with `fnmatch.fnmatchcase`, which needs no backtracking across a `*`. A whole-segment `**` takes any number of segments. A run of `*` is one, and `[` is literal (`app/[id].ts`), as the old converters had it.
- **Braces are expanded up to 64 patterns** and the glob is capped at 300 characters. Past either, `glob_match` says True: an area that matches is reviewed, and a rule that matches isn't called dead.
- Doctor's `glob_regex` and `GLOB_LIMITS` and the gate's `_glob_re` are gone.

## Acceptance criteria

- **AC-001** The commit review's area match finishes within 10 s on `*` × 60 + `z`, `*a` × 20 + `z` and a 30-brace glob against a 4000-character path. A brace glob too big to expand counts as a match. The glob semantics the old converters had still hold (the cases in `test_glob_semantics`).

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_globmatch.py › GlobMatchTest.test_a_hostile_security_area_cannot_stall_the_commit_review | `python3.10 -m unittest discover -s tests -t tests -p test_globmatch.py -k test_a_hostile_security_area_cannot_stall_the_commit_review` |

## Must never break

- test_sdlc_review_gate, test_doctor (rule paths, the hostile rule-paths test), the objects UI checks.

## Out of scope

- `role_guard`'s area globs: already fnmatch per segment.

## Review

Security review fires (Risk: high); deferred by the user to one review over all of the 2026-11-22 todo fixes at the end of the push.
