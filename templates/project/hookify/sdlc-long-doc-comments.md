---
name: sdlc-long-doc-comments
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(ts|tsx|js|jsx|mjs|cjs|vue|svelte|py|go|rs|java|kt|rb|php|cs|swift)$
  - field: new_text
    operator: regex_match
    pattern: /\*\*(\n[ \t]*\*(?!/)[^\n]*){7,}|"""[^\n]*\n([^\n]*\n){8,}?[ \t]*"""|(\n[ \t]*//[^\n]*){8,}
---

**Long comment block.** Doc comments are one line by default; add params/returns only where the contract isn't obvious from names and types. Cut it to what a maintainer can't get from the code and git history.
