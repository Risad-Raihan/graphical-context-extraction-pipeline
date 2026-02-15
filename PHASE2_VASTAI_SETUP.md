# Phase 2 on vast.ai - Setup Guide

## What You're Running

Phase 2 takes Phase 1 outputs and creates:
- Unified timeline of all events
- Hierarchical chunks (scene-based)
- Text embeddings (sentence-transformers)
- Image embeddings (CLIP)
- Qdrant vector database storage
- Export files (JSON, JSONL, Parquet)

## Prerequisites

1. ✅ RTX 4090 instance rented on vast.ai
2. ✅ `phase2_vastai.tar.gz` uploaded to vast.ai

## Setup Instructions

### 1. Install System Dependencies

```bash
# Update and install Docker
apt-get update
apt-get install -y docker.io docker-compose
systemctl start docker
```

### 2. Extract Archive

```bash
cd /workspace
tar -xzf phase2_vastai.tar.gz
```

### 3. Install Python Dependencies

```bash
cd "/workspace/phase 2"
pip install -r requirements.txt
```

### 4. Start Qdrant Vector Database

```bash
# Start Qdrant in background
docker-compose up -d

# Wait a few seconds for startup
sleep 5

# Verify it's running
curl http://localhost:6333/collections
```

You should see: `{"result":{"collections":[]},"status":"ok","time":0.000xxx}`

### 5. Run Phase 2 Pipeline

```bash
python run.py XNQTWZ87K4I
```

## Expected Output

The pipeline will:
1. Load Phase 1 data (~1s)
2. Build timeline (~1s)
3. Create chunks (~1s)
4. Clean OCR text (~1s)
5. Align speech-to-slides (~1s)
6. Enrich metadata (~1s)
7. Generate embeddings (10-30s) ⚡ GPU-accelerated
8. Store in Qdrant (~1s)
9. Export files (~1s)

**Total time: ~20-40 seconds**

## Output Files

After completion, check:

```bash
ls -lh "/workspace/phase 2/output/XNQTWZ87K4I/"
```

You should see:
- `timeline.json` - Unified temporal spine
- `chunks.json` - All chunks with metadata
- `chunks.jsonl` - One chunk per line (training-ready)
- `chunks.parquet` - Columnar format

## Download Results

```bash
cd "/workspace/phase 2"
tar -czf phase2_results.tar.gz output/
```

Download `phase2_results.tar.gz` via Jupyter file browser.

## Verify Qdrant Data

```bash
# Check collection
curl http://localhost:6333/collections/video_chunks

# Count points
curl http://localhost:6333/collections/video_chunks/points/count
```

## Troubleshooting

### Docker not starting
```bash
systemctl status docker
systemctl start docker
docker-compose up -d
```

### CUDA errors
The pipeline should auto-detect GPU. If issues:
```bash
# Check GPU
nvidia-smi

# Run pipeline (it will use GPU automatically)
python run.py XNQTWZ87K4I
```

### Memory issues
Edit `src/config.py` if needed:
```python
batch_size: int = 4  # Reduce if OOM
```

## Cost Estimate

- RTX 4090 @ $0.26-0.58/hr
- Processing time: ~1 minute
- **Total cost: < $0.01** 💰

## Next Steps

After downloading results:
1. Verify chunk count (~10-12 chunks)
2. Inspect timeline and alignment scores
3. Ready for Phase 3 (RAG + fine-tuning prep)

## Quick Command Summary

```bash
# Full setup (run once)
apt-get update && apt-get install -y docker.io docker-compose
systemctl start docker
cd /workspace && tar -xzf phase2_vastai.tar.gz
cd "/workspace/phase 2" && pip install -r requirements.txt
docker-compose up -d && sleep 5

# Run pipeline
python run.py XNQTWZ87K4I

# Package results
tar -czf phase2_results.tar.gz output/
```
