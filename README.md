# Video Subtitle Creator

AI-powered video subtitle creation app that automatically transcribes videos and burns stylized subtitles.

## Features

- 🎬 Upload MP4 videos (max 5 minutes)
- 🤖 AI transcription with OpenAI Whisper (turbo model)
- 🎨 3 subtitle styles: Yellow Highlight, Multi-color Pop, Clean Outline
- 📝 Word-by-word or sentence display modes
- 📍 Customizable subtitle position (top, center, bottom)
- ⚡ Subtitles burned directly into video

## Quick Start (Docker)

```bash
# Build and run
docker-compose up --build

# Access the app
open http://localhost:3000
```

## Development Setup

### Backend

```bash
cd backend

# Install uv (if not installed)
pip install uv

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install -e .

# Run the server
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Requirements

- Docker & Docker Compose (for containerized setup)
- Python 3.10+ (for local development)
- Node.js 18+ (for local development)
- FFmpeg (for video processing)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload video and start processing |
| `/status/{job_id}` | GET | Check processing status |
| `/download/{job_id}` | GET | Download processed video |
| `/styles` | GET | Get available style options |
| `/health` | GET | Health check |

## License

MIT
