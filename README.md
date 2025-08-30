# DocPixie 🧚‍♀️

**Multimodal RAG Without the Complexity**

DocPixie is a lightweight, vision-first RAG (Retrieval Augmented Generation) library that processes documents as images, eliminating the need for embeddings and vector databases. Built for developers who want powerful document understanding without the infrastructure overhead.

## Why DocPixie?

Traditional RAG systems require:
- Complex embedding pipelines
- Vector databases (Pinecone, Weaviate, etc.)
- Text extraction that loses visual context
- Separate OCR for images and tables

DocPixie simplifies everything:
- **Vision-native**: Documents become images, preserving layout and visual elements
- **No embeddings needed**: Vision models understand pages directly
- **Zero infrastructure**: Works with just local storage or S3
- **Adaptive intelligence**: Dynamic task planning based on document content

## Features

- 📄 **Universal Document Support**: PDF, images, and extensible to any format
- 👁️ **Vision-First RAG**: Analyzes actual page images, not extracted text
- 🧠 **Adaptive Agent**: Dynamically plans and adjusts analysis strategy
- 💬 **Conversation-Aware**: Maintains context across multi-turn interactions
- 🚀 **Simple API**: Both async and sync interfaces
- 🔌 **Multiple AI Providers**: OpenAI, Anthropic, OpenRouter support

## Quick Start

### Installation

```bash
pip install pymupdf pillow openai anthropic
```

### Basic Usage

```python
from docpixie import create_docpixie

# Initialize with your preferred provider
pixie = create_docpixie(
    provider="openai",  # or "anthropic", "openrouter"
    api_key="your-api-key"
)

# Add a document
doc = pixie.add_document_sync("research_paper.pdf")
print(f"Added document: {doc.name} with {doc.page_count} pages")

# Ask questions
result = pixie.query_sync(
    "What are the main findings of this research?"
)
print(result.answer)

# See which pages were analyzed
print(f"Analyzed pages: {result.page_numbers}")
```

### Async Usage

```python
import asyncio
from docpixie import create_docpixie

async def main():
    pixie = create_docpixie(provider="openai")
    
    # Add document
    doc = await pixie.add_document("presentation.pdf")
    
    # Query with conversation history
    from docpixie.models.agent import ConversationMessage
    
    history = [
        ConversationMessage(role="user", content="What's the main topic?"),
        ConversationMessage(role="assistant", content="The main topic is...")
    ]
    
    result = await pixie.query(
        "Can you elaborate on the methodology?",
        conversation_history=history
    )
    
    print(result.answer)

asyncio.run(main())
```

## How It Works

1. **Document Processing**: PDFs and images are converted to optimized JPEGs
2. **Page Summarization**: Vision models analyze all pages to create document summaries
3. **Adaptive Planning**: The agent creates focused tasks based on your query
4. **Vision Selection**: Relevant pages are selected by analyzing actual images
5. **Task Execution**: Each task analyzes specific pages to gather information
6. **Response Synthesis**: All findings are combined into a comprehensive answer

## Architecture Overview

```
DocPixie/
├── Document Processing     # PDF → Image conversion
├── Storage Layer          # Local, Memory, or S3
├── AI Providers           # OpenAI, Anthropic, OpenRouter
└── Adaptive RAG Agent     # Vision-based analysis
    ├── Context Processor  # Conversation handling
    ├── Task Planner      # Dynamic strategy
    ├── Page Selector     # Vision-based selection
    └── Synthesizer       # Response generation
```

## Configuration

```python
from docpixie import DocPixie
from docpixie.core.config import DocPixieConfig

config = DocPixieConfig(
    provider="anthropic",
    model="claude-3-opus-20240229",
    storage_type="local",
    local_storage_path="./my_documents",
    max_pages_per_task=8,
    jpeg_quality=95
)

pixie = DocPixie(config=config)
```

## Documentation

- [Getting Started](docs/getting-started.md) - Installation and first steps
- [Document Processing](docs/document-processing.md) - How documents are handled
- [Storage Options](docs/storage.md) - Local, memory, and S3 backends
- [Models & Providers](docs/models_and_providers.md) - AI models and provider configuration

## Requirements

- Python 3.8+
- PyMuPDF for PDF processing
- PIL/Pillow for image optimization
- OpenAI, Anthropic, or OpenRouter API key

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read our contributing guidelines before submitting PRs.

## Support

- GitHub Issues: [Report bugs or request features](https://github.com/your-org/docpixie/issues)
- Documentation: [Full documentation](https://docpixie.readthedocs.io)
- Discord: [Join our community](https://discord.gg/docpixie)