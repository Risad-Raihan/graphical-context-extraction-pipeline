"""OCR cleanup: filter UI chrome and deduplicate text."""
import logging
from typing import List, Dict, Set
from collections import Counter

from src.chunker import Chunk
from src.loader import OCRBlock
from src.config import ChunkingConfig


logger = logging.getLogger(__name__)


class OCRCleaner:
    """Clean OCR text by removing UI chrome and duplicates."""
    
    def __init__(self, chunks: List[Chunk], config: ChunkingConfig):
        self.chunks = chunks
        self.config = config
        self.ui_chrome_tokens: Set[str] = set()
    
    def clean(self) -> List[Chunk]:
        """Clean OCR text for all chunks."""
        logger.info("Cleaning OCR text")
        
        # Identify UI chrome tokens
        self._identify_ui_chrome()
        
        # Clean each chunk
        for chunk in self.chunks:
            self._clean_chunk(chunk)
        
        logger.info(f"Cleaned {len(self.chunks)} chunks")
        return self.chunks
    
    def _identify_ui_chrome(self):
        """Identify UI chrome by finding tokens that appear in most frames."""
        # Count token appearances across all frames
        token_counter = Counter()
        total_frames = 0
        
        for chunk in self.chunks:
            for ocr_result in chunk.ocr_results:
                total_frames += 1
                # Extract tokens from each text block
                for block in ocr_result.text_blocks:
                    tokens = block.text.lower().split()
                    token_counter.update(tokens)
        
        if total_frames == 0:
            return
        
        # Find tokens that appear in >= threshold% of frames
        threshold_count = total_frames * self.config.ui_chrome_threshold
        
        for token, count in token_counter.items():
            if count >= threshold_count:
                self.ui_chrome_tokens.add(token)
                logger.debug(f"Identified UI chrome token: '{token}' (appears in {count}/{total_frames} frames)")
        
        logger.info(f"Identified {len(self.ui_chrome_tokens)} UI chrome tokens")
    
    def _clean_chunk(self, chunk: Chunk):
        """Clean OCR text for a single chunk."""
        if not chunk.ocr_results:
            chunk.ocr_text = ""
            return
        
        # Deduplicate OCR results (remove consecutive frames with high overlap)
        unique_ocr_results = self._deduplicate_ocr_results(chunk.ocr_results)
        
        # Extract clean text from each unique OCR result
        clean_texts = []
        for ocr_result in unique_ocr_results:
            clean_text = self._extract_clean_text(ocr_result.text_blocks)
            if clean_text:
                clean_texts.append(clean_text)
        
        # Join all clean texts
        chunk.ocr_text = " | ".join(clean_texts)
    
    def _deduplicate_ocr_results(self, ocr_results: List) -> List:
        """Remove consecutive OCR results with high text overlap."""
        if len(ocr_results) <= 1:
            return ocr_results
        
        unique = [ocr_results[0]]
        
        for i in range(1, len(ocr_results)):
            current = ocr_results[i]
            previous = unique[-1]
            
            # Calculate text overlap
            current_text = set(current.full_text.lower().split())
            previous_text = set(previous.full_text.lower().split())
            
            if not current_text or not previous_text:
                unique.append(current)
                continue
            
            overlap = len(current_text & previous_text) / max(len(current_text), len(previous_text))
            
            if overlap < self.config.text_overlap_threshold:
                # Not enough overlap, keep this result
                unique.append(current)
            else:
                # High overlap, keep the one with higher confidence
                current_conf = sum(b.confidence for b in current.text_blocks) / max(len(current.text_blocks), 1)
                previous_conf = sum(b.confidence for b in previous.text_blocks) / max(len(previous.text_blocks), 1)
                
                if current_conf > previous_conf:
                    # Replace previous with current
                    unique[-1] = current
        
        return unique
    
    def _extract_clean_text(self, text_blocks: List[OCRBlock]) -> str:
        """Extract clean text from OCR blocks, filtering UI chrome."""
        # Sort blocks by position (top to bottom, left to right)
        sorted_blocks = sorted(text_blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
        
        # Extract text, filtering UI chrome
        clean_texts = []
        for block in sorted_blocks:
            # Check if block contains only UI chrome
            tokens = block.text.lower().split()
            non_chrome_tokens = [t for t in tokens if t not in self.ui_chrome_tokens]
            
            if non_chrome_tokens:
                # Has non-chrome content, keep it
                clean_texts.append(block.text)
        
        return " ".join(clean_texts)


def clean_ocr_text(chunks: List[Chunk], config: ChunkingConfig) -> List[Chunk]:
    """Convenience function to clean OCR text."""
    cleaner = OCRCleaner(chunks, config)
    return cleaner.clean()
