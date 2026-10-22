---
name: sdlc-history-comments
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(ts|tsx|js|jsx|mjs|cjs|vue|svelte|py|go|rs|java|kt|rb|php|cs|swift)$
  - field: new_text
    operator: regex_match
    pattern: (?m)^\s*(//|#|\*|/\*).*\b((added|changed|updated|modified|fixed|refactored|moved|renamed)\s+(for|to|per|in)\s+(the\s+|this\s+|that\s+)?([\w-]+\s+){0,2}(task|ticket|pr|issue|feature|requirement|story|review)\b|as\s+(requested|discussed|per\s+(the\s+)?(spec|plan|task|review))\b|(was|were)\s+(previously|originally)\b|\bnew\s+(implementation|version|approach)\b)
---

**Change-history comment.** Comments describe the code as it is, not how it got here or which task asked for it. That belongs in the commit message or PR.
