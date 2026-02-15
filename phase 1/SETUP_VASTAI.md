# Setting Up on Vast.ai

Quick guide for running this pipeline on a Vast.ai GPU instance.

## 1. Select Instance

Recommended specs:
- **GPU**: RTX 3090, RTX 4090, A5000, or better
- **VRAM**: 24GB+ (for Whisper large-v3)
- **RAM**: 32GB+ system RAM
- **Storage**: 100GB+ (videos + models)
- **Image**: PyTorch 2.1+ with CUDA 12+

## 2. Initial Setup

Once connected to your instance:

```bash
# Update system
apt-get update && apt-get install -y ffmpeg git

# Clone the repository
cd /workspace
git clone <your-repo-url> graphical-context-extraction
cd graphical-context-extraction

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e .
```

## 3. Verify GPU

```bash
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}')"
```

Expected output:
```
CUDA available: True
GPU: NVIDIA GeForce RTX 3090
```

## 4. Test with Small Video First

Test with a smaller Whisper model to verify everything works:

```bash
python run.py "https://www.youtube.com/watch?v=XNQTWZ87K4I" \
  --model medium \
  --device cuda
```

This should take 5-15 minutes depending on video length and GPU.

## 5. Full Pipeline Run

Once verified, run with the large model:

```bash
python run.py "https://www.youtube.com/watch?v=XNQTWZ87K4I" \
  --model large-v3 \
  --device cuda \
  --diarize
```

## 6. Monitor Progress

The pipeline logs progress for each stage:

```
================================================================================
STAGE 1: Download Video and Metadata
================================================================================
✓ Download complete in 12.34s

================================================================================
STAGE 2: Normalize Media
================================================================================
✓ Normalization complete in 5.67s

...
```

## 7. Batch Processing Multiple Videos

Create a batch script:

```bash
#!/bin/bash
# batch_process.sh

VIDEOS=(
  "https://www.youtube.com/watch?v=VIDEO_ID_1"
  "https://www.youtube.com/watch?v=VIDEO_ID_2"
  "https://www.youtube.com/watch?v=VIDEO_ID_3"
)

for url in "${VIDEOS[@]}"; do
  echo "Processing: $url"
  python run.py "$url" --model large-v3 --device cuda
  echo "---"
done
```

Run:
```bash
chmod +x batch_process.sh
./batch_process.sh
```

## 8. Download Results

Transfer results back to your local machine:

```bash
# On your local machine
scp -r -P <port> root@<vast-ip>:/workspace/graphical-context-extraction/data/raw ./
```

Or use Vast.ai's file browser in the web interface.

## 9. Expected Performance

Typical processing times on RTX 3090 for a 30-minute video:

| Stage | Time | Notes |
|-------|------|-------|
| Download | 1-5 min | Depends on network |
| Normalize | 0.5-1 min | FFmpeg processing |
| ASR (large-v3) | 3-5 min | Whisper + WhisperX |
| Scene Detection | 1-2 min | PySceneDetect |
| Keyframes | 0.5-1 min | Extraction |
| OCR | 2-5 min | PaddleOCR per keyframe |
| **Total** | **8-20 min** | |

## 10. Troubleshooting

### Out of Memory

If you get CUDA OOM errors:

```bash
# Use smaller Whisper model
python run.py <url> --model medium --device cuda

# Or reduce batch size in code
# Edit src/config.py: whisperx_batch_size = 8
```

### Models Not Downloading

First run downloads several models:
- Whisper (large-v3): ~3GB
- WhisperX alignment models: ~1GB
- PaddleOCR models: ~100MB
- LayoutParser (optional): ~300MB

They cache in `~/.cache/`, so subsequent runs are faster.

### FFmpeg Not Found

```bash
apt-get update && apt-get install -y ffmpeg
```

### LayoutParser Fails

LayoutParser is optional. If it fails to install:

```bash
pip install layoutparser --no-deps
pip install "detectron2@git+https://github.com/facebookresearch/detectron2.git"
```

Or skip it - the pipeline will still work with OCR only.

## 11. Cost Estimation

Typical costs on Vast.ai (varies by GPU availability):

- **RTX 3090**: $0.20-0.40/hour
- **RTX 4090**: $0.40-0.70/hour
- **A5000**: $0.30-0.60/hour

Processing 30-min video: ~0.25 hours = **$0.05-0.20 per video**

## 12. Saving Your Setup

Once configured, you can save the instance as a template:

1. Install all dependencies
2. Stop the instance
3. Create a template from it in Vast.ai dashboard
4. Next time: launch from template (skip steps 2-3)

## 13. Best Practices

- **Use `tmux` or `screen`**: Keep pipeline running if SSH disconnects
  ```bash
  tmux new -s pipeline
  python run.py <url>
  # Ctrl+B then D to detach
  # tmux attach -t pipeline to reconnect
  ```

- **Monitor GPU usage**:
  ```bash
  watch -n 1 nvidia-smi
  ```

- **Set up auto-shutdown**: To avoid wasting credits if you forget
  ```bash
  # After processing completes, auto-shutdown in 10 min
  sudo shutdown -h +10
  ```

- **Backup frequently**: Download results periodically in case instance terminates

## 14. Python API for Batch Processing

```python
from src.pipeline import run_pipeline
from src.config import ModelConfig

model_config = ModelConfig(
    whisper_model="large-v3",
    whisper_device="cuda",
    whisperx_align=True,
    whisperx_diarize=True
)

videos = [
    "https://www.youtube.com/watch?v=VIDEO_ID_1",
    "https://www.youtube.com/watch?v=VIDEO_ID_2",
    "https://www.youtube.com/watch?v=VIDEO_ID_3",
]

for i, url in enumerate(videos, 1):
    print(f"\n{'='*80}")
    print(f"Processing video {i}/{len(videos)}: {url}")
    print('='*80)
    
    try:
        result = run_pipeline(
            video_url=url,
            model_config=model_config,
            skip_existing=True
        )
        print(f"✓ Success: {result['output_dir']}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        continue
```

Save as `batch_process.py` and run:
```bash
python batch_process.py
```
