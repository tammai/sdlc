# Configurable stages and an advisory mode

## Why

**Request (verbatim):** two items from `.sdlc/todo.md`, done together because they share one design:
- "Let a project configure which sdlc stages run, e.g. skip the security review or the PR/CI step — not built yet; stage gates are fixed today in the orchestrator (2026-10-25)"
- "Add an advisory-only use case: the sdlc skills and agents as aids, with no hooks, gates or guardrails, for projects that already have a workflow that would conflict; setup asks which mode to use — not built yet; related to the configurable-stages item above (2026-10-26)"

Who it serves:
- **A team with its own release path** (its CI runs the security scan, or it ships without PRs). Today sdlc forces the security review and the push/PR/CI step on every qualifying change; the only way out is "skip" each time, recorded as a deviation.
- **A team with its own workflow**, where sdlc's hooks and guardrails would fight that workflow. Such a team still wants the skills (brainstorming, TDD, debugging) and the agents (code-reviewer, qa-tester) on demand, with nothing enforced. Today, installing sdlc means taking all of it.

What changes when done:
- Setup asks one question, **full or advisory**.
- A full project can switch off named steps: the security, code or UI review, and the PR/CI step.
- An advisory project gets the skills and agents with no hook, gate or guardrail getting in the way.

**The user's words:** "solve all todo items" (2026-11-23); chose "Configurable stages + advisory" as the next item. Define's approval (2026-11-23): approach A ("Approve A"); in advisory mode the security layer goes silent too ("Silent too"; `SDLC_SECURITY_REVIEW=always` still forces it); a relaxing change is protected by the trust anchor ("Trust anchor"), not a per-machine ratchet.

**What exists today** (inventory, 2026-11-23):
- No mode key.
- Most process hooks are already silent without an active `Process: 3` feature: model router, prove budget, freshness, trust anchor, round cap, user answer, and the commit and turn-end security reviews (`sdlc_layout`, `sdlc_review_gate.review_wanted`/`decide`).
- Always on whatever the state: the hookify guardrails (`.claude/hookify/sdlc-*`), the pretooluse patches (recorded-test guard, Monitor commit deny), security pattern warnings and the push review, `session_status`, and in a workbench the read-only guard and watch.
- The review table and the PR/CI step live in skill text (`flow.md`, `s-track.md`, `SKILL.md` = `commands/start.md`). `trust_anchor` flags a skipped Review, and CI's `invariants.py` checks the record.
- ADR 0029: config the agent can edit must not quietly relax a safety stop.

## Decisions

**Approaches considered:**

| Approach | Trade-off |
|---|---|
| **A. A `mode` key plus a short `skip` list**: `"mode": "full" \| "advisory"` (default full); in full mode, `"skip": ["security-review", "code-review", "ui-review", "pr"]`, any subset | Two concepts, both named in the request. Small surface: four named steps, not every gate. Advisory reuses the fact that most hooks are already feature-gated |
| B. A fine-grained `gates` map (every hook and stage on/off), with advisory as a preset | Most flexible, but dozens of switches to document, test and keep safe; most combinations (no red step, no test lock) undo what the plugin is for (ADR 0020 dropped lighter flows after they failed crash-safety) |
| C. Advisory only (all or nothing); keep per-run "skip" for stages | Smallest, but leaves item 1 unsolved: a team that never wants sdlc's PR step still says "skip" on every change |

