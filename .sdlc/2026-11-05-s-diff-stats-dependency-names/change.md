# diff_stats names a go.mod one-line require by its module and drops every pip specifier

## Why

`diff_stats.new_dependencies()` feeds verify's drift check: a dependency it names that Public Surface doesn't declare fails verify as "undeclared dependency". Wrong names make that fail even when the dependency is declared.

**Request (verbatim):** "diff_stats reports go.mod one-line requires as 'require' and keeps pip version specifiers … a one-line go.mod `require github.com/pkg/errors v0.9.1` is reported as the dependency `require`; requirements.txt lines `requests<3` and `flask~=2.0` keep their version specifiers. … Output: `['require', 'requests<3', 'flask~=2.0']` Expected: `['github.com/pkg/errors', 'requests', 'flask']` … Root cause: In `scripts/diff_stats.py` `new_dependencies()`, the go.mod name is `s.split()[0]`, which is the `require` keyword on a one-line require. Pip names are cut only at `==` and `>=`, not at `<`, `>`, `~=`, `!=`, `[` (extras) or `;` (markers)."

**Bug:** the two tests below fail today (`['require', ...]`; `['-r', 'attrs!=21.1', 'flask~=2.0', 'rich>13', 'urllib3<3', 'uvicorn[standard]', ...]`). Root cause as the request says: the go.mod name is the first word of the line, and the pip name is cut only at `==` and `>=`.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| go.mod: drop a leading `require ` before taking the first word | Parsing go.mod fully | One keyword is the whole bug; block entries already work |
| pip: the name is the PEP 508 name at the start of the line (letters, digits, `.`, `_`, `-`); a line with none (`-r`, `--index-url`) is skipped | Adding more separators to the split chain | Covers every specifier, extra and marker at once; options were wrongly reported as dependencies too |

## Acceptance criteria

- **AC-001** Given a go.mod that adds a one-line `require github.com/pkg/errors v0.9.1` and a block entry, the new dependencies are `github.com/pkg/errors` and the block's module path.
- **AC-002** Given requirements lines with `<`, `>`, `~=`, `!=`, extras, markers and a `-r` option, the new dependencies are the bare package names, and the option isn't one.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_diff_stats.py › test_go_mod_one_line_require_names_the_module | `python3 -m unittest discover -s tests -t tests -p test_diff_stats.py -k test_go_mod_one_line_require_names_the_module` |
| AC-002 | tests/test_diff_stats.py › test_requirements_names_drop_every_specifier | `python3 -m unittest discover -s tests -t tests -p test_diff_stats.py -k test_requirements_names_drop_every_specifier` |

## Must never break

- `package.json` dependencies and `==`/`>=` pins are still named as before (`test_new_dependencies`).

## Out of scope

- Other go.mod directives on one line (`replace`, `exclude`, `retract`, `toolchain`) and other manifests (pyproject.toml, Cargo.toml).

## Review

No review ran: no trigger fired.
