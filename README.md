# DraftGen

DraftGen is a Python CLI that ingests one or more source documents, extracts usable text, and uses an LLM to generate:

- a PowerPoint presentation (`.pptx`)
- a structured Word report (`.docx`)
- or both in a single run

The project is designed for lightweight document-to-deliverable workflows and supports common business file formats such as PDF, DOCX, PPTX, Markdown, plain text, JSON, CSV, and image files.

## Features

- Multi-document input via files or folders
- Support for `pdf`, `docx`, `pptx`, `txt`, `md`, `csv`, `json`, and common image formats
- Optional OCR-based image text extraction with `pytesseract`
- PowerPoint generation with optional template support
- Word report generation from the same source material
- Pluggable LLM backend selection:
  - Google Gemini-compatible API
  - OpenAI-compatible API
  - local Hugging Face Transformers models

## Project Structure

```text
.
├── requirements.txt
├── src
│   ├── agent.py
│   ├── document_loader.py
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

## Notes and Limitations

- PDF text extraction currently focuses on selectable text; embedded PDF image extraction is not implemented.
- OCR is optional and depends on `pytesseract` plus a system Tesseract installation.
- The default output files `output.pptx` and `output.docx` are generated artifacts and are ignored by Git.
- This repository currently does not include automated tests.

## Contributing

Small improvements and cleanup contributions are welcome. Please open an issue or pull request with a clear summary of the problem, the proposed change, and any verification steps.

## License

No license file is included yet. Add a project license before publishing publicly if you want others to reuse or redistribute the code.
