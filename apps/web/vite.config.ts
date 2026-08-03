import { resolve } from "node:path";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@portfolio/shared-config": resolve(__dirname, "../../packages/shared-config/src/index.ts"),
      "@portfolio/shared-contracts": resolve(__dirname, "../../packages/shared-contracts/src/index.ts"),
      "@portfolio/shared-ui": resolve(__dirname, "../../packages/shared-ui/src/index.ts"),
      "@portfolio/shared-types": resolve(__dirname, "../../packages/shared-types/src/index.ts"),
      "@portfolio/modules/analytics": resolve(__dirname, "../../modules/analytics/index.ts"),
      "@portfolio/modules/consent": resolve(__dirname, "../../modules/consent/index.ts"),
      "@portfolio/modules/localization": resolve(__dirname, "../../modules/localization/index.ts"),
      "@portfolio/modules/profile": resolve(__dirname, "../../modules/profile/index.ts"),
      "@portfolio/modules/projects": resolve(__dirname, "../../modules/projects/index.ts"),
      "@portfolio/modules/themes": resolve(__dirname, "../../modules/themes/index.ts")
    }
  },
  server: {
    port: 5173
  }
});
