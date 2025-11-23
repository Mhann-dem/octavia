# Functional Requirements Document (FRD)

## Functional Requirements Document (FRD) for Standard Video Translator Feature in Octavia - Beyond Nations

### Document Information

- **Document Title**: Functional Requirements Document for Standard Video Translator
- **Version**: 2.0
- **Date**: November 18, 2025
- **Prepared By**: AI Design Assistant
- **Purpose**: This FRD specifies the system's functional behaviors for the cloud-native Octavia platform.

### 1. Introduction

### 1.1 Overview

The Standard Video Translator feature processes user-uploaded videos via a cloud pipeline. It automates source separation, diarization, voice cloning, translation, and dubbing. The system ensures the output video matches the input's exact duration with natural dubbing, utilizing a serverless GPU fleet for "Magic Mode" processing.

### 1.2 Scope

- **In Scope**: Web ingestion, Cloud GPU processing, Magic Mode (Cloning/Ducking), API callbacks, SSE progress updates.
- **Out of Scope**: Local processing, offline mode.

### 2. System Overview

The feature comprises a **Next.js Frontend** and a **FastAPI Backend**. Data flows from the browser to **BunnyCDN** (upload), then to **RunPod** workers (processing), and back to CDN for delivery. **Celery** manages the task queue.

### 3. Functional Requirements

### 3.1 Upload and Pre-Analysis

- **FR-1.1: Resumable Web Upload**
    - Inputs: Video file via Drag & Drop.
    - Processes: Request pre-signed URL from API; upload directly to BunnyCDN (tus protocol).
    - Validation: File type check; size limit check.
- **FR-1.2: Pre-Analysis**
    - Processes: Worker downloads first 2 mins; runs Whisper + FFprobe.
    - Outputs: Language detection, Speaker count hint, Music presence score.

### 3.2 Magic Mode Pipeline

- **FR-2.1: Source Separation**
    - Processes: Run Demucs v4 to separate Vocals and Background Music (BGM).
    - Outputs: `vocals.wav`, `bgm.wav`.
- **FR-2.2: Diarization & Cloning**
    - Processes: Run pyannote-audio to identify speakers; extract 30s samples; train XTTS/RVC voice models.
    - Outputs: Speaker labels (A, B, C), Voice Models (latents/weights).
- **FR-2.3: Transcription & Translation**
    - Processes: WhisperX for word-level timestamps; SeamlessM4T/LLM for translation and condensation (≤1.2x length).
    - Outputs: Timed, translated text segments.
- **FR-2.4: Dubbing & Sync**
    - Processes: Generate speech using cloned voices; adjust speed (atempo) to match original segment duration.
    - Outputs: Synced vocal tracks.
- **FR-2.5: Ducking & Merge**
    - Processes: Compress BGM when vocals are present (sidechain); merge Vocals + BGM + Video.
    - Outputs: Final MP4.

### 3.3 Progress & Delivery

- **FR-3.1: Real-time Updates**
    - Processes: Workers push status to Redis; API pushes SSE to Frontend.
    - Outputs: Progress bar, current step name, "Sample Chunk" availability.
- **FR-3.2: Delivery**
    - Processes: Final video uploaded to BunnyCDN private zone; signed URL generated for user.
    - Outputs: Downloadable link.

### 4. Data Requirements

- **Inputs**: Video (MP4/MOV/AVI), Auth Token (Clerk).
- **Outputs**: Final Video, Transcript, Audio Stems.
- **Storage**: BunnyCDN (Object Storage), Neon Postgres (Metadata), Redis (Queue/Cache).

### 5. Interfaces

- **User Interfaces**: Next.js Web App (Dashboard, Upload, Settings).
- **System Interfaces**: FastAPI (REST), Celery (Task Queue).
- **External Interfaces**: Clerk (Auth), Stripe (Billing), RunPod (GPU), BunnyCDN (Storage).

### 6. Acceptance Criteria

- **AC1**: System handles 5GB upload without timeout.
- **AC2**: "Magic Mode" successfully separates and re-integrates background music.
- **AC3**: Voice cloning produces distinct, consistent voices for multiple speakers.
- **AC4**: Total processing time is within 0.5x - 0.7x of video duration.
