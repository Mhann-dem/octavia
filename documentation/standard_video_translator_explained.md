# Standard Video Translator Explained

### Octavia - Beyond Nations: Standard Video Translator Feature Design Document

This design document outlines the **Standard Video Translator** feature for *Octavia - Beyond Nations*, an AI-powered platform aimed at breaking down linguistic barriers through intelligent content adaptation. The feature enables seamless translation of videos from an original language (e.g., Armenian) to a target language (e.g., English) with dubbed audio, ensuring the output maintains the exact original duration and natural pacing. By automating the entire process—from input analysis to final merging—this design prioritizes simplicity for users, leveraging a **cloud-based AI orchestration layer** to dynamically optimize parameters such as chunk sizes, model selections, and timing adjustments.

The app is structured as a **modern web application** (Next.js Frontend + FastAPI Backend), emphasizing scalability and accessibility. It utilizes a serverless GPU fleet (RunPod) to handle intensive tasks like source separation, diarization, and voice cloning, ensuring high performance without demanding user hardware.

### 1. Multi-Angle Analysis: Core Design Principles

- **User Perspective**: Traditional tools often expose overwhelming options. Octavia's AI hides these, boiling the experience down to video upload and language choice. The "Magic Mode" ensures professional results (multi-speaker cloning, music preservation) by default.
- **Technical Feasibility**: The pipeline uses a battle-tested stack: **Next.js 15** for the frontend, **FastAPI** for the backend, **Celery + Redis** for task orchestration, and **RunPod** for GPU compute. Storage is handled by **BunnyCDN** for speed and cost-efficiency.
- **Performance & Scalability**: Targeting sub-realtime processing (e.g., 30 mins for a 1-hour video) using A100 GPUs. The system auto-scales from 0 to 200+ pods to handle concurrent demand.
- **Ethical & Inclusivity**: Prioritizes low-resource languages by using multilingual models (WhisperX, SeamlessM4T) and ensures cultural neutrality in translations.
- **Risk & Reliability**: Potential issues like API failures or GPU unavailability are mitigated by robust retry logic (Celery), exponential backoff, and redundant storage (BunnyCDN + Backblaze B2).

### 2. User Flow & UI/UX Design

The UI adopts a clean, dark-themed "Liquid Glass" interface for focus, with only essential elements to guide users through a 3-screen flow.

**Screen 1: Upload & Language Selection**
- **Goal**: Quick onboarding.
- **Layout**: Drag/drop zone with immediate pre-signed upload to BunnyCDN.
- **Languages**: Searchable dropdowns for Original and Target languages.
- **Magic Toggle**: Option to enable "Magic Mode" (Cloning + Ducking).

**Screen 2: Processing Dashboard**
- **Goal**: Build confidence with visible progress.
- **Layout**: Real-time timeline with SSE (Server-Sent Events) updates.
- **Details**: Steps shown: "Separating Sources", "Diarizing Speakers", "Cloning Voices", "Translating", "Dubbing", "Syncing".
- **Preview**: "Sample Chunk" button to hear a 15s snippet mid-process.

**Screen 3: Output Review & Export**
- **Goal**: Validate and deliver.
- **Layout**: Embedded player streaming from CDN.
- **Stats**: Sync accuracy, duration match.
- **Action**: Download MP4, SRT, or Audio-only.

### 3. Technical Architecture & Pipeline

**Stack**:
- **Frontend**: Next.js 15 (App Router), React 19, Tailwind CSS, shadcn/ui.
- **Backend**: FastAPI 0.115, Pydantic 2.9.
- **Database**: Neon Serverless Postgres 17 + pg_vector.
- **Queue**: Celery 5.9 + Redis Streams.
- **Compute**: RunPod Serverless (A100-80GB pods).
- **Storage**: BunnyCDN Volumes (NVMe) + Backblaze B2.

**Pipeline Step-by-Step ("Magic Mode")**:

1.  **Upload & Pre-analysis**: FFprobe + Whisper large-v3-turbo (first 2 min) for language and speaker hints.
2.  **Source Separation**: Demucs v4 (htdemucs_6s) separates vocals from background music.
3.  **Intelligent Chunking**: Silero VAD 4.0 + BERT sentence segmenter for natural 6-12s chunks.
4.  **Diarization**: pyannote-audio 3.1 + spectral clustering to identify speakers (Speaker A, B, C...).
5.  **Voice Cloning**: XTTS v2 zero-shot + RVC on best 30s segments to create temporary voice models for each speaker.
6.  **Transcription**: WhisperX (large-v3-turbo) with forced alignment for word-level timestamps.
7.  **Translation**: SeamlessM4T-v2 / Grok-4 prompt to translate and condense text (≤1.2x length).
8.  **TTS**: Coqui XTTS v2.0.3 generating audio using the cloned voices.
9.  **Micro-Sync**: FFmpeg `atempo` + strategic pauses to match original duration exactly.
10. **Ducking & Merge**: FFmpeg `sidechaincompress` to duck background music under speech, then merge all streams.

### 4. Edge Cases, Risks & Mitigations

- **Pacing Expansion**: If translation is too long, AI re-generates with a "condense" prompt.
- **Noisy Audio**: Demucs separates vocals; if SNR is still low, fallback to robust transcription models.
- **Hardware Availability**: RunPod spot instances with fallback to on-demand to ensure availability.
- **Privacy**: All temporary voice clones and files are ephemeral and deleted immediately after job completion.
