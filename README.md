# Graphical Context Extraction Pipeline

Automated extraction of multimodal training data from tutorial videos. Captures spoken content, on-screen text, slides, and UI elements for LLM fine-tuning.

## Overview

3-phase pipeline that processes videos and extracts synchronized audio-visual content with 97.8% coverage accuracy.

**Pipeline:** Video → Raw Extraction → Alignment & Chunking → Validation & Q&A Generation

## Quick Start

```bash
# Phase 1: Extract raw data (GPU recommended)
cd "phase 1"
python run.py https://www.youtube.com/watch?v=VIDEO_ID

# Phase 2: Align and chunk data
cd "../phase 2"
python run.py VIDEO_ID

# Phase 3: Validate and generate Q&A pairs
cd "../phase 3"
pip install -r requirements.txt
python run.py VIDEO_ID
```

## Pipeline Architecture

### Phase 1: Raw Extraction (GPU-Accelerated)
- **ASR**: Whisper large-v3 for speech transcription
- **OCR**: EasyOCR for text extraction from frames
- **Scene Detection**: PySceneDetect for visual boundaries
- **Keyframe Extraction**: Smart sampling with blur filtering

**Output:** 53 ASR segments, 18 keyframes, 486 OCR blocks

### Phase 2: Alignment & Enrichment
- **Timeline Building**: Unified temporal spine
- **Hierarchical Chunking**: Chapter → Scene → Segments
- **OCR Cleanup**: Remove UI chrome and duplicates
- **Embeddings**: Text (sentence-transformers) + Image (OpenCLIP)
- **Storage**: Qdrant vector database

**Output:** 9 multimodal chunks with embeddings

### Phase 3: Validation & Q&A Generation
- **Visual Validation**: OCR overlays on keyframes (color-coded by confidence)
- **Coverage Analysis**: Timeline gaps and quality flags
- **HTML Report**: Self-contained report with embedded images
- **Q&A Generation**: Gemini-based training pair creation

**Output:** HTML/PDF report, 35 Q&A pairs, 97.8% coverage

## Sample Q&A Pairs Generated

**Example 1:**
```json
{
  "question": "What is the first common mistake listed regarding cookie banners?",
  "answer": "Having a banner that does not block cookies before explicit consent is given.",
  "evidence_type": "both"
}
```

**Example 2:**
```json
{
  "question": "According to the slide shown, what is the second question related to common mistakes?",
  "answer": "Have you made it easy to withdraw consent?",
  "evidence_type": "visual"
}
```

**Example 3:**
```json
{
  "question": "Which specific regulations are listed under the solution description on screen?",
  "answer": "GDPR, CCPA, and LGPD.",
  "evidence_type": "visual"
}
```

## Key Features

✅ **Multimodal Extraction**: Captures spoken words + on-screen text + visual layout  
✅ **Temporal Alignment**: Synchronizes all data streams on millisecond timeline  
✅ **Smart Chunking**: Hierarchical organization (Chapter → Scene → Segment)  
✅ **Visual Validation**: HTML report with OCR overlays proves extraction quality  
✅ **Training Ready**: Q&A pairs in JSONL format for fine-tuning  
✅ **Vector Search**: Embeddings stored in Qdrant for semantic retrieval

## Results

| Metric | Value |
|--------|-------|
| Extraction Coverage | 97.8% |
| Keyframes Extracted | 18 |
| OCR Text Blocks | 486 |
| ASR Segments | 53 |
| Multimodal Chunks | 9 |
| Q&A Pairs Generated | 35 |
| Quality Issues | 0 |

## Project Structure

```
├── phase 1/              # Raw extraction (ASR, OCR, scenes, keyframes)
│   ├── run.py
│   └── XNQTWZ87K4I/     # Video outputs
├── phase 2/              # Alignment, chunking, embeddings
│   ├── run.py
│   └── output/
├── phase 3/              # Validation report & Q&A generation
│   ├── run.py
│   └── output/
│       └── XNQTWZ87K4I/
│           ├── report.html
│           ├── report.pdf
│           └── qa_pairs.jsonl
└── EXECUTIVE_SUMMARY.pdf
```

## Tech Stack

- **ASR**: faster-whisper (OpenAI Whisper large-v3)
- **OCR**: EasyOCR (GPU-accelerated)
- **Scene Detection**: PySceneDetect
- **Embeddings**: sentence-transformers, OpenCLIP
- **Vector DB**: Qdrant (cloud)
- **Q&A Generation**: Google Gemini 3 Pro
- **Infrastructure**: vast.ai (GPU), local (CPU)

## Dependencies

Each phase has its own `requirements.txt`. Install per phase as needed.

## Documentation

- **Phase 1**: See `phase 1/README.md` and `phase 1/IMPLEMENTATION_SUMMARY.md`
- **Phase 2**: See `phase 2/README.md` and `phase 2/IMPLEMENTATION_SUMMARY.md`
- **Phase 3**: See `phase 3/README.md` and `phase 3/IMPLEMENTATION_SUMMARY.md`
- **Executive Summary**: See `EXECUTIVE_SUMMARY.pdf`
- **Technical Validation**: See `phase 3/output/XNQTWZ87K4I/report.pdf`

## License

Research and educational purposes.
