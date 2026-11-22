# The fixed-name writers refuse a link out of the repo or into .git

## Why

From `.sdlc/todo.md`: "The fixed-name writers follow a committed link anywhere, `.git` included: `write_agents` (AGENTS.md), `cmd_gitignore` (.gitignore) and `cmd_allow` (.claude/settings.json) open with `open(path, "w")`, so `AGENTS.md -> .git/config` or a hook gets the managed block appended; give them the `inside_repo` and `git_internal` checks, or refuse to write through a link — security review R2-3 of 2026-11-22-s-lock-template-trusted, predates it; `scripts/scaffold.py`".

A link is committed like any file, and cloning a repo isn't consent (`knowledge/gotchas/repo-config-is-untrusted.md`). Proof: with `.gitignore`, `.claude/settings.json` or `.claude/settings.local.json` linked to a file outside the repo or to `.git/config`, `scaffold.py gitignore`, `allow` and `enable-plugin` write through the link (the AC-001 tests fail), and `agents` does the same through `AGENTS.md`. Reading through the link also copies the outside file's text into the repo: `.gitignore`'s lines are written back, and AGENTS.md's text reaches the Claude Code mirror rule. Root cause: these files are opened by their fixed name with no containment check, while lock-recorded files already go through `inside_repo` and `git_internal`.

## Decisions

- **One check, `fixed_target(p, rel)`, on every open of a fixed-name file sdlc merges into:** AGENTS.md, `.gitignore`, `.claude/settings.json` and `.claude/settings.local.json`, in `allow`, `gitignore`, `enable-plugin`, the impeccable enable, the plugin-key unmerge, the workbench's `.gitignore` edits and `agents`. It refuses (exit 2, naming the file) when the path, after links, leaves the repo or lands in a git dir. It reuses the two checks lock-recorded files already use, so a folder link (`.claude -> .git/info`) and the Windows `.git` aliases are covered too.
- **A link that stays inside the repo, outside `.git`, is still followed**, as for lock-recorded files: whoever commits it could commit the file itself.
- **Eject doesn't stop half-way:** a linked fixed file, or one under a linked folder such as `.claude`, is listed under `outside` in the plan and the result, and skipped; the rest of the eject runs. An unmerge with nothing recorded opens nothing.
- **Readers too (review r1 H-2, M-2):** the settings readers (`plugin_enabled`, `impeccable_hook_wired`, `enabled_elsewhere`, design's enable, doctor, `context_diet.py`) and doctor's `.gitignore` reads go through `read_fixed_json` / `link_problem` and read a linked file as absent, so its values never decide anything. `enable-plugin` refuses before it reads. The AGENTS.md block skips a CLAUDE.md or `.claude/rules/*.md` that leads out of the repo, so its text never reaches AGENTS.md. Doctor names a linked AGENTS.md instead of calling it stale.
- **AGENTS.md through such a link reads as absent** for the mirror and `agents_state` (doctor), so its text is never copied into the repo.
- Ruled out: refusing every link. Repos link AGENTS.md to CLAUDE.md (or the reverse) to share one file between agents.

## Acceptance criteria

- **AC-001** `gitignore`, `allow`, `enable-plugin` and `agents` refuse (exit 2, naming the file) when `.gitignore`, `.claude/settings.json`, `.claude/settings.local.json` or AGENTS.md is a link to a file outside the repo or into `.git`, or `.claude` is a link into `.git`; neither target changes. A link to a file inside the repo is still written through.
- **AC-002** `eject` (plan and apply) lists a linked `.gitignore`, or the settings files under a `.claude` linked into `.git` or outside, under `outside`, leaves the targets unchanged, and still finishes (the lock is removed).
- **AC-003** A settings file linked out of the repo reads as absent to `plugin_enabled`, `impeccable_hook_wired`, `enabled_elsewhere` and `read_fixed_json`; `enable-plugin` and `enable-plugin --remove` (with keys to take back) refuse it and leave it unchanged.
- **AC-004** A CLAUDE.md or `.claude/rules/*.md` linked to a file outside the repo never reaches AGENTS.md's block.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_fixed_name_writers_refuse_a_link_out_of_the_repo_or_into_git | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_fixed_name_writers_refuse_a_link_out_of_the_repo_or_into_git` |
| AC-001 | tests/test_scaffold.py › ScaffoldTest.test_agents_md_link_out_of_the_repo_is_refused | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_agents_md_link_out_of_the_repo_is_refused` |
| AC-002 | tests/test_scaffold.py › ScaffoldTest.test_eject_leaves_a_linked_fixed_file_untouched_and_lists_it | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_eject_leaves_a_linked_fixed_file_untouched_and_lists_it` |
| AC-002 | tests/test_scaffold.py › ScaffoldTest.test_eject_finishes_with_claude_linked_into_git_or_outside | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_eject_finishes_with_claude_linked_into_git_or_outside` |
| AC-003 | tests/test_scaffold.py › ScaffoldTest.test_settings_read_through_a_link_read_as_absent | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_settings_read_through_a_link_read_as_absent` |
| AC-004 | tests/test_scaffold.py › ScaffoldTest.test_agents_block_skips_sources_linked_out_of_the_repo | `python3.10 -m unittest discover -s tests -t tests -p test_scaffold.py -k test_agents_block_skips_sources_linked_out_of_the_repo` |

## Must never break

- Plain files (and no file yet) are read and written as before: the rest of `test_scaffold`, `test_doctor` and `test_workbench` pass.
- `exclude_locally` still writes `.git/info/exclude`: it is git's own path from `git rev-parse`, not a committed name.

## Failure modes

- Untrusted input reaching a file path: a committed link; checked on the resolved path, every segment, with another Windows drive counted as outside.

## Out of scope

- S-2 (a `generated` lock entry acting on an untracked local file) and R2-5 (HFS+ ignorable code points): separate todos.

## Review

- **Fired:** security, because `Risk: high` (a committed link reaching a file path). `sdlc:code-reviewer` on opus.
- **Round 1, FAIL:** H-1 (high) eject still stopped half-way when `.claude` was the link and the settings files under it were absent. H-2 (high) the settings files were still read through a link before or without the check (`plugin_enabled`, `impeccable_hook_wired`, `enabled_elsewhere`, design's enable, doctor, context_diet). M-1 test gaps; M-2 CLAUDE.md and `.claude/rules/*.md` copied into AGENTS.md through a link (same class, folded in); M-3 doctor called a linked AGENTS.md stale; L-1 tests passed silently without symlinks. All fixed, test first: AC-002 widened, AC-003 and AC-004 added; one reader, `read_fixed_json` / `link_problem`, on every open.
- **Round 2, PASS.** Its medium bug R2-M1 (`agents` refused a linked AGENTS.md with nothing to write, stopping setup in a Claude-only repo) was fixed test first (`test_agents_with_nothing_to_write_leaves_a_linked_agents_md_alone`), plus a duplicated `sys.path` insert.
- **Tickets in `.sdlc/todo.md`:** R2-M2 (tests for rewired readers that go through the tested helpers), R2-L1 (doctor reads CLAUDE.md through a link to count lines, predates it), R2-L2 (eject lists linked files sdlc never merged into).
- **Lessons:** none new; the recurring defect "a path rule checked on one form of the path only" already covers it.

