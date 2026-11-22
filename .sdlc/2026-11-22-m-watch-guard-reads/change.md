# The watch guard lets a read name its files

## Why

From `.sdlc/todo.md`: "The guard denies reads that merely name the watch's files (`grep read-only-seeded`, a commit message): narrow it to writes and runs (security-r7 SR7-L4) (2026-11-13)".

Today, in a session started in a workbench, `role_guard.read_only_problem` denies any call whose command or path contains one of the watch's names:
- the script `read_only_watch`;
- its files, `read-only-baseline` and `read-only-seeded`;
- its data folder, `claude_plugin_data` or `.cache/sdlc`.

So `grep read-only-seeded hooks/*.py`, `git log --grep read_only_watch`, a commit message that mentions the watch, and a Grep or Glob tool call on the data folder are all denied, though none can feed the watch a fake accept or remove its baseline. Agents working on sdlc itself in a workbench hit this, and so does anyone reading its logs.

The guard exists so that the agent can't write the watch's baseline or marker, and can't run the watch with a fake `accept read-only` event (spec 06 GRD-FR-034). Writes and runs are what it must stop. Reads aren't.

## Decisions

| Decision | Chosen | Ruled out |
|---|---|---|
| What a mention may do | A shell command naming a watch name is allowed only when it reads: its program is on a short list of readers, and nothing in it writes to, deletes or runs anything | A blocklist of writers (`rm`, `mv`, `tee`, `python`…). Every review found another spelling, the recurring "guard that reads command text" defect, so an unknown program stays denied |
| Readers, sh | `grep` `egrep` `fgrep` `rg` `ag` `ack` `cat` `less` `more` `head` `tail` `wc` `ls` `stat` `file`; `find` without `-delete`, `-exec`, `-execdir`, `-ok`, `-okdir`, `-fprint*`, `-fls`; `git` with `log` `show` `diff` `grep` `status` `blame` `commit` (the token only in its message) | `sed`, `awk`, `xargs`, `env`, `bash -c`: they can write or run |
| Readers, PowerShell | `Select-String` `sls` `Get-Content` `gc` `cat` `type` `Get-ChildItem` `gci` `ls` `dir` `Get-Item` `gi` `Measure-Object` | Any cmdlet with `-Out`, `Set-`, `Remove-` |
| Where a mention still denies | In a redirect target, anywhere in a here-doc a shell reads, in a command substitution or subshell whose program isn't a reader, and as the path of an Edit, Write, MultiEdit or NotebookEdit | — |
| Read-only tools | Read, Grep and Glob naming the files are allowed: they can't write | — |

## Acceptance criteria

- **AC-001** In a workbench, these are allowed: `grep read-only-seeded hooks/*.py`, `rg read_only_watch`, `git log --grep read_only_watch`, `git commit -m "fix read_only_watch"`, `cat .sdlc/.work/read-only-seeded`, `ls ~/.cache/sdlc`, `find ~/.cache/sdlc -name '*.json'`, `Select-String read-only-seeded` (PowerShell), and a Grep or Glob tool call on the data folder.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_workbench.py › ReadOnlyBackstop.test_a_read_that_names_the_watch_is_allowed | `python3.10 -m unittest discover -s tests -t tests -p test_workbench.py -k test_a_read_that_names_the_watch_is_allowed` |

## Must never break

- Every call the guard denies today is still denied (`test_a_write_or_run_that_names_the_watch_is_still_denied`, written with this change and passing before it: it guards the narrowing). That includes the existing test's commands (`rm …`, `echo … | python3 hooks/read_only_watch.py`, `python3 -c 'import read_only_watch'`, `echo {} > …baseline…`, a Write to the marker). It also includes reader programs used to write or run: `grep x > .sdlc/.work/read-only-seeded`, `cat x | tee …seeded`, `find ~/.cache/sdlc -delete`, `find … -exec rm {} +`, `cat $(python3 hooks/read_only_watch.py)`, `git checkout -- .sdlc/.work/read-only-seeded`, `sed -i … read-only-seeded`, `bash -c "cat read-only-seeded"`, and `Remove-Item …seeded` (PowerShell).
- `test_the_agent_cannot_accept_or_edit_the_baseline` passes unchanged.
- An unknown program that names a watch name stays denied: the guard fails closed.
- Outside a workbench the guard stays silent.

## Failure modes

- Untrusted input reaching a file path: the agent's own command text is the input. Each simple command is judged on its own, including the commands inside substitutions and subshells (`lex` already splits those out), and the guard denies when unsure.
- A parser over an open set of shell spellings: an allowlist of readers, never a list of writers.

## Out of scope

- The watch's own backstop. It still sees a change in a read-only repo whatever made it.
- A deliberate agent spelling around the text check, as GRD-FR-034 already says.

## Review

- **Fired:** security and code, both because Risk is high. The user chose both. Security ran as `sdlc:code-reviewer` on opus, code as the built-in `/code-review high`.
- **Security r1, FAIL:** four highs, SR1-H1 to SR1-H4.
  - H1: `lex` reads shell syntax differently from the shell: a substitution inside `$(( ))`, an escaped-space `#`, ANSI-C quoting, zsh's `>!`.
  - H2: environment and bare assignments are never checked (`GIT_TRACE=…marker`, `GIT_EXTERNAL_DIFF`, `PATH=.:$PATH`).
  - H3: git option spellings (`-lOrm`, `--open-files=`).
  - H4: a `cd` into the data folder, followed by a later bare `rm *`.
- **Code r1, FAIL:**
  - Five highs (C1–C5): flags supplied by a variable, environment prefixes, `git grep --op=`/`-nO`, `./cat`, `rg --hostname-bin`.
  - C6: a commit message in Claude Code's here-doc form is still denied, which defeats the main case.
  - C11: the change breaks `.claude/rules/hooks.md`, "move work out of a guarded stage rather than widening a parser".
- **Outcome: not built.** The user chose to drop the narrowing. Every fix would have added another parser rule to a text guard. Reading the watch's files already works through the Read, Grep and Glob tools, which this guard never checks. `hooks/role_guard.py`, `hooks/read_only_watch.py` and spec 06 were reverted to Base. The AC-001 test was removed with them.
- **Kept:** `test_a_write_or_run_that_names_the_watch_is_still_denied`, which pins every bypass found here as denied. It passes on the unchanged guard and guards any later narrowing.
- **Tickets in `.sdlc/todo.md`:**
  - the `lex` gaps (SR1-H1), which predate this change and reach the read-only-repo write guard (GRD-FR-033) too;
  - the Monitor tool, which never reaches `read_only_problem` (C12).
- **Todo closed as won't do,** with this file as the reason.
