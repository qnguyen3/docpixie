# Configuration

DocPixie is configured via `DocPixieConfig` (`docpixie/core/config.py`) or environment variables. This guide covers the most useful settings.

## Providers and API Keys

Pick one provider and set its API key:

- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- OpenRouter: `OPENROUTER_API_KEY`

Select provider in code or via env:

```python
from docpixie.core.config import DocPixieConfig
cfg = DocPixieConfig(provider="openai")
```

`DocPixieConfig` sets sensible default models per provider (e.g., `gpt-4o`, `claude-3` variants). You can override model names by setting `flash_model`, `pro_model`, and `vision_model` in the config.

## Storage

- `storage_type`: `"local"` (default) or `"memory"`
- `local_storage_path`: path for persisted files, default `./docpixie_data`

```python
DocPixieConfig(storage_type="local", local_storage_path="./data")
```

## Agent Settings

- `max_agent_iterations`: cap adaptive replanning iterations (default 5)
- `max_pages_per_task`: soft limit for per-task page analysis (default 6)
- `max_tasks_per_plan`: cap initial tasks (default 4)
- `enable_conversation`: enable conversation-aware processing (default True)

## Conversation Settings

Long histories are summarized to keep prompts efficient:

- `max_conversation_turns`: when to start summarizing (default 8 user turns)
- `turns_to_summarize`: earlier turns summarized (default 5)
- `turns_to_keep_full`: most recent turns kept verbatim (default 3)

## Rendering and Summaries

- PDF rendering: `pdf_render_scale`, `pdf_max_image_size`, `jpeg_quality`
- Summaries: `page_summary_enabled`, `document_summary_enabled`
- Summarizer batch size: `batch_size`

## Request and Caching


## Environment-Based Config

Create from env:

```python
cfg = DocPixieConfig.from_env()
```

Recognized env vars include:

- `DOCPIXIE_PROVIDER` → `provider`
- `DOCPIXIE_STORAGE_PATH` → `local_storage_path`
- `DOCPIXIE_FLASH_MAX_PAGES` → `flash_max_pages`
- `DOCPIXIE_PRO_MAX_PAGES` → `pro_max_pages`
- `DOCPIXIE_JPEG_QUALITY` → `jpeg_quality`
- `DOCPIXIE_ENABLE_CACHE` → `enable_cache`
- `DOCPIXIE_LOG_LEVEL` → `log_level`

Provider-specific API keys use the variables listed in Providers and API Keys above.

## Introspection

Useful helpers for debugging and telemetry:

```python
pixie.get_stats()           # overall system stats
pixie.agent.get_agent_stats()  # agent-specific limits and provider
```
