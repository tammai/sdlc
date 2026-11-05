# doctor reports knowledge index links with spaces as broken

## Why
`doctor.py` should only flag links in `knowledge/index.md` that really point nowhere. Request, verbatim:

> `doctor.py` reports working links in `knowledge/index.md` as broken when the file name has a space: `[Deploy runbook](deploy%20runbook.md)` and `[On call](<on call.md>)` give `knowledge index | warn | broken links: deploy%20runbook.md, <on`, though both files exist.
> Expected: the knowledge index check is `ok`: both are valid Markdown links to existing files.

Root cause: `check_repo()` in `scripts/doctor.py` found links with `\]\(([^)#\s]+)`, which stops at the first space and doesn't know `<…>` targets, and checked the target with `os.path.exists` without URL-decoding it.

## Decisions
- A new helper `knowledge_links(text)` parses targets: `<…>` (spaces allowed, brackets stripped) or a bare target up to whitespace or `)`; a `#fragment` is dropped and a bare `#anchor` is skipped, as before. Each target is `urllib.parse.unquote`d before `os.path.exists`.
- Broken links are reported as written (minus the angle brackets), so the user can find them in the file. Ruled out: a full CommonMark parser (balanced parentheses, escapes): no dependency, and the index is plain lists.

## Acceptance criteria
- AC-001: `deploy%20runbook.md` and `<on call.md>` (also with a `#fragment`) resolve when the files exist; the check is `ok`, and a bare `#anchor` isn't counted.
- AC-002: a `<…>` or `%20` link to a missing file is still reported broken, as written.

## Acceptance tests
| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_doctor.py › test_knowledge_index_links_with_spaces | `python3 -m unittest discover -s tests -t tests -k test_knowledge_index_links_with_spaces` |
| AC-002 | tests/test_doctor.py › test_knowledge_index_links_with_spaces | `python3 -m unittest discover -s tests -t tests -k test_knowledge_index_links_with_spaces` |

## Must never break
- `test_knowledge_index_links`: a plain missing link is reported, `https://` links are skipped, a missing `index.md` warns.

## Out of scope
- Link checks anywhere but `knowledge/index.md`; reference-style links (`[x][id]`).

## Review

No review ran: no trigger fired.
