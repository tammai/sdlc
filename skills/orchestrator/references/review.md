# Review (Stage 5)

Entered from Build's gate. In Stage 5 the freshness hook blocks finishing on stale test results, and the budget hook kills any command other than the project's own at 120 s. Build's passing `verify.py` is the evidence; Review doesn't rerun it unless the code changed (`$V status` → `reuse: true`).

## 1. Recommend

Look at what actually changed (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md --base <Base> --plan <intents>/plan.md`) and recommend, each with a one-line reason:

| Review | Recommend when |
|---|---|
| **Security** | `Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations` (`.sdlc/config.json`), or untrusted input reaches a shell, file path or database |
| **Code, high** | the spec has must-never-break lines or failure modes (concurrency, persisted data, a crash mid-write), a public interface changed, or the diff is large or spread out |
| **Code, default** | a typical M or L change |
| **Code, low** | a small, contained change whose tests cover it, when a second look is still worth it |
| **UI** | the diff touches `areas.ui`: always recommended |
| **Advisor** | only where this agent has one, and only for a real open judgment call the reviews can't settle |
| **None** | a small, contained change, fully covered by its tests, touching nothing above |

- **S:** run what you recommend (or nothing), without stopping, and say in one line what ran and why.
- **M and L:** stop with the recommendation; the user picks. Autopilot or a headless run: take the recommendation and record that you did (`state.py log`).

## 2. Run each chosen review once

Each review is a fresh agent on `opus`, never the context that wrote the code, dispatched together. Each writes its report to `.sdlc/.work/findings/<feature>/<agent>-r<N>.md` ending in `VERDICT: PASS` or `VERDICT: FAIL — <high ids>`; the trust anchor reads those lines.

- **Code:** `sdlc:code-reviewer` with `review-brief.md` at the chosen depth, plus the diff facts above.
- **Security:** `sdlc:code-reviewer` with the brief's security section. Meanwhile, in this session: the stack's dependency audit (`npm audit --omit=dev`, `pip-audit`, …) and every finding the security hooks raised. Report file `security-r<N>.md`.
- **UI:** `sdlc:ui-reviewer` with `<docs>/design-system.md`, the spec and the diff (`ui-work.md`). Screenshots only when the user asked for a visual check. Its proposed design-system changes go to the user: accepted ones go into `design-system.md` and resolve their findings; declined ones are code changes.
- **Advisor:** call it once, with the question the reviews couldn't settle.

## 3. Act on the findings

- **High:** back to Build (`state.py advance <f> 4`), fixed each with a failing test first, fixing the rule not the instance; then `$V` and `advance <f> 5`. The review isn't rerun: the fixes are proven by their tests and the full suite.
- **Disagreement** (you think a high is wrong): it goes to the user with the finding and your case. Never downgrade or waive one yourself; a waiver is the user's, recorded with `state.py deviation <f> "waived round <N>: <ids> — <reason>"` (those words: the trust anchor reads them).
- **Medium and low:** ticketed in `plan.md`'s `## Review`; not fixed now unless trivial.
- A failure to baseline is the user's decision, recorded with `state.py deviation` naming the test.

## 4. Record

In `plan.md`'s `## Review`, once: what you recommended and why, what was chosen (and by whom), each review's verdict, the high findings with what fixed them, and the tickets. If nothing ran, one line saying so and why. List every `## Deviations` line and every `manual` AC in your end-of-Review message, so the user sees them without opening the plan.

**Gate:** `$V status` shows `reuse: true` on the current code; every chosen review's latest report ends `VERDICT: PASS`, or its highs are fixed (and re-verified by `$V`) or waived by the user; security-touched: no critical or high security finding open and no secrets in the diff. Then `state.py verified <f> <commit> <tree>` and `state.py advance <f> 8 --gate pass`.
