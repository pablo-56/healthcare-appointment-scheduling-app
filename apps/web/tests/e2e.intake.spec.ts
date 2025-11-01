import { test, expect } from '@playwright/test';
import crypto from 'crypto';

const API = process.env.VITE_API_BASE || 'http://localhost:8000';
const SECRET = process.env.SIGNATURE_WEBHOOK_SECRET || 'dev-secret';

test('Phase-2: book → intake → consent webhook → docs', async ({ page, request }) => {
    // 0) Make sure API is up
    const health = await request.get(`${API}/healthz`);
    expect(health.ok()).toBeTruthy();

    // 1) /book flow in UI (Phase-1 step)
    await page.goto('/book');
    await page.getByLabel(/reason/i).fill('annual physical');
    await page.getByRole('button', { name: /find slots/i }).click();

    // pick first demo slot
    await page.getByText('slot-1').click();
    await page.getByLabel(/email/i).fill('me@example.com');
    await page.getByRole('button', { name: /^book$/i }).click();

    // landed on /confirm? we need appointment id
    await expect(page).toHaveURL(/\/confirm/);
    const url = new URL(page.url());
    // either /confirm?id=3 or /confirm/3 — support both
    const id = Number(url.searchParams.get('id') || url.pathname.split('/').pop());
    expect(id).toBeGreaterThan(0);

    // 2) Intake page (Phase-2)
    await page.goto(`/intake/${id}`);
    await page.getByLabel(/has_fever/i).check({ force: true });
    await page.getByLabel(/medications/i).fill('none');
    await page.getByLabel(/allergies/i).fill('peanuts');
    await page.getByLabel(/insurance/i).fill('AB-12345');
    await page.getByRole('button', { name: /submit/i }).click();
    await expect(page.getByText(/intake submitted/i)).toBeVisible();

    // 3) Simulate signature provider webhook (Phase-2)
    const body = {
        request_id: `sig-${id}`,
        appointment_id: id,
        signer_name: 'John Doe',
        signer_ip: '127.0.0.1'
    };
    const sig = crypto.createHmac('sha256', SECRET).update(JSON.stringify(body)).digest('hex');

    const wb = await request.post(`${API}/v1/signature/webhook`, {
        headers: { 'Content-Type': 'application/json', 'X-Signature': sig },
        data: body
    });
    expect(wb.ok()).toBeTruthy();

    // 4) Documents page should list Intake (from worker) and Consent
    await page.goto('/docs');
    await expect(page.getByText(/Intake/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Consent/i)).toBeVisible({ timeout: 15_000 });
});
