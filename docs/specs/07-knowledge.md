# Spec 07: Knowledge

What the team learns is kept where the agent finds it at the right moment, without growing the context every session pays for.

**Entry points:** `/sdlc:managing-knowledge lessons`, `/sdlc:managing-knowledge audit`, Define (reads) and Learn, in Ship (writes), setup (seeds) · **Source:** `skills/managing-knowledge/SKILL.md`, `commands/knowledge-audit.md`, `commands/revise-claude-md.md`, `templates/knowledge/`, `skills/managing-knowledge/references/claude-md-improver.md` (and its folder)

## User scenarios

1. **Promote a lesson.** Given a retro bullet that's still true outside the feature, when Learn runs, then it's filed in the right tier (path-specific → a tier-2 rule line, explanation → a tier-3 doc) and linked from `knowledge/index.md`.
2. **Repeated correction.** Given the user corrected the same thing twice and it's checkable, then it becomes a hookify rule rather than more text.
3. **CLAUDE.md too long.** Given `CLAUDE.md` over 60 lines, when `/sdlc:managing-knowledge audit` runs, then it proposes moves line by line with reasons and before/after counts, and applies only what the user approves.

## Requirements

| ID | Requirement | Guarantee |
|---|---|---|
| KNW-FR-001 | Three tiers: **1** `CLAUDE.md`, every session, ≤ 60 lines; **2** `.claude/rules/<area>.md` with `paths:`, loaded when matching files are touched, ≤ 30 lines each; **3** `knowledge/**.md` (OKF, `type` frontmatter, one concept per file), on demand via `knowledge/index.md` and tier-2 links. | `[instructed]` managing-knowledge; budgets checked by doctor `[enforced]` test_doctor › test_claude_md_budget |
| KNW-FR-002 | Never `@import` the knowledge folder or index into `CLAUDE.md`. | `[instructed]` managing-knowledge |
| KNW-FR-003 | Filing a lesson: durable? → checkable and corrected before → hookify; else pick the tier; update before create; write tier-3 docs in OKF folders (conventions, decisions, gotchas, runbooks, features); link from the index and tier-2 rule; log in `knowledge/log.md`. | `[instructed]` managing-knowledge |
| KNW-FR-004 | An unlinked tier-3 doc is invisible: every doc is linked from the index; broken index links are reported. | `[instructed]`; broken links `[enforced]` test_doctor › test_knowledge_index_links |
| KNW-FR-005 | Tier-2 rules whose `paths:` match no files are reported (they never load). | `[enforced]` test_doctor › test_rules_whose_paths_match_nothing |
| KNW-FR-006 | Define reads `knowledge/index.md` and opens only relevant docs. Learn files a lesson only when the session found one that isn't obvious from the code, the commit or the design, through `managing-knowledge` (corrected twice and checkable → hookify; `CLAUDE.md` over 60 lines → the audit); on L it also writes `retro.md` (history, not loaded later) and every promoted lesson is linked from `knowledge/index.md` or a tier-2 rule. | `[instructed]` orchestrator: define, ship |
| KNW-FR-007 | Audit: path-specific lines move to tier 2, explanations and procedures to tier 3, duplicates of tooling and stale lines are deleted; report before/after counts; apply only approved moves. A quality check of a `CLAUDE.md` with targeted edits (formerly the `claude-md-improver` skill) is a reference the audit reads, not a separate skill. | `[instructed]` managing-knowledge (and `references/claude-md-improver.md`), knowledge-audit.md |
| KNW-FR-008 | Brownfield setup drafts conventions, gotchas (from git history), decisions and area rules; written only with per-batch approval; `knowledge/` is user-owned from the start. | `[instructed]` brownfield.md |
| KNW-FR-009 | The plugin never writes `CLAUDE.md` itself; changes there come from the user-approved audit or revise flows. | `[instructed]` setting-up-projects, revise-claude-md |
| KNW-FR-010 | Learn runs at the end of every feature, on every track (a backlog: once, at Feature close), after Ship's verified-tree check and before its one commit, so it lands in it. On S, M lite and `Prove: skip`, which have no Prove and no `review.md`, Learn files a lesson only when it isn't obvious from the code, the commit or the design. Each high finding Prove fixed (`## Fixed` in `review.md`) that a reviewer could check next time gets one line in `<docs>/recurring-defects.md`, unless already listed. Define reads that file (an entry that applies becomes an acceptance criterion), and so does every reviewer brief. | `[instructed]` orchestrator: ship, define, `review-brief.md` |

## Non-goals

- A shared cross-repo knowledge base (deferred to the team rollout); search or embeddings over knowledge.

## Known gaps

- Tier loading itself is Claude Code's behavior (`paths:` rules, `CLAUDE.md`); the plugin only shapes what goes where.
