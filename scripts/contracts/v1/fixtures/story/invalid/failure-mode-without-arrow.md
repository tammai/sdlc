# F-ISS-01 Create issue

## Story

As a member, I create an issue so the team sees it.

## Acceptance criteria

- [ ] **F-ISS-01.AC2** Given team ENG with 11 issues, when a member creates "Fix login", then it is shown as ENG-12. `[observed]`

## Failure modes

- Title empty
- Two creates at once → MNB-1

## Must never break

- **MNB-1** Two issues never share a key — test: acceptance/http/F-ISS-01.AC2.yaml

## Differences from the original

- Keys use 2–4 letters → D-004

## Sources

- docs: https://example.invalid/issues
