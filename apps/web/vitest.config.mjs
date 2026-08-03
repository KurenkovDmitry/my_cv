import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const currentDirectory = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@portfolio/shared-config": resolve(currentDirectory, "../../packages/shared-config/src/index.ts"),
      "@portfolio/shared-contracts": resolve(currentDirectory, "../../packages/shared-contracts/src/index.ts"),
      "@portfolio/shared-ui": resolve(currentDirectory, "../../packages/shared-ui/src/index.ts"),
      "@portfolio/shared-types": resolve(currentDirectory, "../../packages/shared-types/src/index.ts"),
      "@portfolio/modules/analytics": resolve(currentDirectory, "../../modules/analytics/index.ts"),
      "@portfolio/modules/consent": resolve(currentDirectory, "../../modules/consent/index.ts"),
      "@portfolio/modules/localization": resolve(currentDirectory, "../../modules/localization/index.ts"),
      "@portfolio/modules/profile": resolve(currentDirectory, "../../modules/profile/index.ts"),
      "@portfolio/modules/projects": resolve(currentDirectory, "../../modules/projects/index.ts"),
      "@portfolio/modules/themes": resolve(currentDirectory, "../../modules/themes/index.ts"),
    },
  },
  test: {
    environment: "node",
    include: [
      "../../modules/**/*.test.ts",
      "./src/**/*.test.ts",
      "./src/**/*.test.tsx",
    ],
    passWithNoTests: false,
  },
});
