<!-- contracts-version: 1.2.0 -->
# Shared contracts v1

The normative part of the shared-contracts spec, used by rspec, sdlc, bug-hunter and product-rebuild. `contracts.py` in this folder checks every rule. Sections C1–C7 are copied from the spec unchanged. "Settled in v1" fixes the details the spec left open.

## Decisions

| Question | Decision |
|---|---|
| Canonical home **(sign-off D1)** | `tammai/product-rebuild/contracts/v1/`: `CONTRACTS.md` (this spec, normative part), `*.schema.json`, `contracts.py` (stdlib-only validators). |
| Distribution | Vendored byte-identical into each consumer at `contracts/v1/` (sdlc: `scripts/contracts/v1/`). Each file starts with `contracts-version: 1.x.y`: as a first-line comment in `.py`, `.md` and `.yaml` files, and as the first key `"$comment": "contracts-version: 1.x.y"` in `*.schema.json`. Fixture files (valid and invalid examples) carry no header so they stay byte-exact; `MANIFEST` still lists their SHA-256. A CI test in each repo checks the header and the SHA-256 list in `contracts/v1/MANIFEST`. No runtime dependency between plugins. |
| Versioning | SemVer on the contracts. Minor = additive fields, consumers ignore unknown fields. Major = new folder `v2/`; consumers support one major at a time and say which in their README. |
| Language | Field names, IDs, tags and section headings in English. Prose may be in the spec's language. |

## C1 Criterion format

One line per criterion, in a story file (rspec) or a change file (sdlc):

```markdown
- [ ] **F-ISS-01.AC2** Given team ENG with 11 issues, when a member creates "Fix login", then it is shown as ENG-12. `[observed]`
```

| Part | Rule | Checked by |
|---|---|---|
| ID | Spec-backed: `<FEATURE-ID>.AC<n>`, `n` from 1, never renumbered or reused; a removed criterion keeps its ID with `~~strikethrough~~` and a reason. Standalone sdlc: `AC-001`. | `contracts.py id` (error) |
| Grammar | `Given …, when …, then ….`, one observable behaviour, keywords in English. | error |
| Example data | The `then` clause contains a literal a test can assert: a quoted string, a number, an identifier pattern (`ENG-12`), or a named state from `domain.md`. Exempt: tag `[manual]` with a reason. | warning in sdlc S/M, error in rspec and sdlc L |
| Source tag | Exactly one, for the `then`: `[docs]` `[api]` `[observed]` `[code]` `[3p]` `[inferred]` (reverse spec) · `[request]` `[decision]` `[inferred]` (forward spec). `[decision]` = the author chose it; `[inferred]` = assumed from context. | error |
| Test level | Declared where the test is bound (C3 or the sdlc Acceptance tests table): `unit` `integration` `e2e` `manual`. A `then` visible to a user or API client needs `integration` or `e2e`. | warning |

## C2 Story sections (reverse spec)

`Story` · `Acceptance criteria` · `Failure modes` (each line ends `→ <criterion ID>` or `→ MNB-<n>`) · `Must never break` (`MNB-<n>` lines, each with a test or a check named) · `Differences from the original` (each line `→ D-<nnn>`, see C4) · `Sources`. `Edge cases` is removed: each edge case becomes a criterion or a failure mode.

## C3 Criteria lock: `criteria.lock.json`

Written by the producer of the spec (rspec `check`, sdlc Define in standalone L). Read by everyone else. Never edited by hand.

```json
{
  "contracts": "1.0.0",
  "spec": "docs/specs/trackr",
  "generated": "2026-11-08T10:00:00Z",
  "criteria": [{
    "id": "F-ISS-01.AC2",
    "feature": "F-ISS-01",
    "file": "features/F-ISS-01-create-issue.md",
    "text_sha256": "…",
    "tag": "observed",
    "priority": "MVP",
    "level": 2,
    "test": "acceptance/http/F-ISS-01.AC2.yaml",
    "departures": []
  }]
}
```

`level`: **0** written and `check` passes · **1** passed audit (sampled and SUPPORTED by its source, or unsampled in an audited population whose sample has no contradiction); a criterion tagged `[inferred]` never reaches level 1 by audit, since not contradicted is not evidence: it needs a source tag first · **2** a recorded test passed against the running reference (C4). A text change invalidates the level: `text_sha256` mismatch → level drops to 0 until re-verified.

## C4 Acceptance bundle: `acceptance/`

Runnable tests recorded against the reference, owned by the spec, runnable against any build.

```
acceptance/
  manifest.json
  http/<criterion>.yaml        # HTTP replay
  e2e/<criterion>.spec.ts      # Playwright
  mobile/<criterion>.yaml      # Maestro
  cli/<criterion>.yaml         # command, stdin, expected stdout/exit
  seed/                        # how the reference was seeded (scripts or recorded calls)
```

`manifest.json` entry: `criterion`, `runner` (`http|playwright|maestro|cli`), `path`, `sha256`, `level` (`unit|integration|e2e`), `visibility` (`open|hidden`), `recorded_against` (`{kind, version_or_commit, base_url_env}`), `last_green` (timestamp, target), `normalize` (list of departure IDs and ignore rules applied).

