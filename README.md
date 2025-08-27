# DocPixie Open Source - Phase 1

A lightweight, vision-based multimodal RAG library that doesn't require vector databases or embedding models.

## 🚀 Phase 1 Features (Completed)

- ✅ **PyMuPDF Document Processing**: Fast PDF to image conversion
- ✅ **Multi-format Support**: PDF, JPG, PNG, WebP, and more
- ✅ **Flexible Storage**: Local file system and in-memory storage
- ✅ **Configuration System**: Comprehensive settings management
- ✅ **Async/Sync API**: Both async and synchronous interfaces
- ✅ **Flash/Pro Modes**: Different complexity levels for queries
- ✅ **Page Summarization**: Vision-based page summary generation
- ✅ **Document Management**: Add, list, search, and delete documents

## 🔮 Coming in Phase 2

- 🚧 Vision-based page selection
- 🚧 Complete RAG query pipeline
- 🚧 OpenAI GPT-4V integration
- 🚧 Anthropic Claude integration
- 🚧 Streaming responses

## 📦 Installation

```bash
# Basic installation
pip install Pillow PyMuPDF

# With OpenAI support
pip install Pillow PyMuPDF openai

# With Anthropic support  
pip install Pillow PyMuPDF anthropic

# Development installation
pip install -r requirements.txt
```

## 🏁 Quick Start

### Basic Usage

```python
import asyncio
from docpixie import create_docpixie

async def main():
    # Create DocPixie instance
    docpixie = create_docpixie(
        provider="openai",
        api_key="your-openai-api-key"
    )
    
    # Add a document
    document = await docpixie.add_document(
        "research_paper.pdf",
        summarize=True  # Generate page summaries
    )
    
    print(f"Processed {document.page_count} pages")
    
    # Query documents (Phase 2 feature - currently returns placeholder)
    result = await docpixie.query("What are the main findings?")
    print(f"Answer: {result.answer}")

asyncio.run(main())
```

### Synchronous API

```python
from docpixie import create_docpixie

# Create DocPixie instance  
docpixie = create_docpixie(api_key="your-api-key")

# Use sync methods
document = docpixie.add_document_sync("document.pdf")
result = docpixie.query_sync("What is this about?")
```

### Configuration

```python
from docpixie import DocPixie, DocPixieConfig

# Custom configuration
config = DocPixieConfig(
    provider="anthropic",  # Use Claude instead of GPT-4V
    flash_max_pages=3,     # Fewer pages for Flash mode
    pro_max_pages=20,      # More pages for Pro mode  
    pdf_render_scale=3.0,  # Higher quality PDF rendering
    jpeg_quality=95        # Higher image quality
)

docpixie = DocPixie(config=config, api_key="your-anthropic-key")
```

## 🏗️ Architecture

DocPixie uses a clean, extensible architecture:

```
DocPixie/
├── Core Components
│   ├── Document Processor (PyMuPDF)
│   ├── Storage Layer (Local/Memory)  
│   ├── Page Summarizer (Vision AI)
│   └── Configuration System
│
├── Processors
│   ├── PDFProcessor (PyMuPDF)
│   ├── ImageProcessor (Pillow)
│   └── ProcessorFactory
│
├── Storage Backends
│   ├── LocalStorage
│   ├── InMemoryStorage
│   └── BaseStorage (interface)
│
└── AI Integration
    ├── OpenAI GPT-4V
    ├── Anthropic Claude  
    └── BaseAIClient (interface)
```

## 🔧 Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
python -m pytest tests/

# Run specific test
python tests/test_basic.py
```

### Running Examples

```bash
# Basic usage example
python examples/basic_usage.py

# Make sure to set API key
export OPENAI_API_KEY="your-key"
python examples/basic_usage.py
```

## 📚 API Reference

### DocPixie Class

```python
class DocPixie:
    async def add_document(file_path, document_id=None, summarize=True) -> Document
    async def get_document(document_id: str) -> Optional[Document]  
    async def list_documents(limit=None) -> List[Dict]
    async def delete_document(document_id: str) -> bool
    async def query(question: str, mode=QueryMode.AUTO) -> QueryResult
    
    # Synchronous versions
    def add_document_sync(...) -> Document
    def query_sync(...) -> QueryResult
```

### Document Models

```python
@dataclass 
class Document:
    id: str
    name: str
    pages: List[Page]
    summary: Optional[str]
    status: DocumentStatus

@dataclass
class Page:
    page_number: int
    image_path: str
    content_summary: Optional[str]
    
@dataclass
class QueryResult:
    query: str
    answer: str
    selected_pages: List[Page]
    mode: QueryMode
    confidence: float
```

## 🎯 Flash vs Pro Modes

| Feature | Flash Mode | Pro Mode |
|---------|-----------|----------|
| Response Time | ~5-10 seconds | ~20-30 seconds |
| Pages Analyzed | Up to 5 | Up to 15 |
| Vision Detail | Low (thumbnails) | High (full resolution) |
| Analysis Depth | Single-pass | Multi-step synthesis |
| Use Case | Quick answers | Comprehensive analysis |

## 🔐 Environment Variables

```bash
# AI Provider API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# DocPixie Configuration (optional)
DOCPIXIE_PROVIDER=openai
DOCPIXIE_STORAGE_PATH=./my_docs
DOCPIXIE_FLASH_MAX_PAGES=5
DOCPIXIE_PRO_MAX_PAGES=15
```

## 📈 Performance

### Phase 1 Benchmarks

- **PDF Processing**: 3-5x faster than pdf2image (using PyMuPDF)
- **Memory Usage**: ~256KB per page (optimized images)
- **Storage**: Local filesystem or in-memory options
- **Concurrency**: Async/await throughout for better performance

### Supported File Types

- **PDF**: .pdf
- **Images**: .jpg, .jpeg, .png, .webp, .bmp, .tiff, .tif

## 🐛 Troubleshooting

### Common Issues

1. **PyMuPDF Installation**
   ```bash
   pip install --upgrade PyMuPDF
   ```

2. **API Key Issues**
   ```bash
   export OPENAI_API_KEY="your-key"
   # or
   export ANTHROPIC_API_KEY="your-key"  
   ```

3. **Memory Issues with Large PDFs**
   ```python
   config = DocPixieConfig(
       pdf_render_scale=1.5,  # Reduce from default 2.0
       jpeg_quality=85        # Reduce from default 90
   )
   ```

## 🗺️ Roadmap

### Phase 2 (Next 2 weeks)
- Vision-based page selection
- Complete RAG pipeline
- Query answering with GPT-4V/Claude
- Streaming responses

### Phase 3 (Following 2 weeks)  
- Multiple AI provider support
- Enhanced configuration
- Performance optimizations

### Phase 4+ (Future)
- Cloud storage backends (S3, Azure)
- Custom model support
- Advanced caching
- Web interface

## 🤝 Contributing

DocPixie is in active development. Phase 1 provides the foundation - document processing, storage, and configuration. Contributions welcome!

## 📄 License

Apache 2.0 License - see LICENSE file for details.

---

**Note**: This is Phase 1 of the DocPixie open source library. Query functionality returns placeholder responses until Phase 2 implementation is complete.