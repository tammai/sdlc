# Doctor judges a rule's paths with one regex, so a hostile glob can't stall it

## Why

Two items from `.sdlc/todo.md`:

- "Check the security patterns (`hooks/patterns.py`) and the area globs (`hooks/role_guard.py` fnmatch) for regexes that backtrack badly (ReDoS) on long input — whole-plugin review M/L, recovered; the original repro is lost".
- "A rule's `paths:` may stall doctor through brace expansion or repeated `**` (`scripts/doctor.py` `expand_braces`, `glob_matches`); unconfirmed, check with the ReDoS item above — security review L3 of 2026-11-22-s-doctor-reads-no-links".

Proof:
- **Security patterns: no ReDoS.** All 18 regexes in `hooks/patterns.py` were timed on 50 KB inputs, built from each pattern's own keywords followed by long runs of spaces, `(a,`, `=` and the like. The worst took 5 ms. `fnmatch` (role_guard's area globs) took ≤1 ms on `*a*a*a*a*a*a*a*b` against 5000 characters. Nothing to change there.
- **Doctor: confirmed.** A committed rule with `paths: ["{a,b}" × 14 + "x"]` against 2000 files ran over 5 minutes, because `expand_braces` makes 2^n patterns, each matched against every file. A run of `*` makes nested `[^/]*` quantifiers too. AC-001's test stalls past its 20 s limit.

## Decisions

- **`glob_regex`:** one compiled regex per glob. Braces (nested too) become a regex alternation; a run of `*` collapses to `**`, and repeated `**/` to one; it's compiled once and matched against every file.
- **A complexity cap** (200 characters, 6 stars, 6 brace groups after collapsing): a glob past it isn't judged. It counts as matching, so a rule is never called dead on a guess. `objects.py`'s UI check calls the same function, so a too-complex UI glob counts as "the repo has UI files".

## Acceptance criteria

- **AC-001** With rules holding `{a,b}` × 30, 60 stars and `**/*` × 12 against 300 files, doctor finishes within 20 s. A brace glob with `**` (`src/{api,web}/**/*.{ts,tsx}`) still matches. A plain dead rule and the collapsed star rule are still reported, and the brace bomb is never called dead.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_doctor.py › DoctorTest.test_hostile_rule_paths_finish_fast_and_braces_still_match | `python3.10 -m unittest discover -s tests -t tests -p test_doctor.py -k test_hostile_rule_paths_finish_fast_and_braces_still_match` |

## Must never break

- `test_rules_whose_paths_match_nothing`; the objects UI checks.

## Out of scope

- None.

## Review

No review ran: no trigger fired (risk low); everything goes into the end-of-push review.
