# UI evidence leftovers: a git failure is "not checked", an app repo's own UI globs count

## Why

**Request:** "work on open issues": the todo "UI evidence and checks leftovers" from code review round 2 of `2026-11-24-m-gh-92-ui-evidence-profile`. With `guards.ui_evidence` on:

- a git failure inside the UI check reports `git_failed`, not `ui_evidence_not_checked`;
- in a workbench, an app repo's own `areas.ui` globs are ignored, and ADR 0032 doesn't say so;
- deleting a UI file counts as a UI change (unconfirmed).

Separately, setup's `advisory.md` says to take one answer for the monorepo's profile and the solo/shared checks, while `monorepo.md` says never to infer the profile, and neither says what a small team gets.

## Decisions

| Decision | Chosen | Ruled out | Why |
|---|---|---|---|
| An app repo's own `areas.ui` | Counts for that repo's files, added to the workbench's globs; config can only add areas, never remove one | Documenting that only the workbench's count | The app repo's team knows its UI paths. Adding is the rule `ui_globs` already follows. |
| A deleted UI file | Counts as a UI change (unchanged), now said in ADR 0032 | Leaving deletions out | A removed screen or component is a change the user can see; a screenshot or a manual reason records it. |
| Profile and checks in a monorepo greenfield setup | Asked in one message as two questions: a small team is `lean` and shared | One answer for both | `monorepo.md` says never infer the profile; a small team is lean in layout but shares the repo. |

## Acceptance criteria

- **AC-001** When git fails inside the UI evidence check (an unknown Base commit), Ship is refused with `ui_evidence_not_checked`.
- **AC-002** In a workbench, a change in an app repo to a path that repo's own `areas.ui` names needs UI evidence at Ship.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_ui_evidence.py › UiEvidenceGitTest.test_a_git_failure_is_not_checked | `py -3.10 -m unittest discover -s tests -t tests -p test_ui_evidence.py -k test_a_git_failure_is_not_checked` |
| AC-002 | tests/test_ui_evidence.py › WorkbenchOwnGlobsTest.test_an_app_repos_own_ui_glob_counts | `py -3.10 -m unittest discover -s tests -t tests -p test_ui_evidence.py -k test_an_app_repos_own_ui_glob_counts` |

## Must never break

- Every existing UI evidence test passes untouched: the workbench's globs still match app repo files, and an empty or broken `areas.ui` never narrows the plugin's list.

## Review

No review ran: low risk, no trigger fired (1 source file, no public surface); every AC red then green (verify.py); full suite 942 OK on Python 3.10 before the merge of #144, which touched none of these files.
