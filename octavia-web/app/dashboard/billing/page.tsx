"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Zap, AlertCircle, Loader } from "lucide-react";

interface BillingBalance {
    balance: number;
}

interface PricingTier {
    id: string;
    credits: number;
    price: number;
    description: string;
}

interface Transaction {
    id: string;
    type: string;
    amount: number;
    credits: number;
    timestamp: string;
    description: string;
}

interface PricingData {
    tiers: PricingTier[];
    credits_costs: {
        transcribe: number;
        translate: number;
        synthesize: number;
        video_translate: number;
    };
}

const CREDIT_COSTS = {
    transcribe: 1,
    translate: 2,
    synthesize: 3,
    video_translate: 5,
};

export default function BillingPage() {
    const [balance, setBalance] = useState<number>(0);
    const [tiers, setTiers] = useState<PricingTier[]>([]);
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [processingCheckout, setProcessingCheckout] = useState<string | null>(null);

    useEffect(() => {
        fetchBillingData();
    }, []);

    const fetchBillingData = async () => {
        try {
            setLoading(true);
            setError(null);
            const token = localStorage.getItem("access_token");

            if (!token) {
                setError("Not authenticated");
                return;
            }

            const headers = {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
            };

            // Fetch balance
            const balanceRes = await fetch(`${API_BASE_URL}/api/v1/billing/balance`, { headers });
            if (balanceRes.ok) {
                const data: BillingBalance = await balanceRes.json();
                setBalance(data.balance);
            }

            // Fetch pricing
            const pricingRes = await fetch(`${API_BASE_URL}/api/v1/billing/pricing`, { headers });
            if (pricingRes.ok) {
                const data: PricingData = await pricingRes.json();
                setTiers(data.tiers);
            }

            // Fetch transactions
            const transRes = await fetch(`${API_BASE_URL}/api/v1/billing/transactions`, { headers });
            if (transRes.ok) {
                const data = await transRes.json();
                setTransactions(data.transactions.slice(0, 10));
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to fetch billing data");
        } finally {
            setLoading(false);
        }
    };

    const handleBuyCredits = async (tierId: string) => {
        try {
            setProcessingCheckout(tierId);
            const token = localStorage.getItem("access_token");

            if (!token) {
                setError("Not authenticated");
                return;
            }

            const res = await fetch(`${API_BASE_URL}/api/v1/billing/checkout`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ tier_id: tierId }),
            });

            if (res.ok) {
                const data = await res.json();
                if (data.checkout_url) {
                    window.location.href = data.checkout_url;
                }
            } else {
                setError("Failed to create checkout session");
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Checkout failed");
        } finally {
            setProcessingCheckout(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader className="w-8 h-8 text-primary-purple animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="font-display text-3xl font-black text-white mb-2 text-glow-purple">Billing & Credits</h1>
                <p className="text-slate-400 text-sm">Manage your credits and purchase additional capacity</p>
            </div>

            {error && (
                <motion.div className="glass-panel p-4 border-l-2 border-red-500 flex gap-3 items-start">
                    <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                    <div>
                        <h3 className="text-white font-semibold">Error</h3>
                        <p className="text-slate-400 text-sm">{error}</p>
                    </div>
                </motion.div>
            )}

            {/* Credit Balance */}
            <motion.div className="glass-panel p-8 relative overflow-hidden">
                <div className="glass-shine" />
                <div className="relative z-10">
                    <div className="text-slate-400 text-sm mb-2">Current Balance</div>
                    <div className="flex items-baseline gap-3">
                        <span className="text-5xl font-bold text-primary-purple-bright">{Math.floor(balance)}</span>
                        <span className="text-xl text-slate-400">credits</span>
                    </div>
                    <p className="text-slate-500 text-sm mt-4">
                        Each operation costs different amounts: Transcribe (1), Translate (2), Synthesize (3), Video Translate (5)
                    </p>
                </div>
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Pricing Tiers */}
                <div className="lg:col-span-2">
                    <h2 className="text-white font-bold text-xl mb-4">Buy Credits</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {tiers.map((tier) => (
                            <motion.div
                                key={tier.id}
                                className="glass-panel p-6 relative overflow-hidden group hover:border-primary-purple/50 transition-all"
                                whileHover={{ y: -2 }}
                            >
                                <div className="glass-shine" />
                                <div className="relative z-10 space-y-4">
                                    <div>
                                        <div className="text-3xl font-bold text-white">{tier.credits.toLocaleString()}</div>
                                        <div className="text-slate-400 text-sm">{tier.description}</div>
                                    </div>
                                    <div className="text-2xl font-bold text-primary-purple-bright">
                                        ${(tier.price / 100).toFixed(2)}
                                    </div>
                                    <button
                                        onClick={() => handleBuyCredits(tier.id)}
                                        disabled={processingCheckout === tier.id}
                                        className="w-full py-2 px-4 bg-primary-purple hover:bg-primary-purple/80 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-all flex items-center justify-center gap-2"
                                    >
                                        {processingCheckout === tier.id ? (
                                            <>
                                                <Loader className="w-4 h-4 animate-spin" />
                                                Processing...
                                            </>
                                        ) : (
                                            <>
                                                <Zap className="w-4 h-4" />
                                                Buy Credits
                                            </>
                                        )}
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>

                {/* Recent Activity */}
                <div className="glass-panel p-6 h-fit">
                    <h3 className="text-white font-bold text-lg mb-4">Recent Activity</h3>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                        {transactions.length > 0 ? (
                            transactions.map((tx) => (
                                <motion.div
                                    key={tx.id}
                                    className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
                                    whileHover={{ x: 2 }}
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="flex-1 min-w-0">
                                            <div className="text-white font-medium text-sm truncate capitalize">{tx.type}</div>
                                            <div className="text-slate-500 text-xs">
                                                {new Date(tx.timestamp).toLocaleDateString()}
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className={`font-semibold text-sm ${tx.type === "purchase" ? "text-green-400" : "text-slate-400"}`}>
                                                {tx.type === "purchase" ? "+" : "-"}{tx.credits}
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            ))
                        ) : (
                            <div className="text-center text-slate-500 py-4">No transactions yet</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
