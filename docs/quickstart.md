# Quickstart

This guide gets you from zero to running queries over your documents with DocPixie’s adaptive, vision-first RAG agent.

## Prerequisites

- Python 3.10+
- One provider API key (pick one):
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `OPENROUTER_API_KEY`

## Install

```bash
pip install -r requirements.txt
```

## Minimal Usage (Async)

```python
import asyncio
from docpixie.docpixie import create_memory_docpixie

async def main():
    # Uses OPENAI_API_KEY / ANTHROPIC_API_KEY / OPENROUTER_API_KEY
    dp = create_memory_docpixie(provider="openai")

    # Add a PDF document (images also supported by processors)
    doc = await dp.add_document("/path/to/report.pdf", summarize=True)
    print("Document:", doc.name, "pages:", doc.page_count)

    # Ask a question
    result = await dp.query("What are the Q3 revenues?")
    print(result.answer)
    print("Pages analyzed:", [p.page_number for p in result.selected_pages])
    print("Confidence:", result.confidence)

asyncio.run(main())
```

## Minimal Usage (Sync)

```python
from docpixie.docpixie import create_memory_docpixie

pixie = create_memory_docpixie(provider="openai")
doc = pixie.add_document_sync("/path/to/report.pdf", summarize=False)
res = pixie.query_sync("Summarize the main points")
print(res.answer)
```

## Storing Documents Locally

The default `DocPixieConfig` uses local filesystem storage at `./docpixie_data`. To switch to memory storage (ephemeral), use `create_memory_docpixie()` or set `DocPixieConfig(storage_type="memory")`.

## Supported Formats

- PDF via PyMuPDF rendering to page images.
- Image files (via image processor; see processors).

Check programmatically:

```python
pixie.get_supported_extensions()  # dict of extension -> processor
```

## Conversation Context

Provide history for better reformulation and context:

```python
from docpixie.models.agent import ConversationMessage

history = [
    ConversationMessage(role="user", content="We discussed Q3 results."),
    ConversationMessage(role="assistant", content="Yes, revenue grew 12%."),
]

res = await pixie.query("How did expenses change?", conversation_history=history)
```

## Next Steps

- Read `docs/agent.md` to understand the adaptive pipeline.
- Read `docs/configuration.md` to customize providers, storage, and limits.

