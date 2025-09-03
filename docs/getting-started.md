# Getting Started with DocPixie

This guide will walk you through setting up DocPixie and provide detailed examples of how to use it effectively.

## 📋 Prerequisites

- Python 3.8 or higher
- An API key from one of the supported providers:
  - OpenAI API key (for GPT-4V)
  - Anthropic API key (for Claude with vision)
  - OpenRouter API key (for multiple model access)

## 🚀 Installation

### Method 1: Using pip

```bash
# Install dependencies
pip install -r requirements.txt

# For CLI support
pip install textual>=0.47.0 pyfiglet>=0.8.0
```

### Method 2: Using uv (Recommended)

```bash
# Install uv if you haven't already
pip install uv

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

## 🔑 API Key Setup

Set up your API key in your environment:

```bash
# For OpenAI (default)
export OPENAI_API_KEY="sk-your-openai-key-here"

# For Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-your-anthropic-key-here"

# For OpenRouter (gives access to many models)
export OPENROUTER_API_KEY="sk-or-your-openrouter-key-here"
```

Or create a `.env` file in your project root:

```env
OPENAI_API_KEY=sk-your-openai-key-here
# ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
# OPENROUTER_API_KEY=sk-or-your-openrouter-key-here
```

## 🏃‍♂️ Quick Start Examples

### Example 1: Basic Document Processing

```python
import asyncio
from docpixie import DocPixie

async def basic_example():
    # Initialize DocPixie with default settings
    docpixie = DocPixie()
    
    # Add a PDF document
    document = await docpixie.add_document("sample.pdf")
    
    print(f"✅ Added document: {document.name}")
    print(f"📄 Pages: {document.page_count}")
    print(f"📝 Summary: {document.summary}")
    
    # Ask a question
    result = await docpixie.query("What are the main topics covered?")
    
    print(f"\n❓ Query: {result.query}")
    print(f"💡 Answer: {result.answer}")
    print(f"📖 Pages used: {result.page_numbers}")
    print(f"💰 Cost: ${result.total_cost:.4f}")

# Run the example
asyncio.run(basic_example())
```

### Example 2: Multiple Documents with Conversation

```python
import asyncio
from docpixie import DocPixie, ConversationMessage

async def conversation_example():
    docpixie = DocPixie()
    
    # Add multiple documents
    doc1 = await docpixie.add_document("quarterly_report.pdf", document_name="Q3 Report")
    doc2 = await docpixie.add_document("budget_analysis.pdf", document_name="Budget Analysis")
    
    print(f"Added documents: {doc1.name}, {doc2.name}")
    
    # Start a conversation
    conversation = []
    
    # First query
    result1 = await docpixie.query(
        "What was the revenue in Q3?",
        conversation_history=conversation
    )
    
    # Add to conversation history
    conversation.append(ConversationMessage(role="user", content="What was the revenue in Q3?"))
    conversation.append(ConversationMessage(role="assistant", content=result1.answer))
    
    print(f"Q1: {result1.answer}")
    
    # Follow-up question with context
    result2 = await docpixie.query(
        "How does that compare to the budget?",
        conversation_history=conversation
    )
    
    print(f"Q2: {result2.answer}")

asyncio.run(conversation_example())
```

### Example 3: Custom Configuration

```python
import asyncio
from docpixie import DocPixie, DocPixieConfig

async def custom_config_example():
    # Create custom configuration
    config = DocPixieConfig(
        provider="anthropic",  # Use Claude instead of GPT-4V
        model="claude-3-opus-20240229",
        vision_model="claude-3-opus-20240229",
        max_pages_per_task=8,  # Analyze more pages per task
        jpeg_quality=95,       # Higher quality images
        storage_type="memory"  # Use in-memory storage
    )
    
    docpixie = DocPixie(config=config)
    
    # Process document with custom settings
    document = await docpixie.add_document("technical_manual.pdf")
    
    # Query with detailed analysis
    result = await docpixie.query(
        "Explain the technical specifications in detail",
        max_pages=10
    )
    
    print(f"Provider: {config.provider}")
    print(f"Model: {config.model}")
    print(f"Answer: {result.answer}")
    
    # Get system statistics
    stats = docpixie.get_stats()
    print(f"Statistics: {stats}")

