# CI reads the baseline path as Ship does

## Why

**Request (verbatim):** "next", taking the todo item: "Baseline path leftovers (code review r3 of 2026-11-26-s-ship-baseline-config-path, low): a blank or non-string `baseline` is `.sdlc/baseline.md` to Ship but a literal path to CI's `invariants.py`; a baseline that is a symlink in the repo is read through the link now but not at `Base:` (`git show` gives the link text), so it waives nothing; CI's `check_baseline` and `--baseline-tests` use the raw value unnormalized, so an absolute path skips the growth check (pre-existing)".

**Proof:** each criterion's test fails on main: CI's growth check passes a grown baseline when `baseline` is blank, not a string, or an absolute path; it passes and its waiver reads a file outside the repo; a linked baseline passes the growth check; Ship refuses a linked baseline saying it "lists no failing tests".

**Root cause:** `invariants.py` reads `baseline` raw (`str(value or default)`), while `ship.py` folds it through `configured_baseline` and reads it only inside the repo. Neither checks for a link, which `git show` reads as the link's text.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `invariants.py` gets its own `baseline_path()` with Ship's rules (default for a blank or non-string value, `\` as `/`, an absolute path in the repo made relative, folded) | importing ship.py's | invariants.py is a template copied alone into each project's `.sdlc/ci/` |
| A path that leaves the repo or holds a control character fails both CI checks (`baseline_refused`), never read | skipping the check | skipping is how an absolute path passed unchecked: fail closed |
| A baseline that is a link fails in CI and Ship, by name | following it | at the base `git show` gives the link's text, so the two sides never compare |

## Acceptance criteria

- **AC-001** CI reads a blank or non-string `baseline` as `.sdlc/baseline.md`, in the growth check and the waiver.
- **AC-002** CI's growth check reads an absolute `baseline` inside the repo as its relative path.
- **AC-003** A `baseline` that leaves the repo fails both CI checks with `leaves the repo: not read`, and isn't read.
- **AC-004** A baseline that is a link fails both CI checks with `<path> is a link: not read`.
- **AC-005** Ship's `--waive-baseline` refuses a baseline that is a link with `<path> is a link: not read`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_invariants.py › BaselinePathTest.test_a_blank_or_non_string_baseline_is_the_default_file | `python3 -m unittest discover -s tests -t tests -p test_invariants.py -k test_a_blank_or_non_string_baseline_is_the_default_file` |
| AC-002 | tests/test_invariants.py › BaselinePathTest.test_an_absolute_path_in_the_repo_is_checked_as_its_relative_path | `python3 -m unittest discover -s tests -t tests -p test_invariants.py -k test_an_absolute_path_in_the_repo_is_checked_as_its_relative_path` |
| AC-003 | tests/test_invariants.py › BaselinePathTest.test_a_path_out_of_the_repo_fails_and_is_never_read | `python3 -m unittest discover -s tests -t tests -p test_invariants.py -k test_a_path_out_of_the_repo_fails_and_is_never_read` |
| AC-004 | tests/test_invariants.py › BaselinePathTest.test_a_baseline_that_is_a_link_fails_and_is_never_read | `python3 -m unittest discover -s tests -t tests -p test_invariants.py -k test_a_baseline_that_is_a_link_fails_and_is_never_read` |
| AC-005 | tests/test_ship.py › ShipTest.test_a_baseline_that_is_a_link_is_refused_by_name | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_baseline_that_is_a_link_is_refused_by_name` |

## Must never break

- A baseline at config's path still waives in CI and Ship (`tests/test_ci_baseline.py` › `test_configs_baseline_path_and_json`, `tests/test_ship.py` › `test_the_waiver_reads_the_baseline_config_names_as_ci_does`).
- A grown `.sdlc/baseline.md` still needs a Deviations line (`tests/test_invariants.py` › `test_a_grown_baseline_needs_a_deviation`).

## Out of scope

- The trust anchor watching a moved baseline (its own todo item).
- CI's growth check passing on any `git show` failure at the base (pre-existing; todo, security review r2 L3).

## Review

- Fired: security review (`Risk: high`: config's `baseline`, untrusted repo config, reaches a file path), on opus.
- Round 1: FAIL. Medium: a folder link, a case variant or a Windows spelling passed CI's growth check unchecked while the waiver read the file (S1); an absolute value reached `realpath` before the in-repo check (S2). Low: a non-object `config.json` crashed it (S3); a `.git` path was opened (S4); a FIFO stalled the waiver (S5). Fixed test first: CI reads only a regular file the repo tracks under exactly that name, absolute paths are decided by their text in CI and Ship, `config()` reads a non-object as `{}`, a non-regular file is refused.
- Round 2: PASS, S1–S5 gone in every instance. Low, fixed: folders on the way checked for links before any call follows one (L1); the waiver runs where git isn't installed (L2). L3 (pre-existing) ticketed.
- Lessons: none filed; the fix follows the recurring defect "a setting whose readers resolve its file differently".
