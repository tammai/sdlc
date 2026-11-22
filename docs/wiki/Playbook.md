# Playbook

Situation by situation: what to type, what happens, where you decide. Concepts: [How it works](How-it-works.md). Failures: [Troubleshooting](Troubleshooting.md).

| | You want to… | Play |
|---|---|---|
| **Set up** | Start a brand-new project | [15](Setup-and-upgrade.md#15-start-a-new-project) |
| | Adopt sdlc in an existing repo | [14](Setup-and-upgrade.md#14-adopt-sdlc-in-an-existing-repo) |
| | Update after a plugin release | [16](Setup-and-upgrade.md#16-upgrade-after-a-plugin-update) |
| | Remove sdlc from a repo | [17](Setup-and-upgrade.md#17-remove-sdlc-from-a-repo) |
| | Clean up finished features | [18](Setup-and-upgrade.md#18-clean-up-finished-features) |
| **Build** | Fix a bug | [1](Everyday-work.md#1-fix-a-bug-s-track) |
| | Add a feature | [2](Everyday-work.md#2-add-a-feature-m-track) |
| | Build something new or unclear | [3](Everyday-work.md#3-build-a-new-service-or-module-l-track) |
| | Change auth, payments, secrets, PII or migrations | [4](Everyday-work.md#4-change-something-risky) |
| | Pick up where you left off, or pause | [5](Everyday-work.md#5-resume-or-check-status) |
| | Build something too big for one session | [19](Big-work-and-autopilot.md#19-a-big-feature-becomes-a-backlog) |
| | Run a backlog unattended | [20](Big-work-and-autopilot.md#20-run-a-backlog-on-autopilot) |
| | Let Claude iterate alone on one small task | [11](Big-work-and-autopilot.md#11-run-an-autonomous-loop) |
| **Review** | Choose reviews, act on findings | [6](Everyday-work.md#6-choose-the-reviews-and-act-on-findings) |
| | Turn won't finish: "re-run tests" | [7](Everyday-work.md#7-the-stop-hook-says-re-run-tests) |
| | Answer review comments | [8](Everyday-work.md#8-handle-review-feedback) |
| | Understand a "Verification anchors changed" stop | [21](Shipping-and-gates.md#21-the-trust-anchor-stopped-me) |
| **Ship** | Skip process on purpose | [9](Shipping-and-gates.md#9-skip-a-gate-deliberately) |
| | Merge and deploy | [10](Shipping-and-gates.md#10-merge-and-deploy) |
| | Know who decides what | [Who decides what](Shipping-and-gates.md#who-decides-what) |
| **Tune** | Stop repeating the same correction | [12](Rules-and-context.md#12-turn-a-correction-into-a-rule) |
| | Keep CLAUDE.md and per-call context small | [13](Rules-and-context.md#13-keep-always-loaded-context-small) |
| **Fix** | Something feels broken | `/sdlc:doctor`, then the [Troubleshooting](Troubleshooting.md) procedure it names |

**Where files go:** the change file is `<docs>/changes/<feature>.md` (`<docs>` = `docs/sdlc` by default), the state file is `.sdlc/state/<feature>.md`, and working files are in `.sdlc/state/<feature>/`. Feature names look like `2026-10-26-m-csv-export` (date, starting track, slug).
