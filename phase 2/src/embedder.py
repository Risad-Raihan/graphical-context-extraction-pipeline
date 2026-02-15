"""Generate text and image embeddings for chunks."""
import logging
from typing import List, Optional
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer
import open_clip

from src.chunker import Chunk
from src.config import EmbeddingConfig


logger = logging.getLogger(__name__)


class ChunkEmbedder:
    """Generate embeddings for chunks."""
    
    def __init__(self, config: EmbeddingConfig, phase1_dir: Path):
        self.config = config
        self.phase1_dir = phase1_dir
        self.device = torch.device(config.device if torch.cuda.is_available() else "cpu")
        
        logger.info(f"Using device: {self.device}")
        
        # Load models
        logger.info(f"Loading text model: {config.text_model}")
        self.text_model = SentenceTransformer(config.text_model, device=str(self.device))
        
        logger.info(f"Loading image model: {config.image_model}")
        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
            config.image_model,
            pretrained='openai',
            device=self.device
        )
        self.clip_model.eval()
    
    def embed(self, chunks: List[Chunk]) -> List[Chunk]:
        """Generate embeddings for all chunks."""
        logger.info("Generating embeddings")
        
        # Generate text embeddings
        self._embed_text(chunks)
        
        # Generate image embeddings
        self._embed_images(chunks)
        
        logger.info(f"Generated embeddings for {len(chunks)} chunks")
        return chunks
    
    def _embed_text(self, chunks: List[Chunk]):
        """Generate text embeddings."""
        logger.info("Generating text embeddings")
        
        # Collect all texts
        texts = [chunk.merged_text if chunk.merged_text else "" for chunk in chunks]
        
        # Generate embeddings in batches
        embeddings = self.text_model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Attach to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.text_embedding = embedding
    
    def _embed_images(self, chunks: List[Chunk]):
        """Generate image embeddings."""
        logger.info("Generating image embeddings")
        
        for chunk in chunks:
            if not chunk.has_keyframe:
                # No keyframes, use zero vector
                chunk.image_embedding = np.zeros(self.config.image_dim, dtype=np.float32)
                continue
            
            # Load and process keyframe images
            keyframe_embeddings = []
            
            for keyframe in chunk.keyframes:
                try:
                    # Load image
                    image_path = Path(keyframe.path)
                    image = Image.open(image_path).convert('RGB')
                    
                    # Preprocess and embed
                    image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
                    
                    with torch.no_grad():
                        image_features = self.clip_model.encode_image(image_tensor)
                        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                        embedding = image_features.cpu().numpy()[0]
                    
                    keyframe_embeddings.append(embedding)
                
                except Exception as e:
                    logger.warning(f"Failed to embed keyframe {keyframe.filename}: {e}")
            
            if keyframe_embeddings:
                # Average embeddings across keyframes
                chunk.image_embedding = np.mean(keyframe_embeddings, axis=0).astype(np.float32)
            else:
                # No valid keyframes, use zero vector
                chunk.image_embedding = np.zeros(self.config.image_dim, dtype=np.float32)


def embed_chunks(chunks: List[Chunk], config: EmbeddingConfig, phase1_dir: Path) -> List[Chunk]:
    """Convenience function to embed chunks."""
    embedder = ChunkEmbedder(config, phase1_dir)
    return embedder.embed(chunks)
