"""Main pipeline orchestrator for video processing."""
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from src.config import PipelineConfig, ModelConfig
from src.ingest.downloader import download_video
from src.ingest.normalize import normalize_media
from src.extract.asr import process_asr
from src.extract.scenes import detect_scenes
from src.extract.keyframes import extract_keyframes
from src.extract.ocr import process_ocr


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoPipeline:
    """Complete video processing pipeline."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete pipeline.
        
        Returns:
            Dictionary containing all pipeline outputs and timing information
        """
        logger.info("=" * 80)
        logger.info("Starting Video Processing Pipeline")
        logger.info("=" * 80)
        logger.info(f"Video URL: {self.config.video_url}")
        logger.info(f"Video ID: {self.config.video_id}")
        logger.info(f"Output directory: {self.config.paths.get_video_dir(self.config.video_id)}")
        logger.info("=" * 80)
        
        # Ensure directories exist
        self.config.ensure_directories()
        
        pipeline_start = time.time()
        results = {}
        timings = {}
        
        # Stage 1: Download video and metadata
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 1: Download Video and Metadata")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            download_result = download_video(
                self.config.video_url,
                self.config.paths.get_source_dir(self.config.video_id),
                skip_if_exists=self.config.skip_existing
            )
            results['download'] = download_result
            timings['download'] = time.time() - stage_start
            logger.info(f"✓ Download complete in {timings['download']:.2f}s")
        except Exception as e:
            logger.error(f"✗ Download failed: {e}")
            raise
        
        # Stage 2: Normalize media
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 2: Normalize Media")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            normalize_result = normalize_media(
                Path(download_result['video_path']),
                self.config.paths.get_normalized_dir(self.config.video_id),
                audio_sample_rate=self.config.models.audio_sample_rate,
                audio_channels=self.config.models.audio_channels,
                video_fps=self.config.models.video_fps,
                video_codec=self.config.models.video_codec,
                video_preset=self.config.models.video_preset,
                skip_if_exists=self.config.skip_existing
            )
            results['normalize'] = normalize_result
            timings['normalize'] = time.time() - stage_start
            logger.info(f"✓ Normalization complete in {timings['normalize']:.2f}s")
        except Exception as e:
            logger.error(f"✗ Normalization failed: {e}")
            raise
        
        # Stage 3: ASR with word-level timestamps
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 3: ASR Processing")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            asr_result = process_asr(
                Path(normalize_result['audio_path']),
                self.config.paths.get_video_dir(self.config.video_id),
                model_size=self.config.models.whisper_model,
                device=self.config.models.whisper_device,
                compute_type=self.config.models.whisper_compute_type,
                batch_size=self.config.models.whisperx_batch_size,
                align=self.config.models.whisperx_align,
                diarize=self.config.models.whisperx_diarize,
                skip_if_exists=self.config.skip_existing
            )
            results['asr'] = asr_result
            timings['asr'] = time.time() - stage_start
            logger.info(f"✓ ASR complete in {timings['asr']:.2f}s")
            logger.info(f"  - Segments: {len(asr_result['segments'])}")
            logger.info(f"  - Language: {asr_result.get('language', 'unknown')}")
        except Exception as e:
            logger.error(f"✗ ASR failed: {e}")
            raise
        
        # Stage 4: Scene detection
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 4: Scene Detection")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            scenes_result = detect_scenes(
                Path(normalize_result['video_path']),
                self.config.paths.get_video_dir(self.config.video_id),
                threshold=self.config.models.scene_threshold,
                min_scene_len=self.config.models.min_scene_len,
                skip_if_exists=self.config.skip_existing
            )
            results['scenes'] = scenes_result
            timings['scenes'] = time.time() - stage_start
            logger.info(f"✓ Scene detection complete in {timings['scenes']:.2f}s")
            logger.info(f"  - Scenes detected: {scenes_result['total_scenes']}")
        except Exception as e:
            logger.error(f"✗ Scene detection failed: {e}")
            raise
        
        # Stage 5: Keyframe extraction
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 5: Keyframe Extraction")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            keyframes_result = extract_keyframes(
                Path(normalize_result['video_path']),
                scenes_result,
                self.config.paths.get_keyframes_dir(self.config.video_id),
                blur_threshold=self.config.models.blur_threshold,
                long_scene_threshold=self.config.models.long_scene_threshold,
                long_scene_sample_interval=self.config.models.long_scene_sample_interval,
                pixel_delta_threshold=self.config.models.pixel_delta_threshold,
                skip_if_exists=self.config.skip_existing
            )
            results['keyframes'] = keyframes_result
            timings['keyframes'] = time.time() - stage_start
            logger.info(f"✓ Keyframe extraction complete in {timings['keyframes']:.2f}s")
            logger.info(f"  - Keyframes extracted: {keyframes_result['total_keyframes']}")
        except Exception as e:
            logger.error(f"✗ Keyframe extraction failed: {e}")
            raise
        
        # Stage 6: OCR and layout parsing
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 6: OCR and Layout Parsing")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            ocr_result = process_ocr(
                keyframes_result,
                self.config.paths.get_keyframes_dir(self.config.video_id),
                lang=self.config.models.ocr_lang,
                use_gpu=self.config.models.ocr_use_gpu,
                conf_threshold=self.config.models.ocr_conf_threshold,
                layout_model=self.config.models.layout_model,
                layout_conf_threshold=self.config.models.layout_conf_threshold,
                skip_if_exists=self.config.skip_existing
            )
            results['ocr'] = ocr_result
            timings['ocr'] = time.time() - stage_start
            logger.info(f"✓ OCR complete in {timings['ocr']:.2f}s")
            logger.info(f"  - Keyframes processed: {ocr_result['total_keyframes']}")
            total_blocks = sum(r['total_blocks'] for r in ocr_result['results'])
            logger.info(f"  - Total text blocks: {total_blocks}")
        except Exception as e:
            logger.error(f"✗ OCR failed: {e}")
            raise
        
        # Pipeline complete
        total_time = time.time() - pipeline_start
        timings['total'] = total_time
        
        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total time: {total_time:.2f}s")
        logger.info("\nStage Timings:")
        for stage, duration in timings.items():
            if stage != 'total':
                percentage = (duration / total_time) * 100
                logger.info(f"  {stage:15s}: {duration:7.2f}s ({percentage:5.1f}%)")
        
        logger.info("\nOutput Summary:")
        logger.info(f"  ASR segments:    {len(results['asr']['segments'])}")
        logger.info(f"  Scenes:          {results['scenes']['total_scenes']}")
        logger.info(f"  Keyframes:       {results['keyframes']['total_keyframes']}")
        logger.info(f"  OCR text blocks: {sum(r['total_blocks'] for r in results['ocr']['results'])}")
        
        output_dir = self.config.paths.get_video_dir(self.config.video_id)
        logger.info(f"\nAll artifacts saved to: {output_dir}")
        logger.info("=" * 80)
        
        return {
            'results': results,
            'timings': timings,
            'output_dir': str(output_dir)
        }


def run_pipeline(
    video_url: str,
    workspace_root: Optional[Path] = None,
    model_config: Optional[ModelConfig] = None,
    skip_existing: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to run the complete pipeline.
    
    Args:
        video_url: YouTube video URL
        workspace_root: Workspace root directory
        model_config: Model configuration (uses defaults if None)
        skip_existing: Skip stages if outputs already exist
        verbose: Enable verbose logging
        
    Returns:
        Dictionary containing pipeline results and timings
    """
    config = PipelineConfig(
        video_url=video_url,
        workspace_root=workspace_root,
        model_config=model_config,
        skip_existing=skip_existing,
        verbose=verbose
    )
    
    pipeline = VideoPipeline(config)
    return pipeline.run()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline <youtube_url>")
        sys.exit(1)
    
    video_url = sys.argv[1]
    result = run_pipeline(video_url)
    
    print("\nPipeline completed successfully!")
    print(f"Output directory: {result['output_dir']}")
