#!/usr/bin/env node
/**
 * auto-login.js
 * Simple automation script to POST credentials to the backend login endpoint,
 * verify the server-set cookie via `/api/v1/auth/me`, and open the dashboard.
 *
 * Usage:
 *  - Set env vars `TEST_EMAIL` and `TEST_PASSWORD` before running, or pass them inline:
 *      TEST_EMAIL=you@example.com TEST_PASSWORD=secret npm run auto:login
 */

const { exec } = require('child_process');

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8001').replace(/\/$/, '');
const DASHBOARD_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';

const email = process.env.TEST_EMAIL;
const password = process.env.TEST_PASSWORD;

if (!email || !password) {
  console.error('Missing TEST_EMAIL or TEST_PASSWORD environment variables.');
  console.error('Example: TEST_EMAIL=you@example.com TEST_PASSWORD=secret npm run auto:login');
  process.exit(2);
}

async function main() {
  console.log('API base:', API_BASE);
  try {
    const loginRes = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      // include credentials is not relevant from node fetch, but backend will return Set-Cookie header
    });

    console.log('Login status:', loginRes.status);
    const loginData = await loginRes.json().catch(() => null);
    if (!loginRes.ok) {
      console.error('Login failed:', loginData || loginRes.statusText);
      process.exit(1);
    }

    // Log Set-Cookie header if present
    const setCookie = loginRes.headers.get('set-cookie') || loginRes.headers.get('Set-Cookie');
    if (setCookie) {
      console.log('Set-Cookie header present.');
    } else {
      console.warn('No Set-Cookie header found on login response.');
    }

    // Call /api/v1/auth/me to verify session
    const meRes = await fetch(`${API_BASE}/api/v1/auth/me`, { method: 'GET' });
    console.log('/api/v1/auth/me status:', meRes.status);
    let meData = null;
    try { meData = await meRes.json(); } catch (e) { meData = null; }
    console.log('me payload:', meData);

    if (meRes.ok) {
      console.log('Authenticated — opening dashboard:', `${DASHBOARD_URL}/dashboard`);
      // Windows `start` command via cmd; works from Powershell as well.
      const cmd = process.platform === 'win32' ? `start "" "${DASHBOARD_URL}/dashboard"` : `open "${DASHBOARD_URL}/dashboard"`;
      exec(cmd, (err) => {
        if (err) console.error('Failed to open browser:', err);
        else console.log('Browser opened.');
      });
      process.exit(0);
    } else {
      console.error('Not authenticated according to /api/v1/auth/me');
      process.exit(1);
    }
  } catch (err) {
    console.error('Error during auto-login:', err);
    process.exit(1);
  }
}

// Node 18+ has global fetch; if not, instruct to run with node 18+ or install node-fetch
if (typeof fetch === 'undefined') {
  console.error('Global fetch is not available. Run this script with Node 18+ or install a fetch polyfill.');
  process.exit(2);
}

main();
