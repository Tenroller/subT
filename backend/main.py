"""
Video Subtitle Creation App - Backend
FastAPI application for video transcription and subtitle generation
"""
import os
import time
import re
import uuid
import asyncio
import hashlib
from pathlib import Path
from typing import Optional
from enum import Enum

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import cachetools

# Local imports
from transcriber import Transcriber
from subtitle_generator import SubtitleGenerator, SubtitleStyle, DisplayMode, Position, generate_srt
from video_processor import VideoProcessor
from translator import get_translator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
MAX_VIDEO_DURATION = 300          # 5 minutes in seconds
MAX_FILE_SIZE = 500 * 1024 * 1024 # 500 MB hard cap
ALLOWED_EXTENSIONS = {".mp4"}
MAX_CONCURRENT_JOBS_PER_IP = 3   # max active jobs from the same IP at once
MAX_JOB_HISTORY = 1000           # Maximum jobs to keep in memory
JOB_TTL_SECONDS = 86400          # 24 hours TTL for completed jobs

# Allowed language codes (must match translator.get_available_languages())
ALLOWED_LANGUAGE_CODES = {
    "en", "es", "fr", "de", "pt", "it", "zh", "ja", "ko", "ru", "ar"
}

# Hex colour regex: exactly #RRGGBB
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# UUID v4 regex for job-ID validation
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# MP4 magic-bytes signatures (ftyp box at offset 4)
MP4_SIGNATURES = [
    b"ftyp",   # generic ISO Base Media / MP4
]

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Video Subtitle Creator",
    description="Upload videos and generate stylized burned-in subtitles",
    version="1.0.0",
)

# Attach rate-limit exceeded handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — credentials are not used so wildcard origin is safe here.
# In production you can restrict this to your actual frontend domain via the
# ALLOWED_ORIGIN environment variable.
_allowed_origin = os.environ.get("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_allowed_origin],
    allow_credentials=False,   # must be False when origin is "*"
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Initialize services
transcriber: Optional[Transcriber] = None
video_processor = VideoProcessor()

# Concurrency control — limit to 3 concurrent processing jobs globally
processing_semaphore = asyncio.Semaphore(3)

# Transcription concurrency — allow 2 concurrent transcriptions for better throughput
transcription_semaphore = asyncio.Semaphore(2)

# Transcription result cache — LRU cache with file hash lookup (100MB limit, ~20 items)
transcription_cache = cachetools.LRUCache(maxsize=20)

# Per-IP active job tracking  {ip: set_of_job_ids}
ip_active_jobs: dict[str, set] = {}


# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------
class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    TRANSCRIBING = "transcribing"
    TRANSLATING = "translating"
    GENERATING_SUBTITLES = "generating_subtitles"
    PROCESSING_VIDEO = "processing_video"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    id: str
    status: JobStatus
    progress: int = 0
    error: Optional[str] = None
    output_file: Optional[str] = None
    srt_file: Optional[str] = None
    queue_position: Optional[int] = None
    client_ip: Optional[str] = None  # stored internally, never returned to client
    created_at: float = 0  # Unix timestamp for TTL cleanup


# In-memory job storage
jobs: dict[str, Job] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _validate_job_id(job_id: str) -> None:
    """Raise 400 if job_id is not a valid UUID v4."""
    if not UUID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format.")


def _validate_hex_color(value: Optional[str], field_name: str) -> None:
    """Raise 422 if value is present but not a valid #RRGGBB hex colour."""
    if value is not None and not HEX_COLOR_RE.match(value):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {field_name}: must be a hex colour like #FFFFFF.",
        )


def _validate_language(code: Optional[str]) -> None:
    """Raise 422 if code is present but not in the allowed set."""
    if code is not None and code not in ALLOWED_LANGUAGE_CODES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language code '{code}'. "
                   f"Allowed: {sorted(ALLOWED_LANGUAGE_CODES)}",
        )


def _validate_mp4_magic(data: bytes) -> bool:
    """Return True if the first bytes look like an MP4/ISO-BMFF container."""
    # The ftyp box starts at byte offset 4 in a valid MP4
    if len(data) < 12:
        return False
    return data[4:8] in MP4_SIGNATURES


