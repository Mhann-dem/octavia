"use client";

import { useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { CheckCircle, AlertCircle, Loader, Download, Home } from "lucide-react";
import Link from "next/link";
import { getAuthToken } from "@/lib/auth";
import { downloadFile } from "@/lib/downloadHelper";
import { DownloadProgressModal } from "@/components/DownloadProgressModal";
import { Suspense } from "react";

interface Job {
    id: string;
    user_id: string;
    job_type: string;
    status: string;
    input_file: string;
    output_file?: string;
    error_message?: string;
    job_metadata?: string;
    created_at: string;
    completed_at?: string;
    phase?: string;
    progress_percentage?: number;
    current_step?: string;
    started_at?: string;
}

function VideoProgressContent() {
    const searchParams = useSearchParams();
    const jobId = searchParams.get("job_id");
    const [job, setJob] = useState<Job | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [downloadProgress, setDownloadProgress] = useState(0);
    const [downloadStatus, setDownloadStatus] = useState<"idle" | "downloading" | "completed" | "error">("idle");
    const [downloadFilename, setDownloadFilename] = useState("");
    const [downloadError, setDownloadError] = useState("");
    const [showDownloadModal, setShowDownloadModal] = useState(false);

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

    useEffect(() => {
        if (!jobId) {
            setError("No job ID provided");
            setLoading(false);
            return;
        }

        const fetchJob = async () => {
            try {
                const token = getAuthToken();
                const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });

                if (!response.ok) {
                    throw new Error("Failed to fetch job status");
                }

                const data = await response.json();
                setJob(data);

                // Stop auto-refresh if job is completed or failed
                if (data.status === "completed" || data.status === "failed") {
                    setAutoRefresh(false);
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : "Error fetching job status");
            } finally {
                setLoading(false);
            }
        };

        fetchJob();

        // Auto-refresh every 2 seconds if still processing
        let interval: NodeJS.Timeout;
        if (autoRefresh) {
            interval = setInterval(fetchJob, 2000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [jobId, autoRefresh, API_BASE_URL]);

    if (loading) {
        return (
            <div className="space-y-8">
                <h1 className="font-display text-3xl font-black text-white text-glow-purple">Video Translation Progress</h1>
                <div className="flex items-center justify-center py-12">
                    <Loader className="w-8 h-8 text-accent-cyan animate-spin" />
                </div>
            </div>
        );
    }

    if (error || !job) {
        return (
            <div className="space-y-8">
                <h1 className="font-display text-3xl font-black text-white text-glow-purple">Video Translation Progress</h1>
                <div className="glass-panel glass-panel-high p-6 border border-red-500/30 bg-red-500/10">
                    <div className="flex items-start gap-4">
                        <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
                        <div>
                            <h3 className="text-red-300 font-semibold">Error</h3>
                            <p className="text-red-200 text-sm mt-1">{error || "Job not found"}</p>
                        </div>
                    </div>
                </div>
                <Link href="/dashboard/video">
                    <button className="btn-border-beam">
                        <div className="btn-border-beam-inner flex items-center justify-center gap-2 py-3">
                            <Home className="w-4 h-4" />
                            Back to Upload
                        </div>
                    </button>
                </Link>
            </div>
        );
    }

    const isCompleted = job.status === "completed";
    const isFailed = job.status === "failed";
    const isProcessing = job.status === "processing" || job.status === "pending";
    const progress = job.progress_percentage || 0;

    const handleDownload = async () => {
        try {
            const token = getAuthToken();
            if (!token) {
                setDownloadError("Not authenticated");
                setDownloadStatus("error");
                setShowDownloadModal(true);
                return;
            }

            setDownloadProgress(0);
            setDownloadStatus("downloading");
            setShowDownloadModal(true);

            await downloadFile(
                `${API_BASE_URL}/api/v1/jobs/${jobId}/download`,
                token,
                {
                    onProgress: (progress) => {
                        setDownloadProgress(progress);
                    },
                    onSuccess: (filename) => {
                        setDownloadFilename(filename);
                        setDownloadStatus("completed");
                        // Auto-close after 2 seconds if successful
                        setTimeout(() => {
                            setShowDownloadModal(false);
                            setDownloadStatus("idle");
                        }, 2000);
                    },
                    onError: (error) => {
                        setDownloadError(error);
                        setDownloadStatus("error");
                    },
                }
            );
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Download failed";
            setDownloadError(errorMessage);
            setDownloadStatus("error");
            setShowDownloadModal(true);
        }
    };

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex flex-col gap-2">
                <h1 className="font-display text-3xl font-black text-white text-glow-purple">Video Translation Progress</h1>
                <p className="text-slate-400 text-sm">Job ID: {jobId}</p>
            </div>

            {/* Status Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-panel glass-panel-glow p-6 relative overflow-hidden"
            >
                <div className="glass-shine" />
                <div className="relative z-10">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-3">
                            {isCompleted && <CheckCircle className="w-8 h-8 text-green-400" />}
                            {isFailed && <AlertCircle className="w-8 h-8 text-red-400" />}
                            {isProcessing && <Loader className="w-8 h-8 text-accent-cyan animate-spin" />}
                            <div>
                                <h3 className="text-white text-lg font-bold capitalize">
                                    {isCompleted && "Translation Complete"}
                                    {isFailed && "Translation Failed"}
                                    {isProcessing && "Processing..."}
                                </h3>
                                <p className="text-slate-400 text-sm capitalize">{job.current_step || job.phase}</p>
                            </div>
                        </div>
                        <div className="text-right">
                            <p className="text-3xl font-black text-accent-cyan">{Math.round(progress)}%</p>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-700/50 rounded-full h-2 overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 0.3 }}
                            className="h-full bg-gradient-to-r from-accent-cyan to-primary-purple"
                        />
                    </div>

                    {/* Details */}
                    <div className="grid grid-cols-2 gap-4 mt-6">
                        <div>
                            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Status</p>
                            <p className="text-white font-semibold capitalize">{job.status}</p>
                        </div>
                        <div>
                            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Phase</p>
                            <p className="text-white font-semibold capitalize">{job.phase || "Unknown"}</p>
                        </div>
                        <div>
                            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Started</p>
                            <p className="text-white font-semibold text-sm">
                                {job.started_at ? new Date(job.started_at).toLocaleTimeString() : "N/A"}
                            </p>
                        </div>
                        <div>
                            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Completed</p>
                            <p className="text-white font-semibold text-sm">
                                {job.completed_at ? new Date(job.completed_at).toLocaleTimeString() : "In Progress"}
                            </p>
                        </div>
                    </div>

                    {/* Error Message */}
                    {isFailed && job.error_message && (
                        <div className="mt-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
                            <p className="text-red-300 text-sm">{job.error_message}</p>
                        </div>
                    )}
                </div>
            </motion.div>

            {/* Download Section */}
            {isCompleted && job.output_file && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="glass-panel p-6"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-white font-bold">Your translated video is ready!</h3>
                            <p className="text-slate-400 text-sm mt-1">Download your translation or share it with others</p>
                        </div>
                        <button
                            onClick={handleDownload}
                            className="btn-border-beam"
                        >
                            <div className="btn-border-beam-inner flex items-center justify-center gap-2 py-3 px-6">
                                <Download className="w-4 h-4" />
                                Download
                            </div>
                        </button>
                    </div>
                </motion.div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
                <Link href="/dashboard/video" className="flex-1">
                    <button className="btn-border-beam w-full">
                        <div className="btn-border-beam-inner flex items-center justify-center gap-2 py-3">
                            Translate Another Video
                        </div>
                    </button>
                </Link>
                <Link href="/dashboard" className="flex-1">
                    <button className="px-6 py-3 rounded-lg bg-slate-800/50 border border-slate-700/50 text-white hover:border-slate-600/50 transition-colors">
                        Back to Hub
                    </button>
                </Link>
            </div>
        </div>
    );
}

export default function VideoProgressPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <VideoProgressContent />
        </Suspense>
    );
}
