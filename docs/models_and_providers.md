# AI Models and Providers

DocPixie supports multiple AI providers and models for vision-based document understanding. This guide covers provider configuration, model selection, and optimization strategies.

## Supported Providers

DocPixie currently supports three major AI providers:

- **OpenAI** - GPT-4 Vision models
- **Anthropic** - Claude 3 family with vision capabilities  
- **OpenRouter** - Access to multiple models through a unified API

## Quick Configuration

### Basic Setup

```python
from docpixie import create_docpixie

# OpenAI (default)
pixie = create_docpixie(
    provider="openai",
    api_key="sk-..."  # or use OPENAI_API_KEY env var
)

# Anthropic
pixie = create_docpixie(
    provider="anthropic",
    api_key="sk-ant-..."  # or use ANTHROPIC_API_KEY env var
)

# OpenRouter (access to many models)
pixie = create_docpixie(
    provider="openrouter",
    api_key="sk-or-..."  # or use OPENROUTER_API_KEY env var
)
```

### Environment Variables

```bash
# Set API keys via environment
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENROUTER_API_KEY="sk-or-..."

# Optional: Set default provider
export DOCPIXIE_PROVIDER="anthropic"
```

## Provider Details

### OpenAI

OpenAI's GPT-4 Vision models offer excellent multimodal understanding with fast response times.

```python
from docpixie import DocPixie
from docpixie.core.config import DocPixieConfig

config = DocPixieConfig(
    provider="openai",
    model="gpt-4o",           # Latest and fastest
    vision_model="gpt-4o",    # Same model handles vision
    openai_api_key="sk-..."  # Optional if env var is set
)

pixie = DocPixie(config=config)
```

**Available Models:**
- `gpt-4o` - Latest, fastest, and most capable (recommended)
- `gpt-4o-mini` - Smaller, faster, more cost-effective
- `gpt-4-turbo` - Previous generation, still capable
- `gpt-4-vision-preview` - Legacy vision model

**Pros:**
- Fast response times
- Excellent vision capabilities
- Wide language support
- Good at OCR and chart understanding

**Cons:**
- API costs can add up for large documents
- Rate limits on vision requests

### Anthropic

Claude 3 models provide nuanced understanding and longer context windows.

```python
config = DocPixieConfig(
    provider="anthropic",
    model="claude-3-opus-20240229",      # Most capable
    vision_model="claude-3-opus-20240229",  # Same for vision
    anthropic_api_key="sk-ant-..."
)

pixie = DocPixie(config=config)
```

**Available Models:**
- `claude-3-opus-20240229` - Most capable, best for complex documents
- `claude-3-sonnet-20240229` - Balanced performance and cost
- `claude-3-haiku-20240307` - Fastest and most affordable

**Pros:**
- Excellent reasoning capabilities
- Longer context window (200K tokens)
- Strong at following complex instructions
- Good at maintaining conversation context

**Cons:**
- Slightly slower than GPT-4o
- Different system message format (handled automatically)

### OpenRouter

OpenRouter provides access to multiple models through a single API, including open-source options.

```python
config = DocPixieConfig(
    provider="openrouter",
    model="openai/gpt-4o",           # Use OpenAI models
    vision_model="openai/gpt-4o",
    openrouter_api_key="sk-or-..."
)

# Or use Anthropic models via OpenRouter
config = DocPixieConfig(
    provider="openrouter",
    model="anthropic/claude-3-opus",
    vision_model="anthropic/claude-3-opus",
    openrouter_api_key="sk-or-..."
)

pixie = DocPixie(config=config)
```

**Available Models (Vision-capable):**
- `openai/gpt-4o` - Latest OpenAI model
- `openai/gpt-4-vision-preview` - GPT-4 with vision
- `anthropic/claude-3-opus` - Claude 3 Opus
- `anthropic/claude-3-sonnet` - Claude 3 Sonnet
- `google/gemini-pro-vision` - Google's multimodal model
- `fireworks/firellava-13b` - Open-source vision model

**Pros:**
- Access to multiple providers with one API key
- Can compare models easily
- Often has better availability
- Supports open-source models

**Cons:**
- Slight latency overhead
- Pricing may differ from direct provider access

## Model Configuration

### Default Model Selection

DocPixie automatically selects appropriate default models based on your provider:

```python
# Automatic defaults when you specify a provider
config = DocPixieConfig(provider="openai")
# Automatically uses: model="gpt-4o", vision_model="gpt-4o"

config = DocPixieConfig(provider="anthropic")  
# Automatically uses: model="claude-3-opus-20240229", vision_model="claude-3-opus-20240229"

config = DocPixieConfig(provider="openrouter")
# Automatically uses: model="openai/gpt-4o", vision_model="openai/gpt-4o"
```

### Custom Model Selection

