# Selected Technologies & Tools

## Selected Technologies for Octavia Production Architecture

This document outlines the final selection of tools and technologies for the Octavia cloud-native platform, as defined in the Production Architecture (Nov 18, 2025).

### 1. Frontend & UI

- **Next.js 15 (App Router)**
    - **Why**: Server components and streaming allow for instant UI rendering and efficient data fetching.
- **shadcn/ui + Tailwind CSS**
    - **Why**: Provides accessible, high-quality components that match the "Liquid Glass" design system (dark mode, premium feel).
- **TanStack Query**
    - **Why**: Manages server state with optimistic updates, essential for real-time job progress tracking.

### 2. Backend & API

- **FastAPI (Python)**
    - **Why**: Async native, high performance, and automatic OpenAPI documentation. Ideal for AI/ML workloads.
- **Celery + Redis**
    - **Why**: Robust distributed task queue for managing long-running GPU jobs. Supports priority queues (Free vs Pro).
- **Clerk**
    - **Why**: Complete authentication solution with support for Organizations (Teams), MFA, and social login.

### 3. Compute & AI Infrastructure

- **RunPod Serverless**
    - **Why**: Provides on-demand access to A100/H100 GPUs with pay-per-second billing. Scales from 0 to 200+ pods instantly.
- **Docker**
    - **Why**: Ensures consistent execution environments across dev and prod.

### 4. AI Models (The "Magic Mode" Pipeline)

- **Demucs v4 (htdemucs_6s)**: For separating vocals from background music.
- **Silero VAD 4.0**: For precise voice activity detection and chunking.
- **pyannote-audio 3.1**: For speaker diarization (identifying who is speaking).
- **WhisperX (large-v3-turbo)**: For highly accurate transcription with word-level timestamps.
- **Coqui XTTS v2**: For high-quality voice cloning and text-to-speech.
- **SeamlessM4T-v2**: For translation.

### 5. Storage & Database

- **BunnyCDN Volumes**: High-performance NVMe edge storage for video files.
- **Neon Serverless Postgres**: Auto-scaling SQL database with vector support (pg_vector) for future semantic search.
- **Redis**: For caching and real-time pub/sub.

### 6. DevOps & Monitoring

- **Terraform**: For Infrastructure as Code (IaC) to provision RunPod and BunnyCDN resources.
- **GitHub Actions**: For CI/CD pipelines.
- **Sentry**: For error tracking.
- **Prometheus + Grafana**: For metrics and monitoring.
