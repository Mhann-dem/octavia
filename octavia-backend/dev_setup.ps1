<#
PowerShell dev setup script for octavia-backend

Usage: from `octavia-backend` folder run:
  .\dev_setup.ps1

This script:
- Upgrades pip/build tools
- Installs `requirements-core.txt`
- Prompts and installs PyTorch (CPU or CUDA wheels)
- Offers to install `ffmpeg` via Chocolatey if available
- Installs `faster-whisper` (recommended) or `openai-whisper` on request
- Runs `create_tables.py` and optionally starts the dev server
#>

function Run-ExitCheck {
    param([string]$cmd)
    Write-Host "Running: $cmd"
    & powershell -NoProfile -Command $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Error ("Command failed with exit code {0}: {1}" -f $LASTEXITCODE, $cmd)
        return $false
    }
    return $true
}

Write-Host "=== Octavia backend dev setup ==="

# 1) Upgrade pip and build tools
Write-Host "Upgrading pip, setuptools, wheel, setuptools_scm..."
python -m pip install --upgrade pip setuptools wheel setuptools_scm
if ($LASTEXITCODE -ne 0) { Write-Error 'Failed to upgrade pip/build tools'; exit 1 }

# 2) Install core Python dependencies
if (-Not (Test-Path '.\requirements-core.txt')) {
    Write-Error "requirements-core.txt not found in current folder ($(Get-Location)). Please run from octavia-backend folder."; exit 1
}
Write-Host "Installing core dependencies from requirements-core.txt (this may take a few minutes)..."
pip install -r .\requirements-core.txt
if ($LASTEXITCODE -ne 0) { Write-Error 'Failed to install core dependencies'; exit 1 }

# 3) Prompt for PyTorch install choice
Write-Host "PyTorch is required for Whisper/faster-whisper. Choose an option:"
Write-Host '  1) CPU-only'
Write-Host '  2) CUDA 11.8 (common)'
Write-Host '  3) CUDA 12.2 (newer GPUs)'
$choice = Read-Host 'Enter 1, 2, or 3 (default 1)'
if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '1' }

if ($choice -eq '1') {
    Write-Host 'Installing CPU-only PyTorch wheels...'
    pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
} elseif ($choice -eq '2') {
    Write-Host 'Installing PyTorch for CUDA 11.8 (cu118)...'
    pip install --index-url https://download.pytorch.org/whl/cu118 torch torchvision torchaudio
} elseif ($choice -eq '3') {
    Write-Host 'Installing PyTorch for CUDA 12.2 (cu122)...'
    pip install --index-url https://download.pytorch.org/whl/cu122 torch torchvision torchaudio
} else {
    Write-Host 'Unknown choice, defaulting to CPU.'
    pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
}
if ($LASTEXITCODE -ne 0) { Write-Warning 'PyTorch install failed. Inspect output and try the appropriate wheel from https://pytorch.org/get-started/locally/'; }

# 4) ffmpeg install (optional)
Write-Host 'ffmpeg is required for media processing. Do you want to attempt installing via Chocolatey? (y/N)'
$ff = Read-Host 'Install ffmpeg via choco?'
if ($ff -match '^[Yy]') {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install ffmpeg -y
        if ($LASTEXITCODE -ne 0) { Write-Warning 'choco install ffmpeg failed. Please install ffmpeg manually and add to PATH.' }
    } else {
        Write-Warning 'Chocolatey not found. Please install Chocolatey first or install ffmpeg manually from https://www.gyan.dev/ffmpeg/builds/'
    }
} else {
    Write-Host 'Skipping ffmpeg install. Ensure ffmpeg is installed and on PATH.'
}

# 5) Whisper / faster-whisper install
Write-Host 'Install transcription package: (1) faster-whisper (recommended), (2) openai-whisper (may build from source).'
$w = Read-Host 'Enter 1 or 2 (default 1)'
if ([string]::IsNullOrWhiteSpace($w)) { $w = '1' }
if ($w -eq '1') {
    pip install faster-whisper
    if ($LASTEXITCODE -ne 0) { Write-Warning 'faster-whisper install failed; you may try openai-whisper instead.' }
} else {
    pip install -r .\requirements-ml.txt
    if ($LASTEXITCODE -ne 0) { Write-Warning 'openai-whisper (or ML requirements) install failed. Consider installing PyTorch first or use faster-whisper.' }
}

# 6) Final steps: DB create and start server
Write-Host 'Creating DB tables (SQLite dev fallback) using create_tables.py...'
python .\create_tables.py
if ($LASTEXITCODE -ne 0) { Write-Warning 'create_tables.py failed. Check earlier errors.' }

Write-Host "Setup complete. Start the dev server now? (Y/n)"
$start = Read-Host 'Start uvicorn now?'
if ($start -match '^[Nn]') { Write-Host 'Skipping server start. You can run: uvicorn app.main:app --reload --port 8001' ; exit 0 }

Write-Host 'Starting uvicorn on port 8001...'
uvicorn app.main:app --reload --port 8001
