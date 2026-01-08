"""
Video Processor module
Handles video validation and subtitle burning using FFmpeg
"""
import subprocess
import json
from typing import Tuple


class VideoProcessor:
    """FFmpeg-based video processing for subtitle burning"""
    
    def get_duration(self, video_path: str) -> float:
        """
        Get video duration in seconds using ffprobe
        
        Args:
            video_path: Path to video file
            
        Returns:
            Duration in seconds
        """
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to get video duration: {e}")
    
    def get_dimensions(self, video_path: str) -> Tuple[int, int]:
        """
        Get video dimensions (width, height) using ffprobe
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (width, height)
        """
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "v:0",
            video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            stream = data["streams"][0]
            return int(stream["width"]), int(stream["height"])
        except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError, IndexError) as e:
            # Default to 1080p if detection fails
            return 1920, 1080
    
    def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str
    ):
        """
        Burn ASS subtitles into video using FFmpeg
        
        Args:
            video_path: Path to input video
            subtitle_path: Path to ASS subtitle file
            output_path: Path for output video
        """
        # FFmpeg command to burn subtitles
        # Using the ass filter for Advanced SubStation Alpha format
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i", video_path,
            "-vf", f"ass={subtitle_path}",
            "-c:a", "copy",  # Copy audio without re-encoding
            "-c:v", "libx264",  # Re-encode video with x264
            "-preset", "fast",  # Balance between speed and quality
            "-crf", "23",  # Good quality (lower = better, 18-28 is reasonable)
            output_path
        ]
        
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed: {e.stderr}")
    
    def extract_audio(self, video_path: str, audio_path: str):
        """
        Extract audio from video for transcription
        
        Args:
            video_path: Path to input video
            audio_path: Path for output audio (WAV format recommended)
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # WAV format
            "-ar", "16000",  # 16kHz sample rate (optimal for Whisper)
            "-ac", "1",  # Mono
            audio_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Audio extraction failed: {e.stderr}")
