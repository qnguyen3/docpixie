# DocPixie

A lightweight multimodal RAG (Retrieval-Augmented Generation) library that uses vision AI instead of traditional embeddings or vector databases. DocPixie processes documents as images and uses vision language models for both document understanding and intelligent page selection.

## 🌟 Features

- **Vision-First Approach**: Documents processed as images using PyMuPDF, preserving visual information and formatting
- **No Vector Database Required**: Eliminates the complexity of embeddings and vector storage
- **Adaptive RAG Agent**: Single intelligent agent that dynamically plans tasks and selects relevant pages
- **Multi-Provider Support**: Works with OpenAI GPT-4V, Anthropic Claude, and OpenRouter
- **Modern CLI Interface**: Beautiful terminal UI built with Textual
- **Conversation Aware**: Maintains context across multiple queries
- **Pluggable Storage**: Local filesystem or in-memory storage backends

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/qnguyen3/docpixie.git

# Install dependencies
pip install -r requirements.txt

# Or use uv (recommended)
uv pip install -r requirements.txt
```

### Basic Usage

```python
import asyncio
from docpixie import DocPixie

async def main():
    # Initialize with your API key
    docpixie = DocPixie()

    # Add a document
    document = await docpixie.add_document("path/to/your/document.pdf")
    print(f"Added document: {document.name}")

    # Query the document
    result = await docpixie.query("What are the key findings?")
    print(f"Answer: {result.answer}")
    print(f"Pages used: {result.page_numbers}")

# Run the example
asyncio.run(main())
```

### Using the CLI

Start the interactive terminal interface:

```bash
python -m docpixie.cli
```

The CLI provides:
- Interactive document chat
- Document management
- Conversation history
- Model configuration
- Command palette with shortcuts

## 🛠️ Configuration

DocPixie uses environment variables for API key configuration:

```bash
# For OpenAI (default)
export OPENAI_API_KEY="your-openai-key"

# For Anthropic Claude
export ANTHROPIC_API_KEY="your-anthropic-key"

# For OpenRouter (supports many models)
export OPENROUTER_API_KEY="your-openrouter-key"
```

You can also specify the provider:

```python
from docpixie import DocPixie, DocPixieConfig

config = DocPixieConfig(
    provider="anthropic",  # or "openai", "openrouter"
    model="claude-3-opus-20240229",
    vision_model="claude-3-opus-20240229"
)

docpixie = DocPixie(config=config)
```

## 📚 Supported File Types

- **PDF files** (.pdf) - Full multipage support
- More file types coming soon

## 🏗️ Architecture

DocPixie uses a clean, modular architecture:

```
📁 Core Components
├── 🧠 Adaptive RAG Agent - Dynamic task planning and execution
├── 👁️  Vision Processing - Document-to-image conversion via PyMuPDF
├── 🔌 Provider System - Unified interface for AI providers
├── 💾 Storage Backends - Local filesystem or in-memory storage
└── 🖥️  CLI Interface - Modern terminal UI with Textual

📁 Processing Flow
1. Document → Images (PyMuPDF)
2. Vision-based summarization
3. Adaptive query processing
4. Intelligent page selection
5. Response synthesis
```

### Key Design Principles

- **Provider-Agnostic**: Generic model configuration works across all providers
- **Image-Based Processing**: All documents converted to images, preserving visual context
- **Business Logic Separation**: Raw API operations separate from workflow logic
- **Adaptive Intelligence**: Single agent mode that dynamically adjusts based on findings

## 🎯 Use Cases

- **Research & Analysis**: Query academic papers, reports, and research documents
- **Document Q&A**: Interactive questioning of PDFs, contracts, and manuals
- **Content Discovery**: Find specific information across large document collections
- **Visual Document Processing**: Handle documents with charts, diagrams, and complex layouts

## 🔧 Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v
```

## 🌍 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | None |
| `ANTHROPIC_API_KEY` | Anthropic API key | None |
| `OPENROUTER_API_KEY` | OpenRouter API key | None |
| `DOCPIXIE_PROVIDER` | AI provider | `openai` |
| `DOCPIXIE_STORAGE_PATH` | Storage directory | `./docpixie_data` |
| `DOCPIXIE_JPEG_QUALITY` | Image quality (1-100) | `90` |

## 📖 Documentation

- [Getting Started Guide](docs/getting-started.md) - Detailed examples and tutorials
- [CLI Tool Guide](docs/cli-tool.md) - Complete CLI documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF processing
- CLI powered by [Textual](https://textual.textualize.io/)
- Supports OpenAI, Anthropic, and OpenRouter APIs

---
