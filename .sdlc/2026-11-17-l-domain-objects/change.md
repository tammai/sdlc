# An opt-in domain model (`objects.md`): format, check, brief, doctor and the Define/Review/Learn wiring

## Why

**Request (verbatim):** "L: build parts B1 and B2 of the opt-in domain model (objects.md) from C:/Users/Admin/Downloads/proposal-domain-model.md, which is the signed-off written spec (sign-off table D1-D8 decided 2026-11-17). B3 and B4 are out of scope until the measurement passes. Follow the user's testing rule: about 10 ACs or fewer, one test per user-visible behaviour."

The spec is the proposal (signed off 2026-11-17, D1–D8 decided), copied into this repo as `docs/specs/13-domain-model.md` so the record doesn't point outside it: a project's objects, their names, states and rules in one file every change reads, so two changes stop naming one thing two ways and a rule stated once is checked in every later review.

**The user's words:** sign-off answers 2026-11-17: the file is `objects.md`, not `domain.md` (rspec owns that name with another format; D8); the token bar is +10% over 3.11.0 (D6); D1–D7 accepted as proposed; build B1+B2 now, B3/B4 after the measurement.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| `scripts/objects.py check [FEATURE]`, JSON in the `problems.py` shape, exit 1 on an error, nothing when the switch is off | a check inside `verify.py` | the spec names a script run in Define's gate call, beside `capabilities.py check`; keeps `verify.py` unchanged when the switch is off |
| Switch `"objects": true` (file at `<docs>/objects.md`) or a repo-relative path to the file | only `true` | spec §The file: "or a path, following `living_spec`"; the path is checked like `docs_dir` (in the repo, not in `.git`) |
| A spec-backed repo: the switch is ignored, and `brief.py` prints a pointer to rspec's `<spec>/domain.md` (read-only) instead | reading `objects.md` there too | D5 as decided |
| UI files are those matching config's `areas.ui` (defaults included), with doctor's own glob matcher | a new matcher | one definition of "UI file" across doctor and the check |
| A rule line in `## Rules` that doesn't start `**DR-nnn**` is malformed (error) | allowing plain rule lines | the spec makes every rule a stable `DR` id that Review cites |
| Avoid words are matched whole-word, case-insensitive, in `## Acceptance criteria` only | user-visible text too | the spec's rule table; text in code is Review's (medium) |
| The doctor stale-object check takes the first word of `Code:` | every word | decided in the spec's rule table (`Invoice` in `Invoice (table invoices)`) |
| D2 (which additions need the owner's answer) lives in `flow.md`'s Define step, not in a script | a script check | D2 is about who decides, which only the agent can ask |
| ADR 0028 records the design, the rename and D1–D8 | none | every plugin-shaping decision has an ADR |

**Proposals not asked for:** None.

## Acceptance criteria

- **AC-001** spec §objects.py check: Given `"objects": true` and `<docs>/objects.md` copied from the plugin's `templates/objects-template.md`, when `objects.py check` runs, then it prints `{"ok": true, "problems": []}` and exits 0; with no `objects` key, it prints the same without reading any file.
- **AC-002** spec §objects.py check (errors): Given the switch on, when the file is missing, has a code span not declared on a `States:` line, names one object twice or also under `## Avoid`, or has a duplicated or malformed `DR` id, then each is an error with its own `code`, and the check exits 1.
- **AC-003** spec §objects.py check (warnings): Given the switch on, when the file is over 200 lines, or the repo has `areas.ui` files and an object lacks `UI name` or `Shown as`, then each is a warning and the check exits 0.
- **AC-004** spec §objects.py check, with FEATURE: Given an Avoid word (whole word, any case) in the feature's `## Acceptance criteria`, when `objects.py check <feature>` runs, then it is a warning on an M feature (exit 0) and an error on an L feature (exit 1).
- **AC-005** spec D5: Given a spec-backed repo (a tracked `criteria.lock.json`) with `"objects": true`, when `objects.py check` runs, then it checks nothing and exits 0, and `brief.py` prints a pointer to the rspec spec's `domain.md` and no `objects.md` section.
- **AC-006** spec §Where it enters the flow (Define): Given the switch on, when `brief.py` runs, then it prints an `objects: <path>` section with the file's text (cut at 200 lines); with the switch off it prints no such section.
- **AC-007** spec §Where it enters the flow (Doctor): Given the switch on, when doctor runs, then its `objects` check reports the file's problems, and warns when an object's `Code:` name appears in no tracked file other than `objects.md`.
- **AC-008** spec §Where it enters the flow (Define, Define gate): `flow.md` tells Define, when the brief has an `objects` section, to use its names and states in ACs, capability names and UI copy, to ask the owner before adding or renaming an object or changing or removing a `DR` rule (D2), and to run `objects.py check <feature>` in the gate call.
- **AC-009** spec §Where it enters the flow (Review, Learn): `review-brief.md`'s edges check each `DR` rule like a must-never-break line, an undeclared state transition, and an Avoid word or second name in user-visible text (medium), and its Severity list makes a finding that names a `DR` rule high; `managing-knowledge` files a fact about what an object is, its states or a rule it obeys into `objects.md`.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_objects.py › ObjectsTest.test_the_template_passes_and_the_switch_off_reads_nothing | `py -3.10 -m unittest discover -s tests -t tests -p test_objects.py -k test_the_template_passes_and_the_switch_off_reads_nothing` |
| AC-002 | tests/test_objects.py › ObjectsTest.test_each_file_error_has_its_code_and_fails | `py -3.10 -m unittest discover -s tests -t tests -p test_objects.py -k test_each_file_error_has_its_code_and_fails` |
| AC-003 | tests/test_objects.py › ObjectsTest.test_a_long_file_and_missing_ui_fields_warn | `py -3.10 -m unittest discover -s tests -t tests -p test_objects.py -k test_a_long_file_and_missing_ui_fields_warn` |
| AC-004 | tests/test_objects.py › ObjectsTest.test_an_avoid_word_in_the_criteria_warns_on_m_and_fails_on_l | `py -3.10 -m unittest discover -s tests -t tests -p test_objects.py -k test_an_avoid_word_in_the_criteria_warns_on_m_and_fails_on_l` |
| AC-005 | tests/test_objects.py › ObjectsTest.test_a_spec_backed_repo_reads_rspecs_domain_file_instead | `py -3.10 -m unittest discover -s tests -t tests -p test_objects.py -k test_a_spec_backed_repo_reads_rspecs_domain_file_instead` |
| AC-006 | tests/test_brief.py › BriefTest.test_prints_the_objects_file_only_when_the_switch_is_on | `py -3.10 -m unittest discover -s tests -t tests -p test_brief.py -k test_prints_the_objects_file_only_when_the_switch_is_on` |
| AC-007 | tests/test_doctor.py › DoctorTest.test_objects_check_and_unused_code_names | `py -3.10 -m unittest discover -s tests -t tests -p test_doctor.py -k test_objects_check_and_unused_code_names` |
| AC-008 | manual | instructions to the agent in `skills/orchestrator/references/flow.md`; the user's testing rule rules out a test that greps a document. Checked by review against the spec, and by the measurement eval |
| AC-009 | manual | instructions in `skills/orchestrator/references/review-brief.md` and `skills/managing-knowledge/SKILL.md`; no structural tests (user's testing rule). Checked by review against the spec |

## Must never break

- With no `objects` key in `.sdlc/config.json`, Define, Review, doctor and `brief.py` behave exactly as in 3.11.0: no new section, no new check row, no new problem.
- `scripts/contracts/v1/` stays byte-identical to its vendored source.
- S and Trivial never run `objects.py` or read `objects.md`.
- Nothing loads `objects.md` into always-loaded context (`CLAUDE.md`, a rule).

## Failure modes

- Untrusted input: `.sdlc/config.json`'s `objects` value is repo config; a path outside the repo or into `.git` is refused with a problem, never read (recurring defect "Repo config … names a file") → AC-002 (`objects_path_invalid`).
- Loaded data: `objects.md` that isn't valid UTF-8, config that isn't a JSON object, or `objects` of the wrong type gives a problem, never a traceback → AC-002.
- Scale: a long file is a warning, and `brief.py` cuts it at 200 lines → AC-003, AC-006.
- No crash mid-write: the check and the brief only read.

## Out of scope

- B3 (UI layer: `ui-work.md`, `ui-reviewer`, impeccable note) and B4 (`/sdlc:setup objects`), until the measurement passes on B1+B2.
- The measurement eval itself (a five-change sequence, switch off and on); it runs after this ships, when asked.
- Code generation from `objects.md`, a lint of state names in ACs (D3), navigation checks, any change to contracts v1 or to S and Trivial (spec §Out of scope).

## Review

- **Recommended and chosen:** code (L; Public Surface not none) and security (the repo config value `objects` becomes a file path the scripts read and the brief prints); chosen by the trigger list (L, self-chosen, `state.py log`).
- **Verdicts:** code `code-reviewer-r1.md` FAIL — H1, H2, M1, M2, M3 → `code-reviewer-r2.md` PASS; security `security-r1.md` FAIL — S1 → `security-r2.md` FAIL — R2-S1 → (user, review cap: one more fix round) `security-r3.md` FAIL — R3-S1 → (user, review cap: structural fix, one more check) `security-r4.md` PASS. All in `.sdlc/.work/findings/2026-11-17-l-domain-objects/`.
- **Fixed:**
  - H1/S1, R2-S1, R3-S1 (one class: the objects path judged by its spelling, then on one form only): `objects.path()` now runs one rule set, `_refused()`, on the path as written and where it leads, links followed, on both `true` and a named path: a `.md` name, no control or format character, nothing in `.git`, `.claude` or `.sdlc` (the old layout's own `.sdlc/objects.md` under `true` excepted, in any case). Tests: `tests/test_objects_review.py` › `test_a_path_is_judged_by_where_it_leads`, `test_every_path_rule_holds_where_a_link_leads_too`, `test_a_named_path_must_be_a_markdown_file_outside_sdlcs_own_folders`, `test_the_old_layout_keeps_its_file_under_sdlc`.
  - H2: the Review edge, its Severity clause and Learn's filing line are scoped to M and L, so S never reads or writes the file; Learn asks the owner first for a new or renamed object or a changed rule (M4). Instructions, checked by reading.
  - M1/S2 and R2-L3: `unused_code_names` reads git's matched words (`git grep -o -h`), never opens a file, leaves the objects file out by its written and resolved path in any case, and treats no git answer as no warning (`test_unused_code_names_read_gits_answer_right`, `test_the_objects_file_is_left_out_of_the_code_search_however_config_spells_it`).
  - M2: malformed `areas`/`ui` count as no UI files (`test_malformed_areas_and_config_give_json_not_a_traceback`).
  - M3: a feature the check can't find is `objects_feature_missing`; an unreadable track fails closed; flow.md places the check between `state.py new` and `advance 2` and says how to rerun it (`test_a_feature_the_check_cant_read_fails`).
  - L1, L2, L4, R4-L1, R4-L4: `->` arrows, `objects_avoid_line`, case-insensitive avoided names, one-line code spans, an `objects: invalid` brief section, the link case's message, rspec spec names with control characters kept out of the brief (`test_avoid_lines_and_names_are_read_in_every_spelling`, `test_an_invalid_path_still_gives_define_an_objects_section`, `test_an_rspec_spec_folder_name_cant_fake_a_brief_section`).
- **Tickets:** R4-L3, refusing Unicode format characters also refuses names with ZWNJ/ZWJ (Persian, Indic, emoji) in the objects path; L5, doctor computes `objects.path()` more than once and imports doctor lazily from `objects.py`; R4-L2, no junction test, and the link tests skip where symlinks can't be made; R2-L2/R4 8.3 short names and NTFS stream names rest on CPython's realpath (unconfirmed).
- **Drift and manual checks:** Deviations: the repo isn't set up for sdlc (the plugin itself), so the full suite was run by hand: 653 tests OK on Python 3.10; `tests/test_objects.py`'s long-file case changed (200 text lines, not newlines) with `red --at de19fb2`; module-level helpers in `objects.py` and `brief.py`; the round-1 test file and the CONTRIBUTING/Where-things-live rows; the runbook's smoke item. L3: a `.sdlc/config.json` that isn't a JSON object turns the switch off without a problem (doctor's config row reports it), so the Failure modes line above overstates it. AC-008 and AC-009 (manual): flow.md, review-brief.md and managing-knowledge/SKILL.md read against spec 13 O8–O10 by both code-review rounds and by me.
- **Security:** S1 → R2-S1 → R3-S1 closed in round 4; no dependency added, so no dependency audit applies; the security hooks raised nothing.
- **Lessons filed:** `.sdlc/recurring-defects.md` (a path rule checked on one form of the path only).