| Decision | Ruled out | Why |
|---|---|---|
| Approach A | B, C | Covers both items with the fewest switches; the red step, test lock, verify and the record stay fixed in full mode (they are what the plugin is for) |
| `skip` names steps, not hooks: `security-review` (the Review row and the security hook's commit and turn-end model reviews for features; the push review and pattern warnings stay), `code-review`, `ui-review`, `pr` (Ship stops after the local commit: no push, PR or CI watch) | skipping Define, Build or verify | The request names reviews and the PR/CI step; skipping intent or tests would make the record a lie |
| A skipped step is recorded, not silent: `## Review` says which review the config skipped ("Security review skipped by config (`skip`)"). The trust anchor already lets a change with no review go from Build to Ship once its tests pass, so it needs no change for skips | silent skip | A reader months later must see why no review ran |
| Advisory: every sdlc hook returns silently, through one shared check (`sdlc_scopes.advisory(root)`) at each hook's entry, the always-on layer included (hookify rules, pretooluse patches, security pattern warnings and model reviews). Exceptions: a workbench's read-only guard and watch stay on (they protect other teams' repos); `SDLC_SECURITY_REVIEW=always` still forces the security reviews; `session_status` keeps its one context line and names the mode, so the agent knows (it gates nothing) | uninstalling hooks per project | Setup writes no hook entries (they come from the plugin's hooks.json), so each hook must check the mode |
| Advisory skills: `/sdlc:start` and the orchestrator don't run the flow; they say advisory mode is on and do what is asked with the skills and agents, writing no state file. The skills and agents themselves work as today | a reduced flow | The request is "aids, no gates"; a half-flow would conflict with the team's own workflow |
| Advisory setup: asks the mode first; advisory skips guardrails, lint, CI, the workflow rule (`.claude/rules/sdlc.md` replaced by a short advisory note), the `AGENTS.md` block (it carries the workflow rules), the constitution, the PRD, the design system, deploy and review rounds unless asked; keeps gitignore, allowlist, enable-plugin, context-diet and the knowledge base | full setup with hooks off | Nothing that enforces should land in an advisory repo |
| Who may relax it: `mode` and `skip` change only through `scaffold.py mode …` / `scaffold.py skip …` (setup's step, `/sdlc:setup mode advisory`, `/sdlc:setup skip pr`), and the trust anchor reports a change to either key at the next turn end for the user's confirmation, as it does for the baseline and commands | the review-rounds ratchet (outside-repo ceiling raised only by a typed prompt) | A team's committed choice must hold on every teammate's machine; the trust anchor already gives the user the say on agent edits, which is ADR 0029's concern |
| Switching back (advisory → full, or removing a skip) is never flagged; it only adds checks | flag both ways | Tightening needs no confirmation |
| A relaxation counts only once accepted: the hooks honour `advisory` or a skip only when the trust anchor's record of what the user accepted says so; with no readable record, HEAD's committed config (a fresh clone takes the team's choice). The reply accepts what the notice showed; a damaged record is said and reset to HEAD (code r1 H2, M4; security r1 H1, H3, M1) | honour config at once and only notify | an edit counted before the user saw it, a reply accepted changes it never showed, and deleting the record re-seeded silently |
| One resolver for every reader and the trust anchor (`sdlc_scopes.gate_root`): the session's project folder's git top level; for a workbench app repo, the workbench (code r1 H1, security r1 H2) | the nearest `.git` or `.sdlc` from the call's cwd | a nested `.sdlc` or an app repo's own config silenced the hooks unwatched |
| Setup, upgrade, doctor and the design swap follow the *configured* mode (the team's stated choice, before acceptance); the hooks follow the *effective* one (code r1 M2) | the effective mode everywhere | setup renders right after `/sdlc:setup mode advisory`, before any reply |
| `gate_root` returns only a folder holding `.sdlc` (the outermost up to its git top, else the nearest), never creates one, and `scaffold.py mode`/`skip` resolve the same way from `--root` and refuse to write elsewhere (security r2 R2-H1, R2-H2) | the git top level | a nested repo or a subfolder setup got a stray `.sdlc`; scaffold reported a different folder's skips |
| A config asking for no relaxation reads no record and runs no git; every read is of a regular file inside the repo, and git gets 2 s (security r2 R2-H3, code r2 R2-M7, R2-M8) | reading the record on every call | a FIFO or a stalled git timed the gate hooks out open, and every hook paid a git call |
| HEAD's config is read at the gate folder (`HEAD:./.sdlc/config.json`, never the repo top's); scaffold refuses `mode`/`skip` where the session's hooks read another folder; the trust anchor writes its records as a fresh file swapped in (security r3 R3-H1, R3-H2, R3-M1) | resolving from --root alone; a plain write | a subfolder setup read the top's config; a nested repo split scaffold from the hooks; a FIFO or link at the record hung or redirected the write |
| `scaffold.py mode` switches `.claude/rules/sdlc.md` between the workflow rule and the advisory note while unedited; doctor doesn't ask an advisory repo for a PRD or design system (code r2 R2-M2, R2-M3) | leave them | upgrade kept the old rule after a switch |
| In advisory, the unbranched-repo check is off with the other process gates; the read-only guard runs before anything reads the mode (code r1 M3, security r1 H5) | keep it | it gates the flow, not other teams' repos |

**Proposals not asked for:** none.

## Acceptance criteria

- **AC-001** `scaffold.py mode advisory` / `mode full` writes `"mode"` to `.sdlc/config.json`; any other value is refused (exit 2) and an invalid stored value counts as full.
- **AC-002** `scaffold.py skip <step>…` / `skip --clear` writes `"skip"`; only `security-review`, `code-review`, `ui-review` and `pr` are accepted, and only in full mode.
- **AC-003** In an advisory repo, an active feature's process hooks stay silent: a model-router deny, a round-cap hold and a trust-anchor field change all pass (each still fires in full mode).
- **AC-004** In an advisory repo, the always-on layer stays silent: an installed guardrail (dangerous rm), a Monitor `git commit` and a security pattern warning on an edit (each still fires in full mode).
- **AC-006** With `skip: ["security-review"]`, a security-touched feature's commit and turn-end model reviews are not wanted; without it they are.
- **AC-007** A change to `mode` or `skip` toward fewer checks (full → advisory, a step added) during a session raises a trust-anchor notice at turn end, even in advisory mode, and the user's reply accepts it; a change toward more checks raises none.
- **AC-008** The orchestrator (`SKILL.md` and `commands/start.md`, identical in it), `flow.md` and `s-track.md` state each skip's effect (the review row skipped and recorded in `## Review`; `pr` stops Ship after the local commit) and advisory mode's behaviour.
- **AC-009** In an advisory repo `scaffold.py guardrails --render` renders none, and setup's text asks full or advisory first and names the steps advisory skips.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_modes.py › ModesTest.test_mode_is_set_through_scaffold_only_to_known_values | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_mode_is_set_through_scaffold_only_to_known_values` |
| AC-002 | tests/test_modes.py › ModesTest.test_skip_takes_only_named_steps_in_full_mode | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_skip_takes_only_named_steps_in_full_mode` |
| AC-003 | tests/test_modes.py › ModesTest.test_advisory_silences_the_process_hooks | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_advisory_silences_the_process_hooks` |
| AC-004 | tests/test_modes.py › ModesTest.test_advisory_silences_the_always_on_layer | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_advisory_silences_the_always_on_layer` |
| AC-006 | tests/test_modes.py › ModesTest.test_skipped_security_review_turns_off_the_feature_reviews | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_skipped_security_review_turns_off_the_feature_reviews` |
| AC-007 | tests/test_modes.py › ModesTest.test_relaxing_mode_or_skip_raises_a_trust_anchor_notice | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_relaxing_mode_or_skip_raises_a_trust_anchor_notice` |
| AC-008 | tests/test_modes.py › ModesTest.test_the_flow_text_names_skip_and_advisory | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_the_flow_text_names_skip_and_advisory` |
| AC-009 | tests/test_modes.py › ModesTest.test_advisory_setup_renders_nothing_that_enforces | `python3.10 -m unittest discover -s tests -t tests -p test_modes.py -k test_advisory_setup_renders_nothing_that_enforces` |

## Must never break

- A repo with no `mode` or `skip` (every repo today) behaves exactly as before.
- In full mode the red step, the test lock, verify and the change record are never skippable.
- A workbench's read-only guard and watch stay on in every mode. (`tests/test_modes.py › ModesTest.test_advisory_workbench_keeps_the_read_only_guard`)

## Failure modes

- **Untrusted input:** `mode` and `skip` come from a committed, agent-editable file. An unknown value counts as full / is ignored (AC-001, AC-002), and a relaxing change is shown to the user (AC-007).
- **Hook errors:** the advisory check never raises; on any error a hook behaves as in full mode (fail closed).
- Concurrency, persisted data and deploy: none apply (a config read per hook call).

## Out of scope

- Skipping Define, the red step, the test lock or verify.
- Per-feature overrides of `skip` (it's per repo).
- Team mode, Definition of Done and Storybook: separate todo items.

## Review

- **What fired:** code and security reviews (L, Risk: high), run without asking (self-chosen: L), each by a fresh `sdlc:code-reviewer` on opus. No dependency audit: the change adds no dependency.
- **Code review:**
  - r1 FAIL: H1 (one resolver), H2 (a reply accepts only what was shown), M1 to M5. All fixed, test first. M6 (stale docs) fixed in passing.
  - r2 PASS. Its medium bugs, R2-M1 to M3, M7 and M8, were fixed test first and closed by verify.
- **Security review:**
  - r1 FAIL: H1, H2, H3, M1 (plus unconfirmed H4 and H5). Fixed with the structural rule: a relaxation counts only once accepted, every reader uses one resolver, and reads are of regular files only.
  - r2 FAIL past the cap: R2-H1 to R2-H3. The user chose one more fix round.
  - r3 FAIL: R3-H1 (the HEAD path), R3-H2 (scaffold vs the session's folder), R3-M1. The user chose one more round.
  - r4 PASS. Its lows R4-L1 and R4-L2 were fixed test first.
- **Tickets in `.sdlc/todo.md`:** R3-L1 (Codex nested cwd), R3-L2 (check-then-open race), R3-L5 (status line stale mid-session), R4-L4 (spec 02 Known gaps).
- **Reports:** `.sdlc/.work/findings/2026-11-23-l-configurable-stages/` (`code-reviewer-r1`, `-r2`; `security-r1` to `-r4`).
- **Tests:** every AC red then green, re-red at Base after each test change. AC-005 is a must-never-break line, with its own regression test.
- **Lessons filed:** `.sdlc/recurring-defects.md`: "A setting whose readers resolve its file differently" (the class behind code r1 H1 and security r1 H2, r2 R2-H1/H2, r3 R3-H2).