Override defaults with specific models:

```python
from docpixie.core.config import DocPixieConfig

# Use a specific model combination
config = DocPixieConfig(
    provider="openai",
    model="gpt-4o-mini",        # Use mini for text processing
    vision_model="gpt-4o",      # Use full model for vision
)

# Configure for cost optimization
config = DocPixieConfig(
    provider="anthropic",
    model="claude-3-haiku-20240307",    # Fast and cheap
    vision_model="claude-3-sonnet-20240229",  # Better vision
)
```

### Advanced Configuration

```python
config = DocPixieConfig(
    # Provider settings
    provider="openai",
    model="gpt-4o",
    vision_model="gpt-4o",
    
    # Processing settings
    vision_detail="high",  # "high" or "auto" - affects token usage
    
    # Agent settings (affects AI behavior)
    max_agent_iterations=5,     # How many planning iterations
    max_pages_per_task=6,       # Pages analyzed per task
    max_tasks_per_plan=4,       # Tasks in initial plan
    
    # Conversation settings
    max_conversation_turns=8,   # When to summarize conversation
    turns_to_summarize=5,       # How many turns to compress
    turns_to_keep_full=3,       # Recent turns to keep verbatim
)
```

## Model Selection Guide

### By Use Case

| Use Case | Recommended Provider | Model | Why |
|----------|---------------------|-------|-----|
| **General Documents** | OpenAI | `gpt-4o` | Fast, reliable, good OCR |
| **Complex Analysis** | Anthropic | `claude-3-opus` | Best reasoning, long context |
| **High Volume** | OpenAI | `gpt-4o-mini` | Cost-effective, still capable |
| **Research Papers** | Anthropic | `claude-3-opus` | Handles complexity well |
| **Presentations** | OpenAI | `gpt-4o` | Good with visual elements |
| **Budget Conscious** | OpenRouter | `fireworks/firellava-13b` | Open-source, free tier |

### By Document Type

| Document Type | Best Model | Vision Detail | Notes |
|--------------|------------|---------------|-------|
| **Text-heavy PDFs** | `gpt-4o-mini` | `auto` | Lower cost, text focus |
| **Charts/Graphs** | `gpt-4o` | `high` | Better visual analysis |
| **Scanned Documents** | `claude-3-opus` | `high` | Strong OCR capabilities |
| **Mixed Media** | `gpt-4o` | `high` | Balanced performance |
| **Handwritten** | `claude-3-opus` | `high` | Better at unclear text |

## Performance Optimization

### Token Usage Optimization

```python
# Optimize for cost
config = DocPixieConfig(
    provider="openai",
    model="gpt-4o-mini",
    vision_detail="auto",  # Reduces token usage
    max_pages_per_task=4,  # Analyze fewer pages at once
    jpeg_quality=85,       # Smaller images = fewer tokens
)

# Optimize for quality
config = DocPixieConfig(
    provider="anthropic",
    model="claude-3-opus-20240229",
    vision_detail="high",   # Maximum detail
    max_pages_per_task=8,   # More comprehensive analysis
    jpeg_quality=95,        # Higher quality images
)
```

### Request Optimization

```python
# Batch processing for efficiency
async def process_many_documents(file_paths):
    pixie = create_docpixie(provider="openai")
    
    # Process documents in parallel
    tasks = [pixie.add_document(path) for path in file_paths]
    documents = await asyncio.gather(*tasks)
    
    return documents

# Rate limit handling
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(3)
)
async def query_with_retry(pixie, question):
    return await pixie.query(question)
```

## Cost Management

### Estimating Costs

```python
def estimate_document_cost(page_count: int, provider: str, model: str) -> float:
    """Rough cost estimation for document processing"""
    
    # Approximate tokens per page (varies by content)
    tokens_per_page = 800  # Conservative estimate
    
    # Cost per 1K tokens (prices as of 2024)
    pricing = {
        ("openai", "gpt-4o"): {"input": 0.005, "output": 0.015},
        ("openai", "gpt-4o-mini"): {"input": 0.00015, "output": 0.0006},
        ("anthropic", "claude-3-opus"): {"input": 0.015, "output": 0.075},
        ("anthropic", "claude-3-sonnet"): {"input": 0.003, "output": 0.015},
        ("anthropic", "claude-3-haiku"): {"input": 0.00025, "output": 0.00125},
    }
    
    if (provider, model) in pricing:
        price = pricing[(provider, model)]
        # Rough calculation (actual will vary)
        input_cost = (page_count * tokens_per_page / 1000) * price["input"]
        output_cost = (500 / 1000) * price["output"]  # Assume 500 output tokens
        return input_cost + output_cost
    
    return 0.0

# Example usage
pages = 10
cost = estimate_document_cost(pages, "openai", "gpt-4o")
print(f"Estimated cost for {pages} pages: ${cost:.4f}")
```

