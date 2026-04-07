# DraftGen Development Guide

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     agent.py (main entry)                   │
│                - Parse CLI arguments                        │
│                - Orchestrate workflow                       │
│                - Handle multiple input files                │
└────────┬──────────────────┬───────────────────────┬────────┘
         │                  │                       │
         ▼                  ▼                       ▼
┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ document_loader  │  │   image_handler │  │    llm_client    │
│  - Extract text  │  │ - Encode images │  │ - Vision API     │
│  - Extract imgs  │  │ - Resize & opt  │  │ - Text gen       │
└──────────────────┘  └─────────────────┘  └──────────────────┘
         │                     △                       △
         └─────────────────────┴───────────────────────┘
                     
┌──────────────────────┐        ┌──────────────────────┐
│ presentation_builder │        │   report_builder     │
│  - PPTX generation   │        │  - DOCX generation   │
└──────────────────────┘        └──────────────────────┘
```

### Key Classes

#### `ExtractedImage` (document_loader.py)
Wraps a PIL Image with metadata:
- `image`: PIL Image object
- `source`: Source format ("pdf", "docx", "pptx", "image")
- `page_or_shape`: Page/slide number for context
- `width`, `height`: Dimensions

#### `ImageHandler` (image_handler.py)
Static utility for image manipulation:
- Resizing large images
- Base64 encoding for APIs
- Format conversion (RGBA → RGB, etc.)
- Backend-specific encoding (OpenAI, Google, Claude)

#### `LLMClient` (llm_client.py)
Abstraction layer for LLM backends:
- `generate(prompt)`: Text-only generation
- `generate_with_images(prompt, images)`: Vision generation
- Backend detection and fallback logic
- Response parsing from different APIs

## Data Flow: Vision-Based Pipeline

### Input Processing
1. `load_document()` recursively processes input paths
2. For each file:
   - Extract text/structured content
   - Extract images as PIL Image objects → wrap in `ExtractedImage`
3. Return: `(text: str, images: list[ExtractedImage])`

### Generation with Vision
1. User provides `--image-mode auto` (default)
2. `agent.py` collects all extracted images
3. For each generation task (slides/report):
   - Check if LLM backend supports vision (OpenAI, Google)
   - If yes: Call `generate_with_images(prompt, images)`
   - If no: Fall back to `generate(prompt)` with text only
4. LLM receives:
   - All images base64-encoded (resized to prevent token explosion)
   - User prompt mentioning number and content of images
   - Document text for context

### Output Generation
1. Parse JSON response from LLM
2. Pass to `PresentationBuilder` or `ReportBuilder`
3. Generate `.pptx` or `.docx` with structured content

## Testing the Vision Feature

### Setup Test Environment

```bash
cd /home/bharath/Desktop/tests/DraftGen
conda activate agentic
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Test Case 1: Charts and Graphs

Create a test PDF with charts:
```bash
# Using a sample PDF with multiple charts
export GOOGLE_API_KEY="your_key"
python src/agent.py \
  --input "path/to/charts.pdf" \
  --backend google \
  --model-name gemini-2.0-flash \
  --mode report \
  --report-request "Extract all data points and trends from the charts"
```

Expected: Report should include specific numeric values and trend descriptions extracted from chart images.

### Test Case 2: Mixed Content (Text + Images)

```bash
# PDF with both text and embedded charts
export OPENAI_API_KEY="your_key"
python src/agent.py \
  --input "mixed_document.pdf" \
  --backend openai \
  --model-name gpt-4-vision-preview \
  --mode both \
  --slide-request "Focus on key metrics and trends" \
  --report-request "Create an executive summary"
```

Expected: Slides and report should reference specific insights from visualizations.

### Test Case 3: Fallback to Text-Only

```bash
# Using transformers backend (no vision support)
export MODEL_NAME="mistral.community/Mistral-7B-Instruct-v0.1"
python src/agent.py \
  --input "charts.pdf" \
  --backend transformers \
  --mode report
```

Expected: Should log warning about falling back to text-only, still produce valid output.

### Test Case 4: Image Extraction Verification

Create a quick script to verify image extraction:

```python
from src.document_loader import load_document

text, images = load_document("test.pdf")
print(f"Extracted {len(images)} images")
for i, img in enumerate(images):
    print(f"  Image {i+1}: {img.width}x{img.height} from {img.source}")
```

## Development Roadmap

### Phase 1: Core Vision Support ✅
- [x] Image extraction from PDF/DOCX/PPTX
- [x] Base64 encoding for API transmission
- [x] Google Gemini Vision API integration
- [x] OpenAI Vision API integration
- [x] Fallback to text-only for non-vision backends

### Phase 2: Enhanced Image Analysis (In Progress)
- [ ] Image summarization for memory efficiency
- [ ] Image caching to reduce API calls on re-runs
- [ ] Image quality assessment and selective processing
- [ ] Multi-image correlation (e.g., comparing charts across pages)

### Phase 3: Advanced Features
- [ ] Claude Vision API support
- [ ] Image annotation preservation
- [ ] Table structure recognition
- [ ] Handwriting OCR for notes
- [ ] Custom vision backends via plugins

### Phase 4: Optimization
- [ ] Lazy image loading for large documents
- [ ] Parallel image processing
- [ ] Cost estimation before processing
- [ ] Batch processing optimization

## Common Issues & Solutions

### Issue: "No candidates returned from Google Gemini API"
**Cause**: Image data format issue or API error
**Solution**: 
- Verify image dimensions are within API limits
- Check API key validity
- Log raw response in llm_client.py

### Issue: "Module 'image_handler' not found"
**Cause**: PYTHONPATH not set correctly
**Solution**: Run from DraftGen directory: `python src/agent.py`

### Issue: Slides/report missing image insights
**Cause**: Vision backend not activated or backend doesn't support vision
**Solution**: 
- Verify `--backend openai` or `--backend google`
- Check `--image-mode` is not "off"
- Log backup shows vision API was called

### Issue: "Out of context" errors from LLM
**Cause**: Too many images for single prompt
**Solution**:
- Implement image batching (future enhancement)
- Reduce `--max-slides` 
- Split document into smaller files

## Code Style

- Use snake_case for functions/variables
- Use CamelCase for classes
- Add type hints for all function signatures
- Document complex logic with comments
- Log significant operations with `logging.info()`

## Git Workflow

```bash
# Work on feature/direct-image-ingestion branch
git branch feature/direct-image-ingestion
git checkout feature/direct-image-ingestion

# Make changes, test thoroughly
python src/agent.py --input test.pdf --backend google --mode both

# Commit with descriptive messages
git add -A
git commit -m "feat: add Google Gemini Vision support for chart analysis"

# When ready, push and create pull request
git push origin feature/direct-image-ingestion
```

## Performance Notes

### Image Processing Overhead
- Image resizing: ~10-50ms per image (PIL)
- Base64 encoding: ~5-20ms per image
- API transmission: Depends on image size and network (~50-500ms)
- LLM processing: Highly variable (1-30s depending on model and batching)

### Optimization Techniques
- Batch images in groups of 3-5 per API call (future)
- Re-use encoded images across runs (caching)
- Resize images proactively based on backend limits
- Sample images from very large documents (intelligent selection)

## Resources

- [Google Gemini Vision API](https://ai.google.dev/tutorials/rest_quickstart)
- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision)
- [Pillow Image Library](https://python-pillow.org/)
- [PyPDF2 Documentation](https://pypdf2.readthedocs.io/)
