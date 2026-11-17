# The brainstorm companion shows sdlc's name, not Superpowers'

## Why

**Request (verbatim):** "http://localhost:56518/ the mockup by sdlc but still show name of superpowers"

**Bug:** the visual companion `sdlc:brainstorming` opens in the browser (`skills/brainstorming/scripts/server.cjs`, copied from Superpowers under MIT) titles its tab "Superpowers Brainstorming" (`frame-template.html:5`) and prints a "Prime Radiant Superpowers v…" header linking to obra/superpowers (`server.cjs` `brandMarkup()`), with Superpowers' version read from the plugin root's `package.json` (none in sdlc, so "vunknown"). Root cause: the copy kept the upstream branding; `NOTICE.md`'s patches renamed skill references, not the page. Fixed into 3.12.0 at the user's choice.

## Decisions

| Decision | Ruled out | Why |
|---|---|---|
| Brand the page "sdlc brainstorming" with sdlc's version (from `.claude-plugin/plugin.json`), and a small "based on Superpowers (MIT)" credit linking upstream | dropping all mention of Superpowers | the copy is Superpowers' work under MIT; the credit keeps that honest beside the license in `NOTICE.md` and `licenses/` |
| Remove the remote logo path (`primeradiant.com`) entirely | keeping it behind the disabled switch | sdlc never fetches it, and it's Superpowers' brand |

## Acceptance criteria

- **AC-001** Given the companion is started, when its page is fetched with the session key, then the title and header say sdlc (with sdlc's version) and not "Superpowers Brainstorming" or "Prime Radiant", and a "based on Superpowers" credit links to github.com/obra/superpowers.

## Acceptance tests

| AC | Test | Run |
|---|---|---|
| AC-001 | tests/test_companion_brand.py › CompanionBrandTest.test_the_page_is_branded_sdlc_and_credits_superpowers | `py -3.10 -m unittest discover -s tests -t tests -p test_companion_brand.py -k test_the_page_is_branded_sdlc_and_credits_superpowers` |

## Must never break

- The companion's session key, telemetry-off default and everything else the page does stay as they are.

## Out of scope

- Renaming Superpowers' environment variables (`SUPERPOWERS_DISABLE_TELEMETRY` and the like) or the upstream sync notes.

## Review

No review ran: no trigger fired.
