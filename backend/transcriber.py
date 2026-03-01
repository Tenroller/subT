"""
Transcriber module using faster-whisper (CTranslate2) for speech-to-text
with word-level timestamps.

faster-whisper is typically 2-4x faster than openai-whisper and uses
significantly less memory, especially with INT8 quantisation on CPU.
"""
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

from faster_whisper import WhisperModel


# ---------------------------------------------------------------------------
# Data classes (public interface — unchanged from before)
# ---------------------------------------------------------------------------

@dataclass
class Word:
    """Represents a single word with timing"""
    text: str
    start: float
    end: float


@dataclass
class Segment:
    """Represents a segment (sentence) with words"""
    text: str
    start: float
    end: float
    words: List[Word]


# ---------------------------------------------------------------------------
# Transcriber
# ---------------------------------------------------------------------------

class Transcriber:
    """
    faster-whisper based transcription with word-level timestamps.

    The model is configured via environment variables so the same image
    works on both CPU and GPU hosts:

        WHISPER_DEVICE      cpu | cuda          (default: cpu)
        WHISPER_COMPUTE     int8 | float16 | float32
                            (default: int8 on CPU, float16 on CUDA)
        WHISPER_THREADS     number of CPU inter-op threads (default: 4)
    """

    def __init__(self, model_name: str = "turbo"):
        """
        Load a faster-whisper model.

        Args:
            model_name: Any model size supported by faster-whisper:
                        tiny, base, small, medium, large-v1/v2/v3, turbo
        """
        device = os.environ.get("WHISPER_DEVICE", "cpu").lower()

        # Sensible compute-type defaults per device
        if "WHISPER_COMPUTE" in os.environ:
            compute_type = os.environ["WHISPER_COMPUTE"]
        else:
            compute_type = "int8" if device == "cpu" else "float16"

        cpu_threads = int(os.environ.get("WHISPER_THREADS", "4"))

        self.model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )
        self.model_name = model_name

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _build_segments(self, fw_segments) -> List[Segment]:
        """
        Convert faster-whisper segment generator into our Segment dataclasses.

        NOTE: faster-whisper.transcribe() returns a *lazy generator*.
        Materialising it here (via the for-loop) is what actually runs
        the transcription, so callers don't need to worry about that.
        """
        segments: List[Segment] = []

        for seg in fw_segments:
            words: List[Word] = []

            for w in (seg.words or []):
                text = w.word.strip()
                if text:
                    words.append(Word(text=text, start=w.start, end=w.end))

            text = seg.text.strip()
            if text:
                segments.append(
                    Segment(
                        text=text,
                        start=seg.start,
                        end=seg.end,
                        words=words,
                    )
                )

        return segments

    # ------------------------------------------------------------------
    # Public API  (identical signatures to the old openai-whisper version)
    # ------------------------------------------------------------------

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> List[Segment]:
        """
        Transcribe audio/video file and return segments with word-level timestamps.

        Args:
            audio_path: Path to audio or video file.
            language:   Optional BCP-47 language code (e.g. 'en', 'pt').
                        Auto-detected when None.

        Returns:
            List of Segment objects with word-level timestamps.
        """
        fw_segments, _info = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,          # skip silent regions — speeds things up
            beam_size=5,
        )
        return self._build_segments(fw_segments)

    def transcribe_with_language(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> Tuple[List[Segment], str]:
        """
        Transcribe audio/video file and return segments plus the detected language.

        Args:
            audio_path: Path to audio or video file.
            language:   Optional BCP-47 language code. Auto-detected when None.

        Returns:
            Tuple of (List of Segment objects, detected language code string).
        """
        fw_segments, info = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,
            beam_size=5,
        )
        segments = self._build_segments(fw_segments)
        detected_language = info.language  # e.g. "en", "pt"
        return segments, detected_language
