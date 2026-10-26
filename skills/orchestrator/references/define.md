# Define (Stage 1)

One document and one approval: what gets built, how it's proven, and the tasks. Old Stages 1–3 live here. Stay at `Current: Stage 1 – Define` until the approval, then `state.py advance <f> 4 --gate pass`. A feature resumed at old Stage 2 or 3 has an approved spec: finish the design or plan it started, show it with `Build:` for approval, then advance to 4.

1. **Read first.** If `knowledge/index.md` exists, read it and open only the docs relevant here. If `<docs>/recurring-defects.md` exists, read it: an entry that applies to this change becomes an acceptance criterion.
2. **Blocking questions, once** (before the spec; L: before brainstorming; S: before the brief). Ask only what changes what gets built and the request, ticket, code and knowledge don't settle. One message: numbered, plain text, options A/B/C, your recommendation first. Or ask none. Every other open point is a guess: `[inferred]` (Lite: the `Inferred` list) with a one-line reason, kept or dropped at the approval. Answers are `[clarified]`. Never ask again later.
3. **Keep to the brief.** Add no hardening, stricter validation, options, config or tooling that neither the request nor an applicable failure mode calls for. Anything else you'd add is `[inferred]` and dropped unless the user keeps it.
4. **S:** no spec and no approval. Write `<intents>/brief.md`: the bug, the expected behaviour, the answers, your assumptions, and on UI work the mapping line (`ui-work.md`). Then `advance <f> 4 --gate pass`.
5. **L:** `sdlc:brainstorming` first (writes `brainstorm.md`). It builds on the answers and spends its questions on approaches.
6. **The spec**, `<intents>/spec.md` (UI work: read `ui-work.md` first):
   - **`Flow: lite`.** Write it yourself; don't load `sdlc:writing-specs`. Sections:
     - Intent: the request verbatim and the answers, two lines.
     - Goal: one or two sentences.
     - Requirements: `FR-nnn`, each testable, from the request; additions go in an `Inferred` list.
     - Acceptance criteria: about 10 or fewer, each a behaviour a test can prove.
     - Non-Goals.
     - Failure modes: the edges from `review-brief.md` that apply, each turned into an acceptance criterion; none → one line saying so.
     - Tasks: 3–6 lines, each naming its files, FR and test.
     - `## Public Surface`: every export, file, endpoint, option, config key or dependency the change adds.

     No checklist, no plan.md.
   - **`Flow: full`.** Run `sdlc:writing-specs`, which writes `spec.md` and `checklists/requirements.md` with its `## Intent` section; on L the Intent summarizes `brainstorm.md` and links it. Then append `## Tasks` (bite-sized, test first, each naming its files, FR and test; a `UI mapping` section on UI work) and `## Public Surface`. Run `sdlc:clarifying-specs` only when the user asks.
   - **Bigger than one session** (more than about 8 tasks, or several distinct parts): a backlog instead of the Tasks (`backlog-slices.md`), approved with the spec.
7. **Design**, only on L, or on M when the approach isn't obvious. `sdlc:designing-solutions` writes `design.md`, `research.md`, `data-model.md`, `contracts/` and `quickstart.md`, dispatching `sdlc:code-explorer` and `sdlc:code-architect`. Criteria:
   - every FR/SC maps to the design;
   - every Complexity Tracking row (new module, layer, abstraction, dependency, service, config key, store, UI component, variant or token) cites a requirement;
   - nothing in Non-Goals is designed in;
   - the chosen approach and one rejected alternative are recorded;
   - the constitution check passes.

   UI design-system additions the user approves go into `<docs>/design-system.md` before Build, logged with `state.py log`.
8. **Consistency** on L, and on any backlog: run `sdlc:analyzing-consistency`. No CRITICAL or HIGH scope finding may remain; every requirement has a task or slice, and every task or slice cites a requirement.
9. **Size up** to `Flow: full` when the spec needs a design decision the request doesn't settle, or risk turns out high: `state.py set <f> Flow full` (or `Risk high`) and say why in one line. Not for a backlog feature.
10. **Approval, the one hard stop.** One message, containing:
    - the spec path;
    - every `[inferred]` item as its own list, with a one-line reason each (dropped unless the user keeps it; dropped items go to Non-Goals);
    - the design's choice and the rejected alternative, when a design ran;
    - the tasks or backlog;
    - `Build: <the track's default>`, which the user can change in the reply.

    **Gate:**
    - the user approves;
    - the requirements checklist passes (full flow);
    - no `[inferred]` tags remain;
    - Non-Goals is filled;
    - the acceptance criteria are testable;
    - every FR has a task and every task an FR;
    - Public Surface is declared;
    - the design criteria hold, when a design ran.

    Then `state.py set` anything the reply changed, and `state.py advance <f> 4 --gate pass`.
