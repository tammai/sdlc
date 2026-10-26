# Spec: Define writes what, why and how to files

Status: approved 2026-10-26 (the user: "all three for S, option a for slices") · Track M, `Flow: lite` · Intent: [intent.md](intent.md) · Plan: [plan.md](plan.md)

## Goal

When Define ends, every track has `intent.md` (why), `spec.md` (what) and `plan.md` (how), each readable by an agent with no conversation context.

## Requirements

- **FR-001** Define writes all three files on every track (S included), sized by track, and they are approved together in the one approval (S: none).
- **FR-002** `spec.md` holds only what and why: no tasks, files or code structure.
- **FR-003** `plan.md` holds the how:
  - ordered tasks, each with its files, first test, command and FR;
  - Public Surface;
  - UI mapping (on UI work);
  - Review Focus.

  Lite and S write it from `templates/plan-template.md`; full flow and L use `sdlc:writing-plans`, which asks no execution question under the orchestrator.
- **FR-004** Nothing the build needs lives only in the conversation. Build follows `plan.md` and records any deviation in it.
- **FR-005** Prove's surface check and the reviewer brief read `plan.md` (or `plan-B<n>.md` per slice).
- **FR-006** A backlog feature's `plan.md` gives a how-outline per slice; each slice's detailed `plan-B<n>.md` is written as a file when the slice starts.

## Acceptance criteria

1. `define.md` has S, Lite, full flow and L each write `intent.md`, `spec.md` and `plan.md`, and its approval lists all three.
2. Lite's spec sections and `writing-specs` contain no Tasks or Public Surface; `plan-template.md` and `writing-plans` do.
3. `build.md` builds from `plan.md` on every `Build:` value, S's implementer gets the three files, and a deviation is written into `plan.md`.
4. `prove.md`'s diff-facts call passes `--plan <intents>/plan.md`; `diff_stats.py` reads the template's `## Public Surface` (existing behaviour; no code change).
5. `backlog-slices.md` writes the outline in `plan.md` during Define, and `plan-B<n>.md` at slice start.
6. Docs and diagrams name the three files; the stale-docs audit finds no "Tasks in the spec" left.

Failure modes: none apply (instruction text only).

## Non-goals

Team mode; detailed slice plans in Define; changes to prune, hooks or `diff_stats.py`.