def _get_client_ip(request: Request) -> str:
    """Return the real client IP, honouring X-Forwarded-For from nginx."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of file for cache key

    Args:
        file_path: Path to file

    Returns:
        Hex digest of file hash
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def _register_active_job(ip: str, job_id: str) -> None:
    ip_active_jobs.setdefault(ip, set()).add(job_id)


def _unregister_active_job(ip: str, job_id: str) -> None:
    if ip in ip_active_jobs:
        ip_active_jobs[ip].discard(job_id)
        if not ip_active_jobs[ip]:
            del ip_active_jobs[ip]


def _count_active_jobs(ip: str) -> int:
    """Count jobs from this IP that are not yet completed or failed."""
    terminal = {JobStatus.COMPLETED, JobStatus.FAILED}
    job_ids = ip_active_jobs.get(ip, set())
    return sum(
        1 for jid in job_ids
        if jid in jobs and jobs[jid].status not in terminal
    )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Load Whisper model and start cleanup loop"""
    global transcriber
    print("Loading Whisper turbo model... This may take a moment on first run.")
    transcriber = Transcriber(model_name="turbo")
    print("Whisper model loaded successfully!")
    asyncio.create_task(periodic_cleanup())


# ---------------------------------------------------------------------------
# Cleanup helpers
# ---------------------------------------------------------------------------
async def cleanup_file_after_delay(path: str, delay: int = 300):
    """Wait for delay seconds and then delete the file"""
    await asyncio.sleep(delay)
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"Cleaned up file: {path}")

        # Also clean up associated ass file
        ass_path = path.replace("_subtitled.mp4", ".ass")
        if os.path.exists(ass_path):
            os.remove(ass_path)

    except Exception as e:
        print(f"Error cleaning up file {path}: {e}")


async def periodic_cleanup():
    """Periodically clean up stale files (older than 1 hour) and expired jobs"""
    while True:
        try:
            await asyncio.sleep(600)

            now = time.time()
            max_age = 3600  # 1 hour

            # Clean up stale files
            for p in OUTPUT_DIR.glob("*"):
                if p.is_file() and now - p.stat().st_mtime > max_age:
                    try:
                        p.unlink()
                        print(f"Auto-cleaned stale file: {p}")
                    except Exception as e:
                        print(f"Error deleting {p}: {e}")

            for p in UPLOAD_DIR.glob("*"):
                if p.is_file() and now - p.stat().st_mtime > max_age:
                    try:
                        p.unlink()
                    except Exception as e:
                        print(f"Error deleting {p}: {e}")

            # Clean up expired jobs (TTL-based)
            expired_jobs = [
                job_id for job_id, job in jobs.items()
                if job.created_at > 0 and now - job.created_at > JOB_TTL_SECONDS
            ]
            for job_id in expired_jobs:
                job = jobs.pop(job_id, None)
                if job and job.client_ip:
                    _unregister_active_job(job.client_ip, job_id)
                print(f"Cleaned up expired job: {job_id}")

            # Enforce maximum job history (circular buffer)
            if len(jobs) > MAX_JOB_HISTORY:
                # Sort by creation time and remove oldest
                sorted_jobs = sorted(
                    jobs.items(),
                    key=lambda item: item[1].created_at
                )
                to_remove = len(jobs) - MAX_JOB_HISTORY
                for job_id, job in sorted_jobs[:to_remove]:
                    jobs.pop(job_id, None)
                    if job.client_ip:
                        _unregister_active_job(job.client_ip, job_id)
                    print(f"Removed old job from history: {job_id}")

        except Exception as e:
            print(f"Cleanup loop error: {e}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": transcriber is not None}


