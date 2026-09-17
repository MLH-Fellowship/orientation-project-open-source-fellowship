import eslintReact from "@eslint-react/eslint-plugin";
import js from "@eslint/js";
import { defineConfig } from "eslint/config";
import globals from "globals";

export default defineConfig([
  {
    files: ["src/**/*.{js,mjs,cjs,jsx}"],

    extends: [js.configs.recommended, eslintReact.configs.recommended],

    languageOptions: {
      globals: globals.browser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
  },
]);
