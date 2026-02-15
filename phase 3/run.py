#!/usr/bin/env python3
"""
Phase 3: Extraction Validation and Q&A Generation

Usage:
    python run.py XNQTWZ87K4I                    # Full pipeline
    python run.py XNQTWZ87K4I --report-only      # Skip Q&A generation
"""
import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.pipeline import Phase3Pipeline


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Phase 3: Extraction Validation and Q&A Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "video_id",
        help="Video ID to process (e.g., XNQTWZ87K4I)"
    )
    
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report only, skip Q&A generation (no API key needed)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Run pipeline
    config = Config()
    pipeline = Phase3Pipeline(config)
    
    try:
        result = pipeline.run(
            video_id=args.video_id,
            report_only=args.report_only
        )
        
        sys.exit(0)
    
    except Exception as e:
        logging.error(f"\n✗ Pipeline failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
