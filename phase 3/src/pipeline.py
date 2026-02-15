"""Phase 3 Pipeline Orchestrator"""
import logging
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .loader import DataLoader
from .ocr_overlay import OCROverlayGenerator
from .validator import ExtractionValidator
from .report_generator import HTMLReportGenerator
from .qa_generator import QAGenerator

logger = logging.getLogger(__name__)


class Phase3Pipeline:
    """Phase 3: Extraction Validation and Q&A Generation Pipeline"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
    
    def run(self, video_id: str, report_only: bool = False):
        """
        Run Phase 3 pipeline
        
        Args:
            video_id: Video ID to process
            report_only: If True, skip Q&A generation
        """
        start_time = time.time()
        
        logger.info("="*60)
        logger.info("Phase 3: Extraction Validation and Q&A Generation")
        logger.info("="*60)
        logger.info(f"Video ID: {video_id}")
        logger.info(f"Report only mode: {report_only}")
        
        # Setup paths
        phase1_dir = self.config.paths.get_phase1_video_dir(video_id)
        phase2_dir = self.config.paths.get_phase2_video_dir(video_id)
        phase3_dir = self.config.paths.get_phase3_video_dir(video_id)
        phase3_dir.mkdir(parents=True, exist_ok=True)
        
        # Load data
        logger.info("\n[1/5] Loading Phase 1 and Phase 2 data...")
        loader_start = time.time()
        loader = DataLoader(self.config.paths.phase1_root, self.config.paths.phase2_root)
        video_data = loader.load_all(video_id)
        logger.info(f"✓ Loaded in {time.time() - loader_start:.1f}s")
        logger.info(f"  - {len(video_data.keyframes)} keyframes")
        logger.info(f"  - {len(video_data.ocr_blocks)} OCR blocks")
        logger.info(f"  - {len(video_data.asr_segments)} ASR segments")
        logger.info(f"  - {len(video_data.chunks)} chunks")
        
        # Generate OCR overlays
        logger.info("\n[2/5] Generating OCR overlays on keyframes...")
        overlay_start = time.time()
        overlay_dir = phase3_dir / "keyframes_annotated"
        overlay_gen = OCROverlayGenerator(
            high_conf_threshold=self.config.validation.ocr_high_conf,
            low_conf_threshold=self.config.validation.ocr_low_conf
        )
        annotated_keyframes = overlay_gen.generate(video_data, overlay_dir)
        logger.info(f"✓ Generated {len(annotated_keyframes)} annotated keyframes in {time.time() - overlay_start:.1f}s")
        
        # Run validation
        logger.info("\n[3/5] Running extraction validation...")
        validator_start = time.time()
        validator = ExtractionValidator(
            coverage_window_sec=self.config.validation.coverage_window_sec,
            keyframe_gap_threshold_sec=self.config.validation.keyframe_gap_threshold_sec,
            ocr_high_conf=self.config.validation.ocr_high_conf,
            ocr_low_conf=self.config.validation.ocr_low_conf,
            min_ocr_text_length=self.config.validation.min_ocr_text_length
        )
        validation_report = validator.validate(video_data)
        validator.save_report(validation_report, phase3_dir / "coverage.json")
        logger.info(f"✓ Validation complete in {time.time() - validator_start:.1f}s")
        logger.info(f"  - Coverage: {validation_report.overall_coverage_pct:.1f}%")
        logger.info(f"  - Keyframe gaps: {len(validation_report.keyframe_gaps)}")
        logger.info(f"  - Quality flags: {len(validation_report.quality_flags)}")
        
        # Generate HTML report
        logger.info("\n[4/5] Generating HTML validation report...")
        report_start = time.time()
        report_gen = HTMLReportGenerator()
        report_gen.generate(
            video_data,
            validation_report,
            annotated_keyframes,
            phase3_dir / "report.html"
        )
        logger.info(f"✓ Report generated in {time.time() - report_start:.1f}s")
        logger.info(f"  → {phase3_dir / 'report.html'}")
        
        # Generate Q&A pairs (optional)
        qa_count = 0
        if not report_only:
            logger.info("\n[5/5] Generating Q&A pairs with Gemini...")
            qa_start = time.time()
            try:
                qa_gen = QAGenerator(
                    api_key=self.config.llm.api_key,
                    model=self.config.llm.model,
                    max_pairs_per_chunk=self.config.llm.max_qa_pairs_per_chunk,
                    temperature=self.config.llm.temperature
                )
                qa_pairs = qa_gen.generate(video_data.chunks, video_id)
                qa_gen.save_jsonl(qa_pairs, phase3_dir / "qa_pairs.jsonl")
                qa_count = len(qa_pairs)
                logger.info(f"✓ Generated {qa_count} Q&A pairs in {time.time() - qa_start:.1f}s")
                logger.info(f"  → {phase3_dir / 'qa_pairs.jsonl'}")
            except Exception as e:
                logger.error(f"✗ Q&A generation failed: {e}")
        else:
            logger.info("\n[5/5] Skipping Q&A generation (--report-only mode)")
        
        # Summary
        total_time = time.time() - start_time
        logger.info("\n" + "="*60)
        logger.info("Phase 3 Complete")
        logger.info("="*60)
        logger.info(f"Total time: {total_time:.1f}s")
        logger.info(f"\nOutputs:")
        logger.info(f"  • Report: {phase3_dir / 'report.html'}")
        logger.info(f"  • Annotated keyframes: {len(annotated_keyframes)}")
        logger.info(f"  • Coverage: {validation_report.overall_coverage_pct:.1f}%")
        if qa_count > 0:
            logger.info(f"  • Q&A pairs: {qa_count}")
        logger.info("\n✓ Pipeline validation complete")
        
        return {
            "video_id": video_id,
            "report_path": str(phase3_dir / "report.html"),
            "coverage_pct": validation_report.overall_coverage_pct,
            "keyframe_gaps": len(validation_report.keyframe_gaps),
            "quality_flags": len(validation_report.quality_flags),
            "qa_pairs_count": qa_count,
            "total_time_sec": total_time
        }
