#!/usr/bin/env python3
"""CLI entry point for Phase 2 pipeline."""
import argparse
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Phase 2: Alignment, Chunking, Embeddings and Storage"
    )
    parser.add_argument(
        "video_id",
        help="Video ID from Phase 1 (e.g., XNQTWZ87K4I)"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root directory (default: parent of phase 2 directory)"
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Reprocess all stages (don't skip existing outputs)"
    )
    parser.add_argument(
        "--qdrant-url",
        type=str,
        default=None,
        help="Qdrant Cloud URL (e.g., https://xxx.cloud.qdrant.io)"
    )
    parser.add_argument(
        "--qdrant-api-key",
        type=str,
        default=None,
        help="Qdrant Cloud API key"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Phase 2: Alignment, Chunking, Embeddings and Storage")
    print("=" * 80)
    print(f"Video ID: {args.video_id}")
    print()
    
    try:
        result = run_pipeline(
            video_id=args.video_id,
            workspace_root=args.workspace,
            skip_existing=not args.no_skip,
            qdrant_url=args.qdrant_url,
            qdrant_api_key=args.qdrant_api_key
        )
        
        print("\n" + "=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print(f"Output directory: {result['output_dir']}")
        print(f"Total time: {result['timings']['total']:.2f}s")
        print(f"Chunks created: {len(result['chunks'])}")
        print(f"Qdrant points: {result['results']['qdrant_points']}")
        print("=" * 80)
    
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
