# Spec: four phases instead of eleven stages

Status: approved 2026-10-26 · Brief: the user's phases brief (2026-10-26, after eval runs 8–10) · Branch: `tammai/lite-and-slices`

## Intent

**Request (as given):** restructure the pipeline from 11 sequential stages into 4 phases (Define, Build, Prove, Ship, plus a small Learn), keeping every check. Prove runs verify, review and security in parallel on one commit and fixes everything together. Deploy becomes an on-request command, Operate goes. Lite, slices and feature close keep working. Map every old gate to its new home. Choose one hook/state approach and justify it. Keep in-flight features working, and name the eval metric each change should move.

**Evidence:** the plugin matches plain Claude on quality (9/9 acceptance, 10/10 regression, 0 blocking/major blind defects vs 1–2 major for plain). It costs 5–6x more: 107–160 min vs 20–26 min of agent time, 7.7–8.0M vs 1.3M weighted tokens, and 4–5 vs 1 human touches. Scope scored 3/5 (unrequested hardening). The extra touches came from:

- a trust-anchor confirmation right after the user approved a Lite → full switch;
- the build-method question;
- a failed verify round asking whether to ship;
- the track choice at the spec gate;
- the finish question.

**Approaches considered:** (a) keep the internal stage numbers and run each phase at one of them, or (b) new phase identifiers, with hooks rewritten and an upgrade migration for active features. **Chosen: (a)**, see Decided.

**Todo folded in:** the open item "Discover always writes down the complete intent and the brainstorming" becomes this `## Intent` section in every full-flow spec (FR-09).

## Why

The 11 stages are a sound checklist but a costly execution model. Each stage is a gate, loads its own instructions and waits for the previous one:

- Stages 5–7 were 60% of wall-clock, run one after another, and every fix restarted the chain.
- Stage 3 added a gate and a document with no measured quality gain on M.
- Stages 9 and 10 run on no track by default but sit in every `state.md` and prompt.
- Stage 11 ran only on L, so most lessons were lost.

## Requirements

Source: `[user]` from the brief, `[decided]` the agent's call (see Decided). Guarantee: `[enforced]` code and a test prove it, `[instructed]` a skill or command says it. Metric: the eval metric (task `planner-team`) the change should move; hidden tests and blind defects must hold level throughout.

