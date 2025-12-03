'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';

export default function VerifyPage({
    searchParams,
}: {
    searchParams: { token?: string };
}) {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const token = searchParams.token;

    async function handleVerify() {
        if (!token) {
            setError('No verification token provided');
            return;
        }

        setLoading(true);
        setMessage(null);
        setError(null);

        try {
            const res = await fetch(`http://localhost:8001/verify?token=${encodeURIComponent(token)}`, {
                method: 'GET',
            });
            const data = await res.json();
            if (!res.ok) {
                setError(data?.detail || 'Verification failed');
                setLoading(false);
                return;
            }
            setMessage('Email verified successfully! Redirecting to login...');
            setTimeout(() => router.push('/login'), 2000);
        } catch (err: any) {
            setError(err?.message || String(err));
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen w-full bg-bg-dark flex items-center justify-center relative overflow-hidden">
            {/* Ambient Background Glows */}
            <div className="glow-purple-strong"
                style={{ width: "600px", height: "600px", position: "absolute", top: "-200px", right: "-100px", zIndex: 0 }} />
            <div className="glow-purple"
                style={{ width: "400px", height: "400px", position: "absolute", bottom: "-100px", left: "100px", zIndex: 0 }} />

            <div className="relative z-10 w-full max-w-md p-6">
                <a href="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-white mb-8 transition-colors cursor-pointer">
                    <ArrowLeft className="w-4 h-4" />
                    Back to Home
                </a>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-panel p-8"
                >
                    <div className="text-center mb-8">
                        <div className="w-12 h-12 mx-auto mb-4 relative flex items-center justify-center">
                            <img
                                src="/lunartech_logo_small.png"
                                alt="LunarTech Logo"
                                className="w-full h-full object-contain"
                            />
                            <div className="absolute inset-0 bg-white/30 blur-xl rounded-full opacity-20" />
                        </div>
                        <h1 className="text-2xl font-bold text-white mb-2">Verify Email</h1>
                        <p className="text-slate-400 text-sm">Complete your account setup</p>
                    </div>

                    {!message && !error && (
                        <>
                            <p className="text-slate-300 mb-6">
                                {token
                                    ? 'Click the button below to verify your email address.'
                                    : 'No verification token found in the URL.'}
                            </p>

                            {token && (
                                <button
                                    onClick={handleVerify}
                                    disabled={loading}
                                    className="w-full btn-border-beam mt-6"
                                >
                                    <div className="btn-border-beam-inner justify-center py-3">
                                        {loading ? 'Verifying...' : 'Verify Email'}
                                    </div>
                                </button>
                            )}
                        </>
                    )}

                    {message && (
                        <div className="mt-4 p-4 bg-green-500/20 border border-green-500/50 rounded text-green-300">
                            {message}
                        </div>
                    )}

                    {error && (
                        <div className="mt-4 p-4 bg-red-500/20 border border-red-500/50 rounded text-red-300">
                            {error}
                        </div>
                    )}

                    <p className="mt-8 text-center text-sm text-slate-400">
                        Ready to sign in?{" "}
                        <a href="/login" className="text-primary-purple-bright hover:text-white transition-colors font-medium cursor-pointer">
                            Go to login
                        </a>
                    </p>
                </motion.div>
            </div>
        </div>
    );
}
