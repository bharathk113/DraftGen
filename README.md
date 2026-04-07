# DraftGen

DraftGen is a Python CLI for turning source documents into polished deliverables. It ingests one or more files or folders, extracts text and embedded visuals, and uses an LLM to generate:

- PowerPoint presentations (`.pptx`)
- Word reports (`.docx`)
- both outputs in a single run

The project is built for practical document-to-deliverable workflows and supports multimodal generation with vision-capable models, interactive revision, and multiple backend options.

## Highlights

- Multi-document input from files or folders
- Support for `pdf`, `docx`, `pptx`, `txt`, `md`, `csv`, `json`, and common image formats
- Direct image ingestion for charts, graphs, diagrams, maps, and other embedded visuals
- PowerPoint and Word generation from the same source material
- Interactive review loop for refining generated slides and reports
- Optional PowerPoint template support
- Pluggable backend selection across OpenAI, Google Gemini, and local Transformers
- Graceful fallback to text-only generation when vision is unavailable

## How It Works

1. DraftGen loads one or more input documents.
2. It extracts usable text and any embedded images.
3. A selected LLM backend generates structured JSON for slides, reports, or both.
4. DraftGen builds final `.pptx` and `.docx` outputs from that structured content.
5. If interactive mode is enabled, you can iteratively revise the generated content before export.

## Supported Backends

| Backend | Text Generation | Vision Support | Notes |
| --- | --- | --- | --- |
| Google Gemini | Yes | Yes | Good option for multimodal analysis |
| OpenAI-compatible | Yes | Yes | Supports interactive generation and vision-capable models |
| Transformers | Yes | No | Local text-only fallback |

## Requirements

- Python 3.8+
- `pip`
- Optional: Tesseract OCR if you want legacy OCR-based workflows

## Installation

```bash
git clone https://github.com/bharathk113/DraftGen.git
cd DraftGen
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional OCR support:

```bash
pip install pytesseract
```

## Configuration

Set only the credentials required for the backend you plan to use. You can export them directly in your shell or place them in your local environment management workflow.

### OpenAI-compatible backend

```bash
export OPENAI_API_KEY="your_api_key"
python src/agent.py \
  --input path/to/document.pdf \
  --backend openai \
  --model-name gpt-4o-mini
```

### Google Gemini backend

```bash
export GOOGLE_API_KEY="your_api_key"
export GOOGLE_MODEL="gemini-2.0-flash"
python src/agent.py \
  --input path/to/document.pdf \
  --backend google
```

### Local Transformers backend

```bash
export MODEL_NAME="your-huggingface-model"
export HUGGINGFACE_API_TOKEN="your_token_if_required"
python src/agent.py \
  --input path/to/document.pdf \
  --backend transformers
```

## Quick Start

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

## Interactive Review

DraftGen supports iterative refinement after the initial generation step.

Use `--interactive` to review generated slides or report sections in the terminal, then provide natural-language revision requests such as:

- reduce the deck to 3 slides
- add more detail to each slide
- include 3 relevant images per slide
- make the report more executive-summary oriented

Example:

```bash
python src/agent.py \
  --input path/to/document.pdf \
  --mode slides \
  --interactive \
  --interactive-rounds 3 \
  --slide-request "Create a presentation for leadership review"
```

## Vision-Based Image Analysis

DraftGen can analyze embedded visuals directly instead of relying only on OCR. This improves output quality for image-heavy documents such as reports with charts, diagrams, dashboards, or maps.

### Image mode options

- `--image-mode auto`: Use vision if the selected backend supports it
- `--image-mode off`: Ignore images and run in text-only mode
- `--image-mode ocr`: Legacy compatibility mode; currently behaves like `auto`

### Example: report generation with vision

```bash
export GOOGLE_API_KEY="your_api_key"
export GOOGLE_MODEL="gemini-2.0-flash"

python src/agent.py \
  --input path/to/document_with_charts.pdf \
  --backend google \
  --mode report \
  --report-request "Extract key trends, comparisons, and supporting visuals"
```

### Benefits of direct image ingestion

- Better interpretation of charts and trend lines
- Improved understanding of diagrams and spatial relationships
- Stronger grounding for image-referenced observations
- Better handling of visual structure than OCR-only workflows

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
- `--interactive`: Enable interactive revision after initial generation
- `--interactive-rounds`: Maximum number of interactive revision rounds

## Repository Structure

```text
.
├── CHANGELOG.md
├── CONTRIBUTING.md
├── DEVELOPMENT.md
├── README.md
├── pyproject.toml
├── requirements.txt
└── src
    ├── agent.py
    ├── document_loader.py
    ├── image_handler.py
    ├── llm_client.py
    ├── presentation_builder.py
    └── report_builder.py
```

## Limitations

- Vision support is available only on supported OpenAI-compatible and Google backends.
- Transformers mode is text-only.
- Vision-enabled generation can cost more and take longer than text-only runs.
- Very image-dense documents may require tighter prompts or smaller batches for best results.
- The repository currently does not include automated tests.

## Documentation

- [Development Guide](DEVELOPMENT.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Vision Feature Summary](VISION_FEATURE_SUMMARY.md)

## Contributing

Contributions are welcome. Please keep changes focused, document behavior changes, and include clear verification steps in pull requests. For contributor workflow and expectations, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the terms of the [MIT License](LICENSE).
