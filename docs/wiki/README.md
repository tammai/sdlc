# Wiki source

The plugin's user documentation. Every `.md` file here except this one is a page of the [GitHub wiki](https://github.com/tammai/sdlc/wiki), published by `.github/workflows/wiki.yml` on each push to `main` that touches this folder. Edit here, never in the wiki: the sync replaces every page.

- One file per page; the file name is the page name (`Quick-start.md` → "Quick start"). `_Sidebar.md` and `_Footer.md` appear on every page; add a new page to the sidebar.
- Link pages as `Page.md#anchor` and repo files by relative path (`../adr/0001-….md`, `../diagrams/x.svg`); the sync turns them into wiki links and github.com URLs, so links work both here and in the wiki.
- `python3 .github/scripts/wiki_sync.py check` reports a link to a missing page, file or heading; the test suite runs it.
- Maintainer docs stay out of the wiki: [runbook](../runbook.md) (releases, smoke test), [CONTRIBUTING](../../CONTRIBUTING.md), [PRD](../prd.md), [specs](../specs/README.md), [ADRs](../adr/README.md).
