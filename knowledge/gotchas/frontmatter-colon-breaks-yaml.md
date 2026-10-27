---
type: gotcha
title: A colon in unquoted frontmatter drops an agent's metadata
description: Why silent-failure-hunter loaded without its description and model, and how to write descriptions.
tags: [agents, skills, commands, yaml, release]
updated: 2026-10-22
---

# A colon in unquoted frontmatter drops an agent's metadata

## Symptom
`claude plugin validate .` fails with `YAML frontmatter failed to parse` on one agent. At runtime nothing errors: the agent loads with its name taken from the file name and every other field (description, model, tools) silently dropped.

## Cause
An unquoted `description:` value containing `: ` (colon, space) is invalid YAML. Vendored agents carried example dialogue in the description (`Daisy: "Please review…"`); `agents/silent-failure-hunter.md` shipped that way from 1.2.0 to 1.3.0.

## Fix
Keep the description to plain sentences and move examples into a `## When to invoke` section of the body, as `agents/code-reviewer.md` does. Quote the value if it must contain `: `.

## How to detect early
`claude plugin validate .` (release step 1) parses every agent, skill and command; run it after touching any frontmatter.
