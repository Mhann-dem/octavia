"use client";

import { useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { CheckCircle, AlertCircle, Loader, Download, Home } from "lucide-react";
import Link from "next/link";
import { getAuthToken } from "@/lib/auth";

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

export default function VideoProgressPage() {
    const searchParams = useSearchParams();
    const jobId = searchParams.get("job_id");
    const [job, setJob] = useState<Job | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [autoRefresh, setAutoRefresh] = useState(true);

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
                        <a
                            href={`${API_BASE_URL}/api/v1/download/${jobId}`}
                            className="btn-border-beam"
                        >
                            <div className="btn-border-beam-inner flex items-center justify-center gap-2 py-3 px-6">
                                <Download className="w-4 h-4" />
                                Download
                            </div>
                        </a>
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
                    <div>
                        <h2 className="text-xl font-bold text-white mb-4">Translation Pipeline</h2>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
                            {/* Step 1: Completed */}
                            <div className="glass-card flex flex-col items-center gap-3 p-4 text-center border-green-500/30 bg-green-500/5">
                                <div className="flex size-10 items-center justify-center rounded-full bg-green-500/20 text-green-400 shadow-glow">
                                    <CheckCircle className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-white">Splitting</p>
                                    <p className="text-xs text-slate-400">Completed</p>
                                </div>
                            </div>

                            {/* Step 2: Completed */}
                            <div className="glass-card flex flex-col items-center gap-3 p-4 text-center border-green-500/30 bg-green-500/5">
                                <div className="flex size-10 items-center justify-center rounded-full bg-green-500/20 text-green-400 shadow-glow">
                                    <CheckCircle className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-white">Transcribing</p>
                                    <p className="text-xs text-slate-400">Completed</p>
                                </div>
                            </div>

                            {/* Step 3: Completed */}
                            <div className="glass-card flex flex-col items-center gap-3 p-4 text-center border-green-500/30 bg-green-500/5">
                                <div className="flex size-10 items-center justify-center rounded-full bg-green-500/20 text-green-400 shadow-glow">
                                    <CheckCircle className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-white">Translating</p>
                                    <p className="text-xs text-slate-400">Completed</p>
                                </div>
                            </div>

                            {/* Step 4: In Progress */}
                            <div className="glass-panel glass-panel-glow flex flex-col items-center gap-3 p-4 text-center ring-1 ring-primary-purple/50 relative overflow-hidden">
                                <div className="glass-shine" />
                                <div className="relative z-10 flex flex-col items-center gap-3">
                                    <div className="flex size-10 items-center justify-center rounded-full bg-primary-purple/20 text-primary-purple-bright shadow-glow">
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-bold text-white text-glow-purple">Dubbing</p>
                                        <p className="text-xs text-primary-purple-bright">In Progress</p>
                                    </div>
                                </div>
                            </div>

                            {/* Step 5: Queued */}
                            <div className="glass-card flex flex-col items-center gap-3 p-4 text-center opacity-50">
                                <div className="flex size-10 items-center justify-center rounded-full bg-white/5 text-slate-500">
                                    <Clock className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-white">Merging</p>
                                    <p className="text-xs text-slate-400">Queued</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="lg:col-span-1 flex flex-col gap-6">
                    {/* Status Overview */}
                    <div className="glass-panel p-6">
                        <h3 className="text-lg font-bold text-white mb-4">Status Overview</h3>
                        <div className="flex flex-col gap-4">
                            <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
                                <p className="text-sm text-slate-400">Estimated Time</p>
                                <p className="text-sm font-bold text-white">~12 minutes</p>
                            </div>
                            <button className="btn-border-beam w-full group">
                                <div className="btn-border-beam-inner flex items-center justify-center gap-2 py-2.5">
                                    <PlayCircle className="w-5 h-5 group-hover:scale-110 transition-transform" />
                                    <span>Play Sample Chunk</span>
                                </div>
                            </button>
                        </div>
                    </div>

                    {/* Logs */}
                    <div className="glass-panel overflow-hidden">
                        <button
                            onClick={() => setIsLogsOpen(!isLogsOpen)}
                            className="w-full flex items-center justify-between p-4 font-medium text-white bg-white/5 hover:bg-white/10 transition-colors"
                        >
                            <span className="flex items-center gap-2">
                                <Terminal className="w-4 h-4 text-slate-400" />
                                View Technical Logs
                            </span>
                            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isLogsOpen ? "rotate-180" : ""}`} />
                        </button>

                        {isLogsOpen && (
                            <div className="h-80 overflow-y-auto p-4 font-mono text-xs space-y-1 custom-scrollbar bg-black/20 border-t border-white/5">
                                <p className="text-slate-500">[14:32:01] - <span className="text-slate-300">Starting translation job for Video_File_Name.mp4...</span></p>
                                <p className="text-slate-500">[14:32:02] - <span className="text-slate-300">Video split into 82 chunks.</span></p>
                                <p className="text-slate-500">[14:32:05] - <span className="text-green-400">Transcription successful for chunk 1/82.</span></p>
                                <p className="text-slate-500">[14:32:08] - <span className="text-green-400">Translation successful for chunk 1/82.</span></p>
                                <p className="text-slate-500">[14:32:12] - <span className="text-slate-300">Dubbing chunk 1/82: Aligning audio...</span></p>
                                <p className="text-slate-500">[14:32:15] - <span className="text-green-400">Dubbing successful for chunk 1/82.</span></p>
                                <p className="text-slate-500">[...]</p>
                                <p className="text-slate-500">[14:38:22] - <span className="text-green-400">Transcription successful for chunk 56/82.</span></p>
                                <p className="text-slate-500">[14:38:25] - <span className="text-green-400">Translation successful for chunk 56/82.</span></p>
                                <p className="text-slate-500">[14:38:29] - <span className="text-primary-purple-bright">Dubbing chunk 56/82: API call to TTS initiated.</span></p>
                                <p className="text-slate-500">[14:38:33] - <span className="text-primary-purple-bright">Dubbing chunk 56/82: Received audio stream.</span></p>
                                <p className="text-slate-500">[14:38:35] - <span className="text-primary-purple-bright animate-pulse">Dubbing chunk 56/82: Aligning audio with video.</span></p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
