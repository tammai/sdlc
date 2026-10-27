---
name: managing-knowledge
description: Files a lesson, decision, gotcha or runbook into the right loading tier (CLAUDE.md, path-scoped rule or knowledge/ doc) so context stays small; also sets up and audits a knowledge base. Use when saving something future agents need, or when CLAUDE.md grows long.
---

`${CLAUDE_PLUGIN_ROOT}` is the sdlc plugin's folder. Claude Code fills it in; on other agents it stays as written, so use the installed plugin's folder instead: the one above this file that holds `scripts/` and `skills/`.

# Managing Knowledge (3-tier loading)

Paths: `<intents>` is the feature's documents folder, `<state>` its state file and `<docs>` the sdlc docs folder (`docs_dir`); `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" paths <feature>` prints them for this repo's layout.

Goal: the agent sees the right knowledge at the right moment, and nothing else. Context is the budget; every always-loaded line costs every session.

| Tier | Where | Loads | Budget |
|---|---|---|---|
| **1 · Always** | `CLAUDE.md` (repo root) | Every session, at launch | ≤ 60 lines total |
| **2 · By area** | `.claude/rules/<area>.md` with `paths:` | Automatically, the first time the agent reads/edits a matching file | ≤ 30 lines each |
| **3 · On demand** | `knowledge/**.md` (OKF) | Only when a tier-1/2 line or `knowledge/index.md` points there and the task needs it | No limit; one concept per file |

Enforcement sits beside the tiers: anything that was corrected twice and can be checked mechanically becomes a hook (`/sdlc:hookify`), not more text.

**Never `@import` the knowledge folder or index into CLAUDE.md** — imports load at launch and defeat tier 3.

## Set up (once per repo)

1. Create `knowledge/index.md` (template: `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/index.md`) and `knowledge/log.md`.
2. **Only in a repo not set up for sdlc** (no `.claude/rules/sdlc.md`, which already carries the knowledge pointer): trim `CLAUDE.md` to tier 1 using the audit below, and add near the top:
   `Knowledge map: \`knowledge/index.md\` — read it before working in an area you haven't touched this session, then open only the docs relevant to the task.`
   (Backticks keep it from being imported.)
3. Create one `.claude/rules/<area>.md` per real area of the codebase (template: `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/rule.md`). Typical areas: api, db/migrations, frontend, payments, auth, infra, tests.

## File a lesson

For each candidate (from a retro, a review, a debugging session, or the user saying "remember this"):

1. **Is it durable?** Still true in a month, outside this feature? No → leave it in the retro.
2. **Is it enforceable and was it corrected before?** → hookify rule. Optionally one line in the tier-2 rule saying why.
3. **Pick the tier:**
   - Applies to almost every task in the repo (build/test commands, a global non-negotiable) → **tier 1**. CLAUDE.md is over 60 lines? Something must move down a tier first.
   - Applies when touching certain paths → **tier 2**: one imperative line in that area's rule, plus a link to a tier-3 doc if there's a why/how.
   - Explanation, history, decision record, runbook, gotcha detail → **tier 3**.
4. **Update before create.** Search `knowledge/` and the rules for an existing entry; edit it rather than adding a near-duplicate.
5. **Write tier-3 docs in OKF** — one concept per file, path = identity, frontmatter `type` required:
   - `knowledge/conventions/<slug>.md` — `type: convention`
   - `knowledge/decisions/<yyyy-mm>-<slug>.md` — `type: decision` (context, decision, alternatives, consequences)
   - `knowledge/gotchas/<slug>.md` — `type: gotcha` (symptom, cause, fix, how to detect)
   - `knowledge/runbooks/<slug>.md` — `type: runbook` (when, steps, verify, rollback)
   - `knowledge/features/<slug>.md` — `type: feature` (one paragraph + links to `<intents>/intent.md`, `spec.md`, `plan.md`)
   Template: `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/doc.md`. Link related docs with relative Markdown links.
6. **Wire it in:** add one line to `knowledge/index.md` (path + ≤12-word description) and, for path-related docs, a link from the matching tier-2 rule. An unlinked tier-3 doc is invisible — never leave one.
7. **Log it:** `knowledge/log.md` → `- YYYY-MM-DD <add|update|remove> <path> — <why> (from <feature>)`.
8. **Changed CLAUDE.md, a rule or AGENTS.md?** Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" agents` so the other agents' copy in `AGENTS.md` (and Claude Code's copy of the team's `AGENTS.md` text) follows. It does nothing in a repo only Claude Code uses.

## Audit (run when CLAUDE.md > 60 lines, or every few features)

To check a CLAUDE.md's quality and propose targeted edits (the old claude-md-improver), follow [references/claude-md-improver.md](references/claude-md-improver.md).

Go through CLAUDE.md line by line:
- Only matters for some paths → move to the tier-2 rule for that area.
- Explanation, example or history → move to a tier-3 doc; leave at most a one-line pointer.
- Multi-step procedure → tier-3 runbook (or a skill if it's a repeated workflow).
- Duplicates a hook, linter, formatter or type-checker → delete.
- Stale or contradicted → delete (log it).

Then check: every tier-3 doc is linked from the index; every rule's `paths` still match real files; no rule exceeds 30 lines.

Report: lines before → after for CLAUDE.md, files moved/created/deleted.
