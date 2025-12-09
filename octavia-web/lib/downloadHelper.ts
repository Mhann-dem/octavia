/**
 * Enhanced download helper for handling file downloads from the API
 * Provides progress tracking, error handling, and user feedback
 */

export interface DownloadOptions {
    onProgress?: (progress: number) => void;
    onError?: (error: string) => void;
    onSuccess?: (filename: string) => void;
}

/**
 * Download a file from the backend with progress tracking
 */
export async function downloadFile(
    url: string,
    authToken: string,
    options: DownloadOptions = {}
): Promise<void> {
    try {
        const response = await fetch(url, {
            headers: {
                Authorization: `Bearer ${authToken}`,
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            const errorMessage = errorData.detail || `Download failed with status ${response.status}`;
            options.onError?.(errorMessage);
            throw new Error(errorMessage);
        }

        // Get total file size if available
        const contentLength = response.headers.get("content-length");
        const total = parseInt(contentLength || "0", 10);

        // Create a reader for progress tracking
        const reader = response.body?.getReader();
        if (!reader) {
            options.onError?.("Unable to read response body");
            throw new Error("Unable to read response body");
        }

        const chunks: Uint8Array[] = [];
        let received = 0;

        // Read chunks and track progress
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            chunks.push(value);
            received += value.length;

            // Calculate and report progress
            if (total > 0) {
                const progress = (received / total) * 100;
                options.onProgress?.(Math.round(progress));
            }
        }

        // Combine chunks into single blob
        const blob = new Blob(chunks as BlobPart[], { type: response.headers.get("content-type") || "application/octet-stream" });

        // Extract filename from content-disposition header
        const contentDisposition = response.headers.get("content-disposition");
        let filename = `download-${Date.now()}`;

        if (contentDisposition) {
            const match = contentDisposition.match(/filename[^;=\n]*=(["\']?)([^"\';]*)\1/i);
            if (match && match[2]) {
                filename = match[2];
            }
        }

        // Trigger browser download
        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();

        // Cleanup
        URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(link);

        options.onSuccess?.(filename);
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown download error";
        options.onError?.(errorMessage);
        throw error;
    }
}

/**
 * Get appropriate file extension based on job type and format
 */
export function getFileExtension(jobType: string, format?: string): string {
    const extensions: { [key: string]: string } = {
        "video-translate": ".mp4",
        "audio-translate": ".mp3",
        transcribe: format === "srt" ? ".srt" : format === "vtt" ? ".vtt" : ".ass",
        translate: format === "srt" ? ".srt" : format === "vtt" ? ".vtt" : ".ass",
        synthesize: ".mp3",
    };
    return extensions[jobType] || ".bin";
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/**
 * Download multiple files as a batch
 */
export async function downloadBatch(
    jobIds: string[],
    authToken: string,
    apiUrl: string,
    options: DownloadOptions = {}
): Promise<void> {
    try {
        let completed = 0;

        for (const jobId of jobIds) {
            try {
                await downloadFile(
                    `${apiUrl}/api/v1/jobs/${jobId}/download`,
                    authToken,
                    {
                        onProgress: (progress) => {
                            const overallProgress = ((completed + progress / 100) / jobIds.length) * 100;
                            options.onProgress?.(Math.round(overallProgress));
                        },
                    }
                );
                completed++;
            } catch (error) {
                console.error(`Failed to download job ${jobId}:`, error);
                // Continue with next file
            }
        }

        if (completed === jobIds.length) {
            options.onSuccess?.(`Downloaded ${completed} files`);
        } else {
            options.onError?.(`Only downloaded ${completed} out of ${jobIds.length} files`);
        }
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Batch download failed";
        options.onError?.(errorMessage);
        throw error;
    }
}
