# Ship reads the baseline config names

## Why

**Request (verbatim):** "fix item 5, the baseline path mismatch". The todo: "`ship.py --waive-baseline` reads only `.sdlc/baseline.md`, while doctor, scaffold and CI's `invariants.py --baseline-tests` read config's `baseline`: a repo that moved its baseline gets CI waivers Ship refuses (code review r3 of 2026-11-25-m-brownfield-ci-baseline, pre-existing)".

**Proof:** `tests/test_ship.py` › `test_the_waiver_reads_the_baseline_config_names_as_ci_does` fails. With config `baseline: docs/baseline.md` listing the failing test, `ship.py --waive-baseline` refuses with `verify failed`.

**Root cause:** `ship.baseline_failures` hard-coded `.sdlc/baseline.md`. The other readers use `config.get("baseline") or ".sdlc/baseline.md"`.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `baseline_path` reads config's `baseline` the way invariants.py does, else `.sdlc/baseline.md` | importing scaffold's `effective_config` | the plugin defaults carry no `baseline`, and CI reads the raw config |
| The file is read only inside the repo (`sdlc_scopes._inside`: links out and `.git` refused), as text with undecodable bytes replaced | `verify.read` (strict UTF-8, no containment) | config is agent-writable; a hand-saved baseline from a Windows editor would have crashed Ship |
| Messages and the Gate log name the path read | keeping `.sdlc/baseline.md` in the text | the user is told the file to edit |
| A baseline moved out of `.sdlc/baseline.md` counts only as it was at `Base:`: config must name it there, and only tests it listed there are waived (code review r1) | teaching the trust anchor to watch the configured path | the anchor's config fingerprint and its notices are a larger change. Ship's check fails closed, and the anchor gap is parked in the todo |
| The baseline path is config's at `Base:` and must match config's now, whichever way it moved, the default included (code review r2) | checking only a move away from `.sdlc/baseline.md` | a move back into `.sdlc/` with a file new at `Base:` gets no anchor notice either |
| Paths are compared as one spelling (`./`, `//`, `..` folded, absolute in the repo made relative), and a control or format character (`sdlc_scopes.odd_name`) refuses the path before any filesystem call | raw strings, `ord < 32`, `isprintable` | `./docs/b.md` isn't a move; U+2028 is a line break too; a no-break space in a file name is fine |
| An unreadable baseline (missing, out of the repo, a control character in the path) refuses the waiver with the reason | a bare `verify failed` | the user can't tell why |

## Acceptance criteria

- **AC-001** With config's `baseline` naming a moved baseline that lists the failing test, `ship.py --waive-baseline` ships, and the Gate log names that path.
- **AC-002** A `baseline` path outside the repo is never read: the waiver is refused and says why, even when `.sdlc/baseline.md` lists the test.
- **AC-003** A baseline moved during the feature (config at `Base:` named another path) waives nothing.
- **AC-004** A test added to a moved baseline after `Base:` isn't waived.
- **AC-005** A `baseline` path with a control character is never read, and nothing it holds reaches the Gate log.
- **AC-006** Moving the baseline back to `.sdlc/baseline.md` during the feature waives nothing.
- **AC-007** A moved baseline with no rows at `Base:` (not committed there) refuses and says so.
- **AC-008** Another spelling of the same path (`./docs//baseline.md`) isn't a move.
- **AC-009** A path with a Unicode line break (U+2028) is never read.
- **AC-010** A path holding a NUL is refused, never a traceback.
- **AC-011** The default `.sdlc/baseline.md` is read when `Base:` isn't in the clone; a moved one with a `Base:` that isn't a commit id says so.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_ship.py › ShipTest.test_the_waiver_reads_the_baseline_config_names_as_ci_does | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_the_waiver_reads_the_baseline_config_names_as_ci_does` |
| AC-002 | tests/test_ship.py › ShipTest.test_a_baseline_path_out_of_the_repo_is_never_read | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_baseline_path_out_of_the_repo_is_never_read` |
| AC-003 | tests/test_ship.py › ShipTest.test_a_baseline_moved_during_the_feature_waives_nothing | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_baseline_moved_during_the_feature_waives_nothing` |
| AC-004 | tests/test_ship.py › ShipTest.test_a_test_added_to_a_moved_baseline_after_base_is_not_waived | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_test_added_to_a_moved_baseline_after_base_is_not_waived` |
| AC-005 | tests/test_ship.py › ShipTest.test_a_baseline_path_with_a_control_character_is_not_read | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_baseline_path_with_a_control_character_is_not_read` |
| AC-006 | tests/test_ship.py › ShipTest.test_moving_the_baseline_back_into_sdlc_during_the_feature_waives_nothing | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_moving_the_baseline_back_into_sdlc_during_the_feature_waives_nothing` |
| AC-007 | tests/test_ship.py › ShipTest.test_a_moved_baseline_not_committed_at_base_says_why_it_waives_nothing | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_moved_baseline_not_committed_at_base_says_why_it_waives_nothing` |
| AC-008 | tests/test_ship.py › ShipTest.test_another_spelling_of_the_same_baseline_path_is_not_a_move | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_another_spelling_of_the_same_baseline_path_is_not_a_move` |
| AC-009 | tests/test_ship.py › ShipTest.test_a_baseline_path_with_a_unicode_line_break_is_not_read | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_baseline_path_with_a_unicode_line_break_is_not_read` |
| AC-010 | tests/test_ship.py › ShipTest.test_a_baseline_path_with_a_nul_is_refused_not_a_crash | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_a_baseline_path_with_a_nul_is_refused_not_a_crash` |
| AC-011 | tests/test_ship.py › ShipTest.test_the_default_baseline_needs_no_base_commit_in_the_clone | `python3 -m unittest discover -s tests -t tests -p test_ship.py -k test_the_default_baseline_needs_no_base_commit_in_the_clone` |

## Must never break

- With no `baseline` in config, `.sdlc/baseline.md` is read and the existing waiver tests still pass.

## Out of scope

- `hooks/trust_anchor.py` and CI's growth check still don't watch a moved baseline for added failing tests (parked in the todo).
- The loose matching of short test names (todo item 6).
- `verify.py` crashing when `Base:` isn't in the clone (parked in the todo).

## Review

- Fired: code review (the Public Surface changed). Built-in `code-review` at high, all findings.
- Round 1: FAIL. High F1: a moved baseline isn't watched by the trust anchor, so the fix let a feature list its own failures. Medium F2: unreadable baseline gave no reason. Medium F4: plain `open` after the path check. Fixed test first (AC-003 to AC-005), plus the stale docs and the todo.
- Round 2: FAIL at the cap. High R2-1: moving the baseline back to `.sdlc/` skipped the `Base:` check. The user chose one more fix round. Fixed test first (AC-006 to AC-009): the path config named at `Base:` must match whichever way it moved; SHA-256 ids; reasons for every refusal; one spelling of a path; Unicode line breaks.
- Round 3: PASS (no high). Its bugs were fixed test first (AC-010, AC-011): NUL before `realpath`, the Windows path in a test, the default baseline needing no `Base:` in the clone, the at-`Base:` value shown checked, a `Base:` that isn't a commit id named. Lows parked in the todo: CI parity for blank values, symlinked baselines, CI's raw path.
- Lessons: none filed.
