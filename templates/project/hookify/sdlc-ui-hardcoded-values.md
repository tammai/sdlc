---
name: sdlc-ui-hardcoded-values
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(tsx|jsx|vue|svelte|astro|html|css|scss|sass|less)$
  - field: file_path
    operator: not_regex_match
    pattern: (^|[\\/])(_?tokens?|design-tokens|_?variables|themes?)([\\/.]|$)|tailwind\.config\.|\.stories\.
  - field: new_text
    operator: not_regex_match
    pattern: (?m)^\s*--[\w-]+\s*:|@theme\b
  - field: new_text
    operator: regex_match
    pattern: (?<![\w&/])#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})\b|\b(rgba?|hsla?|oklch|oklab|lab|lch)\(\s*[\d.]|[\w-]-\[(#|-?\d)[^\]\s]*\]|\bstyle=["{]
---

**Hard-coded style value.** Use the design system's tokens and components (`.sdlc/design-system.md`): no raw hex/rgb colors, arbitrary Tailwind values like `bg-[#123456]` or `w-[13px]`, or inline `style=`. If no token fits, propose adding one to the design system instead of inlining the value.
