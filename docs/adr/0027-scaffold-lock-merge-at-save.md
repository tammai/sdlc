# ADR 0027: Scaffold's lock and config merge at save; no mutex across commands

- **Status:** Accepted, 2026-11-15. Records:
  - `.sdlc/2026-11-15-m-scaffold-lock-safety/change.md` (two mutex designs, dropped);
  - `.sdlc/2026-11-15-m-lock-merge-and-tickets/change.md` (merge at save);
  - `.sdlc/2026-11-15-m-config-merge-and-containment/change.md` (config, `inside_repo`).
- **Deciders:** Tâm Mai.

## Context

`.sdlc/scaffold.lock.json` records every file the plugin placed, and `.sdlc/config.json` holds the repo's settings.
Every `scaffold.py` command reads one or both, changes them and writes them back. Two commands at once (parallel build
parts, a hook beside a command, Windows and WSL on one checkout) used to lose one's change: the last write won.

Two mutual-exclusion designs were built and reviewed, and both were dropped:
- **A lock file, created exclusively and deleted on release:** a stale takeover and the release could each delete
  another command's lock, giving two writers. The wait could spin forever. Antivirus and clock skew broke it.
- **An OS lock** (`fcntl.flock`, `msvcrt.locking`) **on a file never deleted:** eject deleted a held lock, a
  filesystem without locks hung every command for 60 s, and Windows and WSL don't exclude each other.

## Decision

- **Detect and merge, don't prevent** (the user's choice at the review cap). `Project` keeps a copy of each file as
  it read it. At save it re-reads the file and applies only this command's changes (`merge_into`):
  - sections merge key by key and lists by item;
  - a record in `files`, `conventions` or `command_runs`, and a list of objects such as `packages`, is kept whole,
    and where both commands changed it, the last writer's version wins;
  - this command's own objects stay the ones it saves, so a rollback through a held reference still lands.
- **A file is written only when this command changed it** (the lock also when `init` set it). A file removed or
  broken meanwhile is an error, never recreated or overwritten. Every check and merge runs before either file is
  written.
- **Writes are atomic** (temp file, then rename):
  - the file's mode is kept, and links are followed;
  - a file protected from writing (its mode, the read-only attribute, a Windows ACL) is refused, found by opening it
    for writing without truncating;
  - the lock's and config's temp copies go in `.sdlc/.work/` once it exists.
- **One containment check,** `inside_repo`. A recorded path that resolves outside the repo through a link is
  `outside`: it is never read, written or deleted.

## Consequences

- Concurrent commands keep each other's changes, except two that change the same record, and one save landing in
  the instant between another's re-read and its write.
- Two narrow races stay open by design; closing them would need a mutex:
  - `.claude/rules` swapped for a link mid-render;
  - two renders of one convention at once on a filesystem without hard links.
- The config is re-read before either file is written, so a refusal leaves both untouched, at the cost of a slightly
  wider window for a lost config update.
- An atomic replace resets a file's owner, ACL entries and hard links, where the old in-place write kept them.
- Don't add a mutex without answering the failures above: Windows and WSL on one checkout, filesystems without
  locks, eject removing the scratch folder, and long commands such as `workbench clone`.
