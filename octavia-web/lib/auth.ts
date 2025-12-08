/**
 * Auth helper: cookie-based token storage
 * Uses js-cookie for safer cookie handling and server-side verification support
 */

export const AUTH_COOKIE_NAME = 'octavia_token';

/**
 * Store token in a secure httpOnly cookie (server-side preference) or fallback to localStorage
 * For client-side, we use localStorage + a session cookie for API calls
 */
export function setAuthToken(token: string) {
    // Store in localStorage for client-side access
    localStorage.setItem(AUTH_COOKIE_NAME, token);
    
    // In a real app, you'd set an httpOnly cookie server-side via a Set-Cookie response
    // For now, document that in production you should use Set-Cookie with HttpOnly flag
}

/**
 * Get the stored auth token
 */
export function getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(AUTH_COOKIE_NAME);
}

/**
 * Clear the auth token (logout)
 */
export function clearAuthToken() {
    localStorage.removeItem(AUTH_COOKIE_NAME);
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
    // Prefer server-side authoritative check via /api/v1/auth/me in UI code.
    // This helper remains a localStorage quick-check for legacy flows.
    return getAuthToken() !== null;
}

/**
 * Query server to verify authentication (reads HttpOnly cookie).
 * Returns the decoded payload or null.
 */
export async function fetchSession(): Promise<unknown | null> {
    try {
        const useProxy = process.env.NEXT_PUBLIC_USE_DEV_PROXY === 'true';
        // Accept either NEXT_PUBLIC_API_URL or NEXT_PUBLIC_API_BASE_URL for compatibility
        const envApi = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
        const apiFallback = envApi || 'http://localhost:8001';
        const apiBase = useProxy ? '' : apiFallback.replace(/\/$/, '');
        const url = `${apiBase}/api/v1/auth/me`;
        const res = await fetch(url, { credentials: 'include' });
        if (!res.ok) return null;
        const data = await res.json();
        return data;
    } catch {
        return null;
    }
}

/**
 * Fetch helper that includes auth token in Authorization header
 */
export async function authenticatedFetch(
    url: string,
    options: RequestInit = {}
): Promise<Response> {
    const token = getAuthToken();
    const headers = new Headers(options.headers || {});
    
    if (token) {
        headers.set('Authorization', `Bearer ${token}`);
    }
    const useProxy = process.env.NEXT_PUBLIC_USE_DEV_PROXY === 'true';
    const envApi = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
    const apiFallback = envApi || 'http://localhost:8001';
    const apiBase = useProxy ? '' : apiFallback.replace(/\/$/, '');
    const target = url.startsWith('/') ? `${apiBase}${url}` : url;

    return fetch(target, {
        ...options,
        headers,
        // ensure cookies (httpOnly) are sent with requests to the API
        credentials: 'include',
    });
}
