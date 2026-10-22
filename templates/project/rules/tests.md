---
paths:
{{config.areas.tests|yaml_list}}
---
<!-- Managed by the sdlc plugin v{{plugin_version}}; regenerated on upgrade. Change paths via "areas.tests" in .sdlc/config.json. -->
# Tests (sdlc policy)

- Write the failing test first and watch it fail for the right reason (`sdlc:test-driven-development`).
- Assert observable behavior, not implementation details; one behavior per test, named after it.
- Never commit `.only`, `.skip`, `xit`, `@pytest.mark.skip` or a retried/flaky test to get green. Fix it or report it.
- Never weaken an assertion or delete a test to make it pass; that needs the user's explicit OK.
- Use real code over mocks where it's cheap; mock only at system boundaries (network, clock, randomness).
- Run the full suite with `just test` before claiming anything passes; filtered runs don't count.
