# Phase 3: Extraction Validation and Q&A Generation

Visual validation report and Q&A pair generation for video extraction pipeline.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate validation report only (no API needed)
python run.py XNQTWZ87K4I --report-only

# Generate report + Q&A pairs (requires Gemini API)
python run.py XNQTWZ87K4I
```

## What It Does

1. **OCR Overlay**: Draws bounding boxes on all keyframes to visually verify OCR extraction
2. **Coverage Analysis**: Timeline analysis showing gaps in data extraction
3. **HTML Report**: Self-contained report with embedded images for visual verification
4. **Q&A Pairs**: Generates training Q&A pairs using Gemini

## Outputs

```
output/
  XNQTWZ87K4I/
    report.html              # Open in browser to verify extraction
    keyframes_annotated/     # Keyframes with OCR bounding boxes
    coverage.json            # Timeline coverage analysis
    qa_pairs.jsonl           # Q&A pairs for fine-tuning
```

## Usage

```bash
# Full pipeline
python run.py XNQTWZ87K4I

# Report only (skip Q&A generation)
python run.py XNQTWZ87K4I --report-only

# Verbose logging
python run.py XNQTWZ87K4I --verbose
```

## Configuration

Edit `src/config.py` or set environment variables:

```bash
# Gemini API key (optional, only needed for Q&A generation)
export GEMINI_API_KEY="your_key_here"
```

## Report Sections

1. **Summary Dashboard**: Key metrics and pass/fail verdict
2. **Timeline Strip**: Visual timeline showing chapters, scenes, keyframes, and gaps
3. **Chunk Details**: Frame-by-frame view with OCR overlays, ASR text, and OCR text
4. **Gaps & Issues**: Extraction gaps and quality flags

## Dependencies

- Pillow: Image processing
- numpy: Array operations
- google-genai: Gemini API
- python-dotenv: Environment variables
