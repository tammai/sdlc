---
paths:
  - "skills/**/*"
  - "agents/**/*"
  - "commands/**/*"
---

# Skills, agents and commands

- Name model tiers (cheap, standard, top) and point at Model Selection; never write "the most capable model" — why: [model tiers by name](../../knowledge/conventions/model-tiers-by-name.md)
- A dispatch template's `model:` placeholder stays required.
- Frontmatter descriptions are plain sentences: no `: ` unless quoted, examples go in the body; run `claude plugin validate .` — why: [colon breaks YAML](../../knowledge/gotchas/frontmatter-colon-breaks-yaml.md)
