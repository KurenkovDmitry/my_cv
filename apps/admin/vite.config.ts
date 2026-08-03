import { resolve } from "node:path";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";

const adminBasePath = process.env.VITE_APP_BASE_PATH ?? "/";

export default defineConfig({
  base: adminBasePath.endsWith("/") ? adminBasePath : `${adminBasePath}/`,
  plugins: [react()],
  resolve: {
    alias: {
      "@portfolio/shared-config": resolve(__dirname, "../../packages/shared-config/src/index.ts"),
      "@portfolio/shared-contracts": resolve(__dirname, "../../packages/shared-contracts/src/index.ts"),
      "@portfolio/shared-types": resolve(__dirname, "../../packages/shared-types/src/index.ts")
    }
  }
});
