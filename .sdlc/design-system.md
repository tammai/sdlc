# Design system: the sdlc-stepper band

The only UI this repo ships is the sdlc-stepper mod (`plugins/sdlc-stepper/`): one band above the prompt, in the terminal and in the desktop app. The UI review checks a change to it against this page.

## What the band shows

One row, left to right: the title `SDLC`, the mini stepper (the four stages Define, Build, Review, Ship as marks joined by short lines), a `·`, where the session is now (the agent's own latest update line, else phase · part · step), and at the right the feature (with `repo · ` in a workbench). The words take the room left and are cut with an ellipsis at the end; the feature keeps its own room and is cut at the start.

## Stage marks

| State | Terminal | Desktop |
|---|---|---|
| done | `✓` in `success` | check in a green disc |
| current | `●` in `success` | white dot in a green disc, with the pulse ring |
| current, waiting for the merge (Ship, checks passed) | `●` in `success` | the same dot, without the pulse; alt `Ship: waiting for merge` |
| blocked | `◌` in `warning` (no state reaches it yet) | (not drawn yet: an empty ring) |
| ahead | `○` in `inactive` | empty gray ring |

State is told by shape as well as colour, so it reads without colour. Done and current share the green; the mark tells them apart.

The lines between marks: `─` in `success` once the work is past the stage before it, else `inactive` and dimmed (terminal); a 6px, 1px-high line in green, else gray at 45% opacity (desktop).

## Colour

- **Terminal:** theme keys only, never a literal colour: `success`, `warning`, `inactive`, and `dimColor` for secondary text (the `·` and the feature). The outline is `round` in `inactive`.
- **Desktop:** mods can't read the app's theme, so the drawing uses two colours that read on a white and a black ground alike: green `#2DA44E` and gray `#7C828C` (rings at 70% stroke opacity), with white `#fff` for the check and the dot. The words use the app's text sizes (`caption`, `semibold` for the title) and `dimColor`.

## Motion

One animation only: on the desktop, the current stage's ring spreads out and fades (radius 8 → 11.5, stroke opacity 0.6 → 0, 1.8s, repeating), except while Ship waits for the merge. Nothing else moves; the terminal band never pulses.

A merged ship draws every stage done (`Ship · done`); a merge that failed reads `Ship · merge failed` with Ship current.

## Layout and fit

- Terminal: a rounded outline when the band gets 3 rows or more, else the row alone (the engine hides a band that doesn't fit). Under 60 columns the feature name is left out. The title `SDLC` is bold.
- Desktop: one row with `gap` 2 between the groups and `xs` inside them, `paddingX` 1; the mini stepper is 20px high with 16px icons.

## Accessibility

- The desktop drawing carries alt text per stage (`Build: in progress`, `Review: not started`).
- Never colour alone: every state has its own mark.
