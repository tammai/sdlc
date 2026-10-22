# ADR 0003: Guard against over-engineering and comment noise

- **Status:** Accepted, 2026-10-22.
- **Deciders:** Tâm Mai.

## Context

Agents tend to write long, narrating comments and to over-engineer: abstractions with one implementation, options nobody asked for, extra files and dependencies. The plugin only caught this after the fact (YAGNI wording in plans, `code-simplifier` in Stage 6), and some of it worked against itself: `comment-analyzer` asked for comments aimed at "the least experienced future maintainer", and the Stage 6 gate only blocked on high severity, which over-engineering rarely gets.

Most of it starts before any code exists. A speculative requirement in the spec becomes an abstraction in the design, then tasks in the plan, and by review it looks requested.

## Decision

Act at every point where it can creep in, and turn checkable rules into checks.

**Upstream: trace scope to a request.**

| Stage | Mechanism |
|---|---|
| Sizing | Smallest fitting track; sizing up names its signal in `state.md` |
| 1 Spec | Every requirement tagged `[user]`, `[clarified]` or `[inferred]`; required Non-Goals; future-proofing words need a measurable requirement. At the gate, `[inferred]` items are **dropped unless the user keeps them**, and dropped ones go to Non-Goals. |
| 2 Design | Complexity Tracking always filled: every new module, layer, abstraction, dependency, service, config key or store cites a requirement, or comes out. Architect options: minimal, minimal plus one named extension, pragmatic; minimal is recommended unless it fails a named requirement. A "Deliberately not built" section. |
| 3 Plan | Every task has a `Requirements:` line, checked both ways in the self-review; a **Public Surface** section declares every new export, endpoint, command, config key, env var and dependency. In `analyzing-consistency`, leftover `[inferred]` or a planned Non-Goal is CRITICAL, other scope creep HIGH. |

**While writing:** a generated policy rule, `sdlc-code-style.md`, scoped to source files: comments say *why* only (no narration, restated code or change history), doc comments on exported API and one line by default, the smallest diff that meets the criteria, no unrequested abstractions or surface. The same lines go into the subagent implementer prompt, since rules files may not reach subagents.

**Automatic checks:** seeded hookify guardrails warn on narrating, history and long doc comments, suppressions, focused or skipped tests and `console.log`, and block dangerous `rm`, force-push to main and secret values. ESLint and Ruff snippets cover complexity, nesting, parameter count, function length and leftover TODOs.

**Review:** `scripts/diff_stats.py` gives every reviewer measured facts: comment share, new files, unused and single-use exports, single-implementation abstractions, new dependencies, and, with `--plan`, exports and dependencies missing from the Public Surface. Unrequested public surface is high severity; comment noise is medium and fixed in Stage 6. The S track also runs `code-simplifier`. `comment-analyzer` now asks for comments only where the code, names, types and git history can't carry the meaning. The constitution template ships a default Simplicity principle.

Hookify needed three patches for this (recorded in NOTICE.md): load committed team rules from `.claude/hookify/*.md`; send warnings to Claude as `additionalContext` and block reasons as `permissionDecisionReason` (upstream only used `systemMessage`, which only the user sees); and stop re-evaluating every rule after each tool call.

## Consequences

- **Good:** scope that slips in during implementation is flagged mechanically; the agent sees warnings while writing, not only at review.
- **Costs:** more for the user to read at the Stage 1 gate (the inferred list) and Stage 3 (Public Surface); regex guardrails will sometimes warn on legitimate comments (they warn, they don't block).
- **Limits:** spec and design tracing is instructions plus user approval; only the Stage 6 surface check and the guardrails are mechanical. The S track has no plan to check against.
