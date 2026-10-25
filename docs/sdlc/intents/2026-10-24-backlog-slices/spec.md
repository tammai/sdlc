# Spec: backlog slices and batched intent questions

Status: draft for approval · revised 2026-10-25 · Intent: [intent.md](intent.md) · Branch: `tammai/lite-and-slices`

## Why

The user's goal: state an intent, the agent does the rest, and the code is what a senior engineer would ship. Every prompt and approval the workflow adds is a cost. Two problems stand in the way:

- **Large features run in one session.** Stage 1 to Stage 8 takes hours, the context grows until limits hit, and every turn pays for the whole history. Splitting the work into vertical slices that each fit a session lets the work pause, `/clear` and resume, or run unattended in fresh sessions.
- **Questions arrive late and one at a time.** M's spec guesses, then asks up to 3 clarification questions; L's brainstorm asks one per turn. Asking only what blocks, all at once, and listing the rest as assumptions keeps quality with 0–1 touches.

The Lite flow (ADR 0008) already gets a low-risk M feature done in 2 touches. Slices reuse its inner loop instead of the full flow's, so a large feature costs a few Lite runs, not a full-flow run per slice.

## Requirements

Source tags as in `writing-specs`: `[user]` the user asked; `[clarified]` the user settled it in the intent conversation (2026-10-24, revised 2026-10-25). Guarantee tags as in `docs/specs/`: `[enforced]` code and a test prove it; `[instructed]` a skill or command says it.

### Intent questions (Stage 1)

| ID | Requirement | Source | Guarantee |
|---|---|---|---|
| FR-01 | Before the spec (on L, before brainstorming; on S, before the brief), the orchestrator asks the questions whose answers would change what gets built, in **one** message, plain text with options, so it works without a question tool. When nothing blocks, it asks nothing. Everything else it would have asked becomes an assumption: an `Inferred` / `[inferred]` item in the spec with a one-line reason (on S, a line in the brief and the final summary). | [user] [clarified] | [instructed] |
| FR-02 | The spec carries no `[NEEDS CLARIFICATION]` markers: answers are tagged `[clarified]`, the rest are assumptions the user keeps or drops at the spec gate, together with the spec. `clarifying-specs` runs only when the user asks. L's brainstorm builds on the answers and doesn't ask them again. | [clarified] | [instructed] |

### Backlog and slices

| ID | Requirement | Source | Guarantee |
|---|---|---|---|
| FR-03 | Planning estimates the work. A feature that fits one session (about 8 tasks or fewer, one part) keeps its current flow: a low-risk M feature stays on the Lite flow with one spec-and-tasks document and one commit; others get one `plan.md`. A bigger one gets `<intents>/backlog.md` instead: one row per vertical slice with ID (`B1`…), title, FRs, acceptance criteria, dependencies, size and status (`todo`, `in progress`, `done <commit>`, `blocked: <reason>`). Every spec FR is covered by a slice. S never gets a backlog. | [user] [clarified] | [instructed] |
| FR-04 | Approval: on M, the user approves the spec and the backlog once, in one message. On L, the backlog is approved at the Stage 3 gate, after the spec and design gates. No execution-method question: slices build natively. | [user] | [instructed] |
| FR-05 | A backlog feature runs with `Flow: lite` at any track and risk, and every slice runs Lite's inner loop: a short `plan-B<n>.md` (3–6 tasks, each naming files, FR and test, plus a Public Surface list); a native, test-first build in the session; one fresh verifier; one review with Lite's named edges (durable writes, error paths, loaded data) on the slice's diff only (`--base <Slice base> --plan plan-B<n>.md`); high findings fixed test first and re-verified in-session; one commit; the backlog row set to `done <commit>`. Verifier and reviewer run on the standard tier, the top tier on `Risk: high` (the model router requires it). The Lite flow's size-up rule (high risk → full M flow) applies only to a single-session Lite feature. `state.md` records `Slice: B<n>` and `Slice base: <commit>`; `Base:` stays the feature's start. | [user] | [instructed] |
| FR-06 | With yolo off, slices run back to back without asking. They stop only for a failed gate (a second verifier FAIL), a backlog change that adds scope, or a hard stop (merge, deploy, migrations, anything irreversible). Per-slice approval of the plan, the review findings or the commit is opt-in (`Slice gates:` in `state.md`, default `none`). When the remaining work would overflow the session, the run stops at a slice boundary with a one-line status naming the next slice. | [user] | [instructed] |
| FR-07 | `/sdlc:start` with no argument resumes the active feature at its current slice, or starts the next ready slice: the first `todo` row whose dependencies are all `done`. `/sdlc:start B<n>` starts that slice and is refused while its dependencies aren't done. `scripts/backlog.py next` and `check B<n>` make that choice for the orchestrator and yolo. | [clarified] | [enforced] backlog.py |
| FR-08 | A slice that turns out too big, or uncovered work, becomes a proposed backlog change. A split that keeps the same FRs is made and logged; anything that adds scope waits for the user. Work outside the spec is never added silently. | [clarified] | [instructed] |
| FR-09 | Feature close, once every slice is `done`: one fresh verifier round over every acceptance criterion on the whole branch; the feature's one top-tier review, over `Base..HEAD`, checked against the union of every slice plan's Public Surface (`diff_stats.py --plan` repeatable); Stage 7 (light, or full on L and high risk); Stage 8, whose merge, PR or keep question is the user's; Stage 11 on L. | [clarified] | [enforced] surface union; rest [instructed] |
| FR-10 | Yolo mode is off unless the user asks. `scripts/yolo.py <feature>` runs one fresh headless `claude -p "/sdlc:start B<n> --yolo"` session per ready slice, for features whose remaining slices would overflow one session, then one feature-close session that ends at Stage 8's question. It stops when a slice ends `blocked:`, a run ends without changing its slice's status, or a trust-anchor notice is open (a new `-p` prompt would accept it unseen). It passes no permission-bypass flag. Claude Code only. | [user] [clarified] | [enforced] stop conditions |
| FR-11 | The hooks accept the slice loop under `Flow: lite`: Stage 6 → Stage 3 for the next slice is no trust-anchor notice when the code matches the last full test run, and is one when a review fix was left untested (the same check as leaving Stage 5; it covers single-session Lite leaving Stage 6 too). Each slice commit runs Stage 8's verified-tree check first. Features already running with one `plan.md` keep working unchanged. | [user] | [enforced] trust anchor; rest [instructed] |

