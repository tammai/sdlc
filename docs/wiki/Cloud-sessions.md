# Cloud sessions

A cloud session (Claude Code on the web, the desktop and mobile apps' cloud mode, a routine) clones the repo but does not install the plugins its `.claude/settings.json` turns on under `enabledPlugins`, even ones from marketplaces it lists under `extraKnownMarketplaces`. So neither choice in setup's "where do the keys go" question gives a cloud session sdlc: the committed file is for teammates on their own machines. The session still gets the repo's rules, hookify files and `.sdlc/config.json`, but no sdlc skills, agents, hooks or `/sdlc:*` commands. Two routes work; sdlc writes neither for you:

- **Organization-wide** (Team or Enterprise, an Owner sets it): paste this at Organization settings > Claude Code > Managed settings. A cloud session fetches these before it installs plugins.

  ```json
  {
    "extraKnownMarketplaces": {
      "sdlc": { "source": { "source": "github", "repo": "tammai/sdlc" } }
    },
    "enabledPlugins": { "sdlc@sdlc": true, "sdlc-extras@sdlc": true, "sdlc-stepper@sdlc": true }
  }
  ```

  Leave out `sdlc-extras@sdlc` or `sdlc-stepper@sdlc` if you don't want that companion. This applies to everyone in the organization, not one repo.
- **Per cloud environment:** add a setup script to the environment (the environment dialog at claude.ai/code) so it installs the plugin before Claude starts:

  ```bash
  claude plugin marketplace add tammai/sdlc
  claude plugin install sdlc@sdlc --yes
  ```

Check with `claude plugin list` in the session: it should show `sdlc@sdlc`. Not yet checked: whether the commit security review can authenticate in a cloud session without `ANTHROPIC_API_KEY`. Source: Claude Code docs, [cloud environments](https://code.claude.com/docs/en/cloud-environments.md#what-carries-over-from-your-setup) and [plugins for your organization](https://code.claude.com/docs/en/plugins/org.md).
