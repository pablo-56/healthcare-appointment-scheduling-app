import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  timeout: 60_000,
  use: {
    baseURL: process.env.WEB_BASE || "http://localhost:5173",
    trace: "on-first-retry",
    // headless true by default in CI image
  },
  // we already run web/api in compose, so no webServer here
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  globalSetup: require.resolve("./tests/global-setup"),
});