@app.post("/upload")
@limiter.limit("5/minute")
async def upload_video(
    request: Request,
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    style: str = Form("yellow_highlight"),
    display_mode: str = Form("word"),
    position: str = Form("bottom"),
    text_color: str = Form(None),
    highlight_color: str = Form(None),
    target_language: str = Form(None),
    fast_mode: bool = Form(False),
):
    """
    Upload a video and start subtitle generation

    - **video**: MP4 file, max 5 minutes / 500 MB
    - **style**: yellow_highlight, multicolor_pop, or clean_outline
    - **display_mode**: word (word-by-word) or sentence
    - **position**: top, center, or bottom
    - **text_color**: Custom text color in hex format (e.g., #FFFFFF)
    - **highlight_color**: Custom highlight color in hex format (e.g., #FFD700)
    - **target_language**: Target language code for translation (e.g., "es", "fr")
    - **fast_mode**: Skip video re-encoding for 50-100x speedup (larger output files)
    """
    client_ip = _get_client_ip(request)

    # ── 1. Per-IP concurrent job cap ────────────────────────────────────────
    if _count_active_jobs(client_ip) >= MAX_CONCURRENT_JOBS_PER_IP:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You already have {MAX_CONCURRENT_JOBS_PER_IP} active jobs. "
                "Please wait for them to finish before submitting more."
            ),
        )

    # ── 2. File extension check ──────────────────────────────────────────────
    file_ext = Path(video.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only {', '.join(ALLOWED_EXTENSIONS)} allowed.",
        )

    # ── 3. File size guard (check Content-Length before reading) ────────────
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    # ── 4. Read file content ─────────────────────────────────────────────────
    content = await video.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    # ── 5. MIME type validation (magic bytes) ───────────────────────────────
    if not _validate_mp4_magic(content):
        raise HTTPException(
            status_code=400,
            detail="Invalid file content. File does not appear to be a valid MP4.",
        )

    # ── 6. Input validation ──────────────────────────────────────────────────
    _validate_hex_color(text_color, "text_color")
    _validate_hex_color(highlight_color, "highlight_color")
    _validate_language(target_language)

    # ── 7. Parse subtitle options ────────────────────────────────────────────
    try:
        subtitle_style = SubtitleStyle(style)
        subtitle_display_mode = DisplayMode(display_mode)
        subtitle_position = Position(position)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ── 8. Save file ─────────────────────────────────────────────────────────
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}{file_ext}"

    # Async file write to avoid blocking event loop
    await asyncio.to_thread(lambda: input_path.write_bytes(content))

    # ── 9. Validate video duration ───────────────────────────────────────────
    try:
        # Async FFprobe to avoid blocking
        duration = await asyncio.to_thread(video_processor.get_duration, str(input_path))
        if duration > MAX_VIDEO_DURATION:
            await asyncio.to_thread(lambda: input_path.unlink(missing_ok=True))
            raise HTTPException(
                status_code=400,
                detail=f"Video too long. Maximum duration is {MAX_VIDEO_DURATION // 60} minutes.",
            )
    except HTTPException:
        raise
    except Exception:
        await asyncio.to_thread(lambda: input_path.unlink(missing_ok=True))
        raise HTTPException(status_code=400, detail="Invalid video file.")

    # ── 10. Create job and start background processing ───────────────────────
    job = Job(id=job_id, status=JobStatus.QUEUED, client_ip=client_ip, created_at=time.time())
    jobs[job_id] = job
    _register_active_job(client_ip, job_id)

    background_tasks.add_task(
        process_video_task,
        job_id,
        str(input_path),
        subtitle_style,
        subtitle_display_mode,
        subtitle_position,
        text_color,
        highlight_color,
        target_language,
        client_ip,
        fast_mode,
    )

    return {"job_id": job_id, "status": job.status}


