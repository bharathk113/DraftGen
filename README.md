# DraftGen

DraftGen is a Python CLI that ingests one or more source documents, extracts usable text, and uses an LLM to generate:

- a PowerPoint presentation (`.pptx`)
- a structured Word report (`.docx`)
- or both in a single run

The project is designed for lightweight document-to-deliverable workflows and supports common business file formats such as PDF, DOCX, PPTX, Markdown, plain text, JSON, CSV, and image files.

## Features

- Multi-document input via files or folders
- Support for `pdf`, `docx`, `pptx`, `txt`, `md`, `csv`, `json`, and common image formats
- **NEW: Direct image ingestion with vision-capable LLMs** - Analyzes charts, graphs, maps, and diagrams directly for accurate context (requires OpenAI GPT-4V/Claude Vision or Google Gemini Vision)
- Optional OCR-based image text extraction with `pytesseract` (fallback for non-vision backends)
- PowerPoint generation with optional template support
- Word report generation from the same source material
- Pluggable LLM backend selection with vision support:
  - Google Gemini Vision (supports images)
  - OpenAI GPT-4 Vision (supports images)
  - OpenAI-compatible API
  - local Hugging Face Transformers models (text-only)

## Project Structure

```text
.
├── requirements.txt
├── src
│   ├── agent.py
│   ├── document_loader.py
│   ├── image_handler.py
│   ├── llm_client.py
│   ├── presentation_builder.py
│   └── report_builder.py
└── .env.example
```

## Requirements

- Python 3.9+
- `pip`
- Optional: Tesseract OCR installed on your system if you want OCR from embedded images

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you plan to use OCR:

```bash
pip install pytesseract
```

## Configuration

Copy the example environment file if you want a simple starting point:

```bash
cp .env.example .env
```

Set only the variables needed for the backend you want to use.

### OpenAI-compatible backend

```bash
export OPENAI_API_KEY="your_api_key"
python src/agent.py --input path/to/document.pdf --backend openai --model-name gpt-4o-mini
```

### Google backend

```bash
export GOOGLE_API_KEY="your_api_key"
export GOOGLE_MODEL="gemini-flash-latest"
python src/agent.py --input path/to/document.pdf --backend google
```

### Local Transformers backend

```bash
export MODEL_NAME="your-huggingface-model"
export HUGGINGFACE_API_TOKEN="your_token_if_required"
python src/agent.py --input path/to/document.pdf --backend transformers
```

## Usage

Generate slides:

```bash
python src/agent.py \
  --input path/to/document.pdf \
  --mode slides \
  --output-ppt output.pptx
```

Generate a report:

```bash
python src/agent.py \
  --input path/to/document.pdf \
  --mode report \
  --output-docx output.docx
```

Generate both outputs:

```bash
python src/agent.py \
  --input path/to/folder_or_file \
  --mode both \
  --output-ppt output.pptx \
  --output-docx output.docx
```

Use a PowerPoint template:

```bash
python src/agent.py \
  --input path/to/document.pdf \
  --mode slides \
  --template path/to/template.pptx \
  --output-ppt output.pptx
```

Disable embedded-image OCR/context:

```bash
python src/agent.py \
  --input path/to/document.pdf \
  --image-mode off
```

## Vision-Based Image Analysis (Direct Image Ingestion)

**New Feature**: DraftGen now supports direct image ingestion with vision-capable LLMs for superior analysis of charts, graphs, maps, and visual data.

### How It Works

Instead of extracting text from images via OCR, DraftGen:
1. **Extracts images directly** from PDF, DOCX, and PPTX files
2. **Sends images to vision-capable LLMs** (Google Gemini Vision, OpenAI GPT-4V, etc.)
3. **Analyzes visual content** including:
   - Charts and trend analysis
   - Maps and geographic data
   - Diagrams and flowcharts
   - Tables and data visualizations
   - Technical drawings

### Using Vision-Capable Backends

For best results with image-heavy documents:

**Google Gemini Vision**:
```bash
export GOOGLE_API_KEY="your_api_key"
export GOOGLE_MODEL="gemini-2.0-flash"
python src/agent.py \
  --input path/to/document_with_charts.pdf \
  --backend google \
  --mode both \
  --report-request "Extract data from all charts and graphs, including trends and values"
```

**OpenAI GPT-4V**:
```bash
export OPENAI_API_KEY="your_api_key"
python src/agent.py \
  --input path/to/document_with_charts.pdf \
  --backend openai \
  --model-name gpt-4-vision-preview \
  --mode both
```

### Image Mode Options

- `--image-mode off`: Ignore all images (text-only mode)
- `--image-mode auto`: Use vision API if available with the current backend, otherwise fall back to text-only
- `--image-mode ocr`: Legacy mode - same as `auto` (for backward compatibility)

### Benefits Over OCR

- **Accurate trend analysis**: Identifies slopes, inflection points, and patterns in charts
- **Spatial understanding**: Comprehends relationships in diagrams and maps
- **Color and formatting**: Understands visual hierarchy and emphasis
- **No text loss**: Captures handwritten notes and non-standard fonts
- **Reduced hallucination**: Vision models provide grounded analysis

### Limitations

- Transformers backend does not support images (uses text-only fallback)
- Image analysis is more expensive per token than text-only processing
- Vision-capable models may have higher latency

## CLI Options

Key options exposed by `src/agent.py`:

- `--input`: One or more input files or folders
- `--mode`: `slides`, `report`, or `both`
- `--output-ppt`: Output path for generated presentation
- `--output-docx`: Output path for generated report
- `--template`: Optional PowerPoint template
- `--slide-request`: Custom instruction for slide generation
- `--report-request`: Custom instruction for report generation
- `--max-slides`: Maximum number of generated slides
- `--backend`: `auto`, `openai`, `google`, or `transformers`
- `--model-name`: Override model selection for supported backends
- `--image-mode`: `off`, `ocr`, or `auto`
- `--interactive`: Enable interactive review after initial generation
- `--interactive-rounds`: Maximum number of interactive revision rounds

## Notes and Limitations

- **PDF image extraction**: Direct image extraction from PDFs is now supported for vision-capable backends.
- **Vision model costs**: Vision-capable LLMs (GPT-4V, Gemini Vision) process images token-by-token and may be more expensive than text-only models.
- **OCR** (optional, legacy): Requires `pytesseract` plus system Tesseract installation for text extraction from images when using non-vision backends.
- Image filtering: Very small images (< 50x50 pixels) are automatically filtered out to reduce processing overhead.
- The default output files `output.pptx` and `output.docx` are generated artifacts and are ignored by Git.
- This repository currently does not include automated tests.

## Contributing

Small improvements and cleanup contributions are welcome. Please open an issue or pull request with a clear summary of the problem, the proposed change, and any verification steps.
