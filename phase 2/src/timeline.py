"""Build unified temporal spine from all modalities."""
import logging
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

from src.loader import VideoData


logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Type of timeline event."""
    CHAPTER_START = "chapter_start"
    CHAPTER_END = "chapter_end"
    SCENE_START = "scene_start"
    SCENE_END = "scene_end"
    ASR_SEGMENT = "asr_segment"
    KEYFRAME = "keyframe"
    OCR_BLOCK = "ocr_block"


@dataclass
class TimelineEvent:
    """A single event on the timeline."""
    timestamp_ms: int
    event_type: EventType
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp_ms": self.timestamp_ms,
            "event_type": self.event_type.value,
            "data": self.data
        }


class TimelineBuilder:
    """Build a unified temporal spine."""
    
    def __init__(self, video_data: VideoData):
        self.video_data = video_data
        self.events: List[TimelineEvent] = []
    
    def build(self) -> List[TimelineEvent]:
        """Build the timeline."""
        logger.info("Building temporal spine")
        
        # Add chapter events
        self._add_chapter_events()
        
        # Add scene events
        self._add_scene_events()
        
        # Add ASR segments
        self._add_asr_events()
        
        # Add keyframe events
        self._add_keyframe_events()
        
        # Add OCR events (grouped by keyframe)
        self._add_ocr_events()
        
        # Sort by timestamp
        self.events.sort(key=lambda e: e.timestamp_ms)
        
        logger.info(f"Built timeline with {len(self.events)} events")
        
        return self.events
    
    def _add_chapter_events(self):
        """Add chapter start/end events."""
        for i, chapter in enumerate(self.video_data.metadata.chapters):
            # Chapter start
            self.events.append(TimelineEvent(
                timestamp_ms=int(chapter.start_time * 1000),
                event_type=EventType.CHAPTER_START,
                data={
                    "chapter_index": i,
                    "chapter_title": chapter.title,
                    "start_time_s": chapter.start_time,
                    "end_time_s": chapter.end_time
                }
            ))
            
            # Chapter end
            self.events.append(TimelineEvent(
                timestamp_ms=int(chapter.end_time * 1000),
                event_type=EventType.CHAPTER_END,
                data={
                    "chapter_index": i,
                    "chapter_title": chapter.title
                }
            ))
    
    def _add_scene_events(self):
        """Add scene start/end events."""
        for scene in self.video_data.scenes:
            # Scene start
            self.events.append(TimelineEvent(
                timestamp_ms=scene.start_ms,
                event_type=EventType.SCENE_START,
                data={
                    "scene_id": scene.scene_id,
                    "start_ms": scene.start_ms,
                    "end_ms": scene.end_ms,
                    "duration_ms": scene.duration_ms
                }
            ))
            
            # Scene end
            self.events.append(TimelineEvent(
                timestamp_ms=scene.end_ms,
                event_type=EventType.SCENE_END,
                data={
                    "scene_id": scene.scene_id
                }
            ))
    
    def _add_asr_events(self):
        """Add ASR segment events."""
        for i, segment in enumerate(self.video_data.asr_segments):
            self.events.append(TimelineEvent(
                timestamp_ms=segment.start,
                event_type=EventType.ASR_SEGMENT,
                data={
                    "segment_index": i,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "word_count": len(segment.words),
                    "words": segment.words
                }
            ))
    
    def _add_keyframe_events(self):
        """Add keyframe events."""
        for keyframe in self.video_data.keyframes:
            self.events.append(TimelineEvent(
                timestamp_ms=keyframe.timestamp_ms,
                event_type=EventType.KEYFRAME,
                data={
                    "frame_id": keyframe.frame_id,
                    "scene_id": keyframe.scene_id,
                    "filename": keyframe.filename,
                    "path": keyframe.path,
                    "blur_score": keyframe.blur_score,
                    "width": keyframe.width,
                    "height": keyframe.height
                }
            ))
    
    def _add_ocr_events(self):
        """Add OCR block events (grouped by keyframe timestamp)."""
        for ocr_result in self.video_data.ocr_results:
            self.events.append(TimelineEvent(
                timestamp_ms=ocr_result.timestamp_ms,
                event_type=EventType.OCR_BLOCK,
                data={
                    "frame_id": ocr_result.frame_id,
                    "scene_id": ocr_result.scene_id,
                    "image_path": ocr_result.image_path,
                    "total_blocks": ocr_result.total_blocks,
                    "full_text": ocr_result.full_text,
                    "text_blocks": [
                        {
                            "text": block.text,
                            "bbox": block.bbox,
                            "confidence": block.confidence
                        }
                        for block in ocr_result.text_blocks
                    ]
                }
            ))
    
    def save_timeline(self, output_path: str) -> None:
        """Save timeline to JSON."""
        import json
        
        timeline_data = {
            "video_id": self.video_data.video_id,
            "total_events": len(self.events),
            "duration_ms": self.video_data.total_duration_ms,
            "events": [event.to_dict() for event in self.events]
        }
        
        with open(output_path, 'w') as f:
            json.dump(timeline_data, f, indent=2)
        
        logger.info(f"Timeline saved to {output_path}")


def build_timeline(video_data: VideoData) -> List[TimelineEvent]:
    """Convenience function to build timeline."""
    builder = TimelineBuilder(video_data)
    return builder.build()
