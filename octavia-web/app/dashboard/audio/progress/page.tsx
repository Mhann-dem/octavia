"use client";

import { motion } from "framer-motion";
import { useSearchParams, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { CheckCircle, Loader, AlertCircle, Download, SkipBack } from "lucide-react";
import { getAuthToken } from "@/lib/auth";

export default function AudioTranslationProgressPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const jobId = searchParams.get("job_id");
    const [jobStatus, setJobStatus] = useState<{
        id: string;
        status: string;
        created_at?: string;
        duration?: number;
        output?: string;
        error?: string;
    } | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState("");
    const [downloadUrl, setDownloadUrl] = useState("");

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

    useEffect(() => {
        if (!jobId) {
            setError("No job ID provided");
            setIsLoading(false);
            return;
        }

        const fetchProgress = async () => {
            const token = getAuthToken();
            try {
                const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });

                if (!response.ok) {
                    throw new Error("Failed to fetch job status");
                }

                const data = await response.json();
                setJobStatus(data);

                if (data.status === "completed" && data.output) {
                    setDownloadUrl(data.output);
                }

                if (data.status === "failed") {
                    setError(data.error || "Job processing failed");
                }

                // Continue polling if not done
                if (data.status === "processing" || data.status === "queued") {
                    setTimeout(() => {
                        setIsLoading(false);
                    }, 500);
                } else {
                    setIsLoading(false);
                }
            } catch (err) {
                const message = err instanceof Error ? err.message : "Failed to fetch progress";
                setError(message);
                setIsLoading(false);
            }
        };

        // Initial fetch
        fetchProgress();

        // Poll for updates
        const interval = setInterval(fetchProgress, 3000);
        return () => clearInterval(interval);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [jobId]);

    const getStatusColor = (status: string) => {
        switch (status) {
            case "completed":
                return "text-accent-cyan";
            case "processing":
            case "queued":
                return "text-primary-purple-bright";
            case "failed":
                return "text-red-400";
            default:
                return "text-slate-400";
        }
    };

    const getProgressPercentage = () => {
        if (!jobStatus) return 0;
        switch (jobStatus.status) {
            case "queued":
                return 25;
            case "processing":
                return 75;
            case "completed":
                return 100;
            case "failed":
                return 0;
            default:
                return 0;
        }
    };

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex flex-col gap-2">
                    <h1 className="font-display text-3xl font-black text-white text-glow-purple">Audio Translation Progress</h1>
                    <p className="text-slate-400 text-sm">Your audio is being processed</p>
                </div>
                <button
                    onClick={() => router.push("/dashboard/audio")}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-300 hover:text-white transition-colors"
                >
                    <SkipBack className="w-4 h-4" />
                    Back
                </button>
            </div>

            {error && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-300 text-sm flex items-start gap-3"
                >
                    <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                    <div>{error}</div>
                </motion.div>
            )}

            {/* Status Card */}
            {jobStatus && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-panel glass-panel-high p-8 relative overflow-hidden"
                >
                    <div className="glass-shine" />
                    <div className="relative z-10">
                        {/* Status */}
                        <div className="flex items-center justify-between mb-8">
                            <div>
                                <p className="text-slate-400 text-sm mb-2">Current Status</p>
                                <h2 className={`text-3xl font-black capitalize ${getStatusColor(jobStatus.status)}`}>
                                    {jobStatus.status === "queued" ? "Queued" : jobStatus.status === "processing" ? "Processing" : "Completed"}
                                </h2>
                            </div>
                            <div>
                                {jobStatus.status === "completed" && (
                                    <CheckCircle className="w-16 h-16 text-accent-cyan" />
                                )}
                                {(jobStatus.status === "processing" || jobStatus.status === "queued") && (
                                    <Loader className="w-16 h-16 text-primary-purple-bright animate-spin" />
                                )}
                                {jobStatus.status === "failed" && (
                                    <AlertCircle className="w-16 h-16 text-red-400" />
                                )}
                            </div>
                        </div>

                        {/* Progress Bar */}
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-slate-400">Overall Progress</span>
                                <span className="text-white font-semibold">{getProgressPercentage()}%</span>
                            </div>
                            <div className="h-2 bg-slate-800/50 border border-slate-700/50 rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${getProgressPercentage()}%` }}
                                    transition={{ duration: 0.5 }}
                                    className="h-full bg-linear-to-r from-primary-purple to-primary-purple-bright"
                                />
                            </div>
                        </div>

                        {/* Job Details */}
                        <div className="mt-8 pt-8 border-t border-slate-700/50">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="glass-card p-4">
                                    <p className="text-slate-400 text-xs mb-1">Job ID</p>
                                    <p className="text-white text-sm font-mono">{jobId}</p>
                                </div>
                                <div className="glass-card p-4">
                                    <p className="text-slate-400 text-xs mb-1">Started</p>
                                    <p className="text-white text-sm">
                                        {jobStatus.created_at
                                            ? new Date(jobStatus.created_at).toLocaleString()
                                            : "Just now"}
                                    </p>
                                </div>
                                <div className="glass-card p-4">
                                    <p className="text-slate-400 text-xs mb-1">Duration</p>
                                    <p className="text-white text-sm">
                                        {jobStatus.duration ? `${jobStatus.duration}s` : "Calculating..."}
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Download Button */}
                        {jobStatus.status === "completed" && downloadUrl && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="mt-8"
                            >
                                <a
                                    href={downloadUrl}
                                    download
                                    className="btn-border-beam w-full group flex items-center justify-center gap-2 py-4"
                                >
                                    <Download className="w-5 h-5" />
                                    <span>Download Translated Audio</span>
                                </a>
                            </motion.div>
                        )}

                        {/* Back Button for Failed Jobs */}
                        {jobStatus.status === "failed" && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="mt-8"
                            >
                                <button
                                    onClick={() => router.push("/dashboard/audio")}
                                    className="btn-border-beam w-full group flex items-center justify-center gap-2 py-4"
                                >
                                    <SkipBack className="w-5 h-5" />
                                    <span>Try Again</span>
                                </button>
                            </motion.div>
                        )}
                    </div>
                </motion.div>
            )}

            {/* Loading State */}
            {isLoading && !jobStatus && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="glass-panel glass-panel-high p-8 flex items-center justify-center gap-4"
                >
                    <Loader className="w-6 h-6 text-primary-purple-bright animate-spin" />
                    <span className="text-slate-300">Loading job details...</span>
                </motion.div>
            )}

            {/* Processing Steps */}
            {jobStatus && (jobStatus.status === "processing" || jobStatus.status === "queued") && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-panel glass-panel-glow p-6"
                >
                    <h3 className="text-white text-sm font-bold mb-4">Processing Steps</h3>
                    <div className="space-y-3">
                        {[
                            { step: "Queued", active: jobStatus.status === "queued" },
                            { step: "Transcribing", active: jobStatus.status === "processing" },
                            { step: "Translating", active: jobStatus.status === "processing" },
                            { step: "Synthesizing", active: jobStatus.status === "processing" },
                        ].map((item, idx) => (
                            <motion.div
                                key={idx}
                                className="flex items-center gap-3"
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.1 }}
                            >
                                {item.active ? (
                                    <Loader className="w-4 h-4 text-primary-purple-bright animate-spin" />
                                ) : (
                                    <div className="w-4 h-4 rounded-full border border-slate-600" />
                                )}
                                <span className={item.active ? "text-white font-semibold" : "text-slate-400"}>
                                    {item.step}
                                </span>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>
            )}
        </div>
    );
}
