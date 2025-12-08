"use client";

import { motion } from "framer-motion";
import { Upload, Video, Sparkles, CheckCircle, Rocket, Link as LinkIcon } from "lucide-react";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { getAuthToken } from "@/lib/auth";

export default function VideoTranslationPage() {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [videoUrl, setVideoUrl] = useState("");
    const [uploadMode, setUploadMode] = useState<"file" | "url">("file");
    const [sourceLanguage, setSourceLanguage] = useState("en");
    const [targetLanguage, setTargetLanguage] = useState("es");
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");
    const router = useRouter();

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

    const handleFileSelect = (file: File | null) => {
        setError("");
        if (file && file.type.startsWith("video/")) {
            setSelectedFile(file);
            setVideoUrl("");
            setUploadMode("file");
        } else if (file) {
            setError("Please select a valid video file (MP4, AVI, MOV, etc.)");
        }
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        const file = e.dataTransfer.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
    };

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
    };

    const handleUrlPaste = (e: React.ChangeEvent<HTMLInputElement>) => {
        const url = e.target.value;
        setVideoUrl(url);
        setError("");
        if (url) {
            setSelectedFile(null);
            setUploadMode("url");
        }
    };

    const handleTranslate = async () => {
        if (!selectedFile && !videoUrl) {
            setError("Please select a video file or paste a URL");
            return;
        }

        setIsLoading(true);
        setError("");
        const token = getAuthToken();

        try {
            let storagePath = "";

            // Step 1: Upload file if using file mode
            if (selectedFile) {
                const formData = new FormData();
                formData.append("file", selectedFile);
                formData.append("file_type", "video");

                const uploadResponse = await fetch(`${API_BASE_URL}/api/v1/upload`, {
                    method: "POST",
                    body: formData,
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });

                if (!uploadResponse.ok) {
                    const errorData = await uploadResponse.json();
                    throw new Error(errorData.detail || "Upload failed");
                }

                const uploadData = await uploadResponse.json();
                storagePath = uploadData.storage_path;
            } else {
                // For URL mode, use the URL directly as storage path
                storagePath = videoUrl;
            }

            // Step 2: Create video translation job
            const jobResponse = await fetch(`${API_BASE_URL}/api/v1/jobs/video-translate/create`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    file_id: selectedFile ? selectedFile.name : "url",
                    storage_path: storagePath,
                    source_language: sourceLanguage,
                    target_language: targetLanguage,
                    model_size: "base",
                }),
            });

            if (!jobResponse.ok) {
                const errorData = await jobResponse.json();
                throw new Error(errorData.detail || "Failed to create job");
            }

            const jobData = await jobResponse.json();
            const jobId = jobData.id;

            // Step 3: Queue the job for processing
            const processResponse = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/process`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            if (!processResponse.ok) {
                const errorData = await processResponse.json();
                throw new Error(errorData.detail || "Failed to process job");
            }

            // Success - redirect to progress page with job ID
            router.push(`/dashboard/video/progress?job_id=${jobId}`);
        } catch (err) {
            const message = err instanceof Error ? err.message : "An error occurred";
            setError(message);
            console.error("Translation error:", err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex flex-col gap-2">
                <h1 className="font-display text-3xl font-black text-white text-glow-purple">Video AI Translator</h1>
                <p className="text-slate-400 text-sm">Upload your video and translate it across languages</p>
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

            {/* Upload Tabs */}
            <div className="flex gap-2 mb-4">
                <button
                    onClick={() => setUploadMode("file")}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                        uploadMode === "file"
                            ? "bg-primary-purple/30 border border-primary-purple/50 text-white"
                            : "bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white"
                    }`}
                >
                    <Upload className="w-4 h-4" />
                    Upload File
                </button>
                <button
                    onClick={() => setUploadMode("url")}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                        uploadMode === "url"
                            ? "bg-primary-purple/30 border border-primary-purple/50 text-white"
                            : "bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white"
                    }`}
                >
                    <LinkIcon className="w-4 h-4" />
                    Paste URL
                </button>
            </div>

            {/* Upload Zone */}
            {uploadMode === "file" ? (
                <motion.div
                    whileHover={{ scale: 1.01 }}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className="glass-panel glass-panel-high relative border-2 border-dashed border-primary-purple/30 hover:border-primary-purple/50 transition-all cursor-pointer group mb-6 overflow-hidden"
                >
                    <div className="glass-shine" />

                    <div className="relative z-20 py-12 px-6">
                        <div className="flex flex-col items-center justify-center gap-3 text-center">
                            <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-purple/10 border border-primary-purple/30 shadow-glow group-hover:scale-110 transition-transform">
                                <Video className="w-8 h-8 text-primary-purple-bright" />
                            </div>
                            <div>
                                <h3 className="text-white text-lg font-bold mb-1 text-glow-purple">
                                    {selectedFile ? "✓ File Selected" : "Drop your video here"}
                                </h3>
                                {selectedFile ? (
                                    <p className="text-slate-300 text-sm">{selectedFile.name}</p>
                                ) : (
                                    <p className="text-slate-400 text-sm">or click to browse files • MP4, AVI, MOV supported</p>
                                )}
                            </div>
                        </div>
                    </div>
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="video/*"
                        onChange={handleFileInputChange}
                        className="hidden"
                    />
                </motion.div>
            ) : (
                <motion.div className="glass-panel glass-panel-high p-6 mb-6">
                    <div className="flex flex-col gap-3">
                        <label htmlFor="video-url" className="text-white text-sm font-semibold">Video URL</label>
                        <input
                            id="video-url"
                            type="url"
                            title="Video URL"
                            placeholder="https://example.com/video.mp4"
                            value={videoUrl}
                            onChange={handleUrlPaste}
                            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-purple/50 transition-colors"
                        />
                        {videoUrl && <p className="text-accent-cyan text-sm">✓ URL ready for processing</p>}
                    </div>
                </motion.div>
            )}

            {/* Configuration */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {/* Source Language */}
                <div className="glass-card p-4">
                    <label htmlFor="source-lang" className="text-white text-sm font-semibold mb-2 block">Source Language</label>
                    <select
                        id="source-lang"
                        title="Select source language"
                        value={sourceLanguage}
                        onChange={(e) => setSourceLanguage(e.target.value)}
                        className="glass-select w-full"
                    >
                        <option value="en">English</option>
                        <option value="es">Spanish</option>
                        <option value="fr">French</option>
                        <option value="de">German</option>
                        <option value="it">Italian</option>
                        <option value="pt">Portuguese</option>
                        <option value="ja">Japanese</option>
                        <option value="zh">Chinese</option>
                    </select>
                </div>

                {/* Target Language */}
                <div className="glass-card p-4">
                    <label htmlFor="target-lang" className="text-white text-sm font-semibold mb-2 block">Target Language</label>
                    <select
                        id="target-lang"
                        title="Select target language"
                        value={targetLanguage}
                        onChange={(e) => setTargetLanguage(e.target.value)}
                        className="glass-select w-full"
                    >
                        <option value="es">Spanish</option>
                        <option value="en">English</option>
                        <option value="fr">French</option>
                        <option value="de">German</option>
                        <option value="it">Italian</option>
                        <option value="pt">Portuguese</option>
                        <option value="ja">Japanese</option>
                        <option value="zh">Chinese</option>
                    </select>
                </div>
            </div>

            {/* AI Options */}
            <div className="glass-panel glass-panel-glow mb-6 p-5 relative overflow-hidden">
                <div className="glass-shine" />
                <div className="relative z-10">
                    <div className="flex items-start gap-3 mb-3">
                        <Sparkles className="w-5 h-5 text-accent-cyan" />
                        <div>
                            <h3 className="text-white text-sm font-bold mb-1">AI-Powered Features</h3>
                            <p className="text-slate-400 text-xs">Enhance your translation with advanced AI capabilities</p>
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent-cyan/10 border border-accent-cyan/30">
                            <CheckCircle className="w-3.5 h-3.5 text-accent-cyan" />
                            <span className="text-slate-200 text-xs font-medium">Voice Synthesis</span>
                        </div>
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary-purple/10 border border-primary-purple/30">
                            <CheckCircle className="w-3.5 h-3.5 text-primary-purple-bright" />
                            <span className="text-slate-200 text-xs font-medium">Lip Sync</span>
                        </div>
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-accent-pink/10 border border-accent-pink/30">
                            <CheckCircle className="w-3.5 h-3.5 text-accent-pink" />
                            <span className="text-slate-200 text-xs font-medium">Subtitle Generation</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Start Button */}
            <button
                onClick={handleTranslate}
                disabled={isLoading || (!selectedFile && !videoUrl)}
                className="btn-border-beam w-full group disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <div className="btn-border-beam-inner flex items-center justify-center gap-2 py-4 text-base">
                    <Rocket className="w-5 h-5 group-hover:rotate-12 transition-transform duration-300" />
                    <span>{isLoading ? "Processing..." : "Start Translation"}</span>
                </div>
            </button>
        </div>
    );
}
