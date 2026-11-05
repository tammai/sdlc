# Spec 12: State changes and the control contract

Every change to a feature's state goes through one call, which updates `state.md` (the model's view and the committed record) and writes machine-readable files that a headless runner or a control app ("flightdeck") reads without knowing the pipeline's internals.

**Entry points:** `python3 scripts/state.py` (called by the orchestrator) · **Source:** `scripts/state.py`, `skills/orchestrator/SKILL.md`

## User scenarios

1. **A stage moves.** Given a feature at Stage 2, when the orchestrator runs `state.py advance <feature> 3 --gate pass`, then `state.md` reads `Current: Stage 3 – Review` with Stage 2 ticked and a Gate log line, the hooks treat the feature as in Stage 3, `state.json` shows Stage 3, and one `stage_entered` event is appended.
2. **A damaged state file.** Given a `state.md` without a `Current:` line, any `state.py` call exits 1 with a JSON error and writes nothing.
3. **A control app watches.** It reads `state.json` for the current picture and tails `events.jsonl` for what happened, and later drops command files in `commands/` for the runner.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| CTL-FR-001 | `state.py` subcommands, each one call: `advance FEATURE STAGE [--gate pass\|fail] [--note] [--verified [COMMIT TREE]]` (a bare `--verified` records the last passing verify run's head and tree, and is refused when none is current; Gate log line for the stage being left, its checklist line ticked on pass, `Current:` set; advancing to the current stage is refused), `verified FEATURE COMMIT TREE`, `log FEATURE TEXT [--type note\|review_done]` (Gate log line), `deviation FEATURE TEXT` (a `## Deviations` line, which the sdlc-invariants CI check reads), `slice FEATURE start\|done\|block B<n> [COMMIT \| REASON]` (`Slice:` line and the backlog row; `block` also adds an open question), `blocker FEATURE raise\|resolve TEXT` (Open questions), `set FEATURE FIELD VALUE` (Status, Track, Risk, Build, Top model, Base, Owner, Tool, Slice gates, Process; the value is replaced and a trailing `(comment)` kept; Slice gates is edited inside the `Slice:` line), `sync FEATURE` (re-derive `state.json`, no event), `migrate` (every `Process: 2` state file to the current stage numbers, CTL-FR-008), `new FEATURE --track S\|M\|L --risk low\|high --task "<title> \| <ACs> \| <files>" … [--surface "<kind> <name> — <AC>" …] [--handoff …] [--build …] [--risk-why …] [--sized …] [--footprint N]` (writes the state file from the track's template, looking up Base, Owner, the test command and the date; refuses a name that already has one, and a `--surface` without a kind (export, endpoint, command, config, env, dependency), writing each as `` - <kind> `<name>` — <AC> ``, the form `verify.py`'s drift check reads; starts the contract with a `feature_started` event). | `[enforced]` test_state › test_advancing_a_stage_updates_state_md_the_snapshot_and_one_event (advance), test_new_writes_the_state_file_from_defines_answers (new), test_slice_gates_are_set_on_the_slice_line, test_a_deviation_goes_under_deviations, test_new_writes_the_public_surface_in_the_form_verify_reads, test_a_bare_verified_without_a_passing_verify_run_is_refused_and_moves_nothing, test_ship › test_a_bare_verified_records_the_head_and_tree_verify_passed_on; the rest `[instructed]` by the script's usage |
| CTL-FR-002 | `Current:` is always written as `Current: Stage <n> – <name>`, the form the freshness hook, trust anchor and model router match. The four phases run at one number each (1 Define, 2 Build, 3 Review, 4 Ship); a part rests at Stage 2 once committed. | `[enforced]` test_state › test_advancing_a_stage_updates_state_md_the_snapshot_and_one_event, test_a_feature_moves_through_four_phases |
| CTL-FR-007 | A state file without a `Process:` line was started under sdlc 1.x: every call that would change it is refused with how to finish it (sdlc 1.8.1, or archive it with `Status: done`), and nothing is written. | `[enforced]` test_state › test_a_1x_feature_is_refused_with_how_to_finish_it |
| CTL-FR-008 | A state file with `Process: 2` (sdlc 2.x, phases at stages 1, 4, 5, 8) is refused the same way, with `/sdlc:upgrade` as the fix. `state.py migrate` rewrites every `Process: 2` state file to `Process: 3` and stages 1 to 4 (the `Current:` line, the Stages checklist and the Gate log), keeps CRLF, drops the trust anchor's remembered stage for it, rewrites the snapshot, skips a file holding a stage it can't map and says why, and does nothing the second time. | `[enforced]` test_state › test_a_2x_feature_is_refused_and_told_to_migrate, test_migrate_renumbers_a_2x_feature_and_only_that, test_migrate_skips_a_file_it_cannot_map_and_says_why |
| CTL-FR-003 | A `state.md` without `Status:` or a well-formed `Current:` line is refused: exit 1, `{"ok": false, "error": …}`, and neither `state.md` nor the contract files change. An unknown feature, a value with a line break, or a failed write is refused the same way (a failed write names the files already written; `sync` repairs the contract); usage errors, a non-numeric stage included, exit 2, also as JSON. | `[enforced]` test_state › test_a_malformed_state_file_is_reported_not_mirrored, test_advancing_to_the_current_stage_is_refused |
| CTL-FR-006 | Everything is computed before anything is written, then `backlog.md`, `state.md`, `state.json` and the event are written in that order: each file through a temp file, fsync and rename, so a crash or a reader never sees half a file; the event appended and synced. Line endings (CRLF) and a backlog's BOM are kept; the backlog's Status cell is found by its column name. | `[instructed]` the script |
| CTL-FR-004 | The contract files are git-ignored runtime files beside the state file: `.sdlc/state/<feature>.json`, `<feature>.events.jsonl` and `<feature>.commands/`, in either layout (an old-layout feature folder holds only documents, so `relocate` moves nothing of the contract). Setup's `gitignore` step adds the patterns, and `/sdlc:upgrade` re-runs it for repos set up before. One set per worktree, so parallel slices in separate worktrees don't conflict. `state.md` stays the committed record; `state.json` is derived from it. | `[enforced]` location: test_state › test_advancing_a_stage_updates_state_md_the_snapshot_and_one_event, test_an_old_layout_feature_keeps_its_contract_where_the_ignore_patterns_cover_it; ignore patterns `[instructed]` setting-up-projects |
| CTL-FR-005 | The orchestrator changes state only through `state.py`; a hand edit leaves `state.json` behind until the next call or `sync`. | `[instructed]` orchestrator |

## `state.json`

Written whole (temp file, fsync, rename) on every call.

| Field | Type | Meaning |
|---|---|---|
| `contract_version` | int | `3` (2 while the phases ran at stages 1, 4, 5 and 8; 1 before the phases: stage names Discover, Implement, Verify, PR / CI; no `phase`) |
| `feature` | string | the feature's name |
| `updated` | string | UTC time of this write, `YYYY-MM-DDThh:mm:ssZ` |
| `status`, `track`, `risk`, `build`, `top_model`, `base`, `owner`, `tool`, `process` | string or null | the first word of the matching `state.md` line (`process`: `3` on a current feature) |
| `current` | `{stage: int, name: string}` | from `Current:` |
| `phase` | string | `define` (1), `build` (4), `review` (5), `ship` (8) |
| `slice` | `{id, base, gates}` or null | from the `Slice:` line |
| `backlog` | `[{id, status}]` or null | the backlog table, when the feature has one |
| `verified` | `{commit, tree}` or null | from `Verified:` |
| `gates` | `[{date, stage, result, note}]` | Gate log lines of the form `<date> Stage <n>: pass\|fail — note` |
| `verify_rounds` | `[{round, commit, result, reason}]` | a 1.x state file's Verify rounds lines; always empty on 2.0 |
| `open_questions` | `[string]` | Open questions lines: the feature's blockers |
| `spend` | object or null | reserved; null until spend is known |

## `events.jsonl`

One JSON object per line, appended, never rewritten. Every event has `ts` (UTC, as above), `feature` and `type`. Each `state.py` call except `sync` appends exactly one.

| `type` | From | Extra fields |
|---|---|---|
| `stage_entered` | `advance` | `from`, `stage`, `gate` (`pass`, `fail` or null), `note` |
| `verified` | `verified` | `commit`, `tree` |
| `note`, `review_done` | `log` | `text` |
| `slice_started` | `slice start` | `slice`, `base` |
| `slice_done` | `slice done` | `slice`, `commit` (null: it runs before the part's commit, which names the part) |
| `slice_blocked` | `slice block` | `slice`, `reason` |
| `deviation_logged` | `deviation` | `text` |
| `blocker_raised`, `blocker_resolved` | `blocker` | `text` |
| `field_set` | `set` | `field`, `value` |
| `feature_started` | `new` (writes the state file from Define's answers) | `state` (its path) |
| `feature_done` | `set … Status done` | — |

## `commands/` (reserved)

The runner's inbox: one JSON file per command, `<id>.json`, with `id` (unique string), `ts`, `type` (`approve`, `answer`, `pause`, `resume`, `cancel`, `set_budget`) and `payload` (an object, by type). The runner creates the folder and turns commands into prompts. The engine never reads or executes a command, and a file there is never the user's approval or answer.

## Versioning

Adding a field, an event type or a command type keeps `contract_version`. Removing or renaming one, or changing a field's type or meaning, bumps it. Readers ignore fields and event types they don't know.

## Known gaps

- Nothing stops a hand edit to `state.md`; `state.json` then lags until the next `state.py` call.
- `spend` is always null.
