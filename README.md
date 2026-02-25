# Video Shorts MVP

Automatically convert long-form landscape videos (16:9) into viral vertical shorts (9:16) using AI-powered face tracking and LLM hook detection.

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  Next.js     │────▶│  FastAPI Backend                               │
│  Frontend    │◀────│                                              │
│  (Port 3000) │     │  Step 1: Ingest & Transcribe (Whisper)       │
└─────────────┘     │  Step 2: Hook Curation (Claude / GPT-4o)     │
                     │  Step 3: Vision & Crop (MediaPipe + FFmpeg)  │
                     │  (Port 8000)                                 │
                     └──────────────────────────────────────────────┘
```

## Quick Start

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Requirements
- Python 3.10+
- Node.js 18+
- FFmpeg (installed and on PATH)
