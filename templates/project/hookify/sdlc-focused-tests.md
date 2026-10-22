---
name: sdlc-focused-tests
enabled: true
event: file
action: warn
conditions:
  - field: new_text
    operator: regex_match
    pattern: \b(it|test|describe|context)\.(only|skip)\(|\b(fit|fdescribe|xit|xdescribe|xtest)\(|@pytest\.mark\.(skip|xfail)\b|\bt\.Skip\(
---

**Focused or skipped test added.** `.only`/`.skip`/`xit`/`@pytest.mark.skip` must not be committed: it hides failures from the full test run and fails Stage 5.
