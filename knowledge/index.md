---
type: index
title: Knowledge map
description: Entry point. Read this, then open only the docs relevant to the task.
---

# Knowledge map

One line per doc: path — what it answers (≤12 words). Keep this file under ~80 lines; split into `<folder>/index.md` files when it grows.

## Conventions
- [conventions/model-tiers-by-name.md](conventions/model-tiers-by-name.md) — why skills name haiku/sonnet/opus, never "most capable"

## Decisions
- [../docs/adr/README.md](../docs/adr/README.md) — the plugin's ADRs live in docs/adr, not here

## Gotchas
- [gotchas/crlf-checkout.md](gotchas/crlf-checkout.md) — exact-match edits fail on Windows checkouts with CRLF
- [gotchas/windows-stdout-encoding.md](gotchas/windows-stdout-encoding.md) — why scripts crash printing non-ASCII on Windows; write UTF-8

## Runbooks
- [../docs/runbook.md](../docs/runbook.md) — maintainer and user procedures, including releases

## Features
-
