# A refused impeccable config is named, not answered with "hooks on"

## Why

From `.sdlc/todo.md`: "A machine-local `.impeccable/config.local.json` that is a link (a dotfiles manager) now counts as hook off, and doctor and `/sdlc:setup design` advise `/impeccable hooks on` without saying the file was refused as a link; name it (`scripts/doctor.py`, `scaffold.swap_ui_guardrail`) — security review R2-4 of 2026-11-23-todo-fixes".

Proof: with a skill-folder impeccable and `.impeccable/config.local.json` linked out of the repo, doctor says "its detector hook is off (/impeccable hooks on)" (AC-001's test fails). Running that writes the linked file, which sdlc still won't read, so the advice can't help.

## Decisions

- `scaffold.impeccable_config_refused(root)` lists the impeccable config files that are there but that sdlc doesn't read (a link out of the repo or into `.git`, or unreadable): the same rule `impeccable_hook_off` applies. Doctor's line and `/sdlc:setup design`'s "kept" reason name them and say to replace the link with the file; with none, the advice is as before.

## Acceptance criteria

- **AC-001** With a refused impeccable config, doctor names the file instead of advising `/impeccable hooks on`, and `impeccable_config_refused` lists it.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_doctor.py › DoctorTest.test_a_refused_impeccable_config_is_named_not_hooks_on | `python3.10 -m unittest discover -s tests -t tests -p test_doctor.py -k test_a_refused_impeccable_config_is_named_not_hooks_on` |

## Must never break

- With no refused file, doctor's and setup's impeccable lines read as before.

## Review

No review ran: no trigger fired.
