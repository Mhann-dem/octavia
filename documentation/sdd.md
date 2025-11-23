# System Design Document (SDD)

## System Design Document (SDD) for Standard Video Translator Feature in Octavia - Beyond Nations

### Document Information

- **Document Title**: System Design Document for Standard Video Translator
- **Version**: 2.0
- **Date**: November 18, 2025
- **Prepared By**: AI Design Assistant
- **Purpose**: This SDD describes the high-level and detailed design of the cloud-native Octavia platform.

### 1. Introduction

### 1.1 Overview

The Standard Video Translator is a **distributed cloud system**. It uses a microservices-like architecture where the frontend (Next.js) is decoupled from the heavy processing backend (GPU Workers). The system relies on event-driven communication (Webhooks, Redis Streams) to orchestrate the "Magic Mode" pipeline.

### 1.2 Scope

- **In Scope**: Cloud architecture, API design, Worker orchestration, Data flow, Security.
- **Out of Scope**: Local desktop app design.

### 2. System Overview

The system follows a **Event-Driven Cloud Architecture**:

- **Frontend**: Next.js 15 (Vercel) - UI and Uploads.
- **API Gateway**: FastAPI (Fly.io/Render) - Business logic, Auth, Job management.
- **Orchestrator**: Celery + Redis - Task scheduling.
- **Compute**: RunPod Serverless - GPU workers.
- **Storage**: BunnyCDN - Object storage.

### 3. Architectural Design

### 3.1 Design Patterns

- **BFF (Backend for Frontend)**: FastAPI serves as the API for the Next.js frontend.
- **Worker Pattern**: Heavy tasks are offloaded to GPU workers via Celery.
- **Event Sourcing**: Job status updates are pushed via Redis Pub/Sub to SSE.
- **Zero Trust**: All internal components authenticate via JWT/API Keys.

### 3.2 Scalability and Performance Design

- **Horizontal Scaling**: API scales based on request load; Workers scale based on queue depth (KEDA/RunPod Autoscaling).
- **Edge Caching**: Static assets and final videos served via BunnyCDN edge.
- **Spot Instances**: Use spot GPU instances for cost optimization with fallback.

### 3.3 Reliability Design

- **Idempotency**: Webhooks and tasks are idempotent to handle retries.
- **Dead Letter Queues**: Failed tasks are moved to DLQ for analysis.
- **Circuit Breakers**: API handles downstream failures (e.g., Stripe, Clerk) gracefully.

### 4. Component Design

### 4.1 Frontend (Next.js)

- **Responsibilities**: UI rendering, Auth (Clerk), Direct Uploads (tus), SSE subscription.
- **Internal Flow**: User logs in -> Get Upload URL -> Upload to CDN -> Poll/Listen for Job Status.

### 4.2 Backend API (FastAPI)

- **Responsibilities**: Auth validation, Job creation, Webhook handling, Billing.
- **Internal Flow**: Receive BunnyCDN Webhook -> Create Job -> Push to Celery -> Return 200 OK.

### 4.3 Task Orchestrator (Celery/Redis)

- **Responsibilities**: Queue management, Priority routing (Paid vs Free).
- **Internal Flow**: Receive Task -> Route to "gpu-workers" queue -> Monitor Worker Heartbeat.

### 4.4 GPU Worker (RunPod)

- **Responsibilities**: Execute "Magic Mode" pipeline (Demucs, Whisper, XTTS).
- **Internal Flow**: Pull Task -> Download Video -> Process (Diarize/Clone/Translate/Dub) -> Upload Result -> Callback API.

### 5. Data Design

- **Database**: Neon Postgres 17.
    - `users`: Clerk ID, Credits, Plan.
    - `jobs`: Status, Input/Output URLs, Metadata.
    - `voices`: Cloned voice embeddings (encrypted).
- **Storage**: BunnyCDN Volumes.
    - `/uploads`: Raw user files (Lifecycle: 24h).
    - `/results`: Final videos (Lifecycle: Permanent).
    - `/temp`: Intermediate chunks (Lifecycle: Immediate delete).

### 6. Interface Design

- **API**: RESTful JSON (OpenAPI 3.1).
- **Real-time**: Server-Sent Events (SSE) at `/jobs/{id}/events`.
- **Internal**: Redis Streams for Task/Worker comms.

### 7. Edge Cases, Risks & Mitigations

- **Cold Starts**: RunPod workers may take 15-45s to boot. Mitigation: Keep warm pool.
- **Upload Failures**: Client-side retry with tus protocol.
- **GPU OOM**: Catch CUDA OOM, retry with smaller batch size or higher VRAM pod.
