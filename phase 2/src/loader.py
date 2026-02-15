"""Load and validate Phase 1 artifacts."""
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


logger = logging.getLogger(__name__)


@dataclass
class ASRSegment:
    """ASR segment with words."""
    start: int
    end: int
    text: str
    words: List[Dict[str, Any]]


@dataclass
class Scene:
    """Scene boundary."""
    scene_id: int
    start_ms: int
    end_ms: int
    duration_ms: int
    start_frame: int
    end_frame: int


@dataclass
class Keyframe:
    """Keyframe metadata."""
    frame_id: int
    scene_id: int
    timestamp_ms: int
    frame_number: int
    filename: str
    path: str
    blur_score: float
    width: int
    height: int


@dataclass
class OCRBlock:
    """OCR text block."""
    text: str
    bbox: List[float]  # [x_min, y_min, x_max, y_max]
    confidence: float


@dataclass
class OCRResult:
    """OCR result for a keyframe."""
    frame_id: int
    timestamp_ms: int
    scene_id: int
    image_path: str
    width: int
    height: int
    text_blocks: List[OCRBlock]
    full_text: str
    total_blocks: int


@dataclass
class Chapter:
    """Video chapter."""
    title: str
    start_time: float  # seconds
    end_time: float


@dataclass
class Metadata:
    """Video metadata."""
    id: str
    title: str
    description: str
    duration: int
    channel: str
    upload_date: str
    tags: List[str]
    chapters: List[Chapter]


@dataclass
class VideoData:
    """Complete Phase 1 video data."""
    video_id: str
    metadata: Metadata
    asr_segments: List[ASRSegment]
    scenes: List[Scene]
    keyframes: List[Keyframe]
    ocr_results: List[OCRResult]
    
    # Computed properties
    @property
    def total_duration_ms(self) -> int:
        """Get total video duration in milliseconds."""
        if self.scenes:
            return self.scenes[-1].end_ms
        return 0


class Phase1Loader:
    """Load Phase 1 artifacts."""
    
    def __init__(self, phase1_video_dir: Path):
        self.phase1_video_dir = phase1_video_dir
    
    def load(self) -> VideoData:
        """Load all Phase 1 artifacts."""
        logger.info(f"Loading Phase 1 artifacts from {self.phase1_video_dir}")
        
        # Load metadata
        metadata = self._load_metadata()
        
        # Load ASR
        asr_segments = self._load_asr()
        
        # Load scenes
        scenes = self._load_scenes()
        
        # Load keyframes
        keyframes = self._load_keyframes()
        
        # Load OCR
        ocr_results = self._load_ocr()
        
        video_data = VideoData(
            video_id=metadata.id,
            metadata=metadata,
            asr_segments=asr_segments,
            scenes=scenes,
            keyframes=keyframes,
            ocr_results=ocr_results
        )
        
        logger.info(f"Loaded: {len(asr_segments)} ASR segments, {len(scenes)} scenes, "
                   f"{len(keyframes)} keyframes, {len(ocr_results)} OCR results")
        
        return video_data
    
    def _load_metadata(self) -> Metadata:
        """Load video metadata."""
        metadata_path = self.phase1_video_dir / "source" / "metadata.json"
        
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        chapters = [
            Chapter(
                title=ch["title"],
                start_time=ch["start_time"],
                end_time=ch["end_time"]
            )
            for ch in data.get("chapters", [])
        ]
        
        return Metadata(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            duration=data["duration"],
            channel=data.get("channel", ""),
            upload_date=data.get("upload_date", ""),
            tags=data.get("tags", []),
            chapters=chapters
        )
    
    def _load_asr(self) -> List[ASRSegment]:
        """Load ASR segments."""
        asr_path = self.phase1_video_dir / "asr.json"
        
        with open(asr_path, 'r') as f:
            data = json.load(f)
        
        segments = [
            ASRSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"],
                words=seg.get("words", [])
            )
            for seg in data["segments"]
        ]
        
        return segments
    
    def _load_scenes(self) -> List[Scene]:
        """Load scene boundaries."""
        scenes_path = self.phase1_video_dir / "scenes.json"
        
        with open(scenes_path, 'r') as f:
            data = json.load(f)
        
        scenes = [
            Scene(
                scene_id=sc["scene_id"],
                start_ms=sc["start_ms"],
                end_ms=sc["end_ms"],
                duration_ms=sc["duration_ms"],
                start_frame=sc["start_frame"],
                end_frame=sc["end_frame"]
            )
            for sc in data["scenes"]
        ]
        
        return scenes
    
    def _load_keyframes(self) -> List[Keyframe]:
        """Load keyframe metadata."""
        keyframes_path = self.phase1_video_dir / "keyframes.json"
        
        with open(keyframes_path, 'r') as f:
            data = json.load(f)
        
        keyframes = [
            Keyframe(
                frame_id=kf["frame_id"],
                scene_id=kf["scene_id"],
                timestamp_ms=kf["timestamp_ms"],
                frame_number=kf["frame_number"],
                filename=kf["filename"],
                path=kf["path"],
                blur_score=kf["blur_score"],
                width=kf["width"],
                height=kf["height"]
            )
            for kf in data["keyframes"]
        ]
        
        return keyframes
    
    def _load_ocr(self) -> List[OCRResult]:
        """Load OCR results."""
        ocr_path = self.phase1_video_dir / "ocr.json"
        
        with open(ocr_path, 'r') as f:
            data = json.load(f)
        
        ocr_results = [
            OCRResult(
                frame_id=res["frame_id"],
                timestamp_ms=res["timestamp_ms"],
                scene_id=res["scene_id"],
                image_path=res["image_path"],
                width=res["width"],
                height=res["height"],
                text_blocks=[
                    OCRBlock(
                        text=block["text"],
                        bbox=block["bbox"],
                        confidence=block["confidence"]
                    )
                    for block in res["text_blocks"]
                ],
                full_text=res["full_text"],
                total_blocks=res["total_blocks"]
            )
            for res in data["results"]
        ]
        
        return ocr_results


def load_phase1_data(phase1_video_dir: Path) -> VideoData:
    """Convenience function to load Phase 1 data."""
    loader = Phase1Loader(phase1_video_dir)
    return loader.load()
