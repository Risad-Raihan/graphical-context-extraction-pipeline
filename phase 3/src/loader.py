"""Load Phase 1 and Phase 2 artifacts"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ASRSegment:
    """ASR segment from Phase 1"""
    text: str
    start_ms: int
    end_ms: int
    confidence: float


@dataclass
class OCRBlock:
    """OCR block from Phase 1"""
    text: str
    bbox: List[List[int]]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    confidence: float
    keyframe_path: str


@dataclass
class Keyframe:
    """Keyframe from Phase 1"""
    path: Path
    timestamp_ms: int
    scene_idx: int


@dataclass
class Scene:
    """Scene from Phase 1"""
    idx: int
    start_ms: int
    end_ms: int


@dataclass
class Chapter:
    """Chapter from metadata"""
    title: str
    start_ms: int
    end_ms: int


@dataclass
class Metadata:
    """Video metadata from Phase 1"""
    video_id: str
    title: str
    duration_sec: float
    chapters: List[Chapter]


@dataclass
class Chunk:
    """Chunk from Phase 2"""
    chunk_id: str
    chapter_idx: int
    chapter_title: str
    scene_indices: List[int]
    t_start_ms: int
    t_end_ms: int
    duration_sec: float
    asr_text: str
    ocr_text_cleaned: str
    ocr_text_raw: str
    keyframe_paths: List[str]
    has_speech: bool
    has_visual: bool
    has_ocr_text: bool
    asr_confidence_avg: float
    ocr_confidence_avg: float
    alignment_score: float


@dataclass
class VideoData:
    """Complete video data from Phase 1 and Phase 2"""
    video_id: str
    metadata: Metadata
    asr_segments: List[ASRSegment]
    scenes: List[Scene]
    keyframes: List[Keyframe]
    ocr_blocks: List[OCRBlock]
    chunks: List[Chunk]


class DataLoader:
    """Load Phase 1 and Phase 2 data"""
    
    def __init__(self, phase1_dir: Path, phase2_dir: Path):
        self.phase1_dir = phase1_dir
        self.phase2_dir = phase2_dir
    
    def load_all(self, video_id: str) -> VideoData:
        """Load all data for a video"""
        # Load Phase 1 data
        metadata = self._load_metadata(video_id)
        asr_segments = self._load_asr(video_id)
        scenes = self._load_scenes(video_id)
        keyframes = self._load_keyframes(video_id)
        ocr_blocks = self._load_ocr(video_id)
        
        # Load Phase 2 data
        chunks = self._load_chunks(video_id)
        
        return VideoData(
            video_id=video_id,
            metadata=metadata,
            asr_segments=asr_segments,
            scenes=scenes,
            keyframes=keyframes,
            ocr_blocks=ocr_blocks,
            chunks=chunks
        )
    
    def _load_metadata(self, video_id: str) -> Metadata:
        """Load video metadata"""
        path = self.phase1_dir / video_id / "source" / "metadata.json"
        with open(path) as f:
            data = json.load(f)
        
        chapters = []
        for ch in data.get("chapters", []):
            chapters.append(Chapter(
                title=ch["title"],
                start_ms=int(ch["start_time"] * 1000),
                end_ms=int(ch["end_time"] * 1000)
            ))
        
        return Metadata(
            video_id=video_id,
            title=data["title"],
            duration_sec=data["duration"],
            chapters=chapters
        )
    
    def _load_asr(self, video_id: str) -> List[ASRSegment]:
        """Load ASR segments"""
        path = self.phase1_dir / video_id / "asr.json"
        with open(path) as f:
            data = json.load(f)
        
        segments = []
        for seg in data["segments"]:
            # ASR uses milliseconds directly
            segments.append(ASRSegment(
                text=seg["text"],
                start_ms=seg["start"],
                end_ms=seg["end"],
                confidence=seg.get("confidence", 1.0)
            ))
        
        return segments
    
    def _load_scenes(self, video_id: str) -> List[Scene]:
        """Load scene boundaries"""
        path = self.phase1_dir / video_id / "scenes.json"
        with open(path) as f:
            data = json.load(f)
        
        scenes = []
        for scene in data["scenes"]:
            scenes.append(Scene(
                idx=scene["scene_id"],
                start_ms=scene["start_ms"],
                end_ms=scene["end_ms"]
            ))
        
        return scenes
    
    def _load_keyframes(self, video_id: str) -> List[Keyframe]:
        """Load keyframes"""
        path = self.phase1_dir / video_id / "keyframes.json"
        with open(path) as f:
            data = json.load(f)
        
        keyframes = []
        for kf in data["keyframes"]:
            # Always use local path - ignore the path from JSON which may be from vast.ai
            kf_path = self.phase1_dir / video_id / "keyframes" / kf["filename"]
            
            keyframes.append(Keyframe(
                path=kf_path,
                timestamp_ms=kf["timestamp_ms"],
                scene_idx=kf["scene_id"]
            ))
        
        return keyframes
    
    def _load_ocr(self, video_id: str) -> List[OCRBlock]:
        """Load OCR blocks"""
        path = self.phase1_dir / video_id / "ocr.json"
        with open(path) as f:
            data = json.load(f)
        
        ocr_blocks = []
        for result in data["results"]:
            # OCR uses 'image_path' not 'keyframe_path'
            keyframe_path = result["image_path"]
            for block in result["text_blocks"]:
                # Use bbox_polygon for the actual coordinates
                bbox = block.get("bbox_polygon", block.get("bbox", []))
                ocr_blocks.append(OCRBlock(
                    text=block["text"],
                    bbox=bbox,
                    confidence=block.get("confidence", 1.0),
                    keyframe_path=keyframe_path
                ))
        
        return ocr_blocks
    
    def _load_chunks(self, video_id: str) -> List[Chunk]:
        """Load Phase 2 chunks"""
        path = self.phase2_dir / "output" / video_id / "chunks.json"
        with open(path) as f:
            # Phase 2 outputs a list directly, not wrapped in {"chunks": [...]}
            data = json.load(f)
        
        chunks = []
        for chunk_data in data:
            # Calculate duration if not present
            duration_sec = (chunk_data["t_end_ms"] - chunk_data["t_start_ms"]) / 1000
            
            chunks.append(Chunk(
                chunk_id=chunk_data["chunk_id"],
                chapter_idx=chunk_data.get("chapter_index", chunk_data.get("chapter_idx", 0)),
                chapter_title=chunk_data["chapter_title"],
                scene_indices=[chunk_data.get("scene_id", 0)],  # Phase 2 uses scene_id
                t_start_ms=chunk_data["t_start_ms"],
                t_end_ms=chunk_data["t_end_ms"],
                duration_sec=duration_sec,
                asr_text=chunk_data["asr_text"],
                ocr_text_cleaned=chunk_data.get("ocr_text", ""),
                ocr_text_raw=chunk_data.get("ocr_text", ""),
                keyframe_paths=chunk_data["keyframe_paths"],
                has_speech=chunk_data["completeness"]["has_speech"],
                has_visual=chunk_data["completeness"]["has_visual"],
                has_ocr_text=chunk_data["completeness"]["has_ocr_text"],
                asr_confidence_avg=chunk_data.get("asr_confidence", 1.0),
                ocr_confidence_avg=chunk_data.get("ocr_confidence", 1.0),
                alignment_score=chunk_data.get("alignment_score", 0.0)
            ))
        
        return chunks
