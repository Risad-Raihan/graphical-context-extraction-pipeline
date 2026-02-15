#!/usr/bin/env python3
"""Quick script to set up Qdrant Cloud config for vast.ai."""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from src.config import PipelineConfig

# Create config with Qdrant Cloud credentials
config = PipelineConfig(video_id="XNQTWZ87K4I")

# Update Qdrant config for cloud
# Replace with your actual Qdrant Cloud URL and API key
config.qdrant.url = "YOUR_QDRANT_CLOUD_URL"
config.qdrant.api_key = "YOUR_QDRANT_API_KEY"

print("✓ Qdrant Cloud config ready!")
print(f"  URL: {config.qdrant.url}")
print(f"  Collection: {config.qdrant.collection_name}")
