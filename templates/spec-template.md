# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[yyyy-mm-dd-track-feature-name]`

**Created**: [DATE]

**Status**: Draft

**References**: [links to the docs/ artifacts this feature builds on: BA specs, QA test cases, designs. Link, never copy. Delete the line if there are none.]

**Intent**: [intent.md](intent.md) (the request, answers, approaches and the chosen one; not repeated here)

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

### Failure modes

<!--
  Only the production edges that apply to this change, each also an acceptance or success criterion:
  concurrent use, scale or large inputs, persisted-data migration and compatibility, partial failure or a
  crash mid-write, untrusted input, I/O errors. None apply: say so in one line.
-->

- [Failure mode, e.g. "crash mid-write: the store is never left half-written" → SC-00N]

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

<!--
  Every requirement carries its source:
    [user]       the user asked for it (their words, the request, the brainstorm)
    [clarified]  the user's answer to a question added or settled it
    [inferred]   you added it; it is dropped at Define's approval unless the user keeps it
  Don't smuggle capabilities in as Assumptions: anything that adds work is an FR with a source.
-->

- **FR-001** [user]: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002** [user]: System MUST [specific capability, e.g., "validate email addresses"]
- **FR-003** [clarified]: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004** [inferred]: System MUST [behavior you think is needed but the user never asked for, e.g., "log all security events"]

*Example of a guess the user didn't settle (kept or dropped at the gate):*

- **FR-005** [inferred]: System MUST authenticate users via email and password (the request names no method; the app has no SSO today)

### Non-Goals *(mandatory)*

<!--
  What this feature deliberately does NOT do, so later stages don't add it back.
  Include inferred requirements the user dropped at the gate, and the obvious
  "while we're at it" extensions (admin UI, i18n, caching, bulk operations, …).
  Write "None identified" only after actually looking.
-->

- [Capability left out, e.g., "No admin UI for managing accounts; done via existing tooling"]
- [Dropped at gate, e.g., "No security-event logging in this feature (was FR-004 [inferred])"]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

<!-- Same source tags as FRs. Never invent load or scale numbers: a number the user didn't give is [inferred]. -->

- **SC-001** [user]: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002** [clarified]: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003** [inferred]: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Users have stable internet connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing authentication system will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile API"]
