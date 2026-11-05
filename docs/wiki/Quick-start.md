# Quick start

```
/sdlc:doctor                                     # 1. check the install
/sdlc:setup                                      # 2. set up the repo, once
/sdlc:start add CSV export to the reports page   # 3. start a piece of work
```

- **Setup** runs on its own branch. In an existing repo it records your test, lint and build commands. In an empty repo, add a line saying what you're building, for example `/sdlc:setup a REST API for invoices`, and it creates a skeleton for you. More: [Project setup](Project-setup.md), [Setup and upgrade](Setup-and-upgrade.md).
- **Start** sizes the work and runs it through the four phases, Define → Build → Review → Ship:

| Size | When | You decide |
|---|---|---|
| **S** fix | 1–2 files, clear expected behaviour | merge |
| **M** feature | a few files, approach mostly clear | at high risk: the plan and which reviews run; merge |
| **L** project | several parts, or an approach still unclear | the plan and reviews only if its own checks leave a doubt; merge |

The agent stops at the open PR with CI green. Merging, production deploys and database migrations are always your call.

Run `/sdlc:start` with no argument in a new session to resume where you left off.

Next: [How it works](How-it-works.md) for the ideas, the [Playbook](Playbook.md) for what to do when…, and [Commands](Commands.md) for everything you can type.
