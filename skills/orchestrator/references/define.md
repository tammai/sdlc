# Define (Stage 1)

Three documents and one approval: `intent.md` (why), `spec.md` (what) and `plan.md` (how), on M and L. S writes none of them (step 0). Old Stages 1–3 live here. Stay at `Current: Stage 1 – Define` until the approval, then `state.py advance <f> 4 --gate pass`. A feature resumed at old Stage 2 or 3 has an approved spec: finish the design or plan it started (reuse an existing `plan.md`), show it with `Build:` for approval, then advance to 4.

**Nothing stays in your head.** Build, Prove and later role agents work from these files alone, with no conversation. So every answer, choice, constraint and assumption goes into one of the three files before the approval. Test: could a fresh agent build this from `intent.md`, `spec.md` and `plan.md` without asking?

0. **S writes no documents** (a fix: the expected behaviour is already known). After the read and any blocking question (steps 1–2), record two lines in the state file and nothing else, then `state.py advance <f> 4 --gate pass`, with no approval:
   - `state.py set <f> Intent "<the bug and the expected behaviour, one line>"`;
   - `state.py set <f> Repro "<test file> › <test name> | <command that runs only that test>"`: the repro test Build writes first. `verify.py` treats it as AC-001.

   The steps below are for M and L.
1. **Read first.** If `knowledge/index.md` exists, read it and open only the docs relevant here. If `<docs>/recurring-defects.md` exists, read it: an entry that applies to this change becomes an acceptance criterion.
2. **Blocking questions, once** (before `intent.md`; L: before brainstorming). Ask only what changes what gets built and the request, ticket, code and knowledge don't settle. One message: numbered, plain text, options A/B/C, your recommendation first. Or ask none. Every other open point is a guess: `[inferred]` (Lite: the `Inferred` list) with a one-line reason, kept or dropped at the approval. Answers are `[clarified]`. Never ask again later.
3. **Keep to the brief.** Add no hardening, stricter validation, options, config or tooling that neither the request nor an applicable failure mode calls for. Anything else you'd add is `[inferred]` and dropped unless the user keeps it.
4. **`intent.md`: the why.** Write `<intents>/intent.md` from `${CLAUDE_PLUGIN_ROOT}/templates/intent-template.md` (the core's rule on documents: file-writing tool, never the shell) and keep its seven headings:
   1. intent and why (with the request verbatim)
   2. questions and answers
   3. approaches considered, with trade-offs
   4. the chosen approach and why
   5. the chosen approach in detail (design level: structure, data flow, what stays untouched)
   6. goals, non-goals and constraints
   7. calls made, and what's left to the builder

   By track:
   - **M:** about a page, written yourself after reading the code the change touches. Don't load `sdlc:brainstorming`. Lay out 2–3 approaches and recommend one; the user confirms it, or picks another, in the approval. Ask no extra question.
   - **L:** `sdlc:brainstorming` writes it. It builds on the answers, spends its questions on approaches (the user picks there), and runs its builder check.
5. **`spec.md`: the what.** Requirements and how to tell they're met; no files, code structure or tasks (those are the plan's). It opens with `Intent: [intent.md](intent.md) · Plan: [plan.md](plan.md)`. UI work: read `ui-work.md` first.
   - **Every track:** each acceptance criterion carries an id, `AC-001` onward, numbered across the spec; `plan.md`'s `## Acceptance tests` names the test that proves each one (step 7).
   - **`Flow: lite`:** write it yourself; don't load `sdlc:writing-specs`. Sections:
     - Goal: one or two sentences.
     - Requirements: `FR-nnn`, each testable, from the request; additions go in an `Inferred` list.
     - Acceptance criteria: about 10 or fewer, each a new or changed behaviour a test can prove, so its test fails before the change. Never "existing tests still pass": `verify.py` runs the whole suite anyway, and such a criterion can't be recorded red.
     - Non-Goals.
     - Failure modes: the edges from `review-brief.md` that apply, each turned into an acceptance criterion; none → one line saying so.

     No checklist.
   - **`Flow: full`:** `sdlc:writing-specs` writes `spec.md` and `checklists/requirements.md`. Run `sdlc:clarifying-specs` only when the user asks.
