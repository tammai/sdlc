---
paths:
{{config.areas.sensitive|yaml_list}}
---
<!-- Managed by the sdlc plugin v{{plugin_version}}; regenerated on upgrade. Change paths via "areas.sensitive" in .sdlc/config.json. -->
# Sensitive areas: auth, payments, secrets, PII (sdlc policy)

- Work here is at least M track and always gets a full Stage 7 security review.
- Never hardcode, log, print or commit secrets, tokens or PII; read secrets from the environment or the secret manager.
- Validate and authorize on the server for every request; never trust client-supplied identity, roles or amounts.
- Fail closed: on an error in an auth or payment check, deny.
- Don't change crypto, session or token handling without stating the threat it addresses.