### Cost-Saving Strategies

1. **Use appropriate models for the task:**
```python
# Simple text extraction
config_simple = DocPixieConfig(
    provider="openai",
    model="gpt-4o-mini",
    max_pages_per_task=3
)

# Complex analysis
config_complex = DocPixieConfig(
    provider="anthropic",
    model="claude-3-opus-20240229",
    max_pages_per_task=6
)
```

2. **Optimize image quality:**
```python
# Lower quality for text-only documents
config = DocPixieConfig(
    jpeg_quality=75,
    pdf_render_scale=1.5,
    vision_detail="auto"
)
```

3. **Implement caching:**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
async def cached_query(pixie, question, doc_id):
    """Cache repeated queries"""
    return await pixie.query(question)
```

## Switching Providers

DocPixie makes it easy to switch between providers:

```python
# Start with OpenAI
pixie_openai = create_docpixie(provider="openai")
doc = pixie_openai.add_document_sync("report.pdf")

# Switch to Anthropic for complex analysis
pixie_anthropic = create_docpixie(provider="anthropic")
result = pixie_anthropic.query_sync(
    "Provide a detailed analysis of the methodology section"
)

# Compare results from different providers
providers = ["openai", "anthropic", "openrouter"]
results = {}

for provider in providers:
    pixie = create_docpixie(provider=provider)
    results[provider] = pixie.query_sync("What are the key findings?")
    
# Compare responses
for provider, result in results.items():
    print(f"{provider}: {result.answer[:100]}...")
```

## Custom Provider Implementation

You can add support for new providers by implementing the BaseProvider interface:

```python
from docpixie.providers.base import BaseProvider
from typing import List, Dict, Any

class CustomProvider(BaseProvider):
    """Template for custom AI provider"""
    
    def __init__(self, config):
        super().__init__(config)
        # Initialize your client
        self.client = YourAPIClient(api_key=config.your_api_key)
    
    async def process_text_messages(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 500,
        temperature: float = 0.3
    ) -> str:
        """Process text-only messages"""
        response = await self.client.complete(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.text
    
    async def process_multimodal_messages(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 500,
        temperature: float = 0.3
    ) -> str:
        """Process messages with images"""
        # Convert image_path to your provider's format
        formatted_messages = self._format_messages(messages)
        
        response = await self.client.complete_multimodal(
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.text
```

## Troubleshooting

### Common Issues

**"API key not found"**
```python
# Check environment variable
import os
print(f"OpenAI key set: {'OPENAI_API_KEY' in os.environ}")

# Or set directly
pixie = create_docpixie(
    provider="openai",
    api_key="sk-..."
)
```

**"Model not found"**
```python
# Verify model name for your provider
# OpenAI models don't need prefix
config = DocPixieConfig(provider="openai", model="gpt-4o")

# OpenRouter models need provider prefix
config = DocPixieConfig(provider="openrouter", model="openai/gpt-4o")
```

**"Rate limit exceeded"**
```python
import time

# Simple retry with backoff
for attempt in range(3):
    try:
        result = pixie.query_sync("Your question")
        break
    except Exception as e:
        if "rate_limit" in str(e).lower():
            time.sleep(2 ** attempt)  # Exponential backoff
        else:
            raise
```

**"Context length exceeded"**
```python
# Reduce pages per task
config = DocPixieConfig(
    max_pages_per_task=3,  # Fewer pages at once
    max_agent_iterations=7  # More iterations with smaller chunks
)
```

## Best Practices

1. **Start with defaults**: DocPixie's defaults are optimized for most use cases
2. **Test different providers**: Each has strengths for different document types
3. **Monitor costs**: Use estimation functions to track spending
4. **Implement caching**: Cache results for repeated queries
5. **Handle errors gracefully**: Implement retry logic for transient failures
6. **Optimize images**: Balance quality vs. cost based on document type

## Model Comparison Table

| Feature | GPT-4o | Claude 3 Opus | GPT-4o-mini | Claude 3 Haiku |
|---------|--------|---------------|-------------|----------------|
| **Speed** | Fast | Moderate | Very Fast | Fast |
| **Cost** | $$ | $$$ | $ | $ |
| **Context Window** | 128K | 200K | 128K | 200K |
| **Vision Quality** | Excellent | Excellent | Good | Good |
| **OCR Accuracy** | Very Good | Excellent | Good | Good |
| **Reasoning** | Very Good | Excellent | Good | Good |
| **Best For** | General use | Complex docs | High volume | Budget apps |

## Next Steps

- See [Getting Started](getting-started.md) to begin using DocPixie
- Review [Document Processing](document-processing.md) for input handling
- Check [Storage Options](storage.md) for backend configuration