# Phase 2: Alignment, Chunking, Embeddings and Storage

Transform Phase 1 raw artifacts into structured, searchable, training-ready multimodal chunks stored in Qdrant.

## What This Phase Does

Takes the Phase 1 outputs (ASR, scenes, keyframes, OCR) and:

1. **Builds a unified temporal spine** - All events on a single timeline
2. **Creates hierarchical chunks** - Chapter → Scene with merge/split rules
3. **Cleans OCR text** - Filters UI chrome, deduplicates content
4. **Aligns slide-speech** - Measures how well visual matches spoken content
5. **Enriches metadata** - Quality scores, provenance, completeness flags
6. **Generates embeddings** - Text (sentence-transformers) + Image (CLIP)
7. **Stores in Qdrant** - Multi-vector collection with payload indexes
8. **Exports to files** - JSONL, Parquet, JSON

## Prerequisites

1. **Phase 1 completed** - Must have Phase 1 outputs in `../phase 1/XNQTWZ87K4I/`
2. **GPU access** - Embeddings run best on GPU (via vast.ai)
3. **Docker** - For Qdrant (or use existing Qdrant instance)

## Installation

```bash
cd "phase 2"

# Install dependencies
pip install -r requirements.txt

# Start Qdrant (Docker)
docker-compose up -d

# Verify Qdrant is running
curl http://localhost:6333/collections
```

## Usage

### Basic Usage

```bash
python run.py XNQTWZ87K4I
```

### With Options

```bash
python run.py XNQTWZ87K4I --workspace /path/to/workspace --no-skip
```

### Python API

```python
from pathlib import Path
from src.pipeline import run_pipeline

result = run_pipeline(
    video_id="XNQTWZ87K4I",
    workspace_root=Path("/path/to/workspace"),
    skip_existing=True
)

print(f"Created {len(result['chunks'])} chunks")
print(f"Output: {result['output_dir']}")
```

## Output Structure

After processing, `output/XNQTWZ87K4I/` contains:

```
output/XNQTWZ87K4I/
  timeline.json      # Unified temporal spine (all events)
  chunks.json        # All chunks with full metadata
  chunks.jsonl       # One chunk per line (training-ready)
  chunks.parquet     # Columnar format (efficient loading)
```

Plus Qdrant collection `video_chunks` with ~10-12 points, each containing:
- Text vector (384-dim)
- Image vector (512-dim)
- Full payload metadata

## Chunk Schema

Each chunk contains:

```json
{
  "chunk_id": "XNQTWZ87K4I_ch0_sc0",
  "video_id": "XNQTWZ87K4I",
  "source": "youtube",
  
  "t_start_ms": 0,
  "t_end_ms": 32233,
  
  "chapter_index": 0,
  "chapter_title": "<Untitled Chapter 1>",
  "scene_id": 0,
  
  "asr_text": "So how do you make a website compliant...",
  "ocr_text": "3 common mistakes | GDPR compliance...",
  "merged_text": "[SPOKEN] ... [ON SCREEN] ...",
  
  "keyframe_ids": [0, 1],
  "keyframe_paths": ["frame_00000.jpg", "frame_00001.jpg"],
  "has_keyframe": true,
  
  "asr_confidence": 0.78,
  "ocr_confidence": 0.84,
  "alignment_score": 0.62,
  
  "completeness": {
    "has_speech": true,
    "has_visual": true,
    "has_ocr_text": true
  },
  
  "provenance": {
    "video_title": "3 common GDPR mistakes...",
    "channel": "Secure Privacy",
    "publish_date": "20190323",
    "tags": ["GDPR", "Cookie banner", ...]
  }
}
```

## Configuration

Edit `src/config.py` to customize:

- **Chunking**: `min_chunk_duration_ms`, `max_chunk_duration_ms`, merge/split rules
- **OCR cleanup**: `ui_chrome_threshold`, `text_overlap_threshold`
- **Embeddings**: Models, device, batch size
- **Qdrant**: Host, port, collection name

## Querying Qdrant

### Python Client

```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

# Search by text
results = client.search(
    collection_name="video_chunks",
    query_vector=("text", text_embedding),
    limit=5,
    query_filter={
        "must": [
            {"key": "video_id", "match": {"value": "XNQTWZ87K4I"}}
        ]
    }
)

# Search by image
results = client.search(
    collection_name="video_chunks",
    query_vector=("image", image_embedding),
    limit=5
)

# Filter by time range
results = client.scroll(
    collection_name="video_chunks",
    scroll_filter={
        "must": [
            {"key": "t_start_ms", "range": {"gte": 0, "lte": 60000}}
        ]
    }
)
```

### HTTP API

```bash
# Get collection info
curl http://localhost:6333/collections/video_chunks

# Scroll through points
curl -X POST http://localhost:6333/collections/video_chunks/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

## Expected Performance

RTX 3090, processing XNQTWZ87K4I:

| Stage | Time | Notes |
|-------|------|-------|
| Load | <1s | Read JSON files |
| Timeline | <1s | Merge all events |
| Chunking | <1s | Create ~10-12 chunks |
| OCR Cleanup | <1s | Filter chrome |
| Alignment | <1s | TF-IDF + cosine |
| Enrichment | <1s | Compute scores |
| Embeddings | 10-30s | Text + CLIP (GPU) |
| Qdrant | <1s | Upsert points |
| Export | <1s | Write files |
| **Total** | **15-40s** | Embeddings dominate |

Cost on vast.ai: **~$0.01 per video** (GPU time)

## Troubleshooting

### Qdrant connection failed

```bash
# Check if Qdrant is running
docker-compose ps

# Restart Qdrant
docker-compose restart

# Check logs
docker-compose logs qdrant
```

### CUDA out of memory

Edit `src/config.py`:

```python
class EmbeddingConfig:
    device: str = "cpu"  # Use CPU instead of GPU
    batch_size: int = 4  # Reduce batch size
```

Or use a smaller CLIP model:

```python
image_model: str = "ViT-B/16"  # Smaller than ViT-B/32
```

### Import errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Or install individually
pip install sentence-transformers open-clip-torch qdrant-client
```

### Phase 1 data not found

Check that Phase 1 outputs exist:

```bash
ls -la "../phase 1/XNQTWZ87K4I/"
# Should contain: asr.json, scenes.json, keyframes.json, ocr.json, keyframes/
```

## Next Steps (Phase 3)

Phase 2 produces chunks with embeddings. Phase 3 will:

1. **RAG pipeline** - Query interface, retrieval, prompt templates
2. **Fine-tuning export** - Instruction pairs for supervised training
3. **Evaluation** - Recall@k, citation accuracy, answer quality
4. **Multi-video scaling** - Process multiple videos, deduplicate
5. **Privacy redaction** - Face detection, PII filtering

## Development

### Running Tests

```bash
# Test loading
python -c "from src.loader import load_phase1_data; print(load_phase1_data(Path('../phase 1/XNQTWZ87K4I')))"

# Test chunking
python -c "from src.config import PipelineConfig; from src.pipeline import run_pipeline; run_pipeline('XNQTWZ87K4I')"
```

### Debugging

Set `verbose=True` in config for detailed logging:

```python
config = PipelineConfig(video_id="XNQTWZ87K4I", verbose=True)
```

Or use Python's logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Architecture

```
Phase 1 Artifacts → Loader → Timeline → Chunker → OCR Cleanup → Aligner → Enricher → Embedder → Qdrant + Export
```

See plan file for full architecture diagram.

## License

This project is for research and educational purposes.
