"""
Transcriber module using OpenAI Whisper for speech-to-text
with word-level timestamps
"""
import whisper
from dataclasses import dataclass
from typing import List, Optional


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


class Transcriber:
    """Whisper-based transcription with word-level timestamps"""
    
    def __init__(self, model_name: str = "turbo"):
        """
        Initialize the transcriber with a Whisper model
        
        Args:
            model_name: Whisper model size (tiny, base, small, medium, large, turbo)
        """
        self.model = whisper.load_model(model_name)
        self.model_name = model_name
    
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> List[Segment]:
        """
        Transcribe audio/video file and return segments with word-level timestamps
        
        Args:
            audio_path: Path to audio or video file
            language: Optional language code (e.g., 'en', 'pt'). Auto-detected if None.
            
        Returns:
            List of Segment objects with word-level timestamps
        """
        # Transcribe with word timestamps enabled
        result = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            verbose=False
        )
        
        segments = []
        
        for segment_data in result.get("segments", []):
            words = []
            
            # Extract word-level timestamps
            for word_data in segment_data.get("words", []):
                word = Word(
                    text=word_data.get("word", "").strip(),
                    start=word_data.get("start", 0.0),
                    end=word_data.get("end", 0.0)
                )
                if word.text:  # Only add non-empty words
                    words.append(word)
            
            # Create segment
            segment = Segment(
                text=segment_data.get("text", "").strip(),
                start=segment_data.get("start", 0.0),
                end=segment_data.get("end", 0.0),
                words=words
            )
            
            if segment.text:  # Only add non-empty segments
                segments.append(segment)
        
        return segments
