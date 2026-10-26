---
type: gotcha
title: Rendering the docs diagrams to check them
description: How to look at a hand-edited SVG in docs/diagrams when the Playwright tools won't open it.
tags: [docs, diagrams, windows]
updated: 2026-10-26
---

# Rendering the docs diagrams to check them

## Symptom
The Playwright browser tool refuses `file://` URLs, and on Windows its navigate and screenshot calls can time out even on a local `http.server` page.

## Fix
Serve `docs/diagrams` with `python3 -m http.server 8765 --bind 127.0.0.1` and screenshot with headless Edge, at the SVG's `viewBox` size:
`msedge --headless=new --hide-scrollbars --window-size=1000,<height> --screenshot=<out.png> http://127.0.0.1:8765/<name>.svg`. Then open the PNG.

Dark mode: Edge draws a standalone SVG on a white page even when the dark media query applies, so dark-mode text that sits outside a box (panel titles, legends) looks invisible. That's the render, not the diagram: to check dark mode, embed the SVG in an HTML page with a dark background (e.g. `#1f1e1d`).

## How to detect early
After editing an SVG by hand, also check the numbers it states (commands, agents, guardrails, version) against the files; the `<desc>` and the visible labels can disagree.
