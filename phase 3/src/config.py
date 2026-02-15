"""Configuration for Phase 3"""
from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class PathConfig:
    """Path configuration"""
    # Project root
    project_root: Path = Path(__file__).parent.parent.parent
    
    # Phase 1 paths
    phase1_root: Path = project_root / "phase 1"
    
    # Phase 2 paths
    phase2_root: Path = project_root / "phase 2"
    
    # Output directory
    output_dir: Path = project_root / "phase 3" / "output"
    
    def get_phase1_video_dir(self, video_id: str) -> Path:
        """Get Phase 1 video directory"""
        return self.phase1_root / video_id
    
    def get_phase2_video_dir(self, video_id: str) -> Path:
        """Get Phase 2 output directory"""
        return self.phase2_root / "output" / video_id
    
    def get_phase3_video_dir(self, video_id: str) -> Path:
        """Get Phase 3 output directory"""
        return self.output_dir / video_id


@dataclass
class LLMConfig:
    """LLM configuration for Q&A generation"""
    api_key: str = os.getenv("GEMINI_API_KEY", "AIzaSyA60O0JuSLjbQQxdDabDiH5t4XiuO1AqdI")
    model: str = "gemini-3-pro-preview"  # As specified by user
    max_qa_pairs_per_chunk: int = 5
    temperature: float = 0.7


@dataclass
class ValidationConfig:
    """Validation configuration"""
    # Timeline coverage window (seconds)
    coverage_window_sec: int = 5
    
    # Keyframe gap threshold (seconds)
    keyframe_gap_threshold_sec: int = 15
    
    # OCR confidence thresholds
    ocr_high_conf: float = 0.8
    ocr_low_conf: float = 0.5
    
    # Minimum OCR text length to flag as potential issue
    min_ocr_text_length: int = 10


@dataclass
class Config:
    """Master configuration"""
    paths: PathConfig = field(default_factory=PathConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
