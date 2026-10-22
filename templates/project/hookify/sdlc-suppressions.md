---
name: sdlc-suppressions
enabled: true
event: file
action: warn
conditions:
  - field: new_text
    operator: regex_match
    pattern: @ts-(ignore|nocheck|expect-error)|eslint-disable|#\s*type:\s*ignore|#\s*noqa|#\s*pragma:\s*no\s*cover|//\s*nolint|@SuppressWarnings
---

**Type or lint suppression added.** Fix the underlying error instead. If a suppression is truly needed, scope it to one line and say *why* in the same comment.
