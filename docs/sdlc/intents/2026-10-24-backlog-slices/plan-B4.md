# Slice B4 plan: yolo

Spec FR-10, AC 7 · Backlog B4.

## Tasks

1. `scripts/yolo.py`: one `claude -p "/sdlc:start B<n> --yolo"` per ready slice, then one feature-close session; stops on an open trust-anchor notice, a `blocked:` row, nothing ready, or an unchanged status — tests `tests/test_yolo.py` (each slice then close once; unchanged status stops; open notice stops before any run), against a stub `claude` on PATH. (FR-10)
2. `commands/start.md` and the orchestrator: `--yolo` means no one is there to answer: never ask; anything that would ask (a failed gate, a scope-adding proposal, a hard stop) sets the row `blocked: <reason>` and ends the session; per-slice gates are off; feature close ends at Stage 8's question. Rebuild `hosts/skills/`. (FR-10)
3. Docs: spec 02, README, guidebook, playbook, CHANGELOG, CONTRIBUTING layout.

## Public Surface

- script `scripts/yolo.py` (`--root`, `--permission-mode`, `FEATURE`) — FR-10
- `/sdlc:start ... --yolo` flag — FR-10
