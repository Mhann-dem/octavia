"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getAuthToken, fetchSession } from '@/lib/auth';

/**
 * withAuth: Higher-order component to protect routes requiring authentication
 * Redirects unauthenticated users to /login
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
                // Prefer server-side authoritative check (reads HttpOnly cookie)
                const session = await fetchSession();
                if (!mounted) return;
                if (session) {
                    setAuthenticated(true);
                    setLoading(false);
                    return;
                }

                // Fallback to localStorage token check for legacy flows
                const local = getAuthToken() !== null;
                setAuthenticated(local);
                setLoading(false);
                if (!local) {
                    router.push('/login');
                }
            }

            check();

            return () => {
                mounted = false;
            };
        }, [router]);

        if (loading) {
            return (
                <div className="min-h-screen w-full bg-bg-dark flex items-center justify-center">
                    <p className="text-slate-400">Loading...</p>
                </div>
            );
        }

        if (!authenticated) {
            return null; // redirect already initiated
        }

        return <Component {...props} />;
    };
}
