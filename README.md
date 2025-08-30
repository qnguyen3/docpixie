# DocPixie Core — Multimodal Adaptive RAG Agent and SDK

DocPixie Core is a lightweight, vision-first RAG SDK for analyzing document pages and answering questions with an adaptive, agentic workflow. It focuses on practical multimodal retrieval without requiring embeddings or vector databases.

Key capabilities:
- Vision-based page selection: analyzes actual page images, not just text.
- Adaptive task planning: creates and updates a focused plan while working.
- Conversation-aware: summarizes long history and reformulates queries.
- Pluggable providers: OpenAI, Anthropic, and OpenRouter supported.
- Simple storage: in-memory or local filesystem document storage.
- Async-first with convenient sync wrappers for easy adoption.

See docs in `./docs` for quickstart, architecture, and configuration details.

## Installation

- Python 3.10+
- Install dependencies:

```bash
pip install -r requirements.txt
```

- Set an API key for your preferred provider (pick one):
  - OpenAI: `export OPENAI_API_KEY=...`
  - Anthropic: `export ANTHROPIC_API_KEY=...`
  - OpenRouter: `export OPENROUTER_API_KEY=...`

Optionally choose a provider via config or environment (defaults to OpenAI). See Configuration docs for details.

## Quickstart

Minimal example using in-memory storage:

```python
import asyncio
from docpixie.docpixie import create_memory_docpixie

async def main():
    dp = create_memory_docpixie(provider="openai")  # uses OPENAI_API_KEY

    # Add a PDF (images also supported by processors)
    doc = await dp.add_document("/path/to/file.pdf", summarize=True)

    # Ask a question (adaptive, vision-first RAG)
    result = await dp.query("What are the Q3 revenues?")

    print(result.answer)
    print("Pages used:", [p.page_number for p in result.selected_pages])
    print("Confidence:", result.confidence)

asyncio.run(main())
```

Synchronous API is also available:

```python
from docpixie.docpixie import create_memory_docpixie

pixie = create_memory_docpixie(provider="openai")
doc = pixie.add_document_sync("/path/to/file.pdf", summarize=False)
res = pixie.query_sync("Summarize the main points")
print(res.answer)
```

More examples: `examples/basic_usage.py`.

## How It Works (Agent Pipeline)

`docpixie/ai/agent.py` orchestrates an adaptive multimodal pipeline:
1. Context processing: summarize conversation if long (`ContextProcessor`).
2. Query reformulation: resolve pronouns/refs when conversation exists (`QueryReformulator`).
3. Classification: decide if documents are required (`QueryClassifier`).
4. Task planning: create a 2–4 task initial plan with doc assignments (`TaskPlanner`).
5. Vision page selection: choose relevant pages via model over images (`VisionPageSelector`).
6. Task execution: analyze selected pages per task using a multimodal model.
7. Synthesis: combine all task findings into a coherent answer (`ResponseSynthesizer`).

The agent adapts after each task by potentially modifying the remaining plan. Provider calls are abstracted via `BaseProvider` with OpenAI, Anthropic, and OpenRouter implementations.

## Storage and Processing

- Processors render PDFs to page images with PyMuPDF (`docpixie/processors/pdf.py`).
- Storage backends implement `BaseStorage` (local filesystem or in-memory).
- Page and document summaries can be generated with the vision model (`PageSummarizer`).

## Configuration

Use `DocPixieConfig` to control provider, models, storage, and agent limits:

```python
from docpixie.core.config import DocPixieConfig
cfg = DocPixieConfig(provider="openai", storage_type="memory", max_agent_iterations=5)
```

Environment helpers (`DocPixieConfig.from_env`) are available. See `docs/configuration.md` for a focused guide.

## Testing

An end-to-end agent test using a dummy provider is available in `tests/test_agent_e2e.py`. Run your test runner of choice (e.g., `pytest`) after installing dev dependencies.

## What’s Included

- High-level API: `docpixie/docpixie.py` (add docs, query, list/search).
- Agent and components: `docpixie/ai/*` (planner, selector, synthesizer, prompts).
- Providers: `docpixie/providers/*` (OpenAI, Anthropic, OpenRouter).
- Storage and processors: `docpixie/storage/*`, `docpixie/processors/*`.

## Notes

- This core SDK focuses on a clean, dependency-light agentic RAG loop. No embeddings/vector DBs are required.
- Some advanced features from production DocPixie are simplified here for clarity and portability.

