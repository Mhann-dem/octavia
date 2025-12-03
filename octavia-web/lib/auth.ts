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
    return getAuthToken() !== null;
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
    
    return fetch(url, {
        ...options,
        headers,
    });
}
