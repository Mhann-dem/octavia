import { NextResponse } from 'next/server';

// Use server-side env var (not NEXT_PUBLIC_*) for backend URL
const BACKEND = (process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001').replace(/\/$/, '');

export async function POST(request: Request) {
  const url = `${BACKEND}/login`;
  const headers: Record<string, string> = {};
  const contentType = request.headers.get('content-type');
  if (contentType) headers['content-type'] = contentType;

  const body = await request.text();

  const resp = await fetch(url, {
    method: 'POST',
    headers,
    body,
  });

  const text = await resp.text();
  const init: ResponseInit = { status: resp.status, headers: {} };

  // Forward Set-Cookie header if present so browser receives cookie from same-origin
  const setCookie = resp.headers.get('set-cookie');
  if (setCookie) {
    // Single Set-Cookie forwarded; multiple cookies may require special handling
    (init.headers as Record<string, string>)['set-cookie'] = setCookie;
  }

  const ct = resp.headers.get('content-type');
  if (ct) (init.headers as Record<string, string>)['content-type'] = ct;

  return new Response(text, init);
}
