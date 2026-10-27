# Spec 12: State changes and the control contract

Every change to a feature's state goes through one call, which updates `state.md` (the model's view and the committed record) and writes machine-readable files that a headless runner or a control app ("flightdeck") reads without knowing the pipeline's internals.

**Entry points:** `python3 scripts/state.py` (called by the orchestrator) · **Source:** `scripts/state.py`, `skills/orchestrator/SKILL.md`

## User scenarios

1. **A stage moves.** Given a feature at Stage 4, when the orchestrator runs `state.py advance <feature> 5 --gate pass`, then `state.md` reads `Current: Stage 5 – Review` with Stage 4 ticked and a Gate log line, the hooks treat the feature as in Stage 5, `state.json` shows Stage 5, and one `stage_entered` event is appended.
2. **A damaged state file.** Given a `state.md` without a `Current:` line, any `state.py` call exits 1 with a JSON error and writes nothing.
3. **A control app watches.** It reads `state.json` for the current picture and tails `events.jsonl` for what happened, and later drops command files in `commands/` for the runner.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| CTL-FR-001 | `state.py` subcommands, each one call: `advance FEATURE STAGE [--gate pass\|fail] [--note]` (Gate log line for the stage being left, its checklist line ticked on pass, `Current:` set; advancing to the current stage is refused), `verified FEATURE COMMIT TREE`, `log FEATURE TEXT [--type note\|review_done]` (Gate log line), `deviation FEATURE TEXT` (a `## Deviations` line, which the sdlc-invariants CI check reads), `slice FEATURE start\|done\|block B<n> [COMMIT \| REASON]` (`Slice:` line and the backlog row; `block` also adds an open question), `blocker FEATURE raise\|resolve TEXT` (Open questions), `set FEATURE FIELD VALUE` (Status, Track, Risk, Build, Top model, Base, Owner, Tool, Slice gates, Process; the value is replaced and a trailing `(comment)` kept; Slice gates is edited inside the `Slice:` line), `sync FEATURE` (re-derive `state.json`, no event). | `[enforced]` test_state › test_advancing_a_stage_updates_state_md_the_snapshot_and_one_event (advance), test_slice_gates_are_set_on_the_slice_line, test_a_deviation_goes_under_deviations; the rest `[instructed]` by the script's usage |
| CTL-FR-002 | `Current:` is always written as `Current: Stage <n> – <name>`, the form the freshness hook, trust anchor and model router match. The four phases run at one number each (1 Define, 4 Build, 5 Review, 8 Ship); a part rests at Stage 4 once committed. | `[enforced]` test_state › test_advancing_a_stage_updates_state_md_the_snapshot_and_one_event, test_a_2_0_feature_moves_through_four_phases |
| CTL-FR-007 | A state file without `Process: 2` was started under sdlc 1.x: every call that would change it is refused with how to finish it (sdlc 1.8.1, or archive it with `Status: done`), and nothing is written. | `[enforced]` test_state › test_a_1x_feature_is_refused_with_how_to_finish_it |
| CTL-FR-003 | A `state.md` without `Status:` or a well-formed `Current:` line is refused: exit 1, `{"ok": false, "error": …}`, and neither `state.md` nor the contract files change. An unknown feature, a value with a line break, or a failed write is refused the same way (a failed write names the files already written; `sync` repairs the contract); usage errors, a non-numeric stage included, exit 2, also as JSON. | `[enforced]` test_state › test_a_malformed_state_file_is_reported_not_mirrored, test_advancing_to_the_current_stage_is_refused |
| CTL-FR-006 | Everything is computed before anything is written, then `backlog.md`, `state.md`, `state.json` and the event are written in that order: each file through a temp file, fsync and rename, so a crash or a reader never sees half a file; the event appended and synced. Line endings (CRLF) and a backlog's BOM are kept; the backlog's Status cell is found by its column name. | `[instructed]` the script |
| CTL-FR-004 | The contract files are git-ignored runtime files beside the state file: `.sdlc/state/<feature>.json`, `<feature>.events.jsonl` and `<feature>.commands/`, in either layout (an old-layout feature folder holds only documents, so `relocate` moves nothing of the contract). Setup's `gitignore` step adds the patterns, and `/sdlc:upgrade` re-runs it for repos set up before. One set per worktree, so parallel slices in separate worktrees don't conflict. `state.md` stays the committed record; `state.json` is derived from it. | `[enforced]` location: test_state › test_advancing_a_stage_updates_state_md_the_snapshot_and_one_event, test_an_old_layout_feature_keeps_its_contract_where_the_ignore_patterns_cover_it; ignore patterns `[instructed]` setting-up-projects |
| CTL-FR-005 | The orchestrator changes state only through `state.py`; a hand edit leaves `state.json` behind until the next call or `sync`. | `[instructed]` orchestrator |

## `state.json`

Written whole (temp file, fsync, rename) on every call.

| Field | Type | Meaning |
|---|---|---|
| `contract_version` | int | `2` (1 before the phases: stage names Discover, Implement, Verify, PR / CI; no `phase`) |
| `feature` | string | the feature's name |
| `updated` | string | UTC time of this write, `YYYY-MM-DDThh:mm:ssZ` |
| `status`, `track`, `risk`, `build`, `top_model`, `base`, `owner`, `tool`, `process` | string or null | the first word of the matching `state.md` line (`process`: `2` on a 2.0 feature) |
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
| `slice_done` | `slice done` | `slice`, `commit` |
| `slice_blocked` | `slice block` | `slice`, `reason` |
| `deviation_logged` | `deviation` | `text` |
| `blocker_raised`, `blocker_resolved` | `blocker` | `text` |
| `field_set` | `set` | `field`, `value` |
| `feature_done` | `set … Status done` | — |

## `commands/` (reserved)

The runner's inbox: one JSON file per command, `<id>.json`, with `id` (unique string), `ts`, `type` (`approve`, `answer`, `pause`, `resume`, `cancel`, `set_budget`) and `payload` (an object, by type). The runner creates the folder and turns commands into prompts. The engine never reads or executes a command, and a file there is never the user's approval or answer.

## Versioning

Adding a field, an event type or a command type keeps `contract_version`. Removing or renaming one, or changing a field's type or meaning, bumps it. Readers ignore fields and event types they don't know.

## Known gaps

- Nothing stops a hand edit to `state.md`; `state.json` then lags until the next `state.py` call.
- `spend` is always null.
