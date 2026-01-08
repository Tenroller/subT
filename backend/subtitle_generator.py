"""
Subtitle Generator module
Creates styled ASS subtitle files from transcription segments
"""
import pysubs2
from enum import Enum
from typing import List
from dataclasses import dataclass

from transcriber import Segment, Word


class SubtitleStyle(str, Enum):
    YELLOW_HIGHLIGHT = "yellow_highlight"
    MULTICOLOR_POP = "multicolor_pop"
    CLEAN_OUTLINE = "clean_outline"


class DisplayMode(str, Enum):
    WORD = "word"  # Word by word (1-3 words at a time)
    SENTENCE = "sentence"  # Full sentence


class Position(str, Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


# ASS color format: &HAABBGGRR (Alpha, Blue, Green, Red in hex)
# Note: ASS uses BGR order, not RGB!

# Style configurations
STYLE_CONFIGS = {
    SubtitleStyle.YELLOW_HIGHLIGHT: {
        "fontname": "Impact",
        "fontsize": 60,
        "bold": True,
        "italic": False,
        "primary_color": "&H00FFFFFF",  # White
        "secondary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",  # Black
        "back_color": "&H80000000",  # Semi-transparent black shadow
        "outline": 3,
        "shadow": 2,
        "highlight_color": "&H0000FFFF",  # Yellow (BGR: 00FFFF)
    },
    SubtitleStyle.MULTICOLOR_POP: {
        "fontname": "Impact",
        "fontsize": 70,
        "bold": True,
        "italic": False,
        "primary_color": "&H00FFFFFF",  # White
        "secondary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",  # Black
        "back_color": "&H00000000",
        "outline": 4,
        "shadow": 0,
        "colors": [
            "&H00FFFFFF",  # White
            "&H0000FF00",  # Green (BGR)
            "&H0000FFFF",  # Yellow (BGR)
            "&H00FF00FF",  # Magenta
        ]
    },
    SubtitleStyle.CLEAN_OUTLINE: {
        "fontname": "Arial",
        "fontsize": 50,
        "bold": True,
        "italic": True,
        "primary_color": "&H00FFFFFF",  # White
        "secondary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",  # Black
        "back_color": "&H00000000",
        "outline": 3,
        "shadow": 1,
    }
}


def get_position_alignment(position: Position) -> int:
    """
    Get ASS alignment value based on position
    ASS alignment values (numpad layout):
    7 8 9 (top)
    4 5 6 (middle)
    1 2 3 (bottom)
    """
    alignments = {
        Position.TOP: 8,      # Top center
        Position.CENTER: 5,   # Middle center
        Position.BOTTOM: 2,   # Bottom center
    }
    return alignments[position]


def get_margin_v(position: Position, video_height: int) -> int:
    """Get vertical margin based on position"""
    margins = {
        Position.TOP: int(video_height * 0.08),
        Position.CENTER: 0,
        Position.BOTTOM: int(video_height * 0.08),
    }
    return margins[position]


def parse_ass_color(color_str: str) -> pysubs2.Color:
    """
    Parse ASS color string &HAABBGGRR to pysubs2.Color
    """
    # Remove &H prefix
    clean_str = color_str.replace("&H", "")
    
    # Pad if needed (should be 8 chars)
    if len(clean_str) < 8:
        clean_str = clean_str.zfill(8)
        
    # Extract components (AABBGGRR)
    # Note: parsing as hex int
    try:
        val = int(clean_str, 16)
        
        # Extract bytes
        a = (val >> 24) & 0xFF
        b = (val >> 16) & 0xFF
        g = (val >> 8) & 0xFF
        r = val & 0xFF
        
        return pysubs2.Color(r=r, g=g, b=b, a=a)
    except ValueError:
        # Fallback to white if invalid
        return pysubs2.Color(255, 255, 255)


class SubtitleGenerator:
    """Generate styled ASS subtitles from transcription"""
    
    def __init__(
        self,
        style: SubtitleStyle = SubtitleStyle.YELLOW_HIGHLIGHT,
        display_mode: DisplayMode = DisplayMode.WORD,
        position: Position = Position.BOTTOM
    ):
        self.style = style
        self.display_mode = display_mode
        self.position = position
        self.style_config = STYLE_CONFIGS[style]
    
    def generate(
        self,
        segments: List[Segment],
        output_path: str,
        video_width: int = 1920,
        video_height: int = 1080
    ):
        """
        Generate ASS subtitle file from segments
        
        Args:
            segments: List of transcription segments with words
            output_path: Path to save the .ass file
            video_width: Video width for positioning
            video_height: Video height for positioning
        """
        # Create subtitle file
        subs = pysubs2.SSAFile()
        subs.info["PlayResX"] = str(video_width)
        subs.info["PlayResY"] = str(video_height)
        
        # Create base style
        alignment = get_position_alignment(self.position)
        margin_v = get_margin_v(self.position, video_height)
        
        base_style = pysubs2.SSAStyle(
            fontname=self.style_config["fontname"],
            fontsize=self.style_config["fontsize"],
            bold=self.style_config["bold"],
            italic=self.style_config["italic"],
            primarycolor=parse_ass_color(self.style_config["primary_color"]),
            secondarycolor=parse_ass_color(self.style_config["secondary_color"]),
            outlinecolor=parse_ass_color(self.style_config["outline_color"]),
            backcolor=parse_ass_color(self.style_config["back_color"]),
            outline=self.style_config["outline"],
            shadow=self.style_config["shadow"],
            alignment=alignment,
            marginv=margin_v,
        )
        subs.styles["Default"] = base_style
        
        # Generate events based on display mode
        if self.display_mode == DisplayMode.SENTENCE:
            self._generate_sentence_mode(subs, segments)
        else:
            self._generate_word_mode(subs, segments)
        
        # Save file
        subs.save(output_path)
    
    def _generate_sentence_mode(self, subs: pysubs2.SSAFile, segments: List[Segment]):
        """Generate subtitles showing full sentences"""
        for segment in segments:
            if not segment.words:
                continue
            
            if self.style == SubtitleStyle.YELLOW_HIGHLIGHT:
                # For yellow highlight style, highlight current word
                self._generate_sentence_with_highlight(subs, segment)
            elif self.style == SubtitleStyle.MULTICOLOR_POP:
                # For multicolor, use colored words
                self._generate_multicolor_sentence(subs, segment)
            else:
                # Clean outline - simple sentence
                event = pysubs2.SSAEvent(
                    start=int(segment.start * 1000),
                    end=int(segment.end * 1000),
                    text=segment.text.upper()
                )
                subs.events.append(event)
    
    def _generate_sentence_with_highlight(self, subs: pysubs2.SSAFile, segment: Segment):
        """Generate sentence with highlighted current word (yellow box style)"""
        # Yellow box effect using xbord/ybord for rectangular padding
        # \3c = outline/border color (yellow), \1c = text color (black)
        # \xbord/\ybord = horizontal/vertical border size for box effect
        # &H00D7FF = Yellow in BGR (matches frontend preview)
        highlight_start = "{\\1c&H000000&\\3c&H00D7FF&\\xbord10\\ybord5\\shad0}"
        highlight_end = "{\\r}"  # Reset to default style
        
        for i, current_word in enumerate(segment.words):
            # Build the sentence with current word highlighted
            parts = []
            for j, word in enumerate(segment.words):
                if j == i:
                    # Highlight current word with yellow box
                    parts.append(f"{highlight_start}{word.text.upper()}{highlight_end}")
                else:
                    parts.append(word.text.upper())
            
            text = " ".join(parts)
            
            # Determine end time (next word start or segment end)
            if i < len(segment.words) - 1:
                end_time = segment.words[i + 1].start
            else:
                end_time = segment.end
            
            event = pysubs2.SSAEvent(
                start=int(current_word.start * 1000),
                end=int(end_time * 1000),
                text=text
            )
            subs.events.append(event)
    
    def _generate_multicolor_sentence(self, subs: pysubs2.SSAFile, segment: Segment):
        """Generate sentence with alternating colors"""
        colors = self.style_config["colors"]
        
        # Build colored sentence
        parts = []
        for i, word in enumerate(segment.words):
            color = colors[i % len(colors)]
            parts.append(f"{{\\c{color}}}{word.text.upper()}")
        
        text = " ".join(parts)
        
        event = pysubs2.SSAEvent(
            start=int(segment.start * 1000),
            end=int(segment.end * 1000),
            text=text
        )
        subs.events.append(event)
    
    def _generate_word_mode(self, subs: pysubs2.SSAFile, segments: List[Segment]):
        """Generate subtitles showing 1-3 words at a time"""
        words_per_group = 2  # Show 2 words at a time for readability
        
        for segment in segments:
            if not segment.words:
                continue
            
            # Group words
            for i in range(0, len(segment.words), words_per_group):
                group = segment.words[i:i + words_per_group]
                if not group:
                    continue
                
                start_time = group[0].start
                end_time = group[-1].end
                
                # Add small padding to end time for readability
                if i + words_per_group < len(segment.words):
                    # Use next word's start time as end
                    end_time = segment.words[i + words_per_group].start
                
                if self.style == SubtitleStyle.YELLOW_HIGHLIGHT:
                    # Highlight each word as it's spoken
                    self._generate_word_group_with_highlight(subs, group, start_time, end_time)
                elif self.style == SubtitleStyle.MULTICOLOR_POP:
                    self._generate_word_group_multicolor(subs, group, start_time, end_time)
                else:
                    # Clean outline
                    text = " ".join(w.text.upper() for w in group)
                    event = pysubs2.SSAEvent(
                        start=int(start_time * 1000),
                        end=int(end_time * 1000),
                        text=text
                    )
                    subs.events.append(event)
    
    def _generate_word_group_with_highlight(
        self,
        subs: pysubs2.SSAFile,
        group: List[Word],
        group_start: float,
        group_end: float
    ):
        """Generate word group with highlighted current word (yellow box)"""
        # Yellow box effect using xbord/ybord for rectangular padding
        highlight_start = "{\\1c&H000000&\\3c&H00D7FF&\\xbord10\\ybord5\\shad0}"
        highlight_end = "{\\r}"  # Reset to default style
        
        for i, current_word in enumerate(group):
            parts = []
            for j, word in enumerate(group):
                if j == i:
                    parts.append(f"{highlight_start}{word.text.upper()}{highlight_end}")
                else:
                    parts.append(word.text.upper())
            
            text = " ".join(parts)
            
            # End time is next word start or group end
            if i < len(group) - 1:
                end_time = group[i + 1].start
            else:
                end_time = group_end
            
            event = pysubs2.SSAEvent(
                start=int(current_word.start * 1000),
                end=int(end_time * 1000),
                text=text
            )
            subs.events.append(event)
    
    def _generate_word_group_multicolor(
        self,
        subs: pysubs2.SSAFile,
        group: List[Word],
        start_time: float,
        end_time: float
    ):
        """Generate word group with multicolor styling"""
        colors = self.style_config["colors"]
        
        parts = []
        for i, word in enumerate(group):
            color = colors[i % len(colors)]
            parts.append(f"{{\\c{color}}}{word.text.upper()}")
        
        text = " ".join(parts)
        
        event = pysubs2.SSAEvent(
            start=int(start_time * 1000),
            end=int(end_time * 1000),
            text=text
        )
        subs.events.append(event)