Rules:

- Targets come only from environment variables: `ACCEPT_BASE_URL`, `ACCEPT_ACCOUNT_<NAME>` (header or cookie). No URL or secret in any test file; `contracts.py bundle` fails on one.
- Generated values (IDs, timestamps) are captured and compared by rule, never hard-coded: HTTP replay supports `capture:` and `match: {pointer: "/id", rule: "uuid|int|iso8601|same-as:<capture>"}`.
- A test changes only through the owner's amend flow (rspec `amend`, product-rebuild `flows.py unlock --reason`). Consumers treat the bundle as read-only.
- `visibility: hidden` tests are moved out of the bundle by product-rebuild (05, P4); a bundle shipped by rspec alone has only `open`.

### HTTP replay format

```yaml
criterion: F-ISS-01.AC2
seed: [seed/team-eng-11-issues.yaml]
steps:
  - request: {method: POST, path: /api/teams/ENG/issues, account: MEMBER, json: {title: "Fix login"}}
    expect:
      status: 201
      json:
        - {pointer: /key, equals: "ENG-12"}
        - {pointer: /id, rule: uuid, capture: issue_id}
  - request: {method: GET, path: "/api/issues/{issue_id}", account: MEMBER}
    expect: {status: 200, json: [{pointer: /title, equals: "Fix login"}]}
```

The runner (`contracts.py run-http`) is stdlib only, prints JUnit XML, exits non-zero on any failure.

## C5 Departures registry: `departures.yaml`

The one list of accepted differences between the rebuild and the reference. Every check reads it; nothing else may hold an accepted difference.

```yaml
- id: D-004
  kind: simplification        # simplification | deliberate-change | reference-defect-not-copied | environment | branding
  criteria: [F-ISS-07.AC3]
  features: [F-ISS-07]
  summary: Issue keys use 2–4 letters; the reference allows 1–5.
  match:                      # how automated diffs recognise it; empty = human-only
    - {runner: http, pointer: /key, rule: "regex:^[A-Z]{2,4}-\\d+$"}
  decided_by: "Tam Mai, features approval 2026-11-08"
  adr: decisions/0007-issue-keys.md
```

A departure without `decided_by` is invalid. Autopilot may propose, never decide; a proposed entry has `status: proposed` and blocks the gate that reads it.

## C6 Finding format: `finding-v1`

One JSON file per finding, written by bug-hunter (rebuild mode), sdlc qa-tester and test-auditor (spec-backed mode), and product-rebuild G6.

