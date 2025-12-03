#!/usr/bin/env pwsh
# Start backend in detached process
$backendProc = Start-Process -FilePath "python" `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8001", "--host", "127.0.0.1" `
  -WorkingDirectory "C:\Users\robbd\Documents\Git\octavia\octavia-backend" `
  -NoNewWindow -PassThru

Write-Host "Backend PID: $($backendProc.Id)"
Start-Sleep -Seconds 3

# Run the upload test
Write-Host "`nRunning upload test..."
& python clear_users.py
& python test_upload_flow.py
