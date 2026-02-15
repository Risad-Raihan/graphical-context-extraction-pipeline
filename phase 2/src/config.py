"""Configuration for Phase 2 pipeline."""
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class PathConfig:
    """Path configuration."""
    workspace_root: Path
    phase1_dir: Path
    phase2_dir: Path
    output_dir: Path
    
    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            workspace_root = Path(__file__).parent.parent.parent
        self.workspace_root = workspace_root
        self.phase1_dir = workspace_root / "phase 1"
        self.phase2_dir = workspace_root / "phase 2"
        self.output_dir = self.phase2_dir / "output"
    
    def get_phase1_video_dir(self, video_id: str) -> Path:
        """Get Phase 1 video directory."""
        return self.phase1_dir / video_id
    
    def get_output_dir(self, video_id: str) -> Path:
        """Get Phase 2 output directory for video."""
        return self.output_dir / video_id


@dataclass
class ChunkingConfig:
    """Chunking parameters."""
    min_chunk_duration_ms: int = 5000  # 5 seconds
    max_chunk_duration_ms: int = 60000  # 60 seconds
    merge_short_scenes: bool = True
    split_long_scenes: bool = True
    ui_chrome_threshold: float = 0.8  # 80% frequency to consider UI chrome
    text_overlap_threshold: float = 0.9  # 90% overlap for deduplication


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    text_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    text_dim: int = 384
    
    image_model: str = "ViT-B/32"
    image_dim: int = 512
    
    device: str = "cuda"
    batch_size: int = 8


@dataclass
class QdrantConfig:
    """Qdrant configuration."""
    # For local Qdrant
    host: Optional[str] = "localhost"
    port: Optional[int] = 6333
    
    # For Qdrant Cloud
    url: Optional[str] = None
    api_key: Optional[str] = None
    
    collection_name: str = "video_chunks"
    
    text_vector_name: str = "text"
    image_vector_name: str = "image"


@dataclass
class PipelineConfig:
    """Complete pipeline configuration."""
    paths: PathConfig
    chunking: ChunkingConfig
    embedding: EmbeddingConfig
    qdrant: QdrantConfig
    
    video_id: str
    skip_existing: bool = True
    verbose: bool = True
    
    def __init__(
        self,
        video_id: str,
        workspace_root: Optional[Path] = None,
        skip_existing: bool = True,
        verbose: bool = True
    ):
        self.video_id = video_id
        self.paths = PathConfig(workspace_root)
        self.chunking = ChunkingConfig()
        self.embedding = EmbeddingConfig()
        self.qdrant = QdrantConfig()
        self.skip_existing = skip_existing
        self.verbose = verbose
    
    def ensure_directories(self):
        """Create necessary directories."""
        self.paths.get_output_dir(self.video_id).mkdir(parents=True, exist_ok=True)
