# Spec 13: The domain model (`objects.md`)

An opt-in file that says what a product's things are, what they're called, which states they move through and which rules they obey, so every change reads the same names and a rule stated once is checked in every later review. Signed off 2026-11-17 (decisions D1–D8 below); built in parts, B1 and B2 first.

**Entry points:** `"objects"` in `.sdlc/config.json` · `python3 scripts/objects.py check [FEATURE]` · **Source:** `scripts/objects.py`, `scripts/brief.py`, `scripts/doctor.py`, `templates/objects-template.md`, `skills/orchestrator/references/flow.md`, `skills/orchestrator/references/review-brief.md`, `skills/managing-knowledge/SKILL.md` · **Decision:** [ADR 0028](../adr/0028-domain-model-objects-md.md)

## Why

| Gap | Evidence before this spec |
|---|---|
| No shared vocabulary across changes | `ui-reviewer` checks copy against one change's spec, so two changes can name one thing two ways. |
| No object layer in UI work | `templates/design-system-template.md` lists components by UI need; no file says how an Invoice is shown or which actions it offers. |
| Domain rules live in one change at a time | `## Must never break` is per change file: a rule stated in March is invisible to a change in June. |
| Only spec-backed repos have a domain file | rspec writes `<spec>/domain.md` (roles, enumerations, limits, identifiers) for a rebuild; a standalone repo has nothing, and that format has no objects, states per object or UI layer. |

## Constraints

