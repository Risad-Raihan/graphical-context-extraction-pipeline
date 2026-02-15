"""Configuration management for the extraction pipeline."""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class PathConfig:
    """Path configuration for the pipeline."""
    workspace_root: Path
    data_dir: Path
    raw_dir: Path
    
    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            workspace_root = Path(__file__).parent.parent
        self.workspace_root = workspace_root
        self.data_dir = workspace_root / "data"
        self.raw_dir = self.data_dir / "raw"
    
    def get_video_dir(self, video_id: str) -> Path:
        """Get the directory for a specific video."""
        return self.raw_dir / video_id
    
    def get_source_dir(self, video_id: str) -> Path:
        """Get the source directory for raw downloads."""
        return self.get_video_dir(video_id) / "source"
    
    def get_normalized_dir(self, video_id: str) -> Path:
        """Get the normalized media directory."""
        return self.get_video_dir(video_id) / "normalized"
    
    def get_keyframes_dir(self, video_id: str) -> Path:
        """Get the keyframes directory."""
        return self.get_video_dir(video_id) / "keyframes"


@dataclass
class ModelConfig:
    """Model and processing configuration."""
    # Whisper settings
    whisper_model: str = "large-v3"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"
    
    # WhisperX settings
    whisperx_align: bool = True
    whisperx_diarize: bool = False
    whisperx_batch_size: int = 16
    
    # Scene detection settings
    scene_threshold: float = 27.0  # PySceneDetect ContentDetector threshold
    min_scene_len: float = 0.3  # minimum scene length in seconds
    
    # Keyframe extraction settings
    blur_threshold: float = 100.0  # Laplacian variance threshold
    long_scene_threshold: float = 30.0  # seconds
    long_scene_sample_interval: float = 5.0  # seconds
    pixel_delta_threshold: float = 0.15  # fraction of pixels changed
    
    # OCR settings
    ocr_lang: str = "en"
    ocr_use_gpu: bool = True
    ocr_conf_threshold: float = 0.5
    
    # Layout parser settings
    layout_model: str = "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config"
    layout_conf_threshold: float = 0.5
    
    # Media normalization settings
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    video_fps: Optional[int] = None  # None = keep original
    video_codec: str = "libx264"
    video_preset: str = "medium"


@dataclass
class PipelineConfig:
    """Complete pipeline configuration."""
    paths: PathConfig
    models: ModelConfig
    video_url: str
    video_id: str
    
    # Processing flags
    skip_existing: bool = True
    verbose: bool = True
    
    def __init__(
        self,
        video_url: str,
        workspace_root: Optional[Path] = None,
        model_config: Optional[ModelConfig] = None,
        skip_existing: bool = True,
        verbose: bool = True
    ):
        self.video_url = video_url
        self.video_id = self.extract_video_id(video_url)
        self.paths = PathConfig(workspace_root)
        self.models = model_config or ModelConfig()
        self.skip_existing = skip_existing
        self.verbose = verbose
    
    @staticmethod
    def extract_video_id(url: str) -> str:
        """Extract video ID from YouTube URL."""
        # Match various YouTube URL formats
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'^([0-9A-Za-z_-]{11})$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    def ensure_directories(self):
        """Create all necessary directories."""
        self.paths.get_source_dir(self.video_id).mkdir(parents=True, exist_ok=True)
        self.paths.get_normalized_dir(self.video_id).mkdir(parents=True, exist_ok=True)
        self.paths.get_keyframes_dir(self.video_id).mkdir(parents=True, exist_ok=True)
