# Stage 6 · Review

- The reviewer must not be the context that wrote the code. Every reviewer gets the brief in `review-brief.md`, with diff facts `--plan <intents>/plan.md` (no `--plan` on S).
- Polish first: run the `sdlc:code-simplifier` agent on the changed files before the reviewers, so they review the code that will merge.
- This is the feature's only whole-branch review (Stage 4 skipped its own), so on M and L the whole-branch `sdlc:code-reviewer` runs on the top tier (S and the Lite flow keep the standard tier, except a backlog feature's Feature close).
- S track ("light"): `sdlc:code-simplifier` then `sdlc:code-reviewer`, both with the diff facts.
- Any code change in this stage (the simplifier's, or a fix for a finding) sends the feature back to Stage 5 for another round before this gate passes (the Lite flow re-verifies in-session instead; see `lite-flow.md`). Changes to tests or docs alone don't.
- Severity: comment noise flagged by the diff facts or hookify warnings is medium and fixed in this stage, not ticketed.
- UI changed (the diff touches `areas.ui`): also dispatch `sdlc:ui-reviewer` on every track, with `<docs>/design-system.md`, the spec and the diff. Off-system values or components, AI-slop patterns, missing states and accessibility blockers are high severity. A visual check (screenshots) runs only when the user asks for one: say so in the brief; the reviewer uses a browser tool and the dev server if they're available, and reports it if not.
- The ui-reviewer's "Proposed design-system changes" go to the user. Accepted: add them to `<docs>/design-system.md`, log it, and the findings they cover are resolved. Declined: the code moves to an existing token or component (a code change, so back to Stage 5).
- Other review tools: `/sdlc:review-pr` locally before a PR (picks among the review agents by the diff), `sdlc:requesting-code-review` for a plan-vs-implementation review, `/sdlc:code-review` on a GitHub PR, `sdlc:receiving-code-review` for handling feedback (verify before agreeing; push back with evidence).
- **Gate:** no unresolved high-severity finding; findings fixed or ticketed in `<intents>/review.md`. Then `state.py log <f> "<summary>" --type review_done` and `state.py advance <f> <next> --gate pass`.
