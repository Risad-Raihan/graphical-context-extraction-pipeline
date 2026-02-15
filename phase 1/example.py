#!/usr/bin/env python3
"""Example usage of the video processing pipeline."""
from pathlib import Path
from src.pipeline import run_pipeline
from src.config import ModelConfig


def example_basic():
    """Basic usage - process a video with default settings."""
    print("Example 1: Basic usage with defaults")
    print("-" * 80)
    
    result = run_pipeline(
        video_url="https://www.youtube.com/watch?v=XNQTWZ87K4I"
    )
    
    print(f"\nOutput saved to: {result['output_dir']}")
    print(f"Total processing time: {result['timings']['total']:.2f}s")
    
    # Access results
    asr = result['results']['asr']
    print(f"Transcript segments: {len(asr['segments'])}")
    
    scenes = result['results']['scenes']
    print(f"Scenes detected: {scenes['total_scenes']}")
    
    keyframes = result['results']['keyframes']
    print(f"Keyframes extracted: {keyframes['total_keyframes']}")
    
    ocr = result['results']['ocr']
    total_blocks = sum(r['total_blocks'] for r in ocr['results'])
    print(f"OCR text blocks: {total_blocks}")


def example_custom_config():
    """Custom configuration example."""
    print("\nExample 2: Custom configuration")
    print("-" * 80)
    
    # Configure models and thresholds
    model_config = ModelConfig(
        whisper_model="medium",              # Use smaller model
        whisper_device="cuda",
        whisperx_align=True,
        whisperx_diarize=True,               # Enable speaker diarization
        scene_threshold=25.0,                # More sensitive scene detection
        blur_threshold=150.0,                # Only very sharp frames
        ocr_lang="en",
        ocr_conf_threshold=0.7               # Higher confidence threshold
    )
    
    result = run_pipeline(
        video_url="https://www.youtube.com/watch?v=XNQTWZ87K4I",
        model_config=model_config,
        skip_existing=True
    )
    
    print(f"\nProcessed with custom config")
    print(f"Output: {result['output_dir']}")


def example_reading_outputs():
    """Example of reading and using the output files."""
    print("\nExample 3: Reading output files")
    print("-" * 80)
    
    import json
    
    video_id = "XNQTWZ87K4I"
    output_dir = Path("data/raw") / video_id
    
    if not output_dir.exists():
        print(f"Output directory not found: {output_dir}")
        print("Run example_basic() first to process the video")
        return
    
    # Read ASR transcript
    with open(output_dir / "asr.json", 'r') as f:
        asr_data = json.load(f)
    
    print(f"Language: {asr_data['language']}")
    print(f"\nFirst 3 segments:")
    for seg in asr_data['segments'][:3]:
        print(f"  [{seg['start']}ms - {seg['end']}ms] {seg['text']}")
    
    # Read OCR results
    with open(output_dir / "ocr.json", 'r') as f:
        ocr_data = json.load(f)
    
    print(f"\nOCR results from first keyframe:")
    if ocr_data['results']:
        first_frame = ocr_data['results'][0]
        print(f"  Timestamp: {first_frame['timestamp_ms']}ms")
        print(f"  Text blocks: {first_frame['total_blocks']}")
        print(f"  Full text preview: {first_frame['full_text'][:100]}...")
    
    # Read metadata
    with open(output_dir / "source" / "metadata.json", 'r') as f:
        metadata = json.load(f)
    
    print(f"\nVideo metadata:")
    print(f"  Title: {metadata['title']}")
    print(f"  Duration: {metadata['duration']}s")
    print(f"  Channel: {metadata['channel']}")
    
    if 'chapters' in metadata:
        print(f"  Chapters: {len(metadata['chapters'])}")


def example_stage_by_stage():
    """Example of running stages individually."""
    print("\nExample 4: Running stages individually")
    print("-" * 80)
    
    from src.config import PipelineConfig
    from src.ingest.downloader import download_video
    from src.ingest.normalize import normalize_media
    
    video_url = "https://www.youtube.com/watch?v=XNQTWZ87K4I"
    config = PipelineConfig(video_url)
    config.ensure_directories()
    
    # Stage 1: Download only
    print("Downloading video...")
    download_result = download_video(
        video_url,
        config.paths.get_source_dir(config.video_id),
        skip_if_exists=True
    )
    print(f"  Downloaded to: {download_result['video_path']}")
    
    # Stage 2: Normalize only
    print("Normalizing media...")
    normalize_result = normalize_media(
        Path(download_result['video_path']),
        config.paths.get_normalized_dir(config.video_id),
        skip_if_exists=True
    )
    print(f"  Audio: {normalize_result['audio_path']}")
    print(f"  Video: {normalize_result['video_path']}")
    
    print("\nYou can continue with remaining stages using the pipeline...")


if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("Video Processing Pipeline - Examples")
    print("=" * 80)
    
    if len(sys.argv) > 1 and sys.argv[1] == "basic":
        example_basic()
    elif len(sys.argv) > 1 and sys.argv[1] == "custom":
        example_custom_config()
    elif len(sys.argv) > 1 and sys.argv[1] == "read":
        example_reading_outputs()
    elif len(sys.argv) > 1 and sys.argv[1] == "stages":
        example_stage_by_stage()
    else:
        print("\nAvailable examples:")
        print("  python example.py basic    - Basic usage with defaults")
        print("  python example.py custom   - Custom configuration")
        print("  python example.py read     - Reading output files")
        print("  python example.py stages   - Running stages individually")
        print("\nRun any example to see it in action!")
