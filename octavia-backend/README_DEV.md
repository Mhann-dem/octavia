# Development setup (Windows) — octavia-backend

This file documents the recommended development installation steps on Windows (PowerShell). We split core dependencies from heavy ML/media packages to avoid long builds failing early.

1) Upgrade pip / build tools

```powershell
python -m pip install --upgrade pip setuptools wheel setuptools_scm
```

2) Install core backend dependencies (already provided in `requirements-core.txt`)

```powershell
pip install -r .\\requirements-core.txt
```

3) Install PyTorch (choose the correct command for your environment)

- Visit https://pytorch.org/get-started/locally/ and copy the pip command for your CUDA or CPU setup.
- Example (CPU-only):

```powershell
pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
```

- Example (CUDA 12.2, adjust if you have different CUDA):

```powershell
pip install --index-url https://download.pytorch.org/whl/cu122 torch torchvision torchaudio
```

4) Install ffmpeg

- Option A (Chocolatey):

```powershell
choco install ffmpeg -y
```

- Option B: Download a static build from https://www.gyan.dev/ffmpeg/builds/ and add to `PATH`.

5) Install ML/media packages (whisper or faster-whisper)

- Recommended (Windows-friendly):

```powershell
pip install faster-whisper
```

- If you prefer OpenAI's whisper (may build from source):

```powershell
pip install -r .\\requirements-ml.txt
# or
pip install git+https://github.com/openai/whisper.git
```

Notes and troubleshooting
- If you see build errors when installing `openai-whisper`, make sure PyTorch is installed first; many errors are due to missing compatible `torch` wheel.
- If a package complains about `__version__` or metadata, upgrade `setuptools_scm` as shown above.
- For large model inference consider `faster-whisper` or running transcription in a Linux container where builds are typically smoother.

6) Running the app locally

```powershell
# create DB tables (SQLite dev fallback)
python .\\create_tables.py

# run the backend
uvicorn app.main:app --reload --port 8001
```

7) Optional: install full `requirements.txt` later

```powershell
# Once ML deps are resolved you can install the full list
pip install -r .\\requirements.txt
```

If you'd like, I can also:
- Generate a small PowerShell script that automates these steps and prompts you for CPU vs GPU.
- Replace `openai-whisper` in `requirements.txt` with a commented note pointing to `requirements-ml.txt`.
