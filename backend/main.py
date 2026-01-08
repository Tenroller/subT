import time
"""
Video Subtitle Creation App - Backend
FastAPI application for video transcription and subtitle generation
"""
import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from enum import Enum

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Local imports
from transcriber import Transcriber
from subtitle_generator import SubtitleGenerator, SubtitleStyle, DisplayMode, Position
from video_processor import VideoProcessor

# Configuration
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
MAX_VIDEO_DURATION = 300  # 5 minutes in seconds
ALLOWED_EXTENSIONS = {".mp4"}

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="Video Subtitle Creator",
    description="Upload videos and generate stylized burned-in subtitles",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
transcriber: Optional[Transcriber] = None
video_processor = VideoProcessor()


# Concurrency control
# Limit to 3 concurrent processing jobs
processing_semaphore = asyncio.Semaphore(3)

# Lock for Whisper transcription (model is not thread-safe)
transcription_lock = asyncio.Lock()

class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    TRANSCRIBING = "transcribing"
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
    queue_position: Optional[int] = None


# In-memory job storage (for simplicity)
jobs: dict[str, Job] = {}


@app.on_event("startup")
async def startup_event():
    """Load Whisper model and start cleanup loop"""
    global transcriber
    print("Loading Whisper turbo model... This may take a moment on first run.")
    transcriber = Transcriber(model_name="turbo")
    print("Whisper model loaded successfully!")
    
    # Start periodic cleanup task
    asyncio.create_task(periodic_cleanup())


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
    """Periodically clean up stale files (older than 1 hour)"""
    while True:
        try:
            # Check every 10 minutes
            await asyncio.sleep(600)
            
            now = time.time()
            max_age = 3600  # 1 hour
            
            # Clean outputs
            for p in OUTPUT_DIR.glob("*"):
                if p.is_file() and now - p.stat().st_mtime > max_age:
                    try:
                        p.unlink()
                        print(f"Auto-cleaned stale file: {p}")
                    except Exception as e:
                        print(f"Error deleting {p}: {e}")
                        
            # Clean uploads (if any stuck)
            for p in UPLOAD_DIR.glob("*"):
                if p.is_file() and now - p.stat().st_mtime > max_age:
                    try:
                        p.unlink()
                    except Exception as e:
                        print(f"Error deleting {p}: {e}")
                        
        except Exception as e:
            print(f"Cleanup loop error: {e}")


@app.get("/download/{job_id}")
async def download_video(job_id: str, background_tasks: BackgroundTasks):
    """Download the processed video"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Video not ready. Current status: {job.status}"
        )
    
    if not job.output_file or not os.path.exists(job.output_file):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    # Schedule cleanup for 5 minutes after download starts
    background_tasks.add_task(cleanup_file_after_delay, job.output_file, 300)
    
    return FileResponse(
        job.output_file,
        media_type="video/mp4",
        filename=f"subtitled_{job_id}.mp4"
    )

@app.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    style: str = Form("yellow_highlight"),
    display_mode: str = Form("word"),
    position: str = Form("bottom")
):
    """
    Upload a video and start subtitle generation
    
    - **video**: MP4 file, max 5 minutes
    - **style**: yellow_highlight, multicolor_pop, or clean_outline
    - **display_mode**: word (word-by-word) or sentence
    - **position**: top, center, or bottom
    """
    # Validate file extension
    file_ext = Path(video.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only {', '.join(ALLOWED_EXTENSIONS)} allowed."
        )
    
    # Generate job ID and save file
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    
    # Save uploaded file
    content = await video.read()
    with open(input_path, "wb") as f:
        f.write(content)
    
    # Validate video duration
    try:
        duration = video_processor.get_duration(str(input_path))
        if duration > MAX_VIDEO_DURATION:
            os.remove(input_path)
            raise HTTPException(
                status_code=400,
                detail=f"Video too long. Maximum duration is {MAX_VIDEO_DURATION // 60} minutes."
            )
    except Exception as e:
        # If duration check fails (e.g. invalid video), clean up
        if os.path.exists(input_path):
            os.remove(input_path)
        raise HTTPException(status_code=400, detail=f"Invalid video file: {str(e)}")
    
    # Parse options
    try:
        subtitle_style = SubtitleStyle(style)
        subtitle_display_mode = DisplayMode(display_mode)
        subtitle_position = Position(position)
    except ValueError as e:
        os.remove(input_path)
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create job
    job = Job(id=job_id, status=JobStatus.QUEUED)
    jobs[job_id] = job
    
    # Start background processing
    background_tasks.add_task(
        process_video_task,
        job_id,
        str(input_path),
        subtitle_style,
        subtitle_display_mode,
        subtitle_position
    )
    
    return {"job_id": job_id, "status": job.status}


async def process_video_task(
    job_id: str,
    input_path: str,
    style: SubtitleStyle,
    display_mode: DisplayMode,
    position: Position
):
    """Background task to process video with subtitles"""
    job = jobs[job_id]
    output_path = OUTPUT_DIR / f"{job_id}_subtitled.mp4"
    subtitle_path = OUTPUT_DIR / f"{job_id}.ass"
    
    try:
        # Acquire semaphore to limit concurrency
        async with processing_semaphore:
            # Step 1: Transcribe (use lock since Whisper isn't thread-safe)
            job.status = JobStatus.TRANSCRIBING
            job.progress = 10
            
            async with transcription_lock:
                segments = await asyncio.to_thread(
                    transcriber.transcribe,
                    input_path
                )
            
            job.progress = 40
            
            # Step 2: Generate subtitles
            job.status = JobStatus.GENERATING_SUBTITLES
            
            generator = SubtitleGenerator(
                style=style,
                display_mode=display_mode,
                position=position
            )
            
            # Get video dimensions for proper positioning
            width, height = video_processor.get_dimensions(input_path)
            generator.generate(segments, str(subtitle_path), width, height)
            
            job.progress = 60
            
            # Step 3: Burn subtitles into video
            job.status = JobStatus.PROCESSING_VIDEO
            
            await asyncio.to_thread(
                video_processor.burn_subtitles,
                input_path,
                str(subtitle_path),
                str(output_path)
            )
            
            job.progress = 100
            job.status = JobStatus.COMPLETED
            job.output_file = str(output_path)
            
            # Cleanup output from active queue (optional logic update)
        
        # Cleanup input file
        if os.path.exists(input_path):
            os.remove(input_path)
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        # Cleanup on error
        if os.path.exists(input_path):
            os.remove(input_path)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": transcriber is not None}


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a processing job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "error": job.error
    }


@app.get("/styles")
async def get_styles():
    """Get available subtitle styles"""
    return {
        "styles": [
            {
                "id": "yellow_highlight",
                "name": "Yellow Highlight",
                "description": "Bold text with yellow highlight on current word"
            },
            {
                "id": "multicolor_pop",
                "name": "Multi-color Pop",
                "description": "Vibrant alternating colors with heavy weight"
            },
            {
                "id": "clean_outline",
                "name": "Clean Outline",
                "description": "White italic text with dark stroke outline"
            }
        ],
        "display_modes": [
            {"id": "word", "name": "Word by Word", "description": "Show 1-3 words at a time"},
            {"id": "sentence", "name": "Full Sentence", "description": "Show complete sentences"}
        ],
        "positions": [
            {"id": "top", "name": "Top"},
            {"id": "center", "name": "Center"},
            {"id": "bottom", "name": "Bottom"}
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
