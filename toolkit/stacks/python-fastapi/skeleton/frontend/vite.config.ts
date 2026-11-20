import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  // `npm run dev` proxies API calls to a locally running backend (python -m app.serve).
  server: { proxy: { "/api": "http://localhost:8000" } },
  test: { environment: "jsdom", setupFiles: ["./src/setupTests.ts"] },
});
