# Optional integrations (not bundled)

These connect to outside services (they're MCP servers or need accounts/credentials), so they can't be copied into this plugin. Suggest one only when the project actually uses that service, and never install without the user's OK. Install from Claude Code with `/plugin` → Discover, or connect the service's MCP server directly.

| Stage | Need | Options |
|---|---|---|
| 1 Discover | Pull tickets / designs | Linear, Atlassian (Jira/Confluence), Asana, GitHub, GitLab, Figma, Miro |
| 1–4 | Current library docs | Context7 |
| 2 Design | Large-codebase search | Serena, Sourcegraph, Greptile |
| 2 / 9 | Database | Prisma, Supabase, Neon, MongoDB |
| 5 Verify | Browser / e2e | Playwright, Chrome DevTools |
| 5 Verify | API tests | Postman |
| 6 Review | Extra reviewers | CodeRabbit, Qodo, SonarQube |
| 7 Security | Deep scans | Claude Security (Anthropic; license doesn't allow bundling — install separately), Semgrep, Aikido, Sonatype Guide, Endor Labs |
| 8 PR / CI | PRs, CI status | GitHub, GitLab (the bundled commands also work with plain `gh`) |
| 9 Deploy | Hosting | Vercel, Netlify, Railway, Cloudflare, Firebase, AWS (Deploy on AWS / aws-core / AWS Serverless), Azure, Terraform |
| 10 Operate | Errors, metrics, flags | Sentry, Datadog, PostHog, PagerDuty |
| 11 Learn | Docs site | Mintlify |

Plugin catalogs change. If a listed option can't be found, say so and continue without it.
