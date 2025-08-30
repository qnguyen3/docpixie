# Getting Started with DocPixie

Welcome to DocPixie! This guide will help you set up and start using DocPixie for multimodal document understanding.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip or uv package manager

### Install Required Packages

```bash
pip install pymupdf pillow openai anthropic
```

Or if you're using uv (recommended for faster installs):

```bash
uv pip install pymupdf pillow openai anthropic
```

### Set Up API Keys

DocPixie requires an API key from at least one provider:

```bash
# For OpenAI (GPT-4 Vision)
export OPENAI_API_KEY="sk-..."

# For Anthropic (Claude 3)
export ANTHROPIC_API_KEY="sk-ant-..."

# For OpenRouter (access to multiple models)
export OPENROUTER_API_KEY="sk-or-..."
```

## Your First DocPixie Application

### Step 1: Initialize DocPixie

```python
from docpixie import create_docpixie

# Create a DocPixie instance with OpenAI
pixie = create_docpixie(provider="openai")

# Or with Anthropic
pixie = create_docpixie(provider="anthropic")

# Or with explicit API key
pixie = create_docpixie(
    provider="openai",
    api_key="your-api-key-here"
)
```

### Step 2: Add Documents

```python
# Add a single document
document = pixie.add_document_sync("report.pdf")
print(f"Added: {document.name}")
print(f"Pages: {document.page_count}")
print(f"Summary: {document.summary[:200]}...")

# Add multiple documents
docs = [
    "presentation.pdf",
    "research_paper.pdf",
    "financial_report.pdf"
]

for doc_path in docs:
    doc = pixie.add_document_sync(doc_path)
    print(f"✓ Added {doc.name}")
```

### Step 3: Query Your Documents

```python
# Simple question
result = pixie.query_sync("What are the key findings?")
print(result.answer)

# See which pages were used
print(f"Information from pages: {result.page_numbers}")

# Check confidence score
print(f"Confidence: {result.confidence:.2%}")
```

## Working with Conversations

DocPixie maintains context across conversations:

```python
from docpixie.models.agent import ConversationMessage

# Build conversation history
conversation = [
    ConversationMessage(
        role="user", 
        content="What is the main topic of the document?"
    ),
    ConversationMessage(
        role="assistant",
        content="The main topic is renewable energy adoption..."
    ),
    ConversationMessage(
        role="user",
        content="What specific technologies are mentioned?"
    ),
    ConversationMessage(
        role="assistant",
        content="The document mentions solar panels, wind turbines..."
    )
]

# Ask a follow-up question with context
result = pixie.query_sync(
    "How do these compare in terms of efficiency?",
    conversation_history=conversation
)

print(result.answer)
```

## Async Operations

For better performance with multiple operations:

```python
import asyncio
from docpixie import create_docpixie

async def process_documents():
    pixie = create_docpixie(provider="openai")
    
    # Add documents concurrently
    docs = await asyncio.gather(
        pixie.add_document("doc1.pdf"),
        pixie.add_document("doc2.pdf"),
        pixie.add_document("doc3.pdf")
    )
    
    print(f"Added {len(docs)} documents")
    
    # Query the documents
    result = await pixie.query(
        "Compare the main points across all documents"
    )
    
    return result

# Run async function
result = asyncio.run(process_documents())
print(result.answer)
```

## Managing Documents

### List Documents

```python
# Get all documents
documents = pixie.list_documents_sync()

for doc in documents:
    print(f"- {doc['name']} ({doc['page_count']} pages)")
    print(f"  ID: {doc['id']}")
    print(f"  Summary: {doc['summary'][:100]}...")
```

### Search Documents

```python
# Search by name or summary content
results = pixie.search_documents_sync("financial", limit=5)

for doc in results:
    print(f"Found: {doc['name']}")
```

### Delete Documents

```python
# Delete by document ID
success = pixie.delete_document_sync(document_id)
if success:
    print("Document deleted")
```

## Configuration Options

### Custom Storage Path

```python
from docpixie import create_docpixie

pixie = create_docpixie(
    provider="openai",
    storage_path="/path/to/my/documents"
)
```

### In-Memory Storage (for Testing)

```python
from docpixie import create_memory_docpixie

# No files saved to disk
pixie = create_memory_docpixie(provider="openai")
```

### Advanced Configuration

```python
from docpixie import DocPixie
from docpixie.core.config import DocPixieConfig

config = DocPixieConfig(
    # Provider settings
    provider="anthropic",
    model="claude-3-opus-20240229",
    
    # Storage settings
    storage_type="local",
    local_storage_path="./data",
    
    # Processing settings
    jpeg_quality=95,              # Higher quality images
    pdf_render_scale=2.5,         # Higher resolution
    
    # Agent settings
    max_pages_per_task=10,        # More pages per analysis
    max_agent_iterations=7,       # More planning iterations
    
    # Conversation settings
    max_conversation_turns=10     # When to summarize history
)

pixie = DocPixie(config=config)
```

## Error Handling

```python
from docpixie.exceptions import ProcessingError, StorageError

try:
    doc = pixie.add_document_sync("document.pdf")
except ProcessingError as e:
    print(f"Failed to process document: {e}")
except StorageError as e:
    print(f"Storage error: {e}")

# Query with error handling
try:
    result = pixie.query_sync("What is the conclusion?")
    if result.confidence < 0.5:
        print("Warning: Low confidence answer")
    print(result.answer)
except Exception as e:
    print(f"Query failed: {e}")
```

## Best Practices

### 1. Document Preparation
- Ensure PDFs are not password-protected
- Scanned documents work but native PDFs perform better
- Large documents (100+ pages) may take longer to process

### 2. Query Formulation
- Be specific in your questions
- Reference document sections when relevant
- Use conversation history for complex analyses

### 3. Performance Tips
- Use async operations for multiple documents
- Configure appropriate page limits for your use case
- Consider in-memory storage for temporary workflows

### 4. Cost Management
- Each document processing uses vision API calls
- Queries only analyze relevant pages
- Monitor usage through provider dashboards

## Next Steps

- Explore [Document Processing](document-processing.md) to understand how different file types are handled
- Learn about [Storage Options](storage.md) for production deployments
- Review [Data Models](models.md) for advanced integrations

## Troubleshooting

### Common Issues

**"No API key found"**
- Ensure environment variable is set: `echo $OPENAI_API_KEY`
- Or pass directly: `create_docpixie(api_key="...")`

**"PDF processing failed"**
- Check if PDF is corrupted: `file document.pdf`
- Ensure PyMuPDF is installed: `pip show pymupdf`

**"Low confidence answers"**
- Document may not contain relevant information
- Try more specific questions
- Check if correct pages are being selected

### Getting Help

- GitHub Issues: Report bugs or request features
- Documentation: Check our full documentation
- Community: Join our Discord for discussions