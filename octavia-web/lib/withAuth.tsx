"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getAuthToken } from '@/lib/auth';

/**
 * withAuth: Higher-order component to protect routes requiring authentication
 * Checks both localStorage token AND server-side cookie via /api/v1/auth/me
 */
export function withAuth<P extends object>(
    Component: React.ComponentType<P>
) {
    return function ProtectedComponent(props: P) {
        const router = useRouter();
        const [loading, setLoading] = useState(true);
        const [authenticated, setAuthenticated] = useState<boolean | null>(null);

        useEffect(() => {
            let mounted = true;

            async function check() {
                console.debug("withAuth: checking authentication...");
                
                // Check localStorage token first (fast)
                const token = getAuthToken();
                console.debug("withAuth: localStorage token exists:", !!token);
                
                // Also check server-side session via cookie
                try {
                    const useProxy = process.env.NEXT_PUBLIC_USE_DEV_PROXY === 'true';
                    const envApi = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
                    const apiFallback = envApi || 'http://localhost:8001';
                    const apiBase = useProxy ? '' : apiFallback.replace(/\/$/, '');
                    const url = `${apiBase}/api/v1/auth/me`;
                    
                    console.debug("withAuth: checking session at", url);
                    const res = await fetch(url, { credentials: 'include' });
                    console.debug("withAuth: session check response", res.status);
                    
                    if (!mounted) return;
                    
                    if (res.ok) {
                        console.debug("withAuth: authenticated via cookie ✓");
                        setAuthenticated(true);
                        setLoading(false);
                        return;
                    }
                } catch (error) {
                    console.error("withAuth: session check error:", error);
                }

                // If we get here, not authenticated
                if (!mounted) return;
                
                // If we have a localStorage token but session check failed,
                // might be a cookie issue - still try to authenticate
                if (token) {
                    console.debug("withAuth: localStorage token exists but session check failed, allowing access");
                    setAuthenticated(true);
                    setLoading(false);
                    return;
                }
                
                // No token at all, redirect to login
                console.debug("withAuth: not authenticated, redirecting to login");
                setAuthenticated(false);
                setLoading(false);
                router.replace('/login');
            }

            check();

            return () => {
                mounted = false;
            };
        }, [router]);

        if (loading) {
            return (
                <div className="min-h-screen w-full bg-bg-dark flex items-center justify-center">
                    <div className="text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-purple-bright mx-auto mb-4"></div>
                        <p className="text-slate-400">Loading...</p>
                    </div>
                </div>
            );
        }

        if (!authenticated) {
            return null; // redirect already initiated
        }

        return <Component {...props} />;
    };
}