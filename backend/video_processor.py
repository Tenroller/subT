"""
Video Processor module
Handles video validation and subtitle burning using FFmpeg
"""
import subprocess
import json
import os
from typing import Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from subtitle_generator import DrawtextFrame


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
        output_path: str,
        copy_codec: bool = False
    ):
        """
        Burn ASS subtitles into video using FFmpeg

        Args:
            video_path: Path to input video
            subtitle_path: Path to ASS subtitle file
            output_path: Path for output video
            copy_codec: If True, use codec copy for ~50-100x speedup.
                       Results in larger files with potential compatibility issues.
                       If False, re-encode with optimized CPU settings.
        """
        if copy_codec:
            # Fast mode: Copy codec without re-encoding (50-100x faster)
            # Subtitles are burned as an overlay filter
            # Trade-off: Larger output files, potential compatibility issues
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vf", f"ass={subtitle_path}",
                "-c:a", "copy",
                "-c:v", "copy",  # Skip re-encoding
                output_path
            ]
        else:
            # Quality mode: Software re-encode with optimized settings
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vf", f"ass={subtitle_path}",
                "-c:a", "copy",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "26",
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

    def burn_subtitles_drawtext(
        self,
        video_path: str,
        frames: List["DrawtextFrame"],
        output_path: str,
        font_path: str = None,
        copy_codec: bool = False
    ):
        """
        Burn subtitles using FFmpeg drawtext filter for solid background boxes.
        This method is specifically for Yellow Highlight style.

        Args:
            video_path: Path to input video
            frames: List of DrawtextFrame objects from SubtitleGenerator
            output_path: Path for output video
            font_path: Path to font file (defaults to Impact or Arial)
            copy_codec: If True, use codec copy (not compatible with drawtext)
        """
        if not frames:
            raise ValueError("No frames to render")

        # Find available font
        font_file = self._find_font(font_path)

        # Build the filter complex with all drawtext filters
        filter_parts = []

        for frame in frames:
            for word in frame.words:
                # Escape special characters in text for FFmpeg
                escaped_text = self._escape_drawtext(word.text)

                # Build drawtext filter for this word
                if word.is_highlighted and word.box_color:
                    # Highlighted word: solid background box
                    box_color_ffmpeg = self._hex_to_ffmpeg_color(word.box_color)
                    text_color_ffmpeg = self._hex_to_ffmpeg_color(word.text_color)

                    drawtext = (
                        f"drawtext=text='{escaped_text}':"
                        f"fontfile='{font_file}':"
                        f"fontsize={word.font_size}:"
                        f"fontcolor={text_color_ffmpeg}:"
                        f"x={word.x_position}:y={word.y_position}:"
                        f"box=1:boxcolor={box_color_ffmpeg}@1.0:boxborderw=8:"
                        f"enable='between(t,{frame.start:.3f},{frame.end:.3f})'"
                    )
                else:
                    # Non-highlighted word: white text with black shadow/outline
                    text_color_ffmpeg = self._hex_to_ffmpeg_color(word.text_color)

                    drawtext = (
                        f"drawtext=text='{escaped_text}':"
                        f"fontfile='{font_file}':"
                        f"fontsize={word.font_size}:"
                        f"fontcolor={text_color_ffmpeg}:"
                        f"x={word.x_position}:y={word.y_position}:"
                        f"shadowcolor=black@0.8:shadowx=2:shadowy=2:"
                        f"enable='between(t,{frame.start:.3f},{frame.end:.3f})'"
                    )

                filter_parts.append(drawtext)

        # Join all drawtext filters
        filter_complex = ",".join(filter_parts)

        # Build FFmpeg command
        # Note: drawtext requires re-encoding, cannot use copy codec
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vf", filter_complex,
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "26",
            output_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg drawtext failed: {e.stderr}")

    def _find_font(self, font_path: str = None) -> str:
        """Find a suitable font file for drawtext"""
        if font_path and os.path.exists(font_path):
            return font_path

        # Common font locations
        font_candidates = [
            # macOS
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/Library/Fonts/Impact.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
            # Linux
            "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            # Docker/Alpine
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/noto/NotoSans-Bold.ttf",
        ]

        for font in font_candidates:
            if os.path.exists(font):
                return font

        # Fallback: let FFmpeg try to find a font
        return "Impact"

    def _escape_drawtext(self, text: str) -> str:
        """Escape special characters for FFmpeg drawtext filter"""
        # FFmpeg drawtext requires escaping: ' : \ and newlines
        text = text.replace("\\", "\\\\")
        text = text.replace("'", "'\\''")
        text = text.replace(":", "\\:")
        text = text.replace("%", "\\%")
        return text

    def _hex_to_ffmpeg_color(self, hex_color: str) -> str:
        """
        Convert hex color (#RRGGBB) to FFmpeg color format.
        FFmpeg accepts hex colors as 0xRRGGBB or color names.
        """
        if not hex_color:
            return "white"

        # Remove # prefix and return in FFmpeg format
        hex_color = hex_color.lstrip('#')
        return f"0x{hex_color}"
