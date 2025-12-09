"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Search, Filter, Download, ExternalLink, Clock, CheckCircle2, AlertCircle, Loader } from "lucide-react";
import { getAuthToken } from "@/lib/auth";
import { useRouter } from "next/navigation";

interface Job {
    id: string;
    file_id: string;
    job_type: string;
    status: string;
    created_at: string;
    updated_at: string;
    progress_percentage?: number;
    phase?: string;
    metadata?: {
        source_language?: string;
        target_language?: string;
        duration?: number;
    };
}

export default function JobHistoryPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [filteredJobs, setFilteredJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [filterType, setFilterType] = useState("all");
    const router = useRouter();

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

    useEffect(() => {
        fetchJobs();
    }, []);

    useEffect(() => {
        // Filter jobs based on search and type
        let filtered = jobs;

        if (searchQuery) {
            filtered = filtered.filter((job) =>
                job.file_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                job.id.toLowerCase().includes(searchQuery.toLowerCase())
            );
        }

        if (filterType !== "all") {
            filtered = filtered.filter((job) => job.job_type === filterType);
        }

        setFilteredJobs(filtered);
    }, [searchQuery, filterType, jobs]);

    const fetchJobs = async () => {
        try {
            setLoading(true);
            setError("");
            const token = getAuthToken();

            if (!token) {
                setError("Not authenticated");
                setLoading(false);
                return;
            }

            const response = await fetch(`${API_BASE_URL}/api/v1/jobs`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to fetch jobs");
            }

            const data = await response.json();
            setJobs(data.jobs || []);
        } catch (err) {
            const message = err instanceof Error ? err.message : "Failed to fetch job history";
            setError(message);
            console.error("Error fetching jobs:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async (jobId: string) => {
        try {
            const token = getAuthToken();
            const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/download`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            if (!response.ok) {
                throw new Error("Download failed");
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;

            // Extract filename from content-disposition header
            const contentDisposition = response.headers.get("content-disposition");
            const filename = contentDisposition
                ? contentDisposition.split("filename=")[1]?.replace(/"/g, "") || `job-${jobId}`
                : `job-${jobId}`;

            link.download = filename;
            document.body.appendChild(link);
            link.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(link);
        } catch (err) {
            alert("Failed to download file: " + (err instanceof Error ? err.message : "Unknown error"));
        }
    };

    const getJobTypeDisplay = (jobType: string) => {
        const types: { [key: string]: { label: string; icon: string } } = {
            "video-translate": { label: "Video Translation", icon: "🎬" },
            "audio-translate": { label: "Audio Translation", icon: "🎙️" },
            transcribe: { label: "Subtitle Gen", icon: "📝" },
            translate: { label: "Subtitle Trans", icon: "🌐" },
            synthesize: { label: "Synthesis", icon: "🔊" },
        };
        return types[jobType] || { label: jobType, icon: "📋" };
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case "COMPLETED":
                return "text-green-400";
            case "PROCESSING":
            case "PENDING":
                return "text-blue-400";
            case "FAILED":
                return "text-red-400";
            default:
                return "text-slate-400";
        }
    };

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="font-display text-3xl font-black text-white mb-2 text-glow-purple">Job History</h1>
                    <p className="text-slate-400 text-sm">View and manage your past translation tasks</p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Search jobs..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-10 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-primary-purple/50 w-64 transition-all"
                        />
                    </div>
                    <select
                        title="Filter by job type"
                        value={filterType}
                        onChange={(e) => setFilterType(e.target.value)}
                        className="p-2 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition-colors text-sm focus:outline-none focus:border-primary-purple/50"
                    >
                        <option value="all">All Types</option>
                        <option value="video-translate">Video Translation</option>
                        <option value="audio-translate">Audio Translation</option>
                        <option value="transcribe">Subtitle Gen</option>
                        <option value="translate">Subtitle Trans</option>
                        <option value="synthesize">Synthesis</option>
                    </select>
                    <button
                        onClick={fetchJobs}
                        className="p-2 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
                        title="Refresh"
                    >
                        <Filter className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-300 text-sm"
                >
                    {error}
                </motion.div>
            )}

            {/* Loading */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader className="w-8 h-8 text-primary-purple-bright animate-spin" />
                </div>
            ) : (
                <>
                    {/* Jobs List */}
                    <div className="glass-panel overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="border-b border-white/5 bg-white/5">
                                        <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Job Details</th>
                                        <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Type</th>
                                        <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                                        <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Date</th>
                                        <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {filteredJobs.length > 0 ? (
                                        filteredJobs.slice(0, 10).map((job) => {
                                            const typeInfo = getJobTypeDisplay(job.job_type);
                                            return (
                                                <tr key={job.id} className="group hover:bg-white/5 transition-colors">
                                                    <td className="p-4">
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-10 h-10 rounded bg-white/5 flex items-center justify-center border border-white/10">
                                                                <span className="text-lg">{typeInfo.icon}</span>
                                                            </div>
                                                            <div>
                                                                <div className="font-medium text-white group-hover:text-primary-purple-bright transition-colors">{job.file_id}</div>
                                                                <div className="text-xs text-slate-500">
                                                                    {job.id} • {job.metadata?.duration ? `${Math.round(job.metadata.duration)}s` : "N/A"}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="p-4">
                                                        <div className="text-sm text-slate-300">{typeInfo.label}</div>
                                                        <div className="text-xs text-slate-500">
                                                            {job.metadata?.source_language && job.metadata?.target_language
                                                                ? `${job.metadata.source_language.toUpperCase()} → ${job.metadata.target_language.toUpperCase()}`
                                                                : job.metadata?.source_language
                                                                ? job.metadata.source_language.toUpperCase()
                                                                : "N/A"}
                                                        </div>
                                                    </td>
                                                    <td className="p-4">
                                                        <div className="flex items-center gap-2">
                                                            {job.status === "COMPLETED" && <CheckCircle2 className="w-4 h-4 text-green-400" />}
                                                            {(job.status === "PROCESSING" || job.status === "PENDING") && (
                                                                <Clock className="w-4 h-4 text-blue-400 animate-pulse" />
                                                            )}
                                                            {job.status === "FAILED" && <AlertCircle className="w-4 h-4 text-red-400" />}
                                                            <span className={`text-sm font-medium ${getStatusColor(job.status)}`}>
                                                                {job.status}
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td className="p-4 text-sm text-slate-400">{formatDate(job.created_at)}</td>
                                                    <td className="p-4 text-right">
                                                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                            {job.status === "COMPLETED" && (
                                                                <button
                                                                    onClick={() => handleDownload(job.id)}
                                                                    className="p-2 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                                                                    title="Download"
                                                                >
                                                                    <Download className="w-4 h-4" />
                                                                </button>
                                                            )}
                                                            <button
                                                                onClick={() => router.push(`/dashboard/video/progress?job_id=${job.id}`)}
                                                                className="p-2 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                                                                title="View Details"
                                                            >
                                                                <ExternalLink className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    ) : (
                                        <tr>
                                            <td colSpan={5} className="p-8 text-center text-slate-400">
                                                No jobs found. Create your first translation!
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination Info */}
                        {filteredJobs.length > 0 && (
                            <div className="p-4 border-t border-white/5 flex items-center justify-between text-sm text-slate-500">
                                <div>Showing 1-{Math.min(10, filteredJobs.length)} of {filteredJobs.length} jobs</div>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
