#!/usr/bin/env python3
"""Simple script to run the pipeline on a video."""
import argparse
from pathlib import Path
from src.pipeline import run_pipeline
from src.config import ModelConfig


def main():
    parser = argparse.ArgumentParser(
        description="Extract graphical context from tutorial videos"
    )
    parser.add_argument(
        "video_url",
        help="YouTube video URL"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root directory (default: current directory)"
    )
    parser.add_argument(
        "--model",
        choices=["large-v3", "large-v2", "medium", "small", "base", "tiny"],
        default="large-v3",
        help="Whisper model size"
    )
    parser.add_argument(
        "--device",
        choices=["cuda", "cpu"],
        default="cuda",
        help="Device to use for processing"
    )
    parser.add_argument(
        "--no-align",
        action="store_true",
        help="Skip WhisperX alignment"
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        help="Enable speaker diarization"
    )
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=27.0,
        help="Scene detection threshold (lower = more sensitive)"
    )
    parser.add_argument(
        "--blur-threshold",
        type=float,
        default=100.0,
        help="Blur threshold for keyframe selection (higher = sharper)"
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Reprocess all stages (don't skip existing outputs)"
    )
    
    args = parser.parse_args()
    
    # Build model config
    model_config = ModelConfig(
        whisper_model=args.model,
        whisper_device=args.device,
        whisperx_align=not args.no_align,
        whisperx_diarize=args.diarize,
        scene_threshold=args.scene_threshold,
        blur_threshold=args.blur_threshold
    )
    
    # Run pipeline
    print(f"Processing video: {args.video_url}")
    print(f"Model: {args.model} on {args.device}")
    print(f"Alignment: {'enabled' if not args.no_align else 'disabled'}")
    print(f"Diarization: {'enabled' if args.diarize else 'disabled'}")
    print()
    
    result = run_pipeline(
        video_url=args.video_url,
        workspace_root=args.workspace,
        model_config=model_config,
        skip_existing=not args.no_skip
    )
    
    print("\n" + "=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print(f"Output directory: {result['output_dir']}")
    print(f"Total time: {result['timings']['total']:.2f}s")


if __name__ == "__main__":
    main()
