import js from "@eslint/js";
import nextPlugin from "@next/eslint-plugin-next";

export default [
  { ignores: [".next/**", "node_modules/**", "playwright-report/**", "test-results/**", "coverage/**", "record_failures.js"] },
  js.configs.recommended,
  {
    files: ["next.config.mjs", "playwright.config.ts"],
    languageOptions: {
      globals: {
        process: "readonly",
      },
    },
  },
  {
    plugins: {
      "@next/next": nextPlugin,
    },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs["core-web-vitals"].rules,
    },
  },
];
