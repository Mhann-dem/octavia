# Run transcription test
# Starts backend server and runs test script

$BackendDir = "C:\Users\robbd\Documents\Git\octavia\octavia-backend"
$PORT = 8001

Write-Host "Starting Octavia backend server..." -ForegroundColor Cyan
Set-Location $BackendDir

# Kill any existing Python processes on port 8001
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Handles -gt 0 } | ForEach-Object {
    Write-Host "Stopping existing Python process (PID: $($_.Id))..." -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

# Start backend in a detached process
$ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
$ProcessInfo.FileName = "python"
$ProcessInfo.Arguments = "-m uvicorn app.main:app --host 127.0.0.1 --port $PORT"
$ProcessInfo.UseShellExecute = $false
$ProcessInfo.RedirectStandardOutput = $true
$ProcessInfo.RedirectStandardError = $true
$ProcessInfo.CreateNoWindow = $true

$Process = [System.Diagnostics.Process]::Start($ProcessInfo)
$BackendPID = $Process.Id

Write-Host "Backend started (PID: $BackendPID)" -ForegroundColor Green

# Wait for server to start
Write-Host "Waiting for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if server is running
try {
    $HealthCheck = Invoke-WebRequest -Uri "http://localhost:$PORT/docs" -ErrorAction SilentlyContinue
    Write-Host "✓ Backend is ready" -ForegroundColor Green
}
catch {
    Write-Host "✗ Backend failed to start" -ForegroundColor Red
    Stop-Process -Id $BackendPID -Force -ErrorAction SilentlyContinue
    exit 1
}

# Run transcription test
Write-Host "`nRunning transcription test..." -ForegroundColor Cyan
python test_transcription_flow.py
$TestResult = $LASTEXITCODE

# Stop backend
Write-Host "`nStopping backend..." -ForegroundColor Yellow
Stop-Process -Id $BackendPID -Force -ErrorAction SilentlyContinue

if ($TestResult -eq 0) {
    Write-Host "`n✓ Test completed successfully" -ForegroundColor Green
}
else {
    Write-Host "`n✗ Test failed" -ForegroundColor Red
}

exit $TestResult
