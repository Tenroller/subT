# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SubT is an AI-powered video subtitle creation app that automatically transcribes videos and burns stylized subtitles into them. The project consists of:
- **Backend**: FastAPI Python application with Whisper AI for transcription
- **Frontend**: React + Vite SPA with real-time subtitle preview
- **Docker**: Containerized deployment with docker-compose

## Development Commands

### Backend (FastAPI)

```bash
cd backend

# Install dependencies (using uv package manager)
uv pip install -e .

# Run development server
uvicorn main:app --reload

# Run in production (Docker)
docker compose up backend --build
```

The backend runs on port **4569** by default.

### Frontend (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Run development server (port 5173)
npm run dev

# Build for production
npm run build

# Lint
npm run lint

# Preview production build
npm run preview
```

### Full Stack (Docker)

```bash
# Build and start all services
docker compose up --build

# Access frontend at http://localhost:3000
# Backend accessible internally at http://backend:4569
```

## Architecture

### Backend Structure

The backend follows a modular service architecture:

1. **main.py** - FastAPI app with endpoints and job orchestration
   - Handles file upload, validation (MP4 magic bytes, duration, size)
   - Manages background job processing with concurrency control (max 3 concurrent jobs globally)
   - Per-IP rate limiting (5 uploads/min, 60 status checks/min) and job caps (3 active jobs per IP)
   - Automatic file cleanup (1 hour retention)

2. **transcriber.py** - Whisper AI integration
   - Uses OpenAI Whisper "turbo" model for speech-to-text
   - Provides word-level timestamps via `transcribe_with_language()`
   - Returns `Segment` objects containing `Word` objects with precise timing
   - Model loading is async-locked (not thread-safe)

3. **subtitle_generator.py** - ASS subtitle generation
   - Creates styled ASS files with word-by-word or sentence display modes
   - Supports 3 styles: yellow_highlight, multicolor_pop, clean_outline
   - Handles custom colors (hex → ASS BGR conversion)
   - Also generates standard SRT files via `generate_srt()`

4. **video_processor.py** - FFmpeg wrapper
   - `burn_subtitles()`: Hardcodes ASS subtitles into video using FFmpeg
   - `get_duration()`: Video validation using ffprobe
   - `get_dimensions()`: Required for ASS subtitle positioning

5. **translator.py** - Argos Translate integration
   - Provides subtitle translation between languages
   - Downloads language packages on-demand

### Processing Pipeline

The video processing flow (see `process_video_task()` in main.py:395):

1. **Transcription** (JobStatus.TRANSCRIBING) - Extract audio, transcribe with Whisper
2. **Translation** (JobStatus.TRANSLATING) - Optional translation if target_language specified
3. **SRT Generation** - Create standard SRT file for download
4. **Subtitle Generation** (JobStatus.GENERATING_SUBTITLES) - Generate styled ASS file
5. **Video Processing** (JobStatus.PROCESSING_VIDEO) - Burn ASS into video with FFmpeg

Job progress updates: 10% → 30% → 50% → 70% → 100%

### Frontend Structure

Single-page React app (frontend/src/App.jsx):
- **LivePreview component** - Real-time subtitle preview with animated word highlighting
- **Four-step wizard**: Upload → Style → Display Config → Advanced Options
- **Polling mechanism** - Checks `/status/{job_id}` every 10 seconds during processing
- **API integration** - Uses `API_URL` env variable (dev: localhost:4569, prod: /api via nginx)

### Docker Setup

- **Backend container**: Persists Whisper model cache, uploads, and outputs across restarts
- **Frontend container**: Nginx serves static build and proxies `/api/*` to backend
- **Health checks**: Backend health endpoint checked before frontend starts
- **Network**: Custom bridge network `subt-network` for inter-service communication

## Key Design Decisions

### Concurrency & Rate Limiting

- **Global semaphore**: Max 3 concurrent video processing jobs to prevent resource exhaustion
- **Transcription lock**: Whisper model is not thread-safe; serialized access via asyncio.Lock
- **Per-IP tracking**: `ip_active_jobs` dict prevents users from flooding the queue (3 active jobs max)
- **Rate limits**: SlowAPI middleware limits upload (5/min), status checks (60/min), downloads (20/min)

### Subtitle Styling

ASS format uses BGR color order (&HAABBGGRR), not RGB. The frontend uses RGB hex colors which are converted via `hex_to_ass_color()` in subtitle_generator.py:136.

**Yellow Highlight style** uses ASS override tags:
- `\1c` = primary text color
- `\3c` = outline/border color
- `\xbord/\ybord` = horizontal/vertical border for "box" effect around highlighted word

### File Management

- Uploaded videos stored in `uploads/` with UUID filenames
- Processed videos in `outputs/` as `{job_id}_subtitled.mp4`
- ASS files in `outputs/` as `{job_id}.ass`
- SRT files in `outputs/` as `{job_id}.srt`
- Input files deleted after processing succeeds/fails
- Output files deleted 5 minutes after download or 1 hour after creation (periodic cleanup)

### Validation & Security

- **MP4 magic bytes** checked at offset 4 (`ftyp` box signature) in `_validate_mp4_magic()`
- **UUID v4 validation** for job IDs to prevent path traversal
- **Hex color validation** for custom colors (#RRGGBB format)
- **Language code validation** against ALLOWED_LANGUAGE_CODES
- **Size limits**: 500MB hard cap, 5-minute max duration
- **CORS**: Wildcard origin (*) allowed since no credentials used; restrict via ALLOWED_ORIGIN env var in production

## Environment Variables

- **ALLOWED_ORIGIN** (backend): CORS origin restriction (default: "*")
- **VITE_API_URL** (frontend build): Backend API URL for production

## Dependencies

### Backend (Python 3.10+)
- fastapi, uvicorn - Web framework
- openai-whisper - Speech-to-text with word timestamps
- pysubs2 - ASS/SRT subtitle manipulation
- ffmpeg-python - Video processing wrapper (requires FFmpeg binary)
- argostranslate - Offline translation
- torch, torchaudio - Whisper model inference
- slowapi - Rate limiting

### Frontend (Node 18+)
- react 19 - UI framework
- vite - Build tool and dev server

## Notes

- Whisper model is downloaded to `~/.cache/whisper/` on first run (cached in Docker volume)
- Translation language packages download on-demand when first requested
- Frontend preview simulates subtitle appearance with CSS animations; actual output uses FFmpeg ASS rendering
- Job status is in-memory only (lost on restart); for production, consider Redis or database storage
- Use the docker-compose.yml file to build and run the application
- Use the MCP tools available for testing and documentation search