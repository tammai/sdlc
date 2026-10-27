# Notices

sdlc-extras is a companion to the sdlc plugin, from the same repository. Its own files are MIT licensed (`LICENSE`).

## Anthropic Claude Code plugins — Apache License 2.0, Copyright Anthropic, PBC
https://github.com/anthropics/claude-plugins-official — `licenses/anthropic-plugins-Apache-2.0.txt`

- **ralph-loop:** commands `ralph-loop`, `cancel-ralph`, `help` → `ralph-help`; `hooks/stop-hook.sh`; `scripts/setup-ralph-loop.sh`
- **hookify:** commands `list` → `hookify-list`, `configure` → `hookify-configure`, `help` → `hookify-help`; agent `conversation-analyzer`
- **feature-dev:** agent `code-reviewer` → `feature-reviewer`
- **pr-review-toolkit:** agents `comment-analyzer`, `type-design-analyzer`
- **code-simplifier:** agent `code-simplifier`

Modified: command references renamed to the `sdlc-extras:` namespace, and descriptions shortened; the sdlc plugin's NOTICE.md lists its other changes to these files.
