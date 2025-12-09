/**
 * Download Progress Modal Component
 * Shows download progress with visual feedback
 */

"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle2, AlertCircle, Download } from "lucide-react";
import { useEffect, useState } from "react";

interface DownloadProgressModalProps {
    isOpen: boolean;
    onClose: () => void;
    filename?: string;
    progress?: number;
    status?: "downloading" | "completed" | "error";
    error?: string;
}

export function DownloadProgressModal({
    isOpen,
    onClose,
    filename = "file",
    progress = 0,
    status = "downloading",
    error = "",
}: DownloadProgressModalProps) {
    const [displayProgress, setDisplayProgress] = useState(0);

    useEffect(() => {
        // Animate progress bar
        const interval = setInterval(() => {
            setDisplayProgress((prev) => {
                if (progress > prev) {
                    return Math.min(prev + Math.random() * 10, progress);
                }
                return prev;
            });
        }, 100);

        return () => clearInterval(interval);
    }, [progress]);

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 flex items-center justify-center z-50">
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="relative bg-slate-900 border border-white/10 rounded-lg p-6 max-w-sm mx-4 shadow-2xl"
                    >
                        {/* Close Button */}
                        <button
                            onClick={onClose}
                            className="absolute top-4 right-4 p-1 rounded-lg hover:bg-white/10 transition-colors"
                        >
                            <X className="w-5 h-5 text-slate-400 hover:text-white" />
                        </button>

                        {/* Content */}
                        <div className="space-y-4">
                            {/* Status Icon & Heading */}
                            <div className="flex items-center gap-3">
                                {status === "downloading" && (
                                    <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity }}>
                                        <Download className="w-6 h-6 text-blue-400" />
                                    </motion.div>
                                )}
                                {status === "completed" && (
                                    <motion.div
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        transition={{ type: "spring" }}
                                    >
                                        <CheckCircle2 className="w-6 h-6 text-green-400" />
                                    </motion.div>
                                )}
                                {status === "error" && (
                                    <AlertCircle className="w-6 h-6 text-red-400" />
                                )}

                                <div>
                                    <h3 className="font-semibold text-white">
                                        {status === "downloading" && "Downloading..."}
                                        {status === "completed" && "Download Complete"}
                                        {status === "error" && "Download Failed"}
                                    </h3>
                                </div>
                            </div>

                            {/* Filename */}
                            <div className="bg-white/5 rounded p-3 border border-white/10">
                                <p className="text-xs text-slate-400 mb-1">Filename</p>
                                <p className="text-sm font-mono text-slate-200 truncate">{filename}</p>
                            </div>

                            {/* Progress Bar */}
                            {status === "downloading" && (
                                <div className="space-y-2">
                                    <div className="flex justify-between items-center">
                                        <p className="text-xs text-slate-400">Progress</p>
                                        <p className="text-xs font-semibold text-blue-400">{Math.round(displayProgress)}%</p>
                                    </div>
                                    <div className="w-full bg-white/5 rounded-full h-2 border border-white/10 overflow-hidden">
                                        <motion.div
                                            className="h-full bg-gradient-to-r from-blue-400 to-blue-600"
                                            initial={{ width: 0 }}
                                            animate={{ width: `${displayProgress}%` }}
                                            transition={{ duration: 0.3 }}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Error Message */}
                            {status === "error" && error && (
                                <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
                                    <p className="text-sm text-red-300">{error}</p>
                                </div>
                            )}

                            {/* Success Message */}
                            {status === "completed" && (
                                <div className="bg-green-500/10 border border-green-500/30 rounded p-3">
                                    <p className="text-sm text-green-300">File downloaded successfully to your computer</p>
                                </div>
                            )}

                            {/* Action Buttons */}
                            <div className="flex gap-3 pt-2">
                                {status === "downloading" && (
                                    <button
                                        onClick={onClose}
                                        className="flex-1 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors text-sm font-medium"
                                    >
                                        Minimize
                                    </button>
                                )}
                                {status === "completed" && (
                                    <button
                                        onClick={onClose}
                                        className="flex-1 px-4 py-2 rounded-lg bg-green-500/20 hover:bg-green-500/30 text-green-400 hover:text-green-300 transition-colors text-sm font-medium"
                                    >
                                        Done
                                    </button>
                                )}
                                {status === "error" && (
                                    <button
                                        onClick={onClose}
                                        className="flex-1 px-4 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 hover:text-red-300 transition-colors text-sm font-medium"
                                    >
                                        Close
                                    </button>
                                )}
                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
