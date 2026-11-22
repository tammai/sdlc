# Quick start

```
/sdlc:doctor                                     # 1. check the install
/sdlc:setup                                      # 2. set up the repo, once
/sdlc:start add CSV export to the reports page   # 3. start a piece of work
```

- **Setup** runs on its own branch. In an existing repo it records your test, lint and build commands. In an empty repo, say what you're building (`/sdlc:setup a REST API for invoices`) and it generates a skeleton. More: [Project setup](Project-setup.md).
- **Start** sizes the work and runs Define → Build → Review → Ship:

| Size | When | You decide |
|---|---|---|
| **S** fix | 1–2 files, clear expected behaviour | Merge |
| **M** feature | A few files, approach mostly clear | Merge. At high risk, also the plan and which reviews run |
| **L** project | Several parts, or approach unclear | Merge. Also the plan and reviews, if its own checks leave a doubt |

The agent stops at the open PR with CI green. **Merging, production deploys and database migrations are always your call.**

**Resume:** in a new session, run `/sdlc:start` with no argument.

Next: [How it works](How-it-works.md) · [Playbook](Playbook.md) · [Commands](Commands.md)
