import { request, FullConfig } from "@playwright/test";

export default async function globalSetup(_config: FullConfig) {
  const api = process.env.API_BASE || "http://localhost:8000";
  const req = await request.newContext();
  // Seed the three users/roles (idempotent)
  await req.post(`${api}/v1/admin/seed/personas`);
  await req.dispose();
}
