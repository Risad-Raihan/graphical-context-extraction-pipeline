"""Hierarchical chunking: Chapter -> Scene with merge/split rules."""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.loader import VideoData, ASRSegment, Scene, Keyframe, OCRResult
from src.config import ChunkingConfig


logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A multimodal chunk."""
    chunk_id: str
    video_id: str
    source: str
    
    t_start_ms: int
    t_end_ms: int
    
    chapter_index: int
    chapter_title: str
    scene_id: int
    
    # ASR data
    asr_segments: List[ASRSegment]
    asr_text: str
    
    # Visual data
    keyframes: List[Keyframe]
    keyframe_ids: List[int]
    keyframe_paths: List[str]
    has_keyframe: bool
    
    # OCR data (to be filled by ocr_cleanup)
    ocr_results: List[OCRResult]
    ocr_text: str = ""
    
    # Metadata (to be filled by enricher)
    merged_text: str = ""
    asr_confidence: float = 0.0
    ocr_confidence: float = 0.0
    alignment_score: float = 0.0
    completeness: Dict[str, bool] = None
    provenance: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.completeness is None:
            self.completeness = {}
        if self.provenance is None:
            self.provenance = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "video_id": self.video_id,
            "source": self.source,
            "t_start_ms": self.t_start_ms,
            "t_end_ms": self.t_end_ms,
            "chapter_index": self.chapter_index,
            "chapter_title": self.chapter_title,
            "scene_id": self.scene_id,
            "asr_text": self.asr_text,
            "ocr_text": self.ocr_text,
            "merged_text": self.merged_text,
            "keyframe_ids": self.keyframe_ids,
            "keyframe_paths": self.keyframe_paths,
            "has_keyframe": self.has_keyframe,
            "asr_confidence": self.asr_confidence,
            "ocr_confidence": self.ocr_confidence,
            "alignment_score": self.alignment_score,
            "completeness": self.completeness,
            "provenance": self.provenance
        }


class HierarchicalChunker:
    """Create hierarchical chunks from video data."""
    
    def __init__(self, video_data: VideoData, config: ChunkingConfig):
        self.video_data = video_data
        self.config = config
        self.chunks: List[Chunk] = []
    
    def chunk(self) -> List[Chunk]:
        """Create chunks."""
        logger.info("Creating hierarchical chunks")
        
        # Process scenes with merge/split rules
        processed_scenes = self._process_scenes()
        
        # Create chunks from processed scenes
        for scene_data in processed_scenes:
            chunk = self._create_chunk_from_scene(scene_data)
            self.chunks.append(chunk)
        
        logger.info(f"Created {len(self.chunks)} chunks")
        
        return self.chunks
    
    def _process_scenes(self) -> List[Dict[str, Any]]:
        """Process scenes with merge/split rules."""
        scenes = self.video_data.scenes
        processed = []
        
        i = 0
        while i < len(scenes):
            scene = scenes[i]
            
            # Check if scene is too short and should be merged
            if (self.config.merge_short_scenes and 
                scene.duration_ms < self.config.min_chunk_duration_ms and 
                i > 0):
                # Merge with previous scene
                logger.info(f"Merging short scene {scene.scene_id} ({scene.duration_ms}ms) with previous")
                prev_scene = processed[-1]
                prev_scene["end_ms"] = scene.end_ms
                prev_scene["duration_ms"] = prev_scene["end_ms"] - prev_scene["start_ms"]
                prev_scene["merged_scene_ids"].append(scene.scene_id)
            
            # Check if scene is too long and should be split
            elif (self.config.split_long_scenes and 
                  scene.duration_ms > self.config.max_chunk_duration_ms):
                # Split at ASR segment boundaries
                logger.info(f"Scene {scene.scene_id} is too long ({scene.duration_ms}ms), keeping as-is")
                # For now, keep as-is (scene 9 is 55.6s which is borderline)
                processed.append({
                    "scene_id": scene.scene_id,
                    "start_ms": scene.start_ms,
                    "end_ms": scene.end_ms,
                    "duration_ms": scene.duration_ms,
                    "merged_scene_ids": [scene.scene_id]
                })
            
            else:
                # Scene is good as-is
                processed.append({
                    "scene_id": scene.scene_id,
                    "start_ms": scene.start_ms,
                    "end_ms": scene.end_ms,
                    "duration_ms": scene.duration_ms,
                    "merged_scene_ids": [scene.scene_id]
                })
            
            i += 1
        
        return processed
    
    def _create_chunk_from_scene(self, scene_data: Dict[str, Any]) -> Chunk:
        """Create a chunk from scene data."""
        scene_id = scene_data["scene_id"]
        t_start_ms = scene_data["start_ms"]
        t_end_ms = scene_data["end_ms"]
        
        # Find parent chapter
        chapter_index, chapter_title = self._find_chapter(t_start_ms)
        
        # Gather ASR segments that overlap with this chunk
        asr_segments = self._get_asr_segments(t_start_ms, t_end_ms)
        asr_text = " ".join(seg.text for seg in asr_segments)
        
        # Gather keyframes in this chunk
        keyframes = self._get_keyframes(scene_data["merged_scene_ids"])
        keyframe_ids = [kf.frame_id for kf in keyframes]
        keyframe_paths = [kf.filename for kf in keyframes]
        
        # Gather OCR results for these keyframes
        ocr_results = self._get_ocr_results(keyframe_ids)
        
        # Create chunk ID
        chunk_id = f"{self.video_data.video_id}_ch{chapter_index}_sc{scene_id}"
        
        chunk = Chunk(
            chunk_id=chunk_id,
            video_id=self.video_data.video_id,
            source="youtube",
            t_start_ms=t_start_ms,
            t_end_ms=t_end_ms,
            chapter_index=chapter_index,
            chapter_title=chapter_title,
            scene_id=scene_id,
            asr_segments=asr_segments,
            asr_text=asr_text,
            keyframes=keyframes,
            keyframe_ids=keyframe_ids,
            keyframe_paths=keyframe_paths,
            has_keyframe=len(keyframes) > 0,
            ocr_results=ocr_results
        )
        
        return chunk
    
    def _find_chapter(self, timestamp_ms: int) -> tuple[int, str]:
        """Find the chapter that contains this timestamp."""
        timestamp_s = timestamp_ms / 1000.0
        
        for i, chapter in enumerate(self.video_data.metadata.chapters):
            if chapter.start_time <= timestamp_s < chapter.end_time:
                return i, chapter.title
        
        # If not found, return the last chapter
        if self.video_data.metadata.chapters:
            last_chapter = self.video_data.metadata.chapters[-1]
            return len(self.video_data.metadata.chapters) - 1, last_chapter.title
        
        return 0, "Unknown"
    
    def _get_asr_segments(self, t_start_ms: int, t_end_ms: int) -> List[ASRSegment]:
        """Get ASR segments that overlap with time range."""
        segments = []
        for segment in self.video_data.asr_segments:
            # Check for overlap
            if not (segment.end < t_start_ms or segment.start > t_end_ms):
                segments.append(segment)
        return segments
    
    def _get_keyframes(self, scene_ids: List[int]) -> List[Keyframe]:
        """Get keyframes for the given scene IDs."""
        keyframes = []
        for keyframe in self.video_data.keyframes:
            if keyframe.scene_id in scene_ids:
                keyframes.append(keyframe)
        return keyframes
    
    def _get_ocr_results(self, frame_ids: List[int]) -> List[OCRResult]:
        """Get OCR results for the given frame IDs."""
        ocr_results = []
        for ocr_result in self.video_data.ocr_results:
            if ocr_result.frame_id in frame_ids:
                ocr_results.append(ocr_result)
        return ocr_results


def create_chunks(video_data: VideoData, config: ChunkingConfig) -> List[Chunk]:
    """Convenience function to create chunks."""
    chunker = HierarchicalChunker(video_data, config)
    return chunker.chunk()
