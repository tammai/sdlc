# Review (Stage 5)

Entered from Build's gate. In Stage 5 the freshness hook blocks finishing on stale test results, and the budget hook kills any command other than the project's own at 120 s. Build's passing `verify.py` is the evidence; Review doesn't rerun it unless the code changed (`$V status` → `reuse: true`).

## 1. Recommend

Look at what actually changed (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/diff_stats.py" --format md --base <Base> --plan <state>`, run with Build's gate) and recommend, each with a one-line reason:

| Review | Recommend when |
|---|---|
| **Security** | `Risk: high`, or the diff touches `areas.sensitive` or `areas.migrations` (`.sdlc/config.json`), or untrusted input reaches a shell, file path or database |
| **Code, low** | the starting point on M and L: recommended unless a row below fires |
| **Code, default** | the state file's `## Public Surface` isn't `- none`, or the diff is large (diff stats: more than 5 source files or 300 added code lines) |
| **Code, high** | `Risk: high`, or the spec names a crash mid-write or concurrent use as a failure mode |
| **UI** | the diff touches `areas.ui`: always recommended |
| **Advisor** | only where this agent has one, and only for a real open judgment call the reviews can't settle |

The code depth is the highest row that fires, checked against these facts only, not judged; name the row in the reason.

- **S:** doesn't use this table; `s-track.md` step 5 is a fixed trigger list, none by default.
- **M and L:** stop with the recommendation, one line per review with its reason, and nothing else; the user picks (another depth, or none). Autopilot or a headless run: take the recommendation and record that you did (`state.py log`).

## 2. Run each chosen review once

Each review is a fresh agent on `opus`, never the context that wrote the code, dispatched together. Each writes its report to `.sdlc/.work/findings/<feature>/<agent>-r<N>.md` ending in `VERDICT: PASS` or `VERDICT: FAIL — <high ids>`; the trust anchor reads those lines.

- **Code:** `sdlc:code-reviewer` with `review-brief.md` at the chosen depth, plus the diff facts above.
- **Security:** `sdlc:code-reviewer` with the brief's security section. Meanwhile, in this session: the stack's dependency audit (`npm audit --omit=dev`, `pip-audit`, …) and every finding the security hooks raised. Report file `security-r<N>.md`.
- **UI:** `sdlc:ui-reviewer` with `<docs>/design-system.md`, the spec and the diff (`ui-work.md`). Screenshots only when the user asked for a visual check. Its proposed design-system changes go to the user: accepted ones go into `design-system.md` and resolve their findings; declined ones are code changes.
- **Advisor:** call it once, with the question the reviews couldn't settle.

## 3. Act on the findings

- **High:** back to Build (`state.py advance <f> 4`), fixed each with a failing test first, fixing the rule not the instance; then `$V` and `advance <f> 5`. The review isn't rerun: the fixes are proven by their tests and the full suite.
- **Disagreement** (you think a high is wrong): it goes to the user with the finding and your case. Never downgrade or waive one yourself; a waiver is the user's, recorded with `state.py deviation <f> "waived round <N>: <ids> — <reason>"` (those words: the trust anchor reads them).
- **Medium and low:** ticketed in `<change>`'s `## Review`; not fixed now unless trivial.
- A failure to baseline is the user's decision, recorded with `state.py deviation` naming the test.

## 4. Record

Append `## Review` to `<change>` once, as its last section, in the template's shape (`${CLAUDE_PLUGIN_ROOT}/templates/change-template.md`): what you recommended and why, what was chosen (and by whom), each review's verdict, the high findings with what fixed them, the tickets, the drift and manual checks. If nothing ran, one line saying so and why. Everything above it stays as Define wrote it: the trust anchor reports a change there. List every `## Deviations` line and every `manual` AC in your end-of-Review message, so the user sees them without opening the files.

**Gate:** `$V status` shows `reuse: true` on the current code; every chosen review's latest report ends `VERDICT: PASS`, or its highs are fixed (and re-verified by `$V`) or waived by the user; security-touched: no critical or high security finding open and no secrets in the diff. Then, in one shell call, `state.py verified <f> <head> <tree>` (both from that `$V status`) `&& state.py advance <f> 8 --gate pass`.
