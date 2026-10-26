# Optional integrations (not bundled)

These connect to outside services (they're MCP servers or need accounts/credentials), so they can't be copied into this plugin. Suggest one only when the project actually uses that service, and never install without the user's OK. Install from Claude Code with `/plugin` → Discover, or connect the service's MCP server directly.

| Phase | Need | Options |
|---|---|---|
| Define | Pull tickets / designs | Linear, Atlassian (Jira/Confluence), Asana, GitHub, GitLab, Figma, Miro |
| Define, Build | Current library docs | Context7 |
| Define (design) | Large-codebase search | Serena, Sourcegraph, Greptile |
| Define / `/sdlc:deploy` | Database | Prisma, Supabase, Neon, MongoDB |
| Prove | Browser / e2e | Playwright, Chrome DevTools |
| Prove | API tests | Postman |
| Prove | Extra reviewers | CodeRabbit, Qodo, SonarQube |
| Prove (security) | Deep scans | Claude Security (Anthropic; license doesn't allow bundling — install separately), Semgrep, Aikido, Sonatype Guide, Endor Labs |
| Ship | PRs, CI status | GitHub, GitLab (the bundled commands also work with plain `gh`) |
| `/sdlc:deploy` | Hosting | Vercel, Netlify, Railway, Cloudflare, Firebase, AWS (Deploy on AWS / aws-core / AWS Serverless), Azure, Terraform |
| Operate (reference only) | Errors, metrics, flags | Sentry, Datadog, PostHog, PagerDuty |
| Learn | Docs site | Mintlify |

Plugin catalogs change. If a listed option can't be found, say so and continue without it.
