Development setup (local)
=========================

This file documents how to run the backend, frontend, Redis and Celery worker locally for end-to-end testing.

Environment variables
- `NEXT_PUBLIC_API_URL` — frontend -> backend base URL (default `http://localhost:8001`).
- `BACKEND_URL` — used by Next proxy API routes if set (fallback to `http://localhost:8001`).
- `OCTAVIA_ALLOW_CROSS_SITE_COOKIES` — defaults to `true` in dev; when `true` backend sets SameSite=None allowing cross-site cookies.
- `OCTAVIA_SECURE_COOKIES` — set to `true` when serving over HTTPS to set the Secure cookie flag.
- `REDIS_BROKER_URL` — Celery/Redis broker (default `redis://redis:6379/0`).

Start backend (FastAPI)
-----------------------
Open a terminal in `octavia-backend` and run:

```powershell
$env:OCTAVIA_ALLOW_CROSS_SITE_COOKIES='true'; $env:OCTAVIA_SECURE_COOKIES='false'
uvicorn app.main:app --reload --port 8001
```

Start frontend (Next.js)
-----------------------
Open a separate terminal in `octavia-web` and run:

```powershell
npm run dev
```

Run Redis + Celery worker (Docker Compose)
------------------------------------------
From the repository root run:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

This brings up Redis and a Celery worker that mounts the `octavia-backend` directory. The worker will attempt to install dependencies if `requirements.txt` exists, then start Celery. Adjust the command in `docker-compose.dev.yml` to suit your environment.

Automated login check
---------------------
There is a helper script at `octavia-web/scripts/auto-login.js` which uses env vars `TEST_EMAIL` and `TEST_PASSWORD` to POST to `/login`, check `/api/v1/auth/me` and open the dashboard if authenticated. Run it from the `octavia-web` folder:

```powershell
$env:TEST_EMAIL='you@example.com'; $env:TEST_PASSWORD='yourpassword'; npm run auto:login
```

If the script prints `Set-Cookie header present` and `/api/v1/auth/me` returns `200`, the dashboard redirect should work in the browser.

Troubleshooting
---------------
- If `Set-Cookie` is not present or the cookie is blocked: check browser console for cookie/CORS warnings. Ensure `OCTAVIA_ALLOW_CROSS_SITE_COOKIES` is enabled in dev and `OCTAVIA_SECURE_COOKIES=false` when using HTTP.
- If you run frontend and backend on the same origin (proxy), cookies will be accepted without SameSite=None.
- For HTTPS local testing, set `OCTAVIA_SECURE_COOKIES=true` and serve both frontend/backend over TLS (or use a proxy/load balancer).
