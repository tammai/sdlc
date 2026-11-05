# doctor: ask git whether .sdlc/.work/ is ignored

## Why

Request, verbatim: "doctor says .sdlc/.work/ isn't git-ignored when .gitignore spells it differently. `doctor.py` warns `.gitignore | warn | .sdlc/.work/ is not git-ignored (scratch files may get committed)` when `.gitignore` has `.sdlc/.work` or `/.sdlc/.work/`, although git does ignore the folder. Expected: the check is `ok` whenever git ignores the folder. Root cause: `check_repo()` in `scripts/doctor.py` compares `.gitignore`'s whitespace-separated tokens with the literal `.sdlc/.work/`. Asking git (`git check-ignore -q .sdlc/.work/x`) gives the right answer for every spelling; the control-contract patterns in the same check have the same problem."

Proof: `tests/test_doctor.py › test_gitignore_other_spellings_git_ignores_are_ok` fails before the fix (`.sdlc/.work` reports `warn`).

Root cause: `check_repo()` tests string membership of `.sdlc/.work/` and the three contract patterns in `.gitignore`'s tokens, so any equivalent spelling (no trailing slash, leading `/`, a parent directory such as `.sdlc/state/`) or an ignore in `.git/info/exclude` / `core.excludesFile` is missed.

## Decisions

- In a git work tree, ask git: `git check-ignore --no-index` with one probe path per pattern (`.sdlc/.work/x`, `.sdlc/state/x.json`, `.sdlc/state/x.events.jsonl`, `.sdlc/state/x.commands/x`); the paths it prints are the ignored ones. `--no-index` so a tracked file doesn't hide the rule.
- Outside git (or git missing), fall back to `.gitignore`'s lines, normalised by stripping a leading `/` and a trailing `/`. Ruled out: reimplementing gitignore matching in Python (git is the authority, and it's already a required tool).

## Acceptance criteria

- AC-001: in a git repo, `.sdlc/.work` / `/.sdlc/.work/` and equivalent contract spellings (including a parent `.sdlc/state/`) give `ok`.
- AC-002: in a git repo that doesn't ignore them, the check still warns with the same messages and fixes.
- AC-003: without git, a `.gitignore` spelling with or without leading/trailing `/` is accepted.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_doctor.py › test_gitignore_other_spellings_git_ignores_are_ok | `python3 -m unittest discover -s tests -t tests -p test_doctor.py -k test_gitignore_other_spellings_git_ignores_are_ok` |
| AC-002 | tests/test_doctor.py › test_gitignore_in_a_git_repo_not_ignoring_warns | `python3 -m unittest discover -s tests -t tests -p test_doctor.py -k test_gitignore_in_a_git_repo_not_ignoring_warns` |
| AC-003 | tests/test_doctor.py › test_gitignore_without_git_accepts_a_spelling_without_slashes | `python3 -m unittest discover -s tests -t tests -p test_doctor.py -k test_gitignore_without_git_accepts_a_spelling_without_slashes` |

## Must never break

- doctor stays read-only and exits 0 on warnings; the existing `.gitignore` tests (`test_gitignore`, `test_gitignore_set_up_before_the_control_contract_warns`, `test_healthy_set_up_repo`) keep passing.

## Out of scope

- Setup's and upgrade's own gitignore step (what they write into `.gitignore`).

## Review

No review ran: no trigger fired.