| ID | Requirement | Source | Guarantee | Metric |
|---|---|---|---|---|
| FR-01 | **Four phases, each at one stage number.** Define runs at `Stage 1`, Build at `4`, Prove at `5`, Ship at `8`. A new feature never enters 2, 3, 6, 7, 9, 10 or 11; one `state.py advance` per phase move. `state.md` reads `Current: Stage <n> – <phase>` (`Stage 1 – Define`, `Stage 4 – Build`, `Stage 5 – Prove`, `Stage 8 – Ship`). The new template's checklist has only those four lines. The control contract's snapshot gains `phase` (`define`, `build`, `prove`, `ship`, from the number: 1–3, 4, 5–7, 8–11), and the renamed `current.name` values bump `contract_version` to 2. | [user] | [enforced] | agent time, weighted tokens |
| FR-02 | **In-flight features keep working.** A `state.md` written from the old template (11-line checklist, `Current: Stage 6 – Review`, any flow) resumes in the phase its number maps to (1–3 Define, 4 Build, 5–7 Prove, 8 Ship, 9–11 Ship/Learn). `state.py advance` takes it on to the next phase (6 → 8), and every hook behaves as today, since none of them changes how it reads the stage. No upgrade migration. | [user] | [enforced] | — |
| FR-03 | **Define** (old 1–3): the core's blocking questions once; one spec with its tasks and a `## Public Surface` list; a backlog instead of the tasks when the work is bigger than one session; design only when the approach isn't obvious (L, or M that needs it), inside Define. Failure modes become acceptance criteria. Define reads `knowledge/index.md` and `<docs>/recurring-defects.md`. It keeps the work to the brief: no hardening, validation or options the request and the applicable failure modes don't call for; anything else is `[inferred]` and dropped unless the user keeps it. **One approval** covers spec, tasks or backlog, design if any, and `Build:` (shown as the track's default, changeable in the reply). S has no spec and no approval, as today: a brief, then Build. | [user] | [instructed] | human touches, agent time, scope |
| FR-04 | **Build** (old 4): `Build: native \| subagent \| tasks`, set from the track at Define (S `subagent`, M `native`, L `tasks` = `sdlc:subagent-driven-development` with its per-task reviews) and never asked as a separate question. TDD, worktree isolation (L or dirty tree), S's repro-test-first and BLOCKED rules, and the "no TODO without a ticket" rule as today. | [user] | [instructed] | human touches |
| FR-05 | **Prove** (old 5, 6, 7 together), all at Stage 5. On the review-ready commit, everything the track runs is dispatched in parallel, each agent fresh: verifier, code reviewer (never the builder's context), qa-tester, silent-failure-hunter, pr-test-analyzer, ui-reviewer, and on full security the security-brief `feature-reviewer` + `code-reviewer`. The dependency audit runs in-session meanwhile. All findings are fixed together, each with a failing test first, then one re-verification: in-session full suite on `Flow: lite`, a fresh verifier on `full`. A re-verification that fails, or a verifier FAIL the fixes don't address, gets a fresh verifier round instead of a question to the user; only the round cap (3 failed rounds) stops. The track sets tiers and checkers per the matrix below. Fixed high findings are listed in `<intents>/review.md` (Learn reads them). | [user] | [instructed] | agent time, human touches, weighted tokens |
| FR-06 | **Ship** (old 8): the verified-tree check, Learn (FR-07), one commit (the commit-time security review runs on it), then the merge / PR / keep question (a hard stop). CI green before a merge; never merge without the user. Slices commit at Ship's verified-tree check only; the question waits for feature close. | [user] | [instructed] | agent time |
| FR-07 | **Learn**, at the end of every feature, small, before Ship's commit so it lands in it. The defects Prove fixed (from `review.md`, every slice's included) that a reviewer could check next time get one line each in `<docs>/recurring-defects.md`, deduplicated. Define and every reviewer brief read that file. Durable lessons go through `sdlc:managing-knowledge` only when there is one. L keeps `retro.md` and `knowledge/features/<f>.md`. | [user] | [instructed] | blind defects |
| FR-08 | **Deploy** is `/sdlc:deploy`, on request only: the old Stage 9 text (existing deploy path, `release.md`, explicit go-ahead before a production deploy or DB migration, smoke test). Mirrored to Codex, Cursor and Antigravity. **Operate** is removed from every track and template; its text stays as `references/operate.md` for anything that links it. | [user] | [instructed] | weighted tokens |
| FR-09 | **Intent on record.** A full-flow spec opens with `## Intent`: the request verbatim (or the ticket's text), the blocking questions and answers, and on L or a design the approaches considered with the choice and why (L: a summary of `brainstorm.md` and a link). Lite's spec gets a two-line Intent (request and answers). Plain markdown under fixed headings, so a person and a script can both read it. | [user] (todo) | [instructed] | — |
| FR-10 | **Stricter changes don't stop the user.** The trust anchor raises no notice when `Track` goes up (S < M < L), `Risk` goes `low` → `high`, or `Flow` goes `lite` → `full`. Any other change to those fields, and any change to `Top model` or `Base`, is a notice as today. | [user] (touch target) | [enforced] | human touches |
| FR-11 | **Lite, slices and feature close become the defaults.** The phase files describe Lite's shape (one approval, one build, one parallel round, one commit) as every track's default. `lite-flow.md` goes; the full flow differs only in tiers, extra checkers and a fresh-verifier re-verification. `Flow:` stays as the switch between in-session and fresh re-verification (the hooks read it). Slices loop Build → Prove → Ship-commit (4 → 5 → 8, then 4 for the next slice), each slice keeping a short `plan-B<n>.md` with its Public Surface. Feature close runs Prove once (8 → 5) and then Ship (→ 8), where autopilot expects it. | [user] | [instructed] | agent time, weighted tokens |
| FR-12 | **Docs:** the orchestrator core (about 1,000 words or fewer, with a stage → phase → file map so a resumed session loads the right file), one reference file per phase, `docs/specs`, README text and diagram labels, templates that say "Stage 5", CHANGELOG ("run `/sdlc:upgrade`" for the changed templates). The stale-docs audit runs for every stage name and file removed or renamed. | [user] | [instructed] | weighted tokens |

### Prove by track (FR-05)

| Track | Verifier | Code reviewer | Also in the round | Security | Re-verification |
|---|---|---|---|---|---|
| S | standard | standard | — | hooks only | fresh verifier |
| M, risk low (`Flow: lite`) | standard | standard | qa-tester (single session); ui-reviewer on UI | light: hook findings + dependency audit | in-session suite |
| M, full flow | standard | top | qa-tester, silent-failure-hunter; ui-reviewer on UI | light; full if auth, payments, secrets, PII or migrations | fresh verifier |
| L, or risk high | top | top | silent-failure-hunter, pr-test-analyzer (gap ≥ 8 blocks) on L; qa-tester on M; ui-reviewer on UI | full: security-brief feature-reviewer + code-reviewer, top tier | fresh verifier |
| Slice | standard (top on risk high) | standard (top on risk high), this slice's diff | ui-reviewer on UI | at feature close | in-session suite |
| Feature close | standard (top on risk high), whole branch | top, `Base..HEAD` | qa-tester; ui-reviewer on UI | light; full on L or risk high | in-session suite |

## Where every old gate lives now

| Old gate or check | New home | Change |
|---|---|---|
| Blocking questions once, `[inferred]` triage, Non-Goals filled, ACs testable, requirements checklist (full flow) | Define | none |
| End of Stage 1: user approves the spec (hard stop) | Define's one approval | none |
| End of Stage 2: user approves the design (hard stop); FR/SC map to design, Complexity Tracking cites a requirement, no Non-Goal designed in, one rejected alternative, constitution check | Define, in the same approval as the spec when a design runs | two approvals become one; every criterion kept |
| Design-system additions approved before the build | Define (approval) and Prove (ui-reviewer proposals go to the user) | none |
| Stage 3: no CRITICAL/HIGH scope findings (`analyzing-consistency`, L or > 8 tasks), every requirement has a task and every task a requirement, Public Surface declared | Define: the spec's Tasks and `## Public Surface`; `analyzing-consistency` on L | plan.md folds into the spec |
| Stage 3: the user picks the execution method (hard stop, full flow) | Define: `Build:` from the track, shown in the one approval | separate question removed; the user can still change it |
| Stage 4: tasks done, build + suite green, no TODO without a ticket, TDD, worktree on L, S repro first and BLOCKED rule, per-task reviews (subagent-driven) | Build (`Build: tasks` on L keeps per-task reviews) | none |
| Stage 5: latest fresh verifier PASS on the current commit, dispatched in Stage 5 (dispatch log); every AC has evidence; baseline only by the user's decision; S red-green; no skipped or retried-until-green test | Prove (Stage 5; the hooks check it as today) | none |
| Freshness hook (Stage 5; 5–6 on Lite) | Prove (Stage 5), so review and security fixes are now tracked too | stricter |
| Round cap: stop after verify round 3 fails | Prove | none; Lite's earlier stop (after one failed fix pass) becomes a fresh verifier round, so the cap is the only stop on every flow |
| Stage 6: reviewer isn't the builder; no unresolved high finding; medium/low ticketed in `review.md`; a code change after the gate re-verifies; UI design-system proposals to the user | Prove | none |
| Stage 7: hook findings addressed; light = hooks + dependency audit; full = security-brief reviewers (L, risk high, auth/payments/secrets/PII/migrations); no critical/high open; no secrets in the diff (`security.md`); a security fix re-verifies | Prove, dispatched in the same round | runs in parallel instead of after review |
| Commit security review once per review-ready diff | unchanged (Prove is Stage 5, Ship Stage 8) | none |
| Stage 8: verified-tree check before any commit; CI green; never merge without the user; PR links spec, test-report, qa-report | Ship | none |
| Stage 9: go-ahead before a production deploy or DB migration; smoke test; `release.md` | `/sdlc:deploy` | on request only, as before (no track ran it by default) |
| Stage 10: signals within threshold (parked, no track ran it) | `references/operate.md`, on request | removed from tracks and templates |
| Stage 11: recurring defect → `recurring-defects.md`; corrected twice → hookify; promoted lessons linked; CLAUDE.md ≤ 60 lines; L: retro + feature knowledge page | Learn, at every feature's end | stricter: runs on every feature, not only L |
| Ownership check, "skip" → deviation, model-router tiers, role guard, trust anchor | unchanged | trust anchor: no notice for stricter Track/Risk/Flow changes; weakening ones still notice (FR-10) |
| Hard stops: spec approval, scope changes, merge, production deploy, DB migrations, anything irreversible | unchanged | only the execution-method question leaves this list; checks that pass never stop |

## Acceptance criteria

1. `state.py advance <f> 5 --gate pass` from `Stage 4 – Build` writes `Current: Stage 5 – Prove`, ticks Build, and the snapshot shows `phase: prove`, `current.name: Prove`, `contract_version: 2` (FR-01).
2. An old-template `state.md` at `Current: Stage 6 – Review` (`Flow: lite`) advances with `advance <f> 8 --gate pass` to `Stage 8 – Ship`, ticks its Stage 6 line, and the snapshot shows `phase: ship` (FR-02).
3. The trust anchor raises no notice when `Flow` goes `lite` → `full` or `Risk` `low` → `high`, and still raises one when `Flow` goes `full` → `lite` or `Risk` `high` → `low` (FR-10).
4. The orchestrator core is about 1,000 words or fewer and names, for each stage number, the phase and the reference file a resumed session reads; the old `stage-*.md` and `lite-flow.md` are gone and nothing links them (FR-11, FR-12).
5. Define asks one approval for spec + tasks (or backlog) + design + `Build:`, with no separate execution-method question; S asks none (FR-03, FR-04).
6. Prove dispatches the track's checkers, security included, in one parallel round on one commit, fixes together, re-verifies once, and stops only at the round cap (FR-05).
7. Ship runs Learn before its one commit, and Learn adds Prove's fixed defects to `recurring-defects.md` (FR-06, FR-07).
8. `/sdlc:deploy` exists, is mirrored to the other hosts (`hosts.py check` and `scaffold.py agents --check` pass), and no track or template lists Deploy or Operate as a stage (FR-08).
9. The README, `docs/specs`, templates and CHANGELOG describe four phases; the stale-docs audit finds no stale stage name or file (FR-12).
10. The full suite passes at every commit.

## Non-goals

- New phase identifiers in `Current:` or any hook change beyond FR-10 (option b).
- A state migration in `/sdlc:upgrade`, or a version bump or release.
- Configurable phases per project, team mode, advisory-only mode (separate todos).
- Changing the verifier, reviewer, qa-tester or security agents themselves, or the commit/push security review.
- Running or changing the eval.

## Decided (agent's calls, not asked)

- **Option (a), stage numbers kept.** Every hook reads only the number (`Current:\s*Stage\s*(\d+)`; the trust anchor's verifier check matches `Stage 5` in the dispatch log), so phase names cost no hook change and no migration. Each phase runs at one number, so the existing checks fall into place: the `[inferred]` CI check (Stage ≥ 2) fires only after the one approval; freshness covers all of Prove; the trust anchor's "passed Stage 5" and "left Stage 5 untested" rules and the commit-review gate (Stage ≥ 5) still hold; autopilot's "feature close ends at Stage 8" holds. Option (b) would rewrite five hooks, the CI template and the dispatch log format, and need a migration, to gain only nicer numbers.
- **Contract version 2.** Renaming `current.name` values is a breaking change under spec 12's rule, so the version bumps; `phase` is new. No runner reads the contract yet. Legacy numbers keep their old names (2 Design, 3 Plan, 6 Review, 7 Security, 9 Deploy, 10 Operate, 11 Learn) so an in-flight feature reads truthfully.
- **S keeps its code reviewer.** The brief's sketch says "S: verifier only", but S runs a standard reviewer today ("Stage 6 light"), and the brief also says nothing may be weakened. The reviewer runs in the same parallel round, so it adds tokens but no wall-clock. Say "drop it" at approval to remove it.
- **`Build: tasks`** is new (L's subagent-driven default with per-task reviews, a check today). It's free text in `state.md`, so no code changes.
- **Public Surface moves into the spec.** `diff_stats.py --plan` reads any file's `## Public Surface` section, so `--plan <intents>/spec.md` works unchanged. Slices keep `plan-B<n>.md`, because feature close takes the union of their surfaces.
- **Learn reads `review.md`,** which Prove already writes, so defects from slices finished in earlier sessions aren't lost.
- **Intent as a spec section, not a file:** almost free, and it's where Define's readers already look.
- **`Flow:` stays.** It now only picks the re-verification (in-session vs fresh verifier) and the reviewer tier. The freshness hook's Lite `(5|6)` case is dead for new features but stays for in-flight ones.
