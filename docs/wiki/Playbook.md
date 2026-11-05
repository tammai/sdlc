# Playbook

Situation-by-situation plays. Each says what to type, what the agent does, which files appear and where you decide. Concepts are in [How it works](How-it-works.md); failures are in [Troubleshooting](Troubleshooting.md).

A feature's change file goes in `<docs>/changes/<feature>.md` (`<docs>` is `docs/sdlc` unless setup chose another folder), its state in `.sdlc/state/<feature>.md` and its working files (backlog, part plans, QA report) in `.sdlc/state/<feature>/`. Feature names look like `2026-10-26-m-csv-export`: date, the track it started on, slug.

| You want to… | Play |
|---|---|
| Start a brand-new project | [15](Setup-and-upgrade.md#15-start-a-new-project) |
| Adopt sdlc in an existing repo | [14](Setup-and-upgrade.md#14-adopt-sdlc-in-an-existing-repo) |
| Update after a plugin release | [16](Setup-and-upgrade.md#16-upgrade-after-a-plugin-update) |
| Remove sdlc from a repo | [17](Setup-and-upgrade.md#17-remove-sdlc-from-a-repo) |
| Fix a bug | [1](Everyday-work.md#1-fix-a-bug-s-track) |
| Add a feature | [2](Everyday-work.md#2-add-a-feature-m-track) |
| Build something new or unclear | [3](Everyday-work.md#3-build-a-new-service-or-module-l-track) |
| Build something too big for one session | [19](Big-work-and-autopilot.md#19-a-big-feature-becomes-a-backlog) |
| Run a backlog's slices unattended | [20](Big-work-and-autopilot.md#20-run-a-backlog-on-autopilot) |
| Change auth, payments, secrets, PII or migrations | [4](Everyday-work.md#4-change-something-risky) |
| Pick up where you left off, or pause | [5](Everyday-work.md#5-resume-or-check-status) |
| Something feels broken | `/sdlc:doctor`, then the [Troubleshooting](Troubleshooting.md) procedure it names |
| Choose the reviews, or act on their findings | [6](Everyday-work.md#6-choose-the-reviews-and-act-on-findings) |
| Get unblocked when a turn won't finish | [7](Everyday-work.md#7-the-stop-hook-says-re-run-tests) |
| Understand a "Verification anchors changed" stop | [21](Shipping-and-gates.md#21-the-trust-anchor-stopped-me) |
| Answer review comments | [8](Everyday-work.md#8-handle-review-feedback) |
| Skip process on purpose | [9](Shipping-and-gates.md#9-skip-a-gate-deliberately) |
| Merge and deploy | [10](Shipping-and-gates.md#10-merge-and-deploy) |
| Let Claude iterate alone on one small task | [11](Big-work-and-autopilot.md#11-run-an-autonomous-loop) |
| Stop repeating the same correction | [12](Rules-and-context.md#12-turn-a-correction-into-a-rule) |
| Keep CLAUDE.md and per-call context small | [13](Rules-and-context.md#13-keep-always-loaded-context-small) |
| Clean up finished features | [18](Setup-and-upgrade.md#18-clean-up-finished-features) |
| Know who decides what | [Who decides what](Shipping-and-gates.md#who-decides-what) |