async def process_video_task(
    job_id: str,
    input_path: str,
    style: SubtitleStyle,
    display_mode: DisplayMode,
    position: Position,
    text_color: Optional[str] = None,
    highlight_color: Optional[str] = None,
    target_language: Optional[str] = None,
    client_ip: Optional[str] = None,
    fast_mode: bool = False,
):
    """Background task to process video with subtitles"""
    job = jobs[job_id]
    output_path = OUTPUT_DIR / f"{job_id}_subtitled.mp4"
    subtitle_path = OUTPUT_DIR / f"{job_id}.ass"
    srt_path = OUTPUT_DIR / f"{job_id}.srt"

    try:
        async with processing_semaphore:
            # Step 1: Transcribe (with caching)
            job.status = JobStatus.TRANSCRIBING
            job.progress = 10

            # Check cache first
            file_hash = _get_file_hash(input_path)
            cache_key = f"{file_hash}:{target_language or 'auto'}"

            cached_result = transcription_cache.get(cache_key)
            if cached_result:
                print(f"Cache hit for transcription: {cache_key}")
                segments, detected_language = cached_result
            else:
                # Transcribe with concurrency control (allow 2 concurrent)
                async with transcription_semaphore:
                    segments, detected_language = await asyncio.to_thread(
                        transcriber.transcribe_with_language,
                        input_path,
                    )

                # Cache the result
                transcription_cache[cache_key] = (segments, detected_language)
                print(f"Cached transcription result: {cache_key}")

            job.progress = 30

            # Step 2: Translate if needed
            if target_language and target_language != detected_language:
                job.status = JobStatus.TRANSLATING
                job.progress = 35

                translator = get_translator()
                segments = await asyncio.to_thread(
                    translator.translate_segments,
                    segments,
                    detected_language,
                    target_language,
                )

                job.progress = 50
            else:
                job.progress = 50

            # Step 3: Generate SRT
            generate_srt(segments, str(srt_path))
            job.srt_file = str(srt_path)

            # Step 4: Generate styled ASS subtitles
            job.status = JobStatus.GENERATING_SUBTITLES

            generator = SubtitleGenerator(
                style=style,
                display_mode=display_mode,
                position=position,
                text_color=text_color,
                highlight_color=highlight_color,
            )

            width, height = video_processor.get_dimensions(input_path)
            await asyncio.to_thread(
                generator.generate,
                segments,
                str(subtitle_path),
                width,
                height
            )

            job.progress = 70

            # Step 5: Burn subtitles into video
            job.status = JobStatus.PROCESSING_VIDEO

            await asyncio.to_thread(
                video_processor.burn_subtitles,
                input_path,
                str(subtitle_path),
                str(output_path),
                fast_mode,
            )

            job.progress = 100
            job.status = JobStatus.COMPLETED
            job.output_file = str(output_path)

        # Cleanup input file
        if os.path.exists(input_path):
            os.remove(input_path)

    except Exception as e:
        job.status = JobStatus.FAILED
        # Log the real error server-side but return a generic message to clients
        print(f"[ERROR] Job {job_id} failed: {e}")
        job.error = "Processing failed. Please try again with a different video."
        if os.path.exists(input_path):
            os.remove(input_path)
    finally:
        # Always unregister from per-IP tracking
        if client_ip:
            _unregister_active_job(client_ip, job_id)


@app.get("/status/{job_id}")
@limiter.limit("60/minute")
async def get_job_status(request: Request, job_id: str):
    """Get the status of a processing job"""
    _validate_job_id(job_id)

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
    }


@app.get("/download/{job_id}")
@limiter.limit("20/minute")
async def download_video(request: Request, job_id: str, background_tasks: BackgroundTasks):
    """Download the processed video"""
    _validate_job_id(job_id)

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Video not ready. Current status: {job.status}",
        )

    if not job.output_file or not os.path.exists(job.output_file):
        raise HTTPException(status_code=404, detail="Output file not found")

    background_tasks.add_task(cleanup_file_after_delay, job.output_file, 300)

    return FileResponse(
        job.output_file,
        media_type="video/mp4",
        filename=f"subtitled_{job_id}.mp4",
    )


@app.get("/download-srt/{job_id}")
@limiter.limit("20/minute")
async def download_srt(request: Request, job_id: str, background_tasks: BackgroundTasks):
    """Download the SRT subtitle file for the given job"""
    _validate_job_id(job_id)

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Video not ready. Current status: {job.status}",
        )

    if not job.srt_file or not os.path.exists(job.srt_file):
        raise HTTPException(status_code=404, detail="SRT file not found")

    background_tasks.add_task(cleanup_file_after_delay, job.srt_file, 300)

    return FileResponse(
        job.srt_file,
        media_type="text/plain",
        filename=f"subtitles_{job_id}.srt",
    )


@app.get("/styles")
async def get_styles():
    """Get available subtitle styles"""
    return {
        "styles": [
            {
                "id": "yellow_highlight",
                "name": "Yellow Highlight",
                "description": "Bold text with yellow highlight on current word",
            },
            {
                "id": "multicolor_pop",
                "name": "Multi-color Pop",
                "description": "Vibrant alternating colors with heavy weight",
            },
            {
                "id": "clean_outline",
                "name": "Clean Outline",
                "description": "White italic text with dark stroke outline",
            },
        ],
        "display_modes": [
            {"id": "word", "name": "Word by Word", "description": "Show 1-3 words at a time"},
            {"id": "sentence", "name": "Full Sentence", "description": "Show complete sentences"},
        ],
        "positions": [
            {"id": "top", "name": "Top"},
            {"id": "center", "name": "Center"},
            {"id": "bottom", "name": "Bottom"},
        ],
    }


@app.get("/languages")
async def get_languages():
    """Get available languages for translation"""
    translator = get_translator()
    languages = translator.get_available_languages()
    return {
        "languages": languages,
        "note": "Language packages are downloaded on first use. This may take a moment.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4569)
