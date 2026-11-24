---
type: gotcha
title: The full suite can't run in Review in this repo
description: sdlc's Review command budget kills a command that isn't one of config's commands at 120 s; this repo has no commands config.
tags: [testing, hooks, dogfooding]
updated: 2026-11-24
---

# The full suite can't run in Review in this repo

## Symptom
While a feature is at Stage 3 (Review), `py -3.10 -m unittest discover -s tests -t tests` stops after about 120 s with exit 124 and no summary.

## Cause
The plugin's own Review budget (`hooks/prove_budget.py`, ADR 0012) wraps any command that isn't one of `.sdlc/config.json`'s `commands` in `timeout -k 5 120`. This repo isn't set up with sdlc (`setup none`), so it has no commands and the suite counts as foreign. The suite takes about 11 minutes.

## Fix
Run the full suite in Build (Stage 2) before `advance 3`, or after `ship.py` has moved the feature to Ship and before `git commit`. A single test module still runs in Review.
