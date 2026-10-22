# Backlog

Open work after the QA-role changes of 2026-10-22 (commits `088f5a3`, `a30419c`, `aac1df6`, `a9507cc`, `4727d6d`, `43404cf`, `f2283e6`, all local and unpushed). Most important first.

## Verify what's built

1. **Live recheck on an M-track feature** (about 10 min, about $4). The prompt-only rules from this round have never run in a real session:
   - Stage 4 skips the execution skill's final whole-branch review, and the Stage 4 rulings land in the gate log.
   - Stage 6 runs the whole-branch `code-reviewer` on `opus`, and a code fix it causes goes back to Stage 5.
   - The qa-tester reruns only when non-test code changed since its last PASS.
   - Features get dated names (`<yyyy-mm-dd>-<slug>`, with a ticket key when the request names one).

   Reuse the throwaway project `qa-smoke` in the session scratchpad, or a fresh copy.
2. **qa-tester paths not yet run live:**
   - a UI feature with a browser tool
   - `Risk: high`, where the model router requires `opus`
   - a monorepo, where red-green runs `install` per package inside the worktree
   - a feature with no runnable surface ("not run: reason")
3. **Look at the edited diagrams.** `docs/diagrams/sdlc_full_flow.svg` (the qa-tester line, the Stage 5 gate text) and `docs/diagrams/sdlc_plugin_layers.svg` (the qa-tester and prune chips, the 12-subagent and 21-command counts) were edited by hand and never rendered.

## Bugs and risks

4. **`hooks/verify_freshness.py` decodes git output with the Windows code page** (`text=True`, lines 188 and 195). Its file lists are ASCII because git escapes non-ASCII paths, but `rev-parse --show-toplevel` returns the raw path. A repo under a folder with non-ASCII characters in its name could crash the hook. The hook ignores its own errors, so freshness would then switch off silently. Fix with `encoding="utf-8", errors="replace"`, starting with a failing test. `scripts/doctor.py:39` has the same pattern and lower risk.
5. **The orchestrator puts lines under the wrong heading in `state.md`.** In the live run, a deviation line was appended under "Open questions" instead of "Deviations". Low impact.

## Decisions

6. **Which tracks get the qa-tester.** It stays on M and L, and the seeded experiment was skipped. In the one live run it found nothing that other checks missed. That feature was too simple to show its value, so the evidence goes neither way. Revisit after a few real M features; if it never catches anything the verifier misses, move it to L and high-risk work only, which is a one-line change in the orchestrator.
7. **The pipeline audit** `docs/audits/2026-10-22-pipeline-review.md` (written by another session, still untracked). Decide whether to commit it, and which findings to act on. The ones closest to this work:
   - PIPE-01: the trust anchor can be written by the agent
   - PIPE-02: verification expires at the Stage 5 gate
   - PIPE-04: role limits aren't enforced by tool scoping, so the qa-tester's blindness is instructions only
   - PIPE-05: the model router checks agent names, not roles
8. **Push and release.** Seven commits are local. The CHANGELOG's Unreleased section now holds the QA tester, red-green, the scenario trace, the qa-tester rerun rule, `/sdlc:prune`, one review per feature, dated feature names and the `diff_stats.py` fix. That likely means a minor release with the runbook's release smoke test.

## Gaps in the other roles (from the 2026-10-22 review)

9. **Design:** UX and interaction design is a non-goal in spec 10, and the M track usually skips Stage 2, so M features rarely get a `quickstart.md`. The qa-tester falls back to the spec and README; no change is planned unless that proves weak.
10. **`contracts/`:** the qa-tester uses them as input, but nothing checks that the built interfaces match them.

## Cleanup

11. Delete the throwaway project `qa-smoke` in the session scratchpad once item 1 is done, or right away if you skip item 1.
