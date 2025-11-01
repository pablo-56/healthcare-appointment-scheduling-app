import { defineConfig } from '@playwright/test';

const API = process.env.VITE_API_BASE || 'http://localhost:8000';

export default defineConfig({
    testDir: __dirname,
    timeout: 90_000,
    use: {
        baseURL: 'http://localhost:5173',
        headless: true,
        actionTimeout: 15_000,
        navigationTimeout: 30_000,
        extraHTTPHeaders: {
            // Default header for API calls Playwright client might make. The UI itself sets headers already.
            'X-Purpose-Of-Use': 'OPERATIONS'
        }
    },
    // If vite dev server isn't already running via docker, this will start it.
    webServer: [
        {
            command: 'npm run dev',
            cwd: process.cwd(), // apps/web
            port: 5173,
            reuseExistingServer: true,
            timeout: 60_000
        }
    ],
    expect: { timeout: 10_000 },
    reporter: [['list']]
});
