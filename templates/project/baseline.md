# Known failures baseline

<!-- Written by /sdlc:setup (sdlc v{{plugin_version}}). Yours from then on: the plugin never overwrites it.
     Prove (Stage 5) fails only on failures NOT listed here. Rules:
     - Shrinks on its own: when a listed item passes, the build removes it and says so in plan.md's review section.
     - Never grows silently: adding an item needs the user's OK and a Deviations entry in that feature's state.md.
     - Fixing items is its own S-track work, not a side job inside a feature. -->

Recorded: <date> at commit <hash>, running each command in `.sdlc/config.json`

## Failing tests

| Package | Test (file › name) | Failure, one line | Since |
|---|---|---|---|
| — | none | | |

## Lint and type errors

Counts per rule and file. Prove fails if any count goes **up**, or a rule/file appears that isn't listed.

| Package | Tool | Rule | File | Count |
|---|---|---|---|---|
| — | none | | | |

## Build warnings / other

- none
