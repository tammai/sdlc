# docs

What the BA, QA and design roles own. They write these in their own tools and sync them here; this folder is the copy the code points at.

| Folder | Owner | Holds |
|---|---|---|
| `specs/` | BA | product specs and requirements |
| `test-cases/` | QA | test plans and test cases |
| `designs/` | Design | design files, or links to them |
| `runbooks/` | DevOps / leads | how to release, deploy and operate |

## Link, never copy

Feature work (the sdlc feature folders) links to the files here: a spec's **References** line names the BA spec, test cases and designs it builds on. Copying them in means two versions that drift apart; when one of these changes, the link still points at the current one.

Codebase know-how (gotchas, conventions, how-tos for developers and agents) lives in `knowledge/`, not here.
