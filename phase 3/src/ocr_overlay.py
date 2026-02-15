"""Draw OCR bounding boxes on keyframes"""
from pathlib import Path
from typing import List, Dict
import logging
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from .loader import VideoData, OCRBlock, Keyframe

logger = logging.getLogger(__name__)


class OCROverlayGenerator:
    """Generate keyframe images with OCR bounding box overlays"""
    
    def __init__(self, high_conf_threshold: float = 0.8, low_conf_threshold: float = 0.5):
        self.high_conf_threshold = high_conf_threshold
        self.low_conf_threshold = low_conf_threshold
    
    def generate(self, video_data: VideoData, output_dir: Path) -> Dict[str, Path]:
        """
        Generate annotated keyframes with OCR bounding boxes
        
        Returns:
            Dict mapping original keyframe path to annotated image path
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Group OCR blocks by keyframe
        ocr_by_keyframe = self._group_ocr_by_keyframe(video_data.ocr_blocks)
        
        annotated_paths = {}
        
        for keyframe in video_data.keyframes:
            try:
                # Get OCR blocks for this keyframe using filename
                keyframe_name = keyframe.path.name
                ocr_blocks = ocr_by_keyframe.get(keyframe_name, [])
                
                # Annotate the keyframe
                annotated_path = self._annotate_keyframe(
                    keyframe, ocr_blocks, output_dir
                )
                
                annotated_paths[str(keyframe.path)] = annotated_path
                
                logger.info(f"Annotated {keyframe.path.name} with {len(ocr_blocks)} OCR boxes")
            
            except Exception as e:
                logger.error(f"Failed to annotate {keyframe.path}: {e}")
        
        logger.info(f"Generated {len(annotated_paths)} annotated keyframes")
        return annotated_paths
    
    def _group_ocr_by_keyframe(self, ocr_blocks: List[OCRBlock]) -> Dict[str, List[OCRBlock]]:
        """Group OCR blocks by keyframe path"""
        grouped = {}
        for block in ocr_blocks:
            # Use only the filename as key for matching
            key = Path(block.keyframe_path).name
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(block)
        
        return grouped
    
    def _annotate_keyframe(
        self, 
        keyframe: Keyframe, 
        ocr_blocks: List[OCRBlock], 
        output_dir: Path
    ) -> Path:
        """Annotate a single keyframe with OCR bounding boxes"""
        # Load image
        img = Image.open(keyframe.path).convert("RGB")
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        # Draw each OCR block
        for block in ocr_blocks:
            # Get color based on confidence
            color = self._get_confidence_color(block.confidence)
            
            # Draw bounding box
            bbox_points = [tuple(point) for point in block.bbox]
            draw.polygon(bbox_points, outline=color, width=2)
            
            # Draw confidence label at top-left of bbox
            if bbox_points:
                label = f"{block.confidence:.2f}"
                x, y = bbox_points[0]
                
                # Draw background for text
                bbox = draw.textbbox((x, y - 15), label, font=font)
                draw.rectangle(bbox, fill=color)
                draw.text((x, y - 15), label, fill="white", font=font)
        
        # Save annotated image
        output_path = output_dir / f"{keyframe.path.stem}_annotated.jpg"
        img.save(output_path, quality=95)
        
        return output_path
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get color based on OCR confidence"""
        if confidence >= self.high_conf_threshold:
            return "#00FF00"  # Green
        elif confidence >= self.low_conf_threshold:
            return "#FFFF00"  # Yellow
        else:
            return "#FF0000"  # Red
