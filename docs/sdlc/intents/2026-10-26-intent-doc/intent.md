# Intent: intent.md on every track

## Intent and why

**Request (verbatim)**: "currently, only tier L has brainstorm and interview user then brainstorm.md writen down. But a feedback on my team said the content in brainstorm.md is what he looking for when review, but tier s and m lack of it. How do you think to add this step to tier s and m too? and change the name to indent.md, this file must answer: the intent and why; the approachs suggested and which one choosen + explain why it choosen; the detail of choosen approach; plus it current content"

A reviewer on the user's team reads `brainstorm.md` first, because it says what was wanted and why the work took the shape it did. Only L features have one, so S and M reviews start from the spec and the diff without that context. Every feature should leave the same record, under one name.

## Questions and answers

- Name: `indent.md` or `intent.md`? → `intent.md`.
- S: replace `brief.md`, still with no approval? → yes.
- M: confirm the approach in Define's one approval, or in a separate message first? → in the approval.

## Approaches considered

| Approach | Trade-offs |
|---|---|
| A: run `sdlc:brainstorming` on every track | same depth everywhere, but a 2,500-word skill, an interview, a separate approach-pick message and a builder check on every fix: the extra time and touches the evals flagged |
| B: one `intent.md` template on every track, with depth scaled by track; brainstorming only on L | the same headings everywhere and no new question or stop; S and M get a shorter record written by the orchestrator |
| C: keep `brainstorm.md` for L, and add an Intent section to every spec | no new file, but the approaches and the chosen design don't fit a requirements document, and reviewers look in two places |

## Chosen approach and why

B. It gives the reviewer the same seven answers on every feature for the cost of one short file, without undoing the touch and token savings of the four-phases work. The user confirmed the three open choices.

## The chosen approach in detail

- `templates/intent-template.md` holds the seven headings.
- `define.md` writes the file on every track:
  - S: 10–20 lines, which is also the implementer's brief;
  - M: about a page, written after reading the code, with a recommended approach confirmed in the approval;
  - L: written by `brainstorming`.
- The approval message names the chosen approach.
- The spec template and `writing-specs` link `intent.md` instead of carrying an `## Intent` section. `designing-solutions` reads it, and the detail section links `design.md` when one runs.
- Readers fall back to `brief.md` or `brainstorm.md` for features started earlier.
- Instruction text and docs only; no script reads these files, and prune already keeps any file it doesn't list for deletion.

## Goals, non-goals, constraints

- Goals: one record per feature that answers the user's three questions plus brainstorm.md's current content.
- Non-goals: brainstorming on S or M; an approval on S; renaming files in finished features.
- Constraints: no new touch or question on S and M (the eval's main cost metrics); Codex, Cursor and Antigravity mirrors stay in step.

## Calls made, and what's left to the builder

- Calls: the spec links `intent.md` rather than keeping a short Intent section; the template is a plugin template, not a scaffolded project file.
- Left: nothing.
