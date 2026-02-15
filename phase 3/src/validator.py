"""Extraction quality validation and coverage analysis"""
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import logging

from .loader import VideoData

logger = logging.getLogger(__name__)


@dataclass
class TimeWindow:
    """Time window for coverage analysis"""
    start_ms: int
    end_ms: int
    has_asr: bool
    has_keyframe: bool
    has_ocr: bool


@dataclass
class ChapterCoverage:
    """Coverage stats for a chapter"""
    chapter_idx: int
    title: str
    duration_sec: float
    num_scenes: int
    num_keyframes: int
    num_asr_segments: int
    num_ocr_blocks: int
    coverage_pct: float


@dataclass
class Gap:
    """Detected gap in extraction"""
    gap_type: str  # "keyframe", "asr", "ocr"
    start_ms: int
    end_ms: int
    duration_sec: float
    severity: str  # "high", "medium", "low"


@dataclass
class QualityFlag:
    """Quality issue flag"""
    flag_type: str
    severity: str
    description: str
    location: str  # keyframe path, chunk_id, etc.


@dataclass
class ValidationReport:
    """Complete validation report"""
    video_id: str
    video_duration_sec: float
    
    # Coverage stats
    overall_coverage_pct: float
    timeline_windows: List[TimeWindow]
    chapter_coverage: List[ChapterCoverage]
    
    # Gaps
    keyframe_gaps: List[Gap]
    asr_gaps: List[Gap]
    
    # Quality flags
    quality_flags: List[QualityFlag]
    
    # Content density
    richest_chunks: List[Dict[str, Any]]
    thinnest_chunks: List[Dict[str, Any]]
    
    # Summary
    num_total_keyframes: int
    num_total_asr_segments: int
    num_total_ocr_blocks: int
    num_total_chunks: int


