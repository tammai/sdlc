# Setup writes every guardrail itself, and doctor sees when they're missing

## Why

**Request (verbatim):** "Fix it, then release" (the 3.12.0 smoke test's C3 failure; the user's choice at the release stop, 2026-11-17).

**Bug:** in the 3.12.0 smoke test (part C, Windows), greenfield setup left `.claude/hookify/` empty. Setup's `guardrails` step tells the agent to render each entry of `scaffold.py guardrails`; the agent wrote a shell loop (`… | python3 -c … | while read t d; do $S render "$t" "$d" … >/dev/null; done`), and Windows' Python printed CRLF, so every `dest` ended in `\r` and every render failed (`[Errno 22] Invalid argument: '…/sdlc-console-log.md\r'`), hidden by `>/dev/null`. The step committed only a lock change, the report said "15 hookify guardrails seeded", and doctor, `scaffold.py status` and its plugin-files row all said ok, since nothing was recorded to be missing. Root cause: one script call per item, assembled by the agent in a shell, with no check after; listed as a "should" known issue since 3.10.0 ("the guardrail loop … picks up `\r` on Windows"), now silent.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `scaffold.py guardrails --render` renders every listed guardrail in one call (seeded, recorded) and reports what it wrote and what it left | stripping `\r` in the skill's loop | the loop is the agent's improvisation; one call removes the shell from it on every platform |
| A guardrail already recorded and edited by the user, or a file the plugin never wrote, is left as it is and listed (`kept`) | overwriting | setup must not clobber the user's file; `render --if-unchanged`'s rules |
| Doctor warns (not fails) when setup is complete, the repo is set up for Claude Code, and a listed guardrail is neither on disk nor declined | a fail | a deleted guardrail is the user's right (`forget`); a warning with the fix command is enough to be seen |

## Acceptance criteria

- **AC-001** Given a set-up repo, when `scaffold.py guardrails --render` runs, then every guardrail `scaffold.py guardrails` lists is written to its `dest` and recorded as seeded, and the output lists them under `rendered`; a guardrail the user edited since it was written is left unchanged and listed under `kept`.
- **AC-002** Given a finished setup for Claude Code whose listed guardrails were never written, when doctor runs, then its `guardrails` row warns, naming how many are missing and `scaffold.py guardrails --render` as the fix; with them written, the row is ok.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_guardrails_render.py › GuardrailsRenderTest.test_render_writes_every_guardrail_and_keeps_edited_ones | `py -3.10 -m unittest discover -s tests -t tests -p test_guardrails_render.py -k test_render_writes_every_guardrail_and_keeps_edited_ones` |
| AC-002 | tests/test_guardrails_render.py › GuardrailsRenderTest.test_doctor_warns_when_guardrails_were_never_written | `py -3.10 -m unittest discover -s tests -t tests -p test_guardrails_render.py -k test_doctor_warns_when_guardrails_were_never_written` |

## Must never break

- `scaffold.py guardrails` without `--render` prints the list as before and writes nothing.
- A guardrail the user deleted and `forget`-ed is never written back.

## Out of scope

- Other setup steps the agent might loop over (`rules` names its renders one by one).

## Review

- **Recommended and chosen:** code (Public Surface not none: `scaffold.py guardrails --render`); chosen by the trigger list (low risk, not asked); the built-in `code-review` skill, `high --max-findings all`.
- **Verdicts:** `.sdlc/.work/findings/2026-11-17-m-guardrails-render/code-reviewer-r1.md` FAIL — F1, F2, F3, F4, F5, F8, F11 (no high; bugs in round 1) → `code-reviewer-r2.md` PASS on highs (none), its medium and low bugs fixed without another round. Ratings: medium for a partial write leaving files unrecorded, a link aborting the batch, doctor's wrong advice, a deleted guardrail written back, the unseen kept list, the root cause in render, rendering behind the plugin; low for the rest.
- **Fixed:** `--render` calls `cmd_render` per guardrail (recorded as it goes), leaves deleted, declined, outside and edited ones, refuses without Claude Code and on a scaffold behind the plugin, and reports any failure with the full result (exit 1), telling written-but-unrecorded apart; `render` strips a trailing `\r` or space from its template and dest, so setup's rules loop and upgrade's add loop can't hit C3 either; doctor's row covers rules and guardrails on a current scaffold, skips paths outside the repo, and names the exact command per missing file; setup shows each kept guardrail to the user. Tests: `tests/test_guardrails_render.py` (AC-001, AC-002), `tests/test_guardrails_render_review.py`.
- **Tickets:** doctor's row re-implements upgrade-plan's `add` list; one lock save per guardrail; outside and edited checks done twice; the review counted more tests than the user's one-per-behaviour rule asks (kept: each covers a bug a review found).
- **Drift and manual checks:** Deviations: the repo isn't set up for sdlc (full suite by hand: 672 tests OK, Python 3.10); `guardrail_list`; the AC-002 test's ok case writes the rules too (doctor's row widened), re-red at Base; the review fixes. Smoke part C rerun on the fixed tree (round 1): C1–C5 pass, the setup session ran `guardrails --render`, all 15 guardrails written and recorded, doctor's `guardrails` row ok.
- **Lessons filed:** none beyond the fix: the C3 class was a known issue since 3.10.0, and the structural fix (one call, and `render` stripping `\r`) replaces the note.
