# Definition of Done

The team's own bar for "done", which every change shows before Ship. It sits on top of what sdlc already checks (tests green, reviews passed, the record complete).

## The `done` step

**Ask first** (hard stop): what must be true before a change ships, beyond tests and review? Propose items from what the repo shows, for example:
- a `CHANGELOG.md` line for any user-visible change;
- docs updated where behaviour changed (a `docs/` folder or a README section);
- a migration note when a schema changes;
- screenshots for UI changes.

Keep the list to 10 or fewer one-line items, each of 200 characters or fewer, with no ` — ` in an item (it separates an item from its evidence).

- To record it: `$S done "<item>" "<item>" …` (the items given replace the list).
- If the user wants none: `$S step-done done`, and say in your next message that the project has no Definition of Done.
- `/sdlc:setup done` runs this step alone at any time, and `$S done --clear` removes the list. Commit the config change as the `review-rounds` row says: with a feature active, it stays in the working tree.

## What it does

- The brief prints the list, and Define copies it into the change file as `## Definition of Done`, one `- [ ] <item>` line each.
- Before Ship, each line is ticked with its evidence: `- [x] <item> — <evidence>`, or `- [x] <item> — n/a: <reason>`.
- `ship.py` refuses, with nothing moved, while an item is missing, unticked or without evidence.
- A change to the list is shown to the user by the trust anchor. For a feature in flight, Ship holds the live list plus the list the user last accepted (the trust anchor's record, else the list at the feature's Base): an item leaves the bar only through the user's reply to that notice.
- The section is ticked at Ship, after Review began, so ticking it is not a trust-anchor notice.
