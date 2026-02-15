"""Phase 2 pipeline orchestrator."""
import logging
import time
from pathlib import Path
from typing import Dict, Any

from src.config import PipelineConfig
from src.loader import load_phase1_data
from src.timeline import build_timeline, TimelineBuilder
from src.chunker import create_chunks
from src.ocr_cleanup import clean_ocr_text
from src.aligner import align_chunks
from src.enricher import enrich_chunks
from src.embedder import embed_chunks
from src.store import store_in_qdrant
from src.exporter import export_chunks


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Phase2Pipeline:
    """Complete Phase 2 pipeline."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def run(self) -> Dict[str, Any]:
        """Run the complete pipeline."""
        logger.info("=" * 80)
        logger.info("Starting Phase 2 Pipeline")
        logger.info("=" * 80)
        logger.info(f"Video ID: {self.config.video_id}")
        logger.info(f"Phase 1 input: {self.config.paths.get_phase1_video_dir(self.config.video_id)}")
        logger.info(f"Phase 2 output: {self.config.paths.get_output_dir(self.config.video_id)}")
        logger.info("=" * 80)
        
        # Ensure directories exist
        self.config.ensure_directories()
        
        pipeline_start = time.time()
        results = {}
        timings = {}
        
        # Stage 1: Load Phase 1 artifacts
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 1: Load Phase 1 Artifacts")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            phase1_dir = self.config.paths.get_phase1_video_dir(self.config.video_id)
            video_data = load_phase1_data(phase1_dir)
            results['video_data'] = video_data
            timings['load'] = time.time() - stage_start
            logger.info(f"✓ Loaded in {timings['load']:.2f}s")
        except Exception as e:
            logger.error(f"✗ Loading failed: {e}")
            raise
        
        # Stage 2: Build temporal spine
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 2: Build Temporal Spine")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            timeline_events = build_timeline(video_data)
            
            # Save timeline
            timeline_builder = TimelineBuilder(video_data)
            timeline_builder.events = timeline_events
            timeline_path = self.config.paths.get_output_dir(self.config.video_id) / "timeline.json"
            timeline_builder.save_timeline(str(timeline_path))
            
            results['timeline'] = timeline_events
            timings['timeline'] = time.time() - stage_start
            logger.info(f"✓ Timeline built in {timings['timeline']:.2f}s")
            logger.info(f"  - Total events: {len(timeline_events)}")
        except Exception as e:
            logger.error(f"✗ Timeline building failed: {e}")
            raise
        
        # Stage 3: Hierarchical chunking
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 3: Hierarchical Chunking")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            chunks = create_chunks(video_data, self.config.chunking)
            results['chunks'] = chunks
            timings['chunking'] = time.time() - stage_start
            logger.info(f"✓ Chunking complete in {timings['chunking']:.2f}s")
            logger.info(f"  - Chunks created: {len(chunks)}")
        except Exception as e:
            logger.error(f"✗ Chunking failed: {e}")
            raise
        
        # Stage 4: OCR cleanup
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 4: OCR Cleanup")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            chunks = clean_ocr_text(chunks, self.config.chunking)
            timings['ocr_cleanup'] = time.time() - stage_start
            logger.info(f"✓ OCR cleanup complete in {timings['ocr_cleanup']:.2f}s")
        except Exception as e:
            logger.error(f"✗ OCR cleanup failed: {e}")
            raise
        
        # Stage 5: Slide-speech alignment
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 5: Slide-Speech Alignment")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            chunks = align_chunks(chunks)
            timings['alignment'] = time.time() - stage_start
            logger.info(f"✓ Alignment complete in {timings['alignment']:.2f}s")
            avg_score = sum(c.alignment_score for c in chunks) / len(chunks)
            logger.info(f"  - Average alignment score: {avg_score:.3f}")
        except Exception as e:
            logger.error(f"✗ Alignment failed: {e}")
            raise
        
        # Stage 6: Metadata enrichment
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 6: Metadata Enrichment")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            chunks = enrich_chunks(chunks, video_data)
            timings['enrichment'] = time.time() - stage_start
            logger.info(f"✓ Enrichment complete in {timings['enrichment']:.2f}s")
        except Exception as e:
            logger.error(f"✗ Enrichment failed: {e}")
            raise
        
        # Stage 7: Generate embeddings
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 7: Generate Embeddings")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            chunks = embed_chunks(
                chunks,
                self.config.embedding,
                self.config.paths.get_phase1_video_dir(self.config.video_id)
            )
            timings['embeddings'] = time.time() - stage_start
            logger.info(f"✓ Embeddings generated in {timings['embeddings']:.2f}s")
            logger.info(f"  - Text embedding dim: {self.config.embedding.text_dim}")
            logger.info(f"  - Image embedding dim: {self.config.embedding.image_dim}")
        except Exception as e:
            logger.error(f"✗ Embedding generation failed: {e}")
            raise
        
        # Stage 8: Store in Qdrant
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 8: Store in Qdrant")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            point_count = store_in_qdrant(chunks, self.config.qdrant)
            results['qdrant_points'] = point_count
            timings['qdrant'] = time.time() - stage_start
            logger.info(f"✓ Stored in Qdrant in {timings['qdrant']:.2f}s")
            logger.info(f"  - Points stored: {point_count}")
        except Exception as e:
            logger.error(f"✗ Qdrant storage failed: {e}")
            raise
        
        # Stage 9: Export
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 9: Export to Files")
        logger.info("=" * 80)
        stage_start = time.time()
        try:
            output_files = export_chunks(
                chunks,
                self.config.paths.get_output_dir(self.config.video_id)
            )
            results['output_files'] = output_files
            timings['export'] = time.time() - stage_start
            logger.info(f"✓ Export complete in {timings['export']:.2f}s")
            for format_name, file_path in output_files.items():
                logger.info(f"  - {format_name}: {file_path}")
        except Exception as e:
            logger.error(f"✗ Export failed: {e}")
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
        logger.info(f"  Chunks created:      {len(chunks)}")
        logger.info(f"  Timeline events:     {len(timeline_events)}")
        logger.info(f"  Qdrant points:       {point_count}")
        logger.info(f"  Export formats:      {len(output_files)}")
        
        output_dir = self.config.paths.get_output_dir(self.config.video_id)
        logger.info(f"\nAll outputs saved to: {output_dir}")
        logger.info("=" * 80)
        
        return {
            'results': results,
            'timings': timings,
            'output_dir': str(output_dir),
            'chunks': chunks
        }


def run_pipeline(
    video_id: str,
    workspace_root: Path = None,
    skip_existing: bool = True,
    verbose: bool = True,
    qdrant_url: str = None,
    qdrant_api_key: str = None
) -> Dict[str, Any]:
    """Convenience function to run the pipeline."""
    config = PipelineConfig(
        video_id=video_id,
        workspace_root=workspace_root,
        skip_existing=skip_existing,
        verbose=verbose
    )
    
    # Override Qdrant config if cloud credentials provided
    if qdrant_url and qdrant_api_key:
        config.qdrant.url = qdrant_url
        config.qdrant.api_key = qdrant_api_key
        config.qdrant.host = None
        config.qdrant.port = None
    
    pipeline = Phase2Pipeline(config)
    return pipeline.run()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline <video_id>")
        sys.exit(1)
    
    video_id = sys.argv[1]
    result = run_pipeline(video_id)
    
    print("\nPipeline completed successfully!")
    print(f"Output directory: {result['output_dir']}")
