# Local Testing Guide — SSE & Job Progress Tracking

## What We've Built

1. **Job Progress Tracking** — Jobs now track real-time progress with phases (pending, transcribing, translating, synthesizing, uploading, completed, failed)
2. **SSE Streaming** — Real-time job status updates via Server-Sent Events at `/api/v1/jobs/{job_id}/stream`
3. **Polling Endpoint** — Alternative JSON polling at `/api/v1/jobs/{job_id}/status` for clients that don't support SSE
4. **Frontend Integration Tests** — Comprehensive test suite validating SSE behavior, progress updates, phase transitions, error handling, and auth

## Quick Start (5 minutes)

### 1. Setup & Run Backend

```powershell
# Navigate to backend
cd octavia-backend

# Create database (if not exists)
python create_tables.py

# Start the backend with hot-reload
uvicorn app.main:app --reload --port 8001
```

Backend will be available at `http://localhost:8001`

### 2. Run Frontend Integration Tests

In a separate terminal:

```powershell
cd octavia-backend

# Run all SSE integration tests
pytest test_frontend_sse_integration.py -v

# Run a specific test
pytest test_frontend_sse_integration.py::TestFrontendSSEIntegration::test_sse_connection_lifecycle -v

# Run with output capture to see progress
pytest test_frontend_sse_integration.py -s
```

**Expected Results:** 9 tests should pass (1 currently passes; others may fail if JWT secret mismatch — see troubleshooting below)

### 3. Test SSE Manually with cURL/Browser

```powershell
# In PowerShell, create a test token
$token = (python -c "from app.core.security import create_access_token; import sys; sys.stdout.write(create_access_token({'sub': 'test-user-1'}))")

# Stream job progress (replace JOB_ID with actual UUID)
$headers = @{Authorization = "Bearer $token"}
Invoke-WebRequest -Uri "http://localhost:8001/api/v1/jobs/{JOB_ID}/stream" -Headers $headers -ContentType "text/event-stream"

# Or use curl
curl -H "Authorization: Bearer $token" http://localhost:8001/api/v1/jobs/{JOB_ID}/stream
```

### 4. Test Polling Endpoint

```powershell
# Get current job status (JSON)
$headers = @{Authorization = "Bearer $token"}
$response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/jobs/{JOB_ID}/status" -Headers $headers -Method Get
$response | ConvertTo-Json | Write-Host
```

## What to Look For

### ✅ Success Indicators

- Backend starts without errors on port 8001
- Tests pass all 9 assertions (lifecycle, progress, phases, errors, polling consistency, rapid updates, format, auth)
- SSE endpoint returns HTTP 200 and streams `data: {...}` lines as JSON
- Polling endpoint returns HTTP 200 with full job object including: `job_id`, `status`, `phase`, `progress_percentage`, `current_step`, `started_at`, `completed_at`, `error_message`, `output_file`
- Auth rejection test properly returns 401/403 when no token provided

### 🔧 Common Issues & Fixes

#### Issue 1: "Invalid token" / 401 responses in tests

**Root Cause:** JWT secret mismatch between token generation (`app.core.security`) and token validation (`app.upload_routes`)

**Fix:**
```powershell
# Ensure both modules use same secret from environment
$env:JWT_SECRET = "your-secret-key-here"  # Set same key for both

# OR: Verify core/security.py and upload_routes.py both import from app.core.security
```

#### Issue 2: Database errors ("Job table doesn't exist")

**Fix:**
```powershell
python create_tables.py
```

#### Issue 3: Module not found errors

**Fix:**
```powershell
# Ensure venv is activated
.\.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements-core.txt
```

#### Issue 4: Port 8001 already in use

**Fix:**
```powershell
# Use different port
uvicorn app.main:app --reload --port 8002
```

## Test Coverage

| Test | Purpose | Status |
|------|---------|--------|
| `test_sse_connection_lifecycle` | SSE connects and streams initial data | Should pass |
| `test_sse_progress_percentage_changes` | Progress % updates stream correctly | Should pass |
| `test_sse_phase_transitions` | Phase changes (PENDING→TRANSCRIBING→COMPLETED) stream | Should pass |
| `test_sse_error_scenarios` | Error states and error_message field transmitted | Should pass |
| `test_polling_endpoint_consistency_with_sse` | Polling returns same data as SSE | Should pass |
| `test_sse_job_not_found` | Non-existent job returns 404 | Should pass |
| `test_sse_multiple_progress_updates_rapid` | Handles rapid updates without dropping | Should pass |
| `test_sse_response_format_completeness` | All required fields present in response | Should pass |
| `test_sse_auth_required` | Endpoints reject requests without valid JWT | Should pass |

## Next Steps

1. **If all tests pass:** SSE integration is ready for frontend
2. **If tests fail on auth:** Verify `SECRET_KEY` environment variable is set consistently
3. **If SSE doesn't stream:** Check `app/sse_routes.py` has router registration in `app/main.py`
4. **For production:** Update `your-secret-key-change-in-production` to actual secret in `app/core/security.py`

## Frontend Integration

Once tests pass, frontend can connect via:

```javascript
// SSE Example
const eventSource = new EventSource(`/api/v1/jobs/${jobId}/stream`, {
  headers: { Authorization: `Bearer ${token}` }
});

eventSource.onmessage = (event) => {
  const jobUpdate = JSON.parse(event.data);
  console.log('Phase:', jobUpdate.phase, 'Progress:', jobUpdate.progress_percentage);
  
  if (['completed', 'failed'].includes(jobUpdate.status)) {
    eventSource.close();
  }
};

// Polling Example
fetch(`/api/v1/jobs/${jobId}/status`, {
  headers: { Authorization: `Bearer ${token}` }
})
.then(r => r.json())
.then(jobStatus => console.log('Status:', jobStatus));
```

See `docs/JOB_PROGRESS_TRACKING.js` for full frontend integration examples and React hooks.