asyncio.run(custom_config_example())
```

### Example 4: Document Management

```python
import asyncio
from docpixie import DocPixie

async def document_management_example():
    docpixie = DocPixie()
    
    # Add documents
    doc1 = await docpixie.add_document("report1.pdf")
    doc2 = await docpixie.add_document("report2.pdf")
    
    # List all documents
    documents = await docpixie.list_documents()
    print("📚 Available documents:")
    for doc in documents:
        print(f"  - {doc['name']} ({doc['page_count']} pages)")
    
    # Search documents by content
    search_results = await docpixie.search_documents("revenue analysis")
    print(f"\n🔍 Search results for 'revenue analysis':")
    for result in search_results:
        print(f"  - {result['name']}: {result['summary'][:100]}...")
    
    # Get specific document
    document = await docpixie.get_document(doc1.id)
    if document:
        print(f"\n📄 Document: {document.name}")
        print(f"   Created: {document.created_at}")
        print(f"   Status: {document.status}")
    
    # Delete a document
    deleted = await docpixie.delete_document(doc2.id)
    print(f"\n🗑️  Deleted {doc2.name}: {deleted}")

asyncio.run(document_management_example())
```

### Example 5: Synchronous API (Easier for Beginners)

```python
from docpixie import DocPixie

# Use the synchronous API - no async/await needed!
def sync_example():
    docpixie = DocPixie()
    
    # Add document (sync)
    document = docpixie.add_document_sync("sample.pdf")
    print(f"Added: {document.name}")
    
    # Query document (sync)
    result = docpixie.query_sync("What are the key points?")
    print(f"Answer: {result.answer}")
    
    # List documents (sync)
    docs = docpixie.list_documents_sync()
    print(f"Total documents: {len(docs)}")

# No asyncio.run() needed!
sync_example()
```

## 🛠️ Advanced Configuration

### Provider-Specific Settings

```python
from docpixie import DocPixie, DocPixieConfig

# OpenAI Configuration
openai_config = DocPixieConfig(
    provider="openai",
    model="gpt-4o",
    vision_model="gpt-4o",
    max_agent_iterations=5
)

# Anthropic Configuration  
anthropic_config = DocPixieConfig(
    provider="anthropic",
    model="claude-3-opus-20240229",
    vision_model="claude-3-opus-20240229",
    max_agent_iterations=3
)

# OpenRouter Configuration (access to many models)
openrouter_config = DocPixieConfig(
    provider="openrouter",
    model="openai/gpt-4o",
    vision_model="openai/gpt-4o",
    max_agent_iterations=4
)
```

### Storage Configuration

```python
# Local storage (default)
local_config = DocPixieConfig(
    storage_type="local",
    local_storage_path="./my_docpixie_data"
)

# In-memory storage (good for testing)
memory_config = DocPixieConfig(
    storage_type="memory"
)

# Custom storage backend
from docpixie.storage.base import BaseStorage

class MyCustomStorage(BaseStorage):
    # Implement your custom storage logic
    pass

docpixie = DocPixie(storage=MyCustomStorage())
```

### Image Processing Options

```python
config = DocPixieConfig(
    pdf_render_scale=2.5,          # Higher scale = better quality
    jpeg_quality=95,               # Image compression quality
    vision_detail="high",          # Use full resolution
    pdf_max_image_size=(1400, 1400)  # Maximum image dimensions
)
```

## 🎨 Working with Different File Types

### PDF Documents

```python
# Single PDF
doc = await docpixie.add_document("report.pdf")

