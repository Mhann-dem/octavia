// Example: Frontend Job Progress Tracking with SSE and Polling

// ============================================================================
// OPTION 1: Server-Sent Events (Recommended for real-time updates)
// ============================================================================

const jobId = "123abc";
const eventSource = new EventSource(`/api/v1/jobs/${jobId}/stream`);

eventSource.onmessage = (event) => {
    const jobStatus = JSON.parse(event.data);
    
    // Example response structure:
    // {
    //   "job_id": "123abc",
    //   "status": "processing",
    //   "job_type": "transcribe",
    //   "phase": "transcribing",
    //   "progress_percentage": 45.0,
    //   "current_step": "Transcribing audio with Whisper",
    //   "created_at": "2025-01-10T12:00:00",
    //   "started_at": "2025-01-10T12:00:05",
    //   "completed_at": null,
    //   "error_message": null,
    //   "output_file": null,
    //   "timestamp": "2025-01-10T12:00:30"
    // }
    
    console.log(`Progress: ${jobStatus.progress_percentage}%`);
    console.log(`Phase: ${jobStatus.phase}`);
    console.log(`Step: ${jobStatus.current_step}`);
    
    // Update UI progress bar
    document.getElementById('progress').value = jobStatus.progress_percentage;
    document.getElementById('step-text').textContent = jobStatus.current_step;
    
    // Handle completion
    if (jobStatus.status === 'completed') {
        console.log('Job completed!', jobStatus);
        eventSource.close();
    }
};

eventSource.addEventListener('done', (event) => {
    console.log('Job finished (done event)');
    eventSource.close();
});

eventSource.onerror = (error) => {
    console.error('Stream error:', error);
    eventSource.close();
};

// ============================================================================
// OPTION 2: Polling (Alternative if SSE not supported)
// ============================================================================

async function pollJobStatus(jobId, token) {
    const response = await fetch(`/api/v1/jobs/${jobId}/status`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    
    const jobStatus = await response.json();
    
    // Same response structure as SSE:
    // {
    //   "job_id": "123abc",
    //   "status": "processing",
    //   "job_type": "transcribe",
    //   "phase": "transcribing",
    //   "progress_percentage": 45.0,
    //   "current_step": "Transcribing audio with Whisper",
    //   ...
    // }
    
    return jobStatus;
}

// Poll every 1 second
const pollInterval = setInterval(async () => {
    const status = await pollJobStatus(jobId, authToken);
    
    document.getElementById('progress').value = status.progress_percentage;
    document.getElementById('step-text').textContent = status.current_step;
    
    if (['completed', 'failed'].includes(status.status)) {
        clearInterval(pollInterval);
    }
}, 1000);

// ============================================================================
// JOB PHASES
// ============================================================================
// The "phase" field tracks which stage of the pipeline the job is in:
//
// - "pending": Job created, waiting to start processing
// - "transcribing": Extracting audio/text from input
// - "translating": Converting text to target language
// - "synthesizing": Converting translated text to speech
// - "uploading": Saving output files
// - "completed": Successfully finished
// - "failed": Error occurred

// ============================================================================
// PROGRESS PERCENTAGE GUIDANCE
// ============================================================================
// Approximate progress tracking for different job types:
//
// Transcription:
//   0-20%: Initialization
//   20-80%: Audio processing with Whisper
//   80-100%: Finalization
//
// Translation:
//   0-20%: Initialization
//   20-80%: Translation with LLM
//   80-100%: Finalization
//
// Synthesis:
//   0-20%: Initialization
//   20-80%: Text-to-speech conversion
//   80-100%: Audio finalization
//
// Video Translation (Full Pipeline):
//   0-15%: Initialization
//   15-40%: Transcription
//   40-65%: Translation
//   65-90%: Synthesis + Video Re-encoding
//   90-100%: Finalization

// ============================================================================
// EXAMPLE: React Component with Progress Tracking
// ============================================================================

import React, { useState, useEffect } from 'react';

export function JobProgressMonitor({ jobId, token }) {
    const [jobStatus, setJobStatus] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Use SSE for real-time updates
        const eventSource = new EventSource(`/api/v1/jobs/${jobId}/stream`);

        eventSource.onmessage = (event) => {
            try {
                const status = JSON.parse(event.data);
                setJobStatus(status);
                setError(null);
            } catch (e) {
                setError('Failed to parse job status');
            }
        };

        eventSource.onerror = (err) => {
            setError('Connection lost');
            eventSource.close();
        };

        return () => eventSource.close();
    }, [jobId]);

    if (error) {
        return <div className="error">{error}</div>;
    }

    if (!jobStatus) {
        return <div>Connecting...</div>;
    }

    const phaseColors = {
        pending: '#cccccc',
        transcribing: '#3498db',
        translating: '#9b59b6',
        synthesizing: '#e74c3c',
        uploading: '#f39c12',
        completed: '#27ae60',
        failed: '#c0392b',
    };

    return (
        <div className="job-monitor">
            <h2>Job Progress</h2>
            
            <div className="status-info">
                <span>Status: {jobStatus.status.toUpperCase()}</span>
                <span>Phase: <span style={{color: phaseColors[jobStatus.phase]}}>{jobStatus.phase}</span></span>
            </div>

            <div className="progress-container">
                <div className="progress-bar">
                    <div 
                        className="progress-fill"
                        style={{width: `${jobStatus.progress_percentage}%`}}
                    />
                </div>
                <span className="progress-text">{jobStatus.progress_percentage}%</span>
            </div>

            <div className="current-step">
                <strong>Current Step:</strong> {jobStatus.current_step || 'Pending...'}
            </div>

            {jobStatus.error_message && (
                <div className="error-message">
                    Error: {jobStatus.error_message}
                </div>
            )}

            <div className="job-timing">
                {jobStatus.started_at && (
                    <p>Started: {new Date(jobStatus.started_at).toLocaleString()}</p>
                )}
                {jobStatus.completed_at && (
                    <p>Completed: {new Date(jobStatus.completed_at).toLocaleString()}</p>
                )}
            </div>

            {jobStatus.output_file && (
                <div className="output">
                    <a href={jobStatus.output_file} download>
                        Download Result
                    </a>
                </div>
            )}
        </div>
    );
}