| Field | Values |
|---|---|
| `id`, `source` | `BH-0007`, `bug-hunter` |
| `class` | `build-defect` · `spec-gap` · `reference-defect` · `accepted-departure` · `test-defect` · `flaky` · `environment` |
| `severity` | `high` · `medium` · `low` (sdlc's Severity list) |
| `criterion` / `rule` | the criterion ID or `domain.md` rule it contradicts, or `null` |
| `repro` | steps in the C4 runner format, so a verifier can run them unchanged |
| `observed` | `{rebuild: …, reference: … or "not run: <reason>"}` |
| `route` | derived from `class`: build-defect, test-defect → `sdlc` · spec-gap → `rspec` · reference-defect → `human` · accepted-departure → `drop` · flaky, environment → `orchestrator` |
| `verified_by` | the fresh-context agent that re-ran it, and the result |

A finding without `verified_by: reproduced` is never routed, with one exception: a spec question (`source: sdlc-question`, `class: spec-gap`, written by sdlc S10) reports an ambiguity, not a behaviour, so it is routed to `rspec` without a verifier, with `verified_by: {agent: null, result: "not run: spec question"}`. `/rspec:amend` still needs human approval when the change touches an MVP criterion's `then`. (Added in contracts 1.1.0, gate G-F.)

## C7 Run log: `cost.jsonl`

One JSON line per agent run: `ts`, `plugin`, `stage`, `agent`, `tier`, `wall_s`, `turns`, `tokens_in`, `tokens_out` (`null` when the host does not report them), `result`. Orchestrators append; `contracts.py cost <file>` sums by stage.

## Settled in v1

Details the spec left open, fixed here so every consumer reads them the same way. `contracts.py` implements each.

| Point | v1 rule |
|---|---|
| Criterion line | `- [ ] **<ID>** <text> `[<tag>]``. The checkbox is optional (`- **<ID>** …` is read too). In a file with an `Acceptance criteria` heading, only that section is read. |
| Removed criterion | `- [ ] ~~**<ID>** <text>~~ <reason>`; the reason is required. |
| Manual exemption | `` `[manual: <reason>]` `` next to the source tag; a bare `[manual]` is an error. |
| Source tags by ID | A spec-backed ID (`F-….AC<n>`) takes the reverse-spec tags; a standalone ID (`AC-<nnn>`) takes the forward-spec tags. rspec accepts only spec-backed IDs. |
| Example data | A quoted string, a digit, or a `` `state` `` code span in the `then` clause. With `--domain`, a code span must be a `` `state` `` written in `domain.md`. Severity by `--profile`: error in `rspec` and `sdlc-l`, warning in `sdlc-s` and `sdlc-m`. |
| `text_sha256` | SHA-256 (UTF-8) of the criterion line after `**<ID>**`, stripped of surrounding whitespace, tags included. Ticking the checkbox does not change it. |
| Lock paths | `spec` is relative to the repo root; each criterion's `file` is relative to `spec`. `lock --root <repo>` names the root (default: the current folder). |
| `priority` | `MVP`, `Later`, `Drop`, or `null` (standalone sdlc). |
| `manifest.json` | `{"contracts": "1.x.y", "tests": [<entry>…]}`. A runner's files live in its folder: `http/*.yaml`, `e2e/*.spec.ts`, `mobile/*.yaml`, `cli/*.yaml`. |
| Account variables | `ACCEPT_ACCOUNT_<NAME>` holds one header line, `Name: value` (`Authorization: Bearer …` or `Cookie: sid=…`). |
| No URL or secret | `bundle` fails on any `scheme://` and on a bearer token or an `Authorization`, `Cookie`, `password`, `api_key` or `secret` key with a value in any bundle file. |
| Match rules | `uuid`, `int`, `iso8601`, `same-as:<capture>`, and `regex:<pattern>` (C5 uses it). `same-as` and `{capture}` in a path name only an earlier capture. |
| Seeds | A seed file listed by an HTTP test uses the replay format without `criterion` (`steps:` only); `run-http` runs it first. |
| Must never break | Each line carries an `MNB-<n>` ID and names `test: …` or `check: …`. |
| Departure status | `proposed` or `accepted`; omitted means `accepted` (C5's example has none). An accepted entry needs `decided_by`; a proposed entry has none, prints `blocked:` and exits 1. |
| `verified_by` | `{agent, result}`; `result` is `reproduced`, `not-reproduced` or `not run: <reason>`. Only `reproduced` is routed, apart from a spec question. |
| `source` | Lower-case kebab name of the writer, `^[a-z][a-z0-9-]*$` (`bug-hunter`, `sdlc-question`). |
| Spec question (1.1.0) | `source: sdlc-question` must be `class: spec-gap`, carry `question` (the ambiguity, as text) and have `verified_by` exactly `{agent: null, result: "not run: spec question"}`; its `repro` and `observed` may be `null`. It routes to `rspec`. On any other finding, a null `repro`, `observed` or `verified_by.agent` is an error. |
| Exit codes | `0` no errors (warnings allowed) · `1` errors, `blocked`, or failed tests · `2` usage. |

## YAML subset

`contracts.py` parses YAML with its own parser, so the plugins share no dependency. Every YAML example in this file
parses under it, and each ships as a valid fixture.

- In: block mappings and sequences (spaces only), flow `{}` and `[]` closed on the same line, plain scalars,
  `'single'` and `"double"` quoted scalars (escapes `\\ \" \/ \n \t \r \0 \b \f \e \xXX \uXXXX \UXXXXXXXX`),
  `#` comments, one leading `---`.
- Scalars follow the YAML 1.2 core schema: `null`/`~`, `true`/`false`, integers, floats. `no`, `on` and
  `2026-11-08` stay strings.
- Out, each a parse error naming its line: anchors `&`, aliases `*`, tags `!`, block scalars `|` `>`, complex keys
  `?`, directives `%`, a second document, duplicate keys, tabs in indentation, bad indentation, a flow collection
  spread over several lines, a plain value containing `: `.

## Distribution

- `contracts/v1/` holds `CONTRACTS.md`, `contracts.py`, `test_contracts.py`, the `*.schema.json` files,
  `fixtures/` and `MANIFEST`.
- `MANIFEST` line 1 is `contracts-version: 1.x.y`. Every other line is `<sha256>  <path>`, one per file under
  `contracts/v1/` except `MANIFEST` and `__pycache__`, sorted, LF.
- Headers: `# contracts-version: …` in `.py` and `.yaml`, `<!-- contracts-version: … -->` in `.md`, and
  `"$comment": "contracts-version: …"` as the first key of each `*.schema.json`. Fixtures carry none.
- Each consumer adds `contracts/v1/** -text` to `.gitattributes` (sdlc: `scripts/contracts/v1/** -text`). Without
  it, a Windows checkout with `core.autocrlf` rewrites line endings, and every hash fails.
- Each consumer's drift test runs `python3 <path>/contracts.py vendor-check <path>`. It fails on a changed byte, a
  missing or extra file, a missing header, or a fixture whose verdict changed.
- Only the canonical repo runs `contracts.py seal`.
- Fixtures sit at `fixtures/<kind>/valid/` (no error allowed) and `fixtures/<kind>/invalid/` (at least one error
  required). The kinds are `criteria`, `story`, `lock`, `bundle`, `http`, `departures`, `finding`, `cost` and
  `yaml`. A criteria fixture named `<profile>--…` is checked with that profile.
