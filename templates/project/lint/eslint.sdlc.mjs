// Managed by the sdlc plugin v{{plugin_version}} (seeded: replaced on upgrade only while unedited).
// Spread into eslint.config.mjs:  import sdlc from "./.sdlc/lint/eslint.sdlc.mjs"; export default [...yourConfig, ...sdlc];
// Core ESLint rules only, so it works with or without typescript-eslint.
export default [
  {
    files: ["**/*.{js,jsx,mjs,cjs,ts,tsx,mts,cts}"],
    rules: {
      complexity: ["warn", 10],
      "max-depth": ["warn", 3],
      "max-params": ["warn", 4],
      "max-lines-per-function": ["warn", { max: 60, skipBlankLines: true, skipComments: true }],
      "max-nested-callbacks": ["warn", 3],
      "no-warning-comments": ["warn", { terms: ["todo", "fixme", "xxx", "hack"], location: "start" }],
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-useless-constructor": "error",
      "no-else-return": ["warn", { allowElseIf: false }],
      "no-unneeded-ternary": "error",
      "prefer-const": "error",
    },
  },
  {
    files: ["**/*.{test,spec}.*", "**/{test,tests,__tests__}/**"],
    rules: { "max-lines-per-function": "off", "max-nested-callbacks": "off" },
  },
];
