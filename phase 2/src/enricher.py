"""Metadata enrichment: quality scores, provenance, completeness flags."""
import logging
from typing import List

from src.chunker import Chunk
from src.loader import VideoData


logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Enrich chunks with quality scores and provenance."""
    
    def __init__(self, chunks: List[Chunk], video_data: VideoData):
        self.chunks = chunks
        self.video_data = video_data
    
    def enrich(self) -> List[Chunk]:
        """Enrich all chunks."""
        logger.info("Enriching chunk metadata")
        
        for chunk in self.chunks:
            self._enrich_chunk(chunk)
        
        logger.info(f"Enriched {len(self.chunks)} chunks")
        return self.chunks
    
    def _enrich_chunk(self, chunk: Chunk):
        """Enrich a single chunk."""
        # Compute quality scores
        chunk.asr_confidence = self._compute_asr_confidence(chunk)
        chunk.ocr_confidence = self._compute_ocr_confidence(chunk)
        
        # Set completeness flags
        chunk.completeness = {
            "has_speech": len(chunk.asr_segments) > 0,
            "has_visual": len(chunk.keyframes) > 0,
            "has_ocr_text": bool(chunk.ocr_text)
        }
        
        # Set provenance
        chunk.provenance = {
            "video_title": self.video_data.metadata.title,
            "channel": self.video_data.metadata.channel,
            "publish_date": self.video_data.metadata.upload_date,
            "tags": self.video_data.metadata.tags,
            "video_description": self.video_data.metadata.description[:500] if self.video_data.metadata.description else ""
        }
    
    def _compute_asr_confidence(self, chunk: Chunk) -> float:
        """Compute average ASR confidence for the chunk."""
        if not chunk.asr_segments:
            return 0.0
        
        total_confidence = 0.0
        total_words = 0
        
        for segment in chunk.asr_segments:
            for word in segment.words:
                if "score" in word:
                    total_confidence += word["score"]
                    total_words += 1
        
        if total_words == 0:
            return 0.0
        
        return total_confidence / total_words
    
    def _compute_ocr_confidence(self, chunk: Chunk) -> float:
        """Compute average OCR confidence for the chunk."""
        if not chunk.ocr_results:
            return 0.0
        
        total_confidence = 0.0
        total_blocks = 0
        
        for ocr_result in chunk.ocr_results:
            for block in ocr_result.text_blocks:
                total_confidence += block.confidence
                total_blocks += 1
        
        if total_blocks == 0:
            return 0.0
        
        return total_confidence / total_blocks


def enrich_chunks(chunks: List[Chunk], video_data: VideoData) -> List[Chunk]:
    """Convenience function to enrich chunks."""
    enricher = MetadataEnricher(chunks, video_data)
    return enricher.enrich()
