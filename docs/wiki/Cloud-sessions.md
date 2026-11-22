# Cloud sessions

A cloud session (Claude Code on the web, the apps' cloud mode, a routine) clones the repo but **does not install the plugins** that its `.claude/settings.json` enables, even from marketplaces it lists. It still gets the repo's rules, hookify files and `.sdlc/config.json`, but no sdlc skills, agents, hooks or `/sdlc:*` commands.

sdlc sets up neither route below for you. Pick one:

| Route | Who | How |
|---|---|---|
| **Organization-wide** | Team or Enterprise Owner | Paste the JSON below at Organization settings → Claude Code → Managed settings. Applies to everyone in the org |
| **Per cloud environment** | Anyone | Add a setup script in the environment dialog at claude.ai/code |

```json
{
  "extraKnownMarketplaces": {
    "sdlc": { "source": { "source": "github", "repo": "tammai/sdlc" } }
  },
  "enabledPlugins": { "sdlc@sdlc": true, "sdlc-extras@sdlc": true, "sdlc-stepper@sdlc": true }
}
```

(Leave out a companion you don't want.)

```bash
claude plugin marketplace add tammai/sdlc
claude plugin install sdlc@sdlc --yes
```

**Check:** `claude plugin list` in the session should show `sdlc@sdlc`.

Not yet verified: whether the commit security review can authenticate in a cloud session without `ANTHROPIC_API_KEY`. Sources: [cloud environments](https://code.claude.com/docs/en/cloud-environments.md#what-carries-over-from-your-setup), [plugins for your organization](https://code.claude.com/docs/en/plugins/org.md).
