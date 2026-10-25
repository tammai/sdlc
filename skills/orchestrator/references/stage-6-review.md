# Stage 6 · Review (closing)

The review itself ran in Stage 5's parallel round, and its fixes were re-verified there. Stage 6 closes it:

- The reviewer must not be the context that wrote the code; there is no separate simplifier pass (simplifications came in as findings).
- Every high finding is fixed and re-verified, or the user waived it (record it with `state.py deviation`); medium and low are ticketed in `<intents>/review.md`.
- UI: the ui-reviewer's high findings are off-system values or components, AI-slop patterns, missing states and accessibility blockers. A visual check (screenshots) runs only when the user asks for one: say so in its brief; it uses a browser tool and the dev server if they're available, and reports it if not. Its "Proposed design-system changes" go to the user: accepted, add them to `<docs>/design-system.md`, log it, and the findings they cover are resolved; declined, the code moves to an existing token or component (a code change, so back to Stage 5 for a re-verification).
- Any code change after the Stage 5 gate (a waived finding taken back, a design-system decision) goes back to Stage 5 for a re-verification. Changes to tests or docs alone don't.
- Other review tools: `/sdlc:review-pr` locally before a PR (picks among the review agents by the diff), `sdlc:requesting-code-review` for a plan-vs-implementation review, `/sdlc:code-review` on a GitHub PR, `sdlc:receiving-code-review` for handling feedback (verify before agreeing; push back with evidence).
- **Gate:** no unresolved high-severity finding; findings fixed or ticketed in `<intents>/review.md`. Then `state.py advance <f> <next> --gate pass`.
