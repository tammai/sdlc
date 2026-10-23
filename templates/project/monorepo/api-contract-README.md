# api-contract

The API contract every app builds against. Backend owns it.

## Versions

One folder per version, each with its spec:

```
v1/openapi.yaml
v2/openapi.yaml
```

- **Merging to `main` publishes a version.** From then on, teams build on it.
- **A published version takes additions only:** a new optional field, a new endpoint. CI (`sdlc contract`) fails a pull request that breaks a published version or removes one.
- **A breaking change is a new version folder** (`v1` → `v2`). Keep the old one while any released client still calls it.
- Each feature names the version the teams agreed to build on.

## Clients

Each app generates its client and types from the version it uses, in its own language, with its `generate:api` script (run before build and test). Generated code is not committed.
