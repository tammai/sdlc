---
type: gotcha
title: Cloud sessions see only what's committed, and install no repo plugins
description: A cloud session starts from a fresh clone, so settings.local.json never reaches it, and it ignores the plugins a repo's settings.json turns on.
tags: [settings, cloud, plugins, setup]
updated: 2026-11-02
---

# Cloud sessions see only what's committed, and install no repo plugins

## Symptom
A repo set up with sdlc ran in Claude Code on the web (or a routine) without sdlc or its companions turned on. Committing the plugin keys to `.claude/settings.json` (2.3.0's `enable-plugin --team`) did not change that.

## Cause
A cloud session clones the repo, so it gets `.claude/settings.json` and the user's account settings, but no machine-local file. It also does not install the plugins that file turns on under `enabledPlugins`, including ones from the marketplaces it lists under `extraKnownMarketplaces` (Claude Code docs, "What carries over from your setup"). 2.3.0 assumed committing the keys was enough; it only helps teammates on their own machines.

## Fix
Give the cloud session the plugin another way: server-managed settings (Team or Enterprise) or a setup script on the cloud environment. Both snippets are in the guidebook's "Cloud sessions". Repo files other than plugins (rules, hookify files, `.sdlc/config.json`) do reach a cloud session when committed. Settings that belong to one machine, such as turning a conflicting plugin off, stay local.