## Acceptance criteria

1. A request with one blocking ambiguity gets one message with that question; a request with none gets no question, and the spec lists the guesses as `Inferred` items (FR-01, FR-02).
2. A low-risk M feature that fits a session stays on the single-document Lite flow; one estimated beyond a session gets `backlog.md` covering every FR, approved with the spec in one message (FR-03, FR-04).
3. With default gates, B1 finishing starts B2 without a question; a proposal that adds scope stops and asks (FR-06, FR-08).
4. A finished slice leaves one commit, its row `done <commit>`, and a review that saw only that slice's diff (FR-05).
5. Given B1 `done` and B2 `todo` depending on B1, `backlog.py next` names B2, and `check B3` (depending on B2) is refused (FR-07).
6. `diff_stats.py --plan plan-B1.md --plan plan-B2.md` doesn't flag an export listed only in `plan-B1.md`, and flags one in neither (FR-09).
7. `yolo.py` runs the next slice after a `done` one, runs the feature-close session once after the last, and stops on a `blocked:` slice, an unchanged status, or an open trust-anchor notice (FR-10).
8. Under `Flow: lite`, Stage 6 → Stage 3 between slices is no notice after a full run, and is one when code changed after the last full run (FR-11).
9. A run that would overflow the session stops at a slice boundary naming the next slice, and `/sdlc:start` resumes there (FR-06, FR-07).

## Non-goals

- Syncing slices to GitHub issues, Linear or Jira.
- One PR per slice, or merging slices to main one at a time.
- Writing every slice's plan up front.
- Yolo on Codex, Cursor or Antigravity.
- Yolo past Stage 8's question (PR, merge, deploy).
- A per-slice top-tier review, or a per-slice Stage 7: the commit-time security hooks still run on every slice commit.
- Moving `Base:` per slice: it stays the feature's start commit, which the trust anchor relies on.

## Decided (agent's calls, not asked)

- **No interview skill and no `intent.md` for new features.** One batched message needs no resume, no per-answer record and no separate skill; the answers and assumptions live in the spec, and the rule fits in the orchestrator's Stage 1 and Lite step 1. Loading one more skill would cost tokens on every M feature. This feature's own `intent.md` stays as its history.
- **Slice state:** `Slice: B<n>`, `Slice base: <commit>` and `Slice gates: none | plan, review, commit` lines in `state.md`. `Current: Stage <n> – <name>` keeps its form, since hooks match it. A slice moves 3 → 4 → 5 → 6, commits, and the next starts at 3. Stage 7, 8 and 11 run once, at feature close.
- **`Flow: lite` covers both**: a single-session Lite feature, or a backlog feature (with a `Slice:` line). The freshness hook already tracks Stages 5–6 under it, which the in-session re-verify of review fixes needs.
- **Next-ready selection** lives in `scripts/backlog.py`, which parses the backlog table; the orchestrator and `yolo.py` both call it.
- **Yolo reads state, not output:** after each run it re-reads `backlog.md` through `backlog.py` and `.sdlc/.work/trust-anchor.json`. The user can pass `--permission-mode <mode>` through.
- **Feature close** is a `▶ Feature close` step in the orchestrator, not a new stage number.
