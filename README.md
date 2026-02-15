# Graphical Context Extraction from Tutorial Videos

Extract rich, timestamped training data from tutorial videos for LLM fine-tuning and RAG systems. This is **Phase 1** of the complete pipeline - raw extraction of ASR, scenes, keyframes, and OCR data.

## Features

- **Video Download**: YouTube video download with metadata and captions
- **Media Normalization**: Audio extraction (16kHz WAV) and video normalization
- **ASR with Word-Level Timestamps**: Whisper large-v3 + WhisperX forced alignment
- **Scene Detection**: PySceneDetect for identifying slide/screen changes
- **Smart Keyframe Extraction**: Blur filtering and delta-based sampling
- **OCR + Layout Parsing**: PaddleOCR for text extraction, LayoutParser for structure

## Requirements

- Python 3.10+
- CUDA-capable GPU (recommended for Whisper and PaddleOCR)
- FFmpeg installed on system

## Installation

1. Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

2. Install Python dependencies:

```bash
pip install -e .
```

Or using requirements.txt:

```bash
pip install -r requirements.txt
```

## Quick Start

Process a single video:

```bash
python -m src.pipeline "https://www.youtube.com/watch?v=XNQTWZ87K4I"
```

Or use the Python API:

```python
from src.pipeline import run_pipeline

result = run_pipeline("https://www.youtube.com/watch?v=XNQTWZ87K4I")
print(f"Output saved to: {result['output_dir']}")
```

## Output Structure

After processing, each video gets its own directory:

```
data/raw/{video_id}/
  source/
    video.mp4           # Original downloaded video
    metadata.json       # Video metadata (title, duration, chapters, etc.)
    captions_en.vtt     # Captions (if available)
  normalized/
    audio.wav           # 16kHz mono audio for ASR
    video.mp4           # Normalized video (constant framerate)
  keyframes/
    frame_00000.jpg     # Extracted keyframes
    frame_00001.jpg
    ...
  asr.json             # ASR transcript with word-level timestamps
  transcript.txt       # Human-readable transcript
  scenes.json          # Scene boundaries
  keyframes.json       # Keyframe metadata (timestamps, blur scores)
  ocr.json             # OCR results per keyframe
```

## Configuration

Customize processing via `ModelConfig`:

```python
from pathlib import Path
from src.config import PipelineConfig, ModelConfig
from src.pipeline import VideoPipeline

model_config = ModelConfig(
    whisper_model="large-v3",         # or "medium", "small"
    whisper_device="cuda",             # or "cpu"
    scene_threshold=27.0,              # Lower = more sensitive
    blur_threshold=100.0,              # Higher = sharper frames only
    ocr_lang="en",                     # or "ch", "fr", etc.
    layout_model="lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config"
)

config = PipelineConfig(
    video_url="https://www.youtube.com/watch?v=XNQTWZ87K4I",
    model_config=model_config,
    skip_existing=True
)

pipeline = VideoPipeline(config)
result = pipeline.run()
```

## Output Formats

### ASR (asr.json)

```json
{
  "segments": [
    {
      "start": 0,
      "end": 3500,
      "text": "Welcome to this GDPR tutorial",
      "words": [
        {"word": "Welcome", "start": 0, "end": 500, "probability": 0.98}
      ]
    }
  ],
  "language": "en",
  "aligned": true
}
```

### Scenes (scenes.json)

```json
{
  "scenes": [
    {
      "scene_id": 0,
      "start_ms": 0,
      "end_ms": 5230,
      "duration_ms": 5230
    }
  ]
}
```

### Keyframes (keyframes.json)

```json
{
  "keyframes": [
    {
      "frame_id": 0,
      "scene_id": 0,
      "timestamp_ms": 1200,
      "filename": "frame_00000.jpg",
      "blur_score": 342.5,
      "width": 1920,
      "height": 1080
    }
  ]
}
```

### OCR (ocr.json)

```json
{
  "results": [
    {
      "frame_id": 0,
      "timestamp_ms": 1200,
      "text_blocks": [
        {
          "text": "Article 6 - Lawful Basis",
          "bbox": [100, 50, 800, 120],
          "confidence": 0.95
        }
      ],
      "layout_regions": [
        {
          "type": "Title",
          "bbox": [50, 40, 850, 130],
          "confidence": 0.92
        }
      ],
      "full_text": "Article 6 - Lawful Basis for Processing..."
    }
  ]
}
```

## GPU Usage

The pipeline automatically uses GPU if available:

- **Whisper**: CUDA via faster-whisper (CTranslate2)
- **WhisperX**: CUDA for alignment and diarization
- **PaddleOCR**: PaddlePaddle GPU support
- **LayoutParser**: Detectron2 CUDA support

To force CPU-only:

```python
model_config = ModelConfig(
    whisper_device="cpu",
    ocr_use_gpu=False
)
```

## Performance Tips

1. **Use GPU**: 10-50x faster for ASR and OCR
2. **Adjust scene threshold**: Lower values detect more scenes (more keyframes)
3. **Skip existing outputs**: Set `skip_existing=True` to resume interrupted runs
4. **Batch processing**: Process multiple videos in parallel

## What's Next?

This is Phase 1 (raw extraction). Future phases:

- **Phase 2**: Temporal alignment, hierarchical chunking, privacy/redaction, vector DB storage
- **Phase 3**: RAG pipeline, fine-tuning export, validation metrics

## Troubleshooting

### WhisperX alignment fails

WhisperX requires additional dependencies for some languages. The pipeline will fall back to base Whisper timestamps if alignment fails.

### LayoutParser not available

LayoutParser is optional. If it fails to install, the pipeline will skip layout detection and only use OCR.

### CUDA out of memory

Reduce batch size or use a smaller Whisper model:

```python
model_config = ModelConfig(
    whisper_model="medium",  # instead of large-v3
    whisperx_batch_size=8    # instead of 16
)
```

## License

This project is for research and educational purposes. Ensure you have the rights to process any videos you download.