# Multiple PDFs
pdfs = ["report1.pdf", "report2.pdf", "report3.pdf"]
documents = []
for pdf in pdfs:
    doc = await docpixie.add_document(pdf)
    documents.append(doc)
```

### Images

```python
# Single image
doc = await docpixie.add_document("chart.png")

# Multiple images as one document
from docpixie.models.document import Document, Page
from pathlib import Path

pages = []
for i, img_path in enumerate(["page1.jpg", "page2.jpg"], 1):
    page = Page(
        page_number=i,
        image_path=str(Path(img_path).absolute())
    )
    pages.append(page)

document = Document(
    id="multi-image-doc",
    name="Multi-Image Document", 
    pages=pages
)

# Save to storage
await docpixie.storage.save_document(document)
```

## 💡 Best Practices

### 1. Optimize for Your Use Case

```python
# For detailed analysis - use more pages and iterations
detailed_config = DocPixieConfig(
    max_pages_per_task=8,
    max_agent_iterations=6,
    jpeg_quality=95
)

# For quick summaries - use fewer pages
quick_config = DocPixieConfig(
    max_pages_per_task=4,
    max_agent_iterations=3,
    jpeg_quality=85
)
```

### 2. Manage Conversation Context

```python
async def smart_conversation():
    docpixie = DocPixie()
    conversation = []
    
    while True:
        user_input = input("Ask a question (or 'quit'): ")
        if user_input.lower() == 'quit':
            break
            
        result = await docpixie.query(user_input, conversation_history=conversation)
        print(f"Answer: {result.answer}")
        
        # Add to conversation
        conversation.append(ConversationMessage(role="user", content=user_input))
        conversation.append(ConversationMessage(role="assistant", content=result.answer))
        
        # Keep conversation manageable (DocPixie handles this automatically)
        if len(conversation) > 16:  # 8 turns
            conversation = conversation[-10:]  # Keep recent 5 turns
```

### 3. Handle Errors Gracefully

```python
import asyncio
from docpixie import DocPixie
from docpixie.exceptions import DocPixieError

async def robust_example():
    try:
        docpixie = DocPixie()
        
        # Try to add document
        document = await docpixie.add_document("document.pdf")
        
        # Try to query
        result = await docpixie.query("What is this document about?")
        print(result.answer)
        
    except FileNotFoundError:
        print("❌ Document file not found")
    except DocPixieError as e:
        print(f"❌ DocPixie error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
```

### 4. Check File Support

```python
docpixie = DocPixie()

# Check if file is supported
if docpixie.supports_file("document.pdf"):
    doc = await docpixie.add_document("document.pdf")
else:
    print("File type not supported")

# See all supported extensions
extensions = docpixie.get_supported_extensions()
print(f"Supported types: {list(extensions.keys())}")
```

## 🚨 Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```bash
   # Make sure environment variable is set
   echo $OPENAI_API_KEY
   
   # Or check in Python
   import os
   print(os.getenv('OPENAI_API_KEY'))
   ```

2. **File Not Found**
   ```python
   from pathlib import Path
   
   file_path = "document.pdf"
   if Path(file_path).exists():
       doc = await docpixie.add_document(file_path)
   else:
       print(f"File not found: {file_path}")
   ```

3. **Memory Issues with Large PDFs**
   ```python
   # Reduce image quality for large files
   config = DocPixieConfig(
       pdf_render_scale=1.5,  # Lower scale
       jpeg_quality=80,       # Lower quality
       pdf_max_image_size=(1000, 1000)
   )
   ```

4. **Rate Limiting**
   ```python
   import asyncio
   
   # Add delays between requests
   await docpixie.add_document("doc1.pdf")
   await asyncio.sleep(1)  # 1 second delay
   await docpixie.add_document("doc2.pdf")
   ```

## 🎯 Next Steps

- Try the [CLI Tool](cli-tool.md) for interactive document chat
- Explore the API reference in the source code
- Build custom storage backends for your needs
- Contribute to the project on GitHub

---

Happy document querying with DocPixie! 🎉