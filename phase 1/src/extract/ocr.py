"""OCR and layout parsing on keyframes."""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
import easyocr
try:
    import layoutparser as lp
    LAYOUTPARSER_AVAILABLE = True
except ImportError:
    LAYOUTPARSER_AVAILABLE = False
    logging.warning("LayoutParser not available. Layout parsing will be skipped.")


logger = logging.getLogger(__name__)


class OCRProcessor:
    """Process keyframes with OCR and layout analysis."""
    
    def __init__(
        self,
        lang: str = "en",
        use_gpu: bool = True,
        conf_threshold: float = 0.5,
        layout_model: Optional[str] = None,
        layout_conf_threshold: float = 0.5
    ):
        """
        Initialize OCR processor.
        
        Args:
            lang: OCR language
            use_gpu: Whether to use GPU for OCR
            conf_threshold: Confidence threshold for OCR results
            layout_model: LayoutParser model name
            layout_conf_threshold: Confidence threshold for layout detection
        """
        self.lang = lang
        self.use_gpu = use_gpu
        self.conf_threshold = conf_threshold
        self.layout_model_name = layout_model
        self.layout_conf_threshold = layout_conf_threshold
        
        # Initialize EasyOCR
        logger.info("Initializing EasyOCR...")
        self.ocr = easyocr.Reader([lang], gpu=use_gpu)
        
        # Initialize LayoutParser if available
        self.layout_model = None
        if LAYOUTPARSER_AVAILABLE and layout_model:
            try:
                logger.info(f"Initializing LayoutParser with model: {layout_model}")
                self.layout_model = lp.Detectron2LayoutModel(
                    layout_model,
                    extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", layout_conf_threshold],
                    label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"}
                )
            except Exception as e:
                logger.warning(f"Could not load LayoutParser model: {e}")
                self.layout_model = None
    
    def process(
        self,
        keyframes_data: Dict[str, Any],
        output_dir: Path,
        skip_if_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Process all keyframes with OCR and layout analysis.
        
        Args:
            keyframes_data: Keyframe extraction results
            output_dir: Directory containing keyframes
            skip_if_exists: Skip if output already exists
            
        Returns:
            Dictionary containing OCR results for all keyframes
        """
        ocr_json_path = output_dir.parent / "ocr.json"
        
        # Check if already processed
        if skip_if_exists and ocr_json_path.exists():
            logger.info(f"OCR results already exist at {ocr_json_path}, skipping")
            with open(ocr_json_path, 'r') as f:
                return json.load(f)
        
        logger.info(f"Processing {len(keyframes_data['keyframes'])} keyframes with OCR")
        
        ocr_results = []
        
        for i, keyframe in enumerate(keyframes_data['keyframes']):
            frame_path = Path(keyframe['path'])
            
            if not frame_path.exists():
                logger.warning(f"Keyframe not found: {frame_path}")
                continue
            
            logger.info(f"Processing keyframe {i+1}/{len(keyframes_data['keyframes'])}: {frame_path.name}")
            
            # Process single keyframe
            result = self._process_keyframe(
                frame_path,
                keyframe['frame_id'],
                keyframe['timestamp_ms'],
                keyframe['scene_id']
            )
            
            ocr_results.append(result)
        
        # Prepare final output
        output = {
            "total_keyframes": len(ocr_results),
            "ocr_lang": self.lang,
            "conf_threshold": self.conf_threshold,
            "layout_model": self.layout_model_name if self.layout_model else None,
            "results": ocr_results
        }
        
        # Save to JSON
        with open(ocr_json_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"OCR processing complete. Results saved to {ocr_json_path}")
        
        return output
    
    def _process_keyframe(
        self,
        frame_path: Path,
        frame_id: int,
        timestamp_ms: int,
        scene_id: int
    ) -> Dict[str, Any]:
        """Process a single keyframe."""
        # Read image
        image = cv2.imread(str(frame_path))
        height, width = image.shape[:2]
        
        # Run OCR
        ocr_blocks = self._run_ocr(image)
        
        # Run layout detection if available
        layout_regions = []
        if self.layout_model is not None:
            layout_regions = self._run_layout_detection(image)
        
        # Merge text blocks with layout regions
        full_text = self._extract_full_text(ocr_blocks)
        
        return {
            "frame_id": frame_id,
            "timestamp_ms": timestamp_ms,
            "scene_id": scene_id,
            "image_path": str(frame_path),
            "width": width,
            "height": height,
            "text_blocks": ocr_blocks,
            "layout_regions": layout_regions,
            "full_text": full_text,
            "total_blocks": len(ocr_blocks),
            "total_regions": len(layout_regions)
        }
    
    def _run_ocr(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Run EasyOCR on image."""
        result = self.ocr.readtext(image)
        
        if not result:
            return []
        
        text_blocks = []
        
        for detection in result:
            # EasyOCR format: (bbox, text, confidence)
            bbox = detection[0]  # 4 points [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = detection[1]
            conf = detection[2]
            
            # Skip low confidence results
            if conf < self.conf_threshold:
                continue
            
            # Convert bbox to simpler format [x_min, y_min, x_max, y_max]
            x_coords = [float(point[0]) for point in bbox]
            y_coords = [float(point[1]) for point in bbox]
            bbox_simple = [
                float(min(x_coords)),
                float(min(y_coords)),
                float(max(x_coords)),
                float(max(y_coords))
            ]
            
            # Convert bbox_polygon to list of lists with native Python floats
            bbox_polygon = [[float(point[0]), float(point[1])] for point in bbox]
            
            text_blocks.append({
                "text": text,
                "bbox": bbox_simple,
                "bbox_polygon": bbox_polygon,
                "confidence": float(conf)
            })
        
        return text_blocks
    
    def _run_layout_detection(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Run LayoutParser layout detection."""
        try:
            # Convert BGR to RGB for layoutparser
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect layout
            layout = self.layout_model.detect(image_rgb)
            
            regions = []
            for block in layout:
                regions.append({
                    "type": block.type,
                    "bbox": [
                        float(block.block.x_1),
                        float(block.block.y_1),
                        float(block.block.x_2),
                        float(block.block.y_2)
                    ],
                    "confidence": float(block.score) if hasattr(block, 'score') else 1.0
                })
            
            return regions
        
        except Exception as e:
            logger.warning(f"Layout detection failed: {e}")
            return []
    
    def _extract_full_text(self, text_blocks: List[Dict[str, Any]]) -> str:
        """Extract full text from OCR blocks in reading order."""
        if not text_blocks:
            return ""
        
        # Sort blocks by vertical position (top to bottom), then horizontal (left to right)
        sorted_blocks = sorted(
            text_blocks,
            key=lambda b: (b['bbox'][1], b['bbox'][0])  # y_min, then x_min
        )
        
        # Join text with spaces
        full_text = " ".join(block['text'] for block in sorted_blocks)
        
        return full_text


def process_ocr(
    keyframes_data: Dict[str, Any],
    output_dir: Path,
    lang: str = "en",
    use_gpu: bool = True,
    conf_threshold: float = 0.5,
    layout_model: Optional[str] = None,
    layout_conf_threshold: float = 0.5,
    skip_if_exists: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to process OCR.
    
    Args:
        keyframes_data: Keyframe extraction results
        output_dir: Directory containing keyframes
        lang: OCR language
        use_gpu: Whether to use GPU
        conf_threshold: OCR confidence threshold
        layout_model: LayoutParser model name
        layout_conf_threshold: Layout confidence threshold
        skip_if_exists: Skip if output exists
        
    Returns:
        Dictionary containing OCR results
    """
    processor = OCRProcessor(
        lang,
        use_gpu,
        conf_threshold,
        layout_model,
        layout_conf_threshold
    )
    return processor.process(keyframes_data, output_dir, skip_if_exists)
