# Spec: intent.md on every track

Status: approved 2026-10-26 (the user's answers to the proposal: name `intent.md`, S's replaces `brief.md`, the approach is confirmed in Define's one approval) · Track M, `Flow: lite` · Branch: `tammai/lite-and-slices`

Intent: [intent.md](intent.md)

## Goal

Every feature, on every track, gets one `intent.md` that a reviewer reads first. It says what was asked and why, which approaches were weighed, which one was chosen and why, and how the chosen one works. It does this without adding a question or a stop to S or M.

## Requirements

- **FR-001** Define writes `<intents>/intent.md` on every track, from `templates/intent-template.md`, under fixed headings:
  1. Intent and why (with the request verbatim)
  2. Questions and answers
  3. Approaches considered (2–3, each with trade-offs)
  4. Chosen approach and why
  5. The chosen approach in detail
  6. Goals, non-goals, constraints
  7. Calls made, and what's left to the builder
- **FR-002** Depth by track:
  - **S:** the orchestrator writes about 10–20 lines; the file replaces `brief.md` as the implementer's brief.
  - **M:** the orchestrator writes about a page after reading the code, without loading `sdlc:brainstorming`.
  - **L:** `sdlc:brainstorming` writes it in place of `brainstorm.md`, interview and builder check as today.
- **FR-003** No new question or stop:
  - on S and M the agent recommends the approach, and the user confirms it or picks another in Define's one approval;
  - S still has no approval;
  - L keeps choosing the approach in the brainstorming conversation.
- **FR-004** No duplication:
  - the spec links `intent.md` instead of carrying an `## Intent` section;
  - when a design runs, section 5 summarizes `design.md` and links it.
- **FR-005** Features started earlier keep working: a skill that reads `intent.md` falls back to `brainstorm.md` or `brief.md`.

## Acceptance criteria

1. `define.md` has every track write `intent.md` with the seven headings, sized as FR-002 says, and its approval message shows the chosen approach.
2. `build.md` and `ui-work.md` hand S's implementer `intent.md`; `brief.md` is no longer written.
3. `sdlc:brainstorming` writes `intent.md` with the seven headings.
4. `sdlc:writing-specs`, `sdlc:designing-solutions` and the spec template read or link `intent.md`, falling back to `brainstorm.md`; the spec template has no `## Intent` section.
5. The docs (guidebook, playbook, specs 02 and 03, prune's kept files, CHANGELOG) name `intent.md`; the stale-docs audit finds no stale `brief.md`, `brainstorm.md` or `## Intent`.

Failure modes: none apply (instruction text only; no data, I/O or concurrency).

## Non-goals

- Loading `sdlc:brainstorming` on S or M, or a separate "pick an approach" message.
- An approval step on S.
- Renaming `brainstorm.md` in features already written.

## Tasks

1. `templates/intent-template.md` (new); `skills/orchestrator/references/define.md`, `build.md`, `ui-work.md`: FR-001–004, AC 1–2. Instructed only.
2. `skills/brainstorming/SKILL.md`, `skills/writing-specs/SKILL.md`, `skills/designing-solutions/SKILL.md`, `templates/spec-template.md`: FR-002, 004, 005, AC 3–4.
3. Docs: guidebook, playbook, specs 02 and 03, ADR 0010 note, `scripts/prune.py` and `commands/prune.md` kept-files wording, CHANGELOG; stale-docs audit. AC 5.

## Public Surface

- `templates/intent-template.md`
- `<intents>/intent.md` (replaces `brief.md` on S and `brainstorm.md` on L)
