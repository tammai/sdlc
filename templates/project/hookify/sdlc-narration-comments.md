---
name: sdlc-narration-comments
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(ts|tsx|js|jsx|mjs|cjs|vue|svelte|py|go|rs|java|kt|rb|php|cs|swift)$
  - field: new_text
    operator: regex_match
    pattern: (?m)^\s*(//|#|\*|/\*)\s*(step\s*\d+\b|first,|next,|then,|finally,|now (we|let'?s|i)\b|here we\b|this (function|method|class|component|hook|code|file|module) (is|will|does|handles|returns|takes|creates)\b|we (now |first |then )?(need to|will|can|have to)\b)
---

**Narrating comment.** Comments say *why*, not what the code does step by step. Delete it, or rewrite it as the reason the code can't show.
