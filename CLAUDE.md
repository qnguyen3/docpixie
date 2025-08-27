# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DocPixie is a lightweight multimodal RAG library that uses vision AI instead of embeddings/vector databases. Documents are processed as images and analyzed using vision language models for both understanding and page selection.

**Current Status**: Phase 1 complete (document processing, storage, configuration, page summarization). Phase 2 in progress (vision-based page selection and full RAG pipeline).

## Development Commands

### Environment Setup
```bash
# Set up virtual environment with uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Or with pip
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_basic.py -v

# Run single test method
python -m pytest tests/test_basic.py::TestDocPixieConfig::test_default_config -v
```

### Running Examples
```bash
# Set API key first
export OPENAI_API_KEY="your-key"
# or 
export ANTHROPIC_API_KEY="your-key"
# or
export OPENROUTER_API_KEY="your-key"

# Run basic usage example
python examples/basic_usage.py
```

## Core Architecture

### Provider System
The codebase uses a clean separation between **raw API operations** and **business logic**:

- **Providers** (`docpixie/providers/`): Handle only raw API calls with generic `process_text_messages()` and `process_multimodal_messages()` methods
- **AI Operations** (`docpixie/ai/`): Contain all business logic, prompt construction, and workflow orchestration

### Key Architectural Principles

1. **Provider-Agnostic Configuration**: Uses generic `flash_model`, `pro_model`, `vision_model` fields that work across all providers
2. **Automatic Provider Defaults**: `DocPixieConfig._set_provider_defaults()` sets appropriate models based on selected provider
3. **Image-Based Processing**: All documents converted to images via PyMuPDF, preserving visual information
4. **Flash/Pro Modes**: Two complexity levels - Flash (5 pages, fast) vs Pro (15 pages, comprehensive)

### Provider Implementation Pattern
When adding new providers:
1. Inherit from `BaseProvider`
2. Implement only `process_text_messages()` and `process_multimodal_messages()`
3. Handle provider-specific message formatting (e.g., image_path → provider format)
4. Add to `providers/factory.py` and provider defaults in `config.py`

Example: OpenRouter provider uses OpenAI client with `base_url="https://openrouter.ai/api/v1"`

### Document Processing Flow
1. **PDF → Images**: PyMuPDF converts PDF pages to optimized JPEGs
2. **Storage**: Local filesystem or in-memory storage via pluggable backends
3. **Summarization**: Vision models analyze all page images in single API call for document summary
4. **Page Selection** (Phase 2): Vision-based selection instead of vector similarity

### Configuration System
- Environment-first approach: API keys loaded from `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`
- Provider-agnostic model configuration
- Mode-specific settings (flash vs pro timeouts, page limits, vision detail)
- Test API key support: Use `"test-key"` to bypass validation during testing

### File Structure Significance

```
docpixie/
├── core/config.py          # Central configuration with provider defaults
├── providers/              # Raw API operations only
│   ├── base.py            # Generic message processing interface
│   ├── openai.py          # OpenAI API client
│   ├── anthropic.py       # Claude API client (handles different system message format)
│   ├── openrouter.py      # OpenRouter using OpenAI client + different base_url
│   └── factory.py         # Provider creation and validation
├── ai/                     # Business logic layer
│   └── summarizer.py      # Page/document summarization workflows
├── processors/             # Document-to-image conversion
│   ├── pdf.py             # PyMuPDF implementation
│   └── factory.py         # Auto-detection of processor type
├── storage/                # Pluggable storage backends
│   ├── local.py           # Filesystem storage
│   └── memory.py          # In-memory storage (for testing)
└── models/document.py      # Core data models without embeddings
```

## Important Implementation Details

### Configuration Testing
Never use test mode flags. Instead, use test API keys (`"test-key"`) which automatically bypass validation.

### Document Summarization
The critical architectural decision: document summaries use ALL page images in a single vision API call, not individual page summaries combined. This preserves visual context and document structure.

### Provider Message Format
All providers receive messages with `image_path` type, then convert to their specific format:
- OpenAI: `image_url` with data URL
- Anthropic: `image` with base64 data  
- OpenRouter: Same as OpenAI

### Flash vs Pro Mode Implementation
Configuration provides mode-specific settings accessed via `config.get_mode_config(mode)`. Providers don't know about modes - business logic layer handles mode differences.

## Environment Variables

```bash
# Required for respective providers
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key  
OPENROUTER_API_KEY=your_openrouter_key

# Optional configuration overrides
DOCPIXIE_PROVIDER=openai|anthropic|openrouter
DOCPIXIE_STORAGE_PATH=./docpixie_data
DOCPIXIE_FLASH_MAX_PAGES=5
DOCPIXIE_PRO_MAX_PAGES=15
DOCPIXIE_JPEG_QUALITY=90
```

## Phase Development Context

This codebase implements a phased approach documented in `DOCPIXIE_IMPLEMENTATION_PLAN.md`:

- **Phase 1 ✅**: Document processing, storage, configuration, page summarization
- **Phase 2 🚧**: Vision-based page selection, complete RAG pipeline  
- **Phase 3+**: Advanced features, optimizations

Current work focuses on Phase 2 implementation. The architecture is designed to support the full vision-based RAG pipeline without embeddings or vector databases.