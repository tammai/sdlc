# Slice B1 plan: state.py and the control contract

Spec FR-03, AC 1–2 · Backlog B1.

## Tasks

1. `scripts/state.py` (advance, round, verified, log, slice, blocker, set, sync) writing `state.md` and `.sdlc/.work/contract/<feature>/` — tests `tests/test_state.py`: a stage move updates `state.md`, `state.json` and one event, and the freshness hook reads it; a malformed `state.md` is refused and nothing is written. (FR-03)
2. `docs/specs/12-control-contract.md` (fields, event types, `commands/` format, versioning); specs README, prd, CONTRIBUTING, CHANGELOG. The orchestrator switches to `state.py` in B2.

## Public Surface

- script `scripts/state.py` and its subcommands — FR-03
- files `.sdlc/.work/contract/<feature>/state.json`, `events.jsonl`, `commands/` — FR-03
