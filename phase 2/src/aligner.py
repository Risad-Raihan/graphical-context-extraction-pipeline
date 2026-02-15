"""Slide-speech alignment scoring."""
import logging
from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.chunker import Chunk


logger = logging.getLogger(__name__)


class SlideSpeechAligner:
    """Align slide content with speech content."""
    
    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            min_df=1,
            max_df=0.95
        )
    
    def align(self) -> List[Chunk]:
        """Compute alignment scores and create merged text."""
        logger.info("Computing slide-speech alignment scores")
        
        for chunk in self.chunks:
            self._align_chunk(chunk)
        
        logger.info(f"Aligned {len(self.chunks)} chunks")
        return self.chunks
    
    def _align_chunk(self, chunk: Chunk):
        """Compute alignment for a single chunk."""
        # Handle empty cases
        if not chunk.asr_text and not chunk.ocr_text:
            chunk.alignment_score = 0.0
            chunk.merged_text = ""
            return
        
        if not chunk.asr_text:
            chunk.alignment_score = 0.0
            chunk.merged_text = f"[ON SCREEN] {chunk.ocr_text}"
            return
        
        if not chunk.ocr_text:
            chunk.alignment_score = 0.0
            chunk.merged_text = f"[SPOKEN] {chunk.asr_text}"
            return
        
        # Compute TF-IDF vectors
        try:
            texts = [chunk.asr_text, chunk.ocr_text]
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Compute cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            chunk.alignment_score = float(similarity)
        
        except Exception as e:
            logger.warning(f"Failed to compute alignment for chunk {chunk.chunk_id}: {e}")
            chunk.alignment_score = 0.0
        
        # Create merged text
        chunk.merged_text = self._create_merged_text(chunk)
    
    def _create_merged_text(self, chunk: Chunk) -> str:
        """Create merged text from ASR and OCR."""
        parts = []
        
        if chunk.asr_text:
            parts.append(f"[SPOKEN] {chunk.asr_text}")
        
        if chunk.ocr_text:
            parts.append(f"[ON SCREEN] {chunk.ocr_text}")
        
        return " ".join(parts)


def align_chunks(chunks: List[Chunk]) -> List[Chunk]:
    """Convenience function to align chunks."""
    aligner = SlideSpeechAligner(chunks)
    return aligner.align()
