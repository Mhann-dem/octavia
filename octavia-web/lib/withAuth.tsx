'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getAuthToken } from '@/lib/auth';

/**
 * withAuth: Higher-order component to protect routes requiring authentication
 * Redirects unauthenticated users to /login
 */
export function withAuth<P extends object>(
    Component: React.ComponentType<P>
) {
    return function ProtectedComponent(props: P) {
        const router = useRouter();
        const isAuthenticated = getAuthToken() !== null;

        useEffect(() => {
            if (!isAuthenticated) {
                router.push('/login');
            }
        }, [isAuthenticated, router]);

        if (!isAuthenticated) {
            return (
                <div className="min-h-screen w-full bg-bg-dark flex items-center justify-center">
                    <p className="text-slate-400">Loading...</p>
                </div>
            );
        }

        return <Component {...props} />;
    };
}
