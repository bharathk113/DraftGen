# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-04-07

### Added
- **Vision Feature**: Direct image ingestion with vision-capable LLMs
  - Support for analyzing charts, graphs, maps, and diagrams directly
  - Google Gemini Vision API integration
  - OpenAI GPT-4 Vision API integration
  - Automatic fallback to text-only mode for non-vision backends
- **New Module**: `image_handler.py` for image processing and encoding
- **Enhanced Document Loading**: Extract actual images from PDF, DOCX, PPTX files
- **Vision-Aware Prompts**: Context-aware prompts that reference embedded images
- **Comprehensive Documentation**: Added `DEVELOPMENT.md` with architecture and testing guides
- **Modern Packaging**: Added `pyproject.toml` for better Python packaging
- **MIT License**: Added open-source license

### Changed
- **Document Loader**: Now extracts PIL Image objects instead of OCR text descriptions
- **LLM Client**: Added `generate_with_images()` method for vision-capable models
- **Agent**: Updated to use vision APIs when available with appropriate prompts
- **README**: Updated with vision feature documentation and examples
- **Image Mode Parameter**: `--image-mode auto` now uses vision APIs by default

### Improved
- **Image Processing**: Automatic resizing and format conversion for API compatibility
- **Error Handling**: Better fallback mechanisms for unsupported backends
- **Performance**: Filtered out tiny images to reduce processing overhead
- **Backward Compatibility**: Maintained support for existing workflows

### Technical Details
- Added `ExtractedImage` class for image metadata tracking
- Implemented base64 encoding for multiple vision API formats
- Added image filtering (< 50x50 pixels) to reduce noise
- Enhanced logging for vision API operations

## [0.1.0] - 2024-01-01

### Added
- Initial release of DraftGen
- Multi-document input support (PDF, DOCX, PPTX, TXT, MD, CSV, JSON)
- PowerPoint presentation generation
- Word report generation
- Pluggable LLM backend support (OpenAI, Google, Transformers)
- OCR support for image text extraction
- CLI interface with comprehensive options

### Features
- Document text extraction and processing
- LLM-powered content generation
- Template-based output generation
- Multi-format output support