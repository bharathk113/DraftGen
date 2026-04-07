# Contributing

Thanks for contributing to DraftGen!

## Development Setup

```bash
git clone https://github.com/bharathk113/DraftGen.git
cd DraftGen
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Testing Vision Features

The project includes advanced vision capabilities for analyzing images, charts, and diagrams. To test these features:

### Prerequisites
- Google Gemini API key (for Google backend)
- OpenAI API key (for OpenAI Vision backend)
- Test documents with charts/graphs/maps

### Testing Commands
```bash
# Test Google Gemini Vision
export GOOGLE_API_KEY="your_key"
python src/agent.py --input test_charts.pdf --backend google --mode report

# Test OpenAI Vision
export OPENAI_API_KEY="your_key"
python src/agent.py --input test_charts.pdf --backend openai --model-name gpt-4-vision-preview --mode both

# Test fallback to text-only
python src/agent.py --input test.pdf --backend transformers --mode report
```

## Guidelines

- Keep changes focused and easy to review.
- Update documentation when behavior or setup changes.
- Test vision features with actual image-containing documents.
- Avoid committing generated files, virtual environments, local editor settings, or secrets.
- Include clear reproduction or verification steps in pull requests.

## Pull Requests

Please include:

- **What changed**: Describe the modifications
- **Why it changed**: Explain the rationale
- **How it was tested**: Include test commands and sample outputs
- **Impact on vision features**: If applicable, describe how it affects image processing

## Code Style

- Use type hints for function signatures
- Add docstrings for complex functions
- Log significant operations with `logging.info()`
- Follow snake_case for variables/functions, CamelCase for classes