6. **Design**, only on L, or on M when the approach isn't obvious. `sdlc:designing-solutions` writes `design.md`, `research.md`, `data-model.md`, `contracts/` and `quickstart.md`, dispatching `sdlc:code-explorer` and `sdlc:code-architect`. `intent.md`'s detail section then summarizes `design.md` and links it. Criteria:
   - every FR/SC maps to the design;
   - every Complexity Tracking row (new module, layer, abstraction, dependency, service, config key, store, UI component, variant or token) cites a requirement;
   - nothing in Non-Goals is designed in;
   - the chosen approach and one rejected alternative are recorded;
   - the constitution check passes.

   UI design-system additions the user approves go into `<docs>/design-system.md` before Build, logged with `state.py log`.
7. **`plan.md`: the how.** It holds:
   - the tasks in order, each naming its files (backticked: `verify.py` reports a changed file no task or test names as drift), the test it starts with, the command that proves it, and its FR;
   - `## Acceptance tests`: one row per `AC-nnn`, with the test that proves it (`file › name`) and a command that runs only that test; a criterion no automated test can prove (a visual result, a wording change) is `manual`, with its reason in the Run cell. Build records each test red before its code and `verify.py` checks the table;
   - `## Public Surface`, which Prove checks the diff against;
   - `## UI mapping` on UI work;
   - `## Review Focus`;
   - `## Deviations`, empty until Build.

   By track:
   - **`Flow: lite`:** write `<intents>/plan.md` yourself from `${CLAUDE_PLUGIN_ROOT}/templates/plan-template.md`, with 3–6 tasks.
   - **`Flow: full`:** `sdlc:writing-plans` writes it. Tell it the orchestrator decides the execution method (`Build:`), so it asks no question, and that a change confined to 1–2 files gets 1–3 tasks: one piece of work stays one piece.
   - **Bigger than one session** (several distinct parts that won't fit one session; never a 1–2-file change): `backlog.md` (`backlog-slices.md`), and `plan.md` gives each slice a how-outline: approach, main files, interfaces between slices, and the feature's Public Surface. Each slice's detailed `plan-B<n>.md` is written when the slice starts.
8. **Consistency** on L, and on any backlog: run `sdlc:analyzing-consistency`. No CRITICAL or HIGH scope finding may remain; every requirement has a task or slice, and every task or slice cites a requirement.
10. **Size up** to `Flow: full` when the spec needs a design decision the request doesn't settle, or risk turns out high: `state.py set <f> Flow full` (or `Risk high`) and say why in one line. Not for a backlog feature. To L only when the approach is still unclear here or the change grew past 1–2 files into several parts; L with a 1–2-file footprint and a settled approach goes down to M (`state.py set <f> Track M`, `Risk high`, `Flow full`).
11. **Approval, the one hard stop.** One message, containing:
    - the paths to `intent.md`, `spec.md` and `plan.md` (and `backlog.md`);
    - the chosen approach in one line, with the alternatives' names (M: your recommendation, which the user can change in the reply; then update `intent.md` and `plan.md`);
    - every `[inferred]` item as its own list, with a one-line reason each (dropped unless the user keeps it; dropped items go to Non-Goals);
    - the design's choice and the rejected alternative, when a design ran;
    - the tasks (or slices) in one line each, and the Public Surface;
    - the acceptance criteria with the test that will prove each, and the `manual` ones listed apart with their reasons;
    - `Build: <the track's default>`, which the user can change in the reply;
    - on M full and L: `Prove: run`, unless the user says skip (record it with `state.py set <f> Prove skip`). In an autopilot or headless run nobody can answer: it stays `run`.

    **Gate:**
    - the user approves;
    - `intent.md` has all seven headings and names the chosen approach;
    - the requirements checklist passes (full flow);
    - no `[inferred]` tags remain;
    - Non-Goals is filled;
    - the acceptance criteria are testable;
    - every FR has a task (or slice) in the plan, and every task an FR;
    - every `AC-nnn` has a row in `## Acceptance tests`;
    - `plan.md` declares the Public Surface;
    - the design criteria hold, when a design ran;
    - the three files stand alone.

    Then update the files and `state.py set` for anything the reply changed, and `state.py advance <f> 4 --gate pass`.