- Off by default: with no `objects` key, behaviour is as in 3.11.0.
- No new model turn: the checks are script-only (the C1 lint in Define was removed for its cost, `rebuild-upgrade/03-sdlc.md`).
- S and Trivial are untouched; S never calls `brief.py`.
- `scripts/contracts/v1/` is vendored and unchanged; the format keeps the file valid input for its `--domain` option, which takes every code span as a state.
- No always-loaded context: the file is read through `brief.py` and by reviewers, never imported into `CLAUDE.md` or a rule.
- One file, at most 200 lines (`brief.py`'s cut).
- Not named `domain.md`: rspec owns that name with another format, and both plugins run in a product-rebuild workbench (D8).

## The file

`<docs>/objects.md` (or the in-repo path `objects` names), project-owned like `design-system.md`: upgrade never overwrites it. The plugin's [template](../../templates/objects-template.md):

```markdown
## Objects

### Invoice
A request for payment sent to one Customer.
- UI name: Invoice, Invoices
- Code: Invoice (table invoices)
- Belongs to: Customer (one)
- Has: Line item (many)
- States: `draft` → `sent` → `paid`; `sent` → `void`
- Actions: send (draft), record payment (sent), void (sent)
- Shown as: InvoiceRow (list), InvoiceCard (summary), /invoices/:id (detail)

## Rules
- **DR-001** An Invoice in `paid` never changes its total.

## Avoid
- Bill, Receipt → Invoice
```

| Part | Rule |
|---|---|
| Code spans | State names only, declared on a `States:` line; every other identifier is plain text. |
| `UI name`, `Shown as`, `Actions` | The UI object layer; expected when the repo has `areas.ui` files. `Shown as` names components from the design system. |
| `DR-<nnn>` | Stable, never renumbered or reused; Review treats a broken one like a must-never-break line. |
| `## Avoid` | Names that must not appear in acceptance criteria or user-visible text, each with the name to use. |

## User scenarios

1. **Define reads it.** Given `"objects": true`, when a new M or L request is sized, the brief prints the file under `objects: <path>`, and the ACs, capability names and UI copy use its names and states.
2. **A gate catches a stray name.** Given an L change whose ACs say "Bill" and the file avoids it, Define's gate call runs `objects.py check <feature>`, which fails, naming "Bill" and "Invoice".
3. **A spec-backed repo.** Given an rspec criteria lock, the switch does nothing, and the brief points at rspec's `domain.md`, read-only.

## Requirements

| # | Requirement | Guarantee |
|---|---|---|
| O1 | With the switch off, `objects.py check` reads nothing and reports nothing; with it on, the plugin's template passes | `[enforced]` tests/test_objects.py › ObjectsTest.test_the_template_passes_and_the_switch_off_reads_nothing |
| O2 | Errors, exit 1, each with its code: the file missing (`objects_missing`), a code span no `States:` line declares (`objects_state_undeclared`), an object listed twice (`objects_duplicate`) or also avoided (`objects_avoided_name`), a duplicated or malformed `DR` id (`objects_rule_id`), an Avoid line without `→` or `->` (`objects_avoid_line`), a file that isn't UTF-8 (`objects_unreadable`) | `[enforced]` tests/test_objects.py › ObjectsTest.test_each_file_error_has_its_code_and_fails; tests/test_objects_review.py › ObjectsReviewTest.test_avoid_lines_and_names_are_read_in_every_spelling |
| O2a | The path is judged as written and where it leads, links followed, on both branches: a `.md` file inside the repo, never in `.git`, `.claude` or `.sdlc` (the old layout's own unlinked `.sdlc/objects.md` under `true` excepted), no control character (`objects_path_invalid`); nothing of a refused file reaches the brief | `[enforced]` tests/test_objects_review.py › ObjectsReviewTest.test_a_path_is_judged_by_where_it_leads, test_a_named_path_must_be_a_markdown_file_outside_sdlcs_own_folders |
| O3 | Warnings, exit 0: over 200 lines (`objects_too_long`); the repo has `areas.ui` files and an object lacks `UI name` or `Shown as` (`objects_ui_fields`) | `[enforced]` tests/test_objects.py › ObjectsTest.test_a_long_file_and_missing_ui_fields_warn |
| O4 | With FEATURE, an Avoid word (whole word, any case) in its `## Acceptance criteria` is a warning on M, an error on L or an unreadable track (`objects_avoid_word`); a feature it can't find in either layout is an error (`objects_feature_missing`) | `[enforced]` tests/test_objects.py › ObjectsTest.test_an_avoid_word_in_the_criteria_warns_on_m_and_fails_on_l; tests/test_objects_review.py › ObjectsReviewTest.test_a_feature_the_check_cant_read_fails |
| O5 | A spec-backed repo: the check does nothing, and the brief prints a pointer to rspec's `<spec>/domain.md` instead of the objects file | `[enforced]` tests/test_objects.py › ObjectsTest.test_a_spec_backed_repo_reads_rspecs_domain_file_instead |
| O6 | `brief.py` prints `objects: <path>` with the file (cut at 200 lines) only when the switch is on | `[enforced]` tests/test_brief.py › BriefTest.test_prints_the_objects_file_only_when_the_switch_is_on |
| O7 | Doctor's `objects` row (only when on): the check's problems, and a warning for an object whose `Code:` name (its first word) is in no tracked file but the objects file; no git answer (not a work tree, git missing) is never "unused" | `[enforced]` tests/test_doctor.py › DoctorTest.test_objects_check_and_unused_code_names; tests/test_objects_review.py › ObjectsReviewTest.test_unused_code_names_read_gits_answer_right |
| O8 | Define uses the file's names and states; adding or renaming an object, or changing or removing a `DR` rule, is asked of the owner before the build (D2); a new state, action or attribute goes ahead, recorded in `## Decisions`; the gate's call runs `objects.py check <feature>` between `state.py new` and the move to Build | `[instructed]` skills/orchestrator/references/flow.md |
| O9 | On M and L, Review checks each `DR` rule like a must-never-break line, an undeclared state transition, and an Avoid word or second name (medium in user-visible text, fixed in passing in identifiers); a finding naming a `DR` rule is high | `[instructed]` skills/orchestrator/references/review-brief.md |
| O10 | On M and L, Learn files a fact about an object, its states or a rule it obeys into the objects file, not `knowledge/`, asking the owner first for a new or renamed object or a changed rule | `[instructed]` skills/managing-knowledge/SKILL.md |

## Decisions (signed off 2026-11-17)

| # | Question | Decided |
|---|---|---|
| D1 | How does the file change? | Edited directly in the change, as `design-system.md` is; no merge script. |
| D2 | Which additions need the owner's answer before the build? | A new or renamed object, and a changed or removed `DR` rule, at any risk. A new state, action or attribute goes ahead, recorded in `## Decisions`. |
| D3 | Lint state names in ACs? | No: in standalone sdlc, code spans in ACs also hold commands and file names. |
| D4 | Workbench: one file or one per app? | One at the workbench root. |
| D5 | Spec-backed repos | The switch does nothing; the brief points at rspec's `<spec>/domain.md`, read-only. |
| D6 | Measurement thresholds | Below, relative to 3.11.0. |
| D7 | Overlap with impeccable's `PRODUCT.md` | When it already lists objects, the objects file links to it for the UI fields (B3). |
| D8 | File name | `objects.md`: rspec's `domain.md` has another format. |

## Measurement (before B3 and B4)

A five-change sequence on one product touching the same three or four objects, with the switch off and on, same models.

| Metric | Pass |
|---|---|
| Switch off: tokens and wall-clock per change | Same as 3.11.0 within run-to-run noise |
| Switch on: tokens on low-risk M | At most +10% over 3.11.0 |
| Distinct names per object in UI copy and identifiers after change 5 | Fewer than with the switch off |
| Review findings on naming, states or a broken earlier rule; questions asked in Define | Reported per run |

**Run 1, 2026-11-17, `b03a992`** (`eval-the-sdlc` task `seq-objects`, headless sonnet, one run per arm; its `results/2026-11-17-seq-objects-b03a992/summary.md`):

| Metric | Result |
|---|---|
| Switch off | As 3.11.0 by construction: `brief.py` and `doctor.py` print the same bytes; the instruction files grew about 1.9 KB |
| Switch on, tokens | +0.3% on the one low-risk M both arms ran as M; 0.89x over the three steps sized alike; 0.84x over all five |
| Names after change 5 | Off named the credit object two ways (credit, refund), on one; both one name for the rest |
| Questions | Same count (one each at changes 2 and 4): on asked D2's owner question for Payment and Credit, off asked plan approvals |
| Hidden tests | All 14 pass in both arms |

All four pass, on one run: step ratios spread from 0.49 to 1.23, and on sized changes 1 and 3 S where off chose M. Whether B3 and B4 go ahead is the owner's call.

## Known gaps

- **B3, the UI layer** (`ui-work.md`'s `## UI mapping` naming each object's `Shown as` and actions, `ui-reviewer` reading the file, the impeccable note) and **B4, `/sdlc:setup objects`** (greenfield draft from the PRD, brownfield from schema, types, enums and routes): built only if the measurement passes.
- Until B4, a repo writes its objects file by hand from the template.
- Out of scope: code generation from the file, navigation or URL checks, any change to contracts v1.
