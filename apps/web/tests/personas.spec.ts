import { test, expect } from "@playwright/test";

const API = process.env.API_BASE || "http://localhost:8000";
const WEB = process.env.WEB_BASE || "http://localhost:5173";

// Set the dev cookie for the API origin so browser fetches include it
async function loginAs(page, email: string) {
  // 1) Hit the API to set the cookie server-side (dev helper)
  const r = await page.request.post(`${API}/v1/dev/session?email=${encodeURIComponent(email)}`);
  expect(r.ok()).toBeTruthy();

  // 2) Ensure the browser context also has the cookie for origin "api"
  const apiHost = new URL(API).hostname; // "api" in docker, "localhost" on host
  await page.context().addCookies([
    {
      name: "demo_email",
      value: email,
      domain: apiHost,
      path: "/",
      httpOnly: false,
      sameSite: "Lax",
    },
  ]);
}

test.describe("Patient persona @patient", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "patient1@example.com");
  });

  test("allowed pages load; forbidden is blocked", async ({ page }) => {
    for (const path of [
      "/", "/login", "/book", "/confirm",
      "/check-in", "/docs",
      "/portal/follow-up", "/portal/tasks",
      "/portal/summary/enc-1",
      "/intake/1", "/consent/req-1",
    ]) {
      await page.goto(`${WEB}${path}`);
      await expect(page.locator("body")).toBeVisible();
    }

    await page.goto(`${WEB}/billing/cases`);
    await expect(page.getByText("Not authorized")).toBeVisible();
  });
});

test.describe("Clinician persona @clinician", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "clinician1@example.com");
  });

  test("allowed pages load; forbidden is blocked", async ({ page }) => {
    for (const path of [
      "/provider/prechart/1",
      "/provider/scribe/1",
      "/portal/summary/enc-1",
      "/billing/cases",
      "/billing/claims/1",
    ]) {
      await page.goto(`${WEB}${path}`);
      await expect(page.locator("body")).toBeVisible();
    }

    await page.goto(`${WEB}/check-in`);
    await expect(page.getByText("Not authorized")).toBeVisible();
  });
});

test.describe("OPS persona @ops", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "ops1@example.com");
  });

  test("allowed pages load; forbidden is blocked", async ({ page }) => {
    for (const path of [
      "/ops/queue",
      "/admin/billing/eligibility",
      "/admin/tasks",
      "/ops/escalations",
      "/admin/compliance/audit",
      "/admin/compliance/pia",
      "/admin/compliance/retention",
      "/admin/analytics",
      "/admin/experiments",
    ]) {
      await page.goto(`${WEB}${path}`);
      await expect(page.locator("body")).toBeVisible();
    }

    await page.goto(`${WEB}/provider/scribe/1`);
    await expect(page.getByText("Not authorized")).toBeVisible();
  });
});