class ExtractionValidator:
    """Validate extraction quality and coverage"""
    
    def __init__(
        self, 
        coverage_window_sec: int = 5,
        keyframe_gap_threshold_sec: int = 15,
        ocr_high_conf: float = 0.8,
        ocr_low_conf: float = 0.5,
        min_ocr_text_length: int = 10
    ):
        self.coverage_window_sec = coverage_window_sec
        self.keyframe_gap_threshold_sec = keyframe_gap_threshold_sec
        self.ocr_high_conf = ocr_high_conf
        self.ocr_low_conf = ocr_low_conf
        self.min_ocr_text_length = min_ocr_text_length
    
    def validate(self, video_data: VideoData) -> ValidationReport:
        """Run full validation on video data"""
        logger.info(f"Starting validation for {video_data.video_id}")
        
        # Timeline coverage analysis
        timeline_windows = self._analyze_timeline_coverage(video_data)
        overall_coverage = self._calculate_overall_coverage(timeline_windows)
        
        # Chapter coverage
        chapter_coverage = self._analyze_chapter_coverage(video_data)
        
        # Gap detection
        keyframe_gaps = self._detect_keyframe_gaps(video_data)
        asr_gaps = self._detect_asr_gaps(video_data)
        
        # Quality flags
        quality_flags = self._detect_quality_issues(video_data)
        
        # Content density analysis
        richest, thinnest = self._analyze_content_density(video_data)
        
        report = ValidationReport(
            video_id=video_data.video_id,
            video_duration_sec=video_data.metadata.duration_sec,
            overall_coverage_pct=overall_coverage,
            timeline_windows=timeline_windows,
            chapter_coverage=chapter_coverage,
            keyframe_gaps=keyframe_gaps,
            asr_gaps=asr_gaps,
            quality_flags=quality_flags,
            richest_chunks=richest,
            thinnest_chunks=thinnest,
            num_total_keyframes=len(video_data.keyframes),
            num_total_asr_segments=len(video_data.asr_segments),
            num_total_ocr_blocks=len(video_data.ocr_blocks),
            num_total_chunks=len(video_data.chunks)
        )
        
        logger.info(f"Validation complete: {overall_coverage:.1f}% coverage, "
                   f"{len(keyframe_gaps)} keyframe gaps, {len(quality_flags)} quality flags")
        
        return report
    
    def _analyze_timeline_coverage(self, video_data: VideoData) -> List[TimeWindow]:
        """Break video into time windows and check coverage"""
        windows = []
        duration_ms = int(video_data.metadata.duration_sec * 1000)
        window_ms = self.coverage_window_sec * 1000
        
        for start_ms in range(0, duration_ms, window_ms):
            end_ms = min(start_ms + window_ms, duration_ms)
            
            # Check for ASR in this window
            has_asr = any(
                seg.start_ms < end_ms and seg.end_ms > start_ms
                for seg in video_data.asr_segments
            )
            
            # Check for keyframe in this window
            has_keyframe = any(
                start_ms <= kf.timestamp_ms < end_ms
                for kf in video_data.keyframes
            )
            
            # Check for OCR (via keyframes with OCR blocks)
            keyframe_paths_in_window = {
                str(kf.path) for kf in video_data.keyframes
                if start_ms <= kf.timestamp_ms < end_ms
            }
            has_ocr = any(
                block.keyframe_path in keyframe_paths_in_window or
                Path(block.keyframe_path).name in {Path(p).name for p in keyframe_paths_in_window}
                for block in video_data.ocr_blocks
            )
            
            windows.append(TimeWindow(
                start_ms=start_ms,
                end_ms=end_ms,
                has_asr=has_asr,
                has_keyframe=has_keyframe,
                has_ocr=has_ocr
            ))
        
        return windows
    
    def _calculate_overall_coverage(self, windows: List[TimeWindow]) -> float:
        """Calculate overall coverage percentage"""
        if not windows:
            return 0.0
        
        covered = sum(1 for w in windows if w.has_asr or w.has_keyframe)
        return (covered / len(windows)) * 100
    
    def _analyze_chapter_coverage(self, video_data: VideoData) -> List[ChapterCoverage]:
        """Analyze coverage per chapter"""
        coverage = []
        
        for i, chapter in enumerate(video_data.metadata.chapters):
            # Count elements in this chapter
            num_scenes = sum(
                1 for scene in video_data.scenes
                if scene.start_ms >= chapter.start_ms and scene.end_ms <= chapter.end_ms
            )
            
            num_keyframes = sum(
                1 for kf in video_data.keyframes
                if chapter.start_ms <= kf.timestamp_ms < chapter.end_ms
            )
            
            num_asr = sum(
                1 for seg in video_data.asr_segments
                if seg.start_ms < chapter.end_ms and seg.end_ms > chapter.start_ms
            )
            
            # OCR blocks (via keyframes in chapter)
            keyframe_paths = {
                str(kf.path) for kf in video_data.keyframes
                if chapter.start_ms <= kf.timestamp_ms < chapter.end_ms
            }
            num_ocr = sum(
                1 for block in video_data.ocr_blocks
                if block.keyframe_path in keyframe_paths or
                Path(block.keyframe_path).name in {Path(p).name for p in keyframe_paths}
            )
            
            # Coverage: chapters with keyframes and ASR
            chapter_duration_sec = (chapter.end_ms - chapter.start_ms) / 1000
            has_data = num_keyframes > 0 and num_asr > 0
            coverage_pct = 100.0 if has_data else 0.0
            
            coverage.append(ChapterCoverage(
                chapter_idx=i,
                title=chapter.title,
                duration_sec=chapter_duration_sec,
                num_scenes=num_scenes,
                num_keyframes=num_keyframes,
                num_asr_segments=num_asr,
                num_ocr_blocks=num_ocr,
                coverage_pct=coverage_pct
            ))
        
        return coverage
    
    def _detect_keyframe_gaps(self, video_data: VideoData) -> List[Gap]:
        """Detect gaps in keyframe coverage"""
        gaps = []
        
        if not video_data.keyframes:
            return gaps
        
        # Sort keyframes by timestamp
        sorted_kf = sorted(video_data.keyframes, key=lambda k: k.timestamp_ms)
        
        for i in range(len(sorted_kf) - 1):
            gap_ms = sorted_kf[i + 1].timestamp_ms - sorted_kf[i].timestamp_ms
            gap_sec = gap_ms / 1000
            
            if gap_sec > self.keyframe_gap_threshold_sec:
                severity = "high" if gap_sec > 30 else "medium"
                gaps.append(Gap(
                    gap_type="keyframe",
                    start_ms=sorted_kf[i].timestamp_ms,
                    end_ms=sorted_kf[i + 1].timestamp_ms,
                    duration_sec=gap_sec,
                    severity=severity
                ))
        
        return gaps
    
    def _detect_asr_gaps(self, video_data: VideoData) -> List[Gap]:
        """Detect gaps in ASR coverage"""
        gaps = []
        
        if not video_data.asr_segments:
            return gaps
        
        # Sort by start time
        sorted_asr = sorted(video_data.asr_segments, key=lambda s: s.start_ms)
        
        for i in range(len(sorted_asr) - 1):
            gap_ms = sorted_asr[i + 1].start_ms - sorted_asr[i].end_ms
            
            if gap_ms > 5000:  # 5 second gap
                gap_sec = gap_ms / 1000
                severity = "low"  # ASR gaps are often just silence
                gaps.append(Gap(
                    gap_type="asr",
                    start_ms=sorted_asr[i].end_ms,
                    end_ms=sorted_asr[i + 1].start_ms,
                    duration_sec=gap_sec,
                    severity=severity
                ))
        
        return gaps
    
    def _detect_quality_issues(self, video_data: VideoData) -> List[QualityFlag]:
        """Detect quality issues"""
        flags = []
        
        # Group OCR by keyframe
        ocr_by_kf = {}
        for block in video_data.ocr_blocks:
            key = Path(block.keyframe_path).name
            if key not in ocr_by_kf:
                ocr_by_kf[key] = []
            ocr_by_kf[key].append(block)
        
        # Check each keyframe
        for keyframe in video_data.keyframes:
            kf_name = keyframe.path.name
            ocr_blocks = ocr_by_kf.get(kf_name, [])
            
            # Flag keyframes with no OCR text
            if not ocr_blocks:
                flags.append(QualityFlag(
                    flag_type="no_ocr",
                    severity="medium",
                    description="No OCR text extracted from keyframe",
                    location=str(keyframe.path)
                ))
                continue
            
            # Flag keyframes with very little text
            total_text = " ".join(b.text for b in ocr_blocks)
            if len(total_text) < self.min_ocr_text_length:
                flags.append(QualityFlag(
                    flag_type="low_ocr_text",
                    severity="low",
                    description=f"Very little OCR text ({len(total_text)} chars)",
                    location=str(keyframe.path)
                ))
            
            # Flag low confidence OCR
            low_conf_blocks = [b for b in ocr_blocks if b.confidence < self.ocr_low_conf]
            if low_conf_blocks:
                flags.append(QualityFlag(
                    flag_type="low_ocr_confidence",
                    severity="low",
                    description=f"{len(low_conf_blocks)} OCR blocks with confidence < {self.ocr_low_conf}",
                    location=str(keyframe.path)
                ))
        
        # Check chunks without visual content
        for chunk in video_data.chunks:
            if not chunk.has_visual:
                flags.append(QualityFlag(
                    flag_type="no_visual",
                    severity="high",
                    description="Chunk has no visual content",
                    location=chunk.chunk_id
                ))
            
            if not chunk.has_speech:
                flags.append(QualityFlag(
                    flag_type="no_speech",
                    severity="medium",
                    description="Chunk has no speech",
                    location=chunk.chunk_id
                ))
        
        return flags
    
    def _analyze_content_density(self, video_data: VideoData) -> Tuple[List[Dict], List[Dict]]:
        """Identify richest and thinnest chunks"""
        # Score each chunk by total text length
        scored_chunks = []
        for chunk in video_data.chunks:
            total_text = len(chunk.asr_text) + len(chunk.ocr_text_cleaned)
            scored_chunks.append({
                "chunk_id": chunk.chunk_id,
                "total_text_chars": total_text,
                "asr_chars": len(chunk.asr_text),
                "ocr_chars": len(chunk.ocr_text_cleaned),
                "duration_sec": chunk.duration_sec,
                "density": total_text / chunk.duration_sec if chunk.duration_sec > 0 else 0
            })
        
        # Sort by total text
        scored_chunks.sort(key=lambda x: x["total_text_chars"], reverse=True)
        
        richest = scored_chunks[:3]  # Top 3
        thinnest = scored_chunks[-3:]  # Bottom 3
        
        return richest, thinnest
    
    def save_report(self, report: ValidationReport, output_path: Path):
        """Save validation report to JSON"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict
        report_dict = asdict(report)
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        logger.info(f"Saved validation report to {output_path}")
