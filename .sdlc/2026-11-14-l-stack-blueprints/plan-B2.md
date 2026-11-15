# Part plan: 2026-11-14-l-stack-blueprints B2

**Record:** the feature's change file (`scaffold.py paths <feature>` → `change`) · **Backlog:** [backlog.md](backlog.md)

## Tasks

1. **New and reconciled stack sections** — AC-004 AC-005 AC-009
   - Files: `skills/setting-up-projects/references/stacks.md`
   - Test first: `StackSections.test_new_sections`, `StackSections.test_reconciled_sections`
   - Then: sections for Vue (without Nuxt), Next.js, Flutter, iOS, Android, FastAPI (pieces, generator, config
     `stack`, five commands); Node validation (`@hono/zod-openapi` with a consumer and a contract, else
     `@hono/zod-validator`); Nuxt and Next.js one-deployable bridge files; no auth library anywhere. Headings must
     not start with Nuxt, React, Node or Go (`PreferredStacks`).
2. **CI toolchains** — AC-006
   - Files: `scripts/scaffold.py`
   - Test first: `CiToolchains.test_ci_sets_up_mobile_toolchains`
   - Then: `CI_SETUP["swift"]` (setup-xcode, latest-stable); a Swift stack with no repo `ci.os` runs on
     `macos-latest` (the defaults' `ci.os` doesn't count). Flutter and Kotlin (→ java) already had setups.
3. **Stale docs**
   - Files: `docs/specs/01-setup-upgrade-eject.md` (SET-FR-011, SET-FR-053), `docs/wiki/Project-setup.md`,
     `skills/setting-up-projects/references/greenfield.md` (ci step), `CHANGELOG.md`

## Public Surface

- none

## Sources checked (AC-009, 2026-11-14)

- Vue: vuejs.org/guide/quick-start.html; create-vue templates (`type-check` = `vue-tsc --build`, `build` runs it).
  The ESLint script name couldn't be confirmed, so the section says "the lint script create-vue writes".
- Nuxt UI in Vue: ui.nuxt.com/docs/getting-started/installation/vue (`@nuxt/ui/vite`, `@nuxt/ui/vue-plugin`,
  tailwindcss, `<UApp>`).
- Next.js: nextjs.org/docs/app/getting-started/installation (`next lint` removed, `lint` = `eslint`),
  nextjs.org/docs/app/guides/testing/vitest.
- Hono on Next.js: hono.dev/docs/getting-started/nextjs; `@hono/vercel` replaces deprecated `hono/vercel`.
- Hono in Nuxt: Nuxt 4 ships h3 v1, which has `toWebRequest`; h3 v2 (Nuxt 5) uses `event.req`, marked "verify on
  upgrade". `ssr: false` keeps server routes under `nuxt build`: nuxt.com/docs/4.x/guide/concepts/rendering.
- `@hono/zod-openapi` (OpenAPIHono, createRoute, app.openapi, app.doc; Zod 4) and `@hono/zod-validator`
  (zValidator; Zod 3.25 or 4): github.com/honojs/middleware.
- Flutter CLI: docs.flutter.dev/reference/flutter-cli; flutter_riverpod 3.x, go_router, dio on pub.dev;
  openapi-generator.tech/docs/generators/dart-dio.
- iOS: github.com/apple/swift-openapi-generator (SwiftPM build plugin, runtime, URLSession transport, config file).
  The xcodebuild commands are standard syntax; the simulator name depends on the runner image, so the section
  says to pick one from `xcrun simctl list devices available`.
- Android: developer.android.com/training/dependency-injection/hilt-android (plugin id, KSP);
  openapi-generator.tech/docs/generators/kotlin (`jvm-okhttp4`, `kotlinx_serialization`); AGP 9.5 needs JDK 17.
- FastAPI/uv: docs.astral.sh/uv/reference/cli (`uv init --app`, `--locked`); fastapi.tiangolo.com
  (`app.openapi()`); SQLAlchemy asyncio docs; Alembic cookbook (`init -t async`).
- Actions: subosito/flutter-action v2, maxim-lobanov/setup-xcode v1 (`latest-stable`), actions/setup-java v6;
  ubuntu-latest has the Android SDK and JDK 17/21; macos-latest has Xcode and iOS simulators
  (github.com/actions/runner-images).
- Dropped, not confirmed: the Xcode-project steps for adding the generator plugin; the blueprint's iPhone 16
  destination (not on macos-latest any more).
