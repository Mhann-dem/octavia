# Technical Specifications Document

## Technical Specifications Document (Tech Stack and Architecture) for Standard Video Translator Feature in Octavia - Beyond Nations

### Document Information

- **Document Title**: Technical Specifications Document for Standard Video Translator
- **Version**: 2.0
- **Date**: November 18, 2025
- **Prepared By**: AI Design Assistant
- **Purpose**: This document details the technical stack and architecture for the cloud-native Octavia platform.

### 1. Introduction

### 1.1 Overview

Octavia is built on a **modern, scalable cloud stack** designed for high-performance video processing. It leverages serverless GPU computing, edge storage, and an event-driven backend to deliver "Magic Mode" translation features.

### 2. Tech Stack Overview

### 2.1 Frontend
- **Framework**: Next.js 15.2 (App Router)
- **Language**: TypeScript / React 19
- **UI Library**: shadcn/ui + Tailwind CSS 3.4
- **State Management**: TanStack Query + Zustand
- **Auth**: Clerk (Organizations + JWT)

### 2.2 Backend API
- **Framework**: FastAPI 0.115
- **Language**: Python 3.12
- **Validation**: Pydantic 2.9
- **Documentation**: OpenAPI (Auto-generated)

### 2.3 Task Orchestration
- **Queue**: Celery 5.9
- **Broker**: Redis 8 (Streams)
- **Result Backend**: PostgreSQL (Neon)

### 2.4 Compute & AI
- **GPU Fleet**: RunPod Serverless (A100-80GB / H100-94GB)
- **Container**: Docker (Multi-stage, PyTorch 2.1+, CUDA 12)
- **Models**:
    - **Separation**: Demucs v4 (htdemucs_6s)
    - **VAD**: Silero VAD 4.0
    - **Diarization**: pyannote-audio 3.1
    - **Transcription**: WhisperX (large-v3-turbo)
    - **Translation**: SeamlessM4T-v2 / LLM
    - **TTS**: Coqui XTTS v2.0.3 / Fish-Speech 1.4
    - **Media**: FFmpeg 6.1+

### 2.5 Data & Storage
- **Database**: Neon Serverless Postgres 17 (pg_vector, pg_cron)
- **Object Storage**: BunnyCDN Volumes (NVMe Edge) + Backblaze B2 (Backup)
- **Caching**: Redis (Upstash)

### 3. System Architecture

### 3.1 High-Level Diagram
(Refer to `production_architecture.md` for the visual diagram)

### 3.2 Infrastructure
- **Hosting**: Vercel (Frontend), Fly.io (API), RunPod (Workers).
- **CDN**: BunnyCDN (Global Edge).
- **Monitoring**: Sentry (Errors), Prometheus + Grafana (Metrics), OpenTelemetry (Tracing).

### 4. Detailed Specifications per Component

### 4.1 Frontend (Next.js)
- **Uploads**: Uses `tus-js-client` for direct-to-CDN resumable uploads.
- **Real-time**: Consumes SSE endpoint for job progress.

### 4.2 Backend (FastAPI)
- **Webhooks**: Verifies HMAC signatures from BunnyCDN and Stripe.
- **Security**: Validates Clerk JWTs on every protected route.

### 4.3 GPU Workers
- **Environment**: Linux (Ubuntu 22.04), Python 3.12, CUDA 12.1.
- **Execution**: Runs the `MagicPipeline` class which orchestrates the 10-step process.
- **Security**: Ephemeral execution; all data wiped after job.

### 5. Hardware Requirements (Cloud)

- **Worker Nodes**:
    - GPU: NVIDIA A100 (80GB VRAM) or H100.
    - CPU: 16 vCPU.
    - RAM: 64GB+.
    - Storage: 100GB NVMe (Ephemeral).
- **API Nodes**:
    - CPU: 2 vCPU.
    - RAM: 4GB.

### 6. Edge Cases & Constraints

- **Max Video Duration**: 10 hours (soft limit).
- **Max File Size**: 50GB.
- **Cold Start**: ~15-45s for new GPU pods (mitigated by warm pool).
