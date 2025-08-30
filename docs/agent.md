# Agent and Architecture

This document explains how the adaptive multimodal RAG agent works and how the major components interact.

## High-Level Flow

`PixieRAGAgent` (`docpixie/ai/agent.py`) orchestrates an end-to-end loop:

1. Context processing (optional):
   - `ContextProcessor` summarizes older conversation turns and builds a compact context string if the history is long.
2. Query reformulation (optional):
   - `QueryReformulator` resolves pronouns and references to produce a concise, searchable query when conversation context exists.
3. Query classification:
   - `QueryClassifier` decides if the query requires document analysis. If not, the agent returns a direct answer.
4. Initial task plan:
   - `TaskPlanner.create_initial_plan` produces 2–4 focused tasks, each with a single assigned document (by ID).
5. Per-task page selection (vision-first):
   - `VisionPageSelector` shows actual page images to the provider and receives the most relevant page indices as JSON.
6. Per-task analysis (multimodal):
   - The agent builds a multimodal message that includes the task prompt and the selected page images; the provider returns the analysis text.
7. Adaptive plan update:
   - `TaskPlanner.update_plan` may add/modify/remove tasks based on findings, until iteration or plan limits are reached.
8. Response synthesis:
   - `ResponseSynthesizer` combines all task analyses into a coherent final answer.

The agent returns a `QueryResult` that includes the final answer, pages used, per-task results, and timing/iteration metadata.

## Core Components

- `ContextProcessor` (`ai/context_processor.py`): Summarizes long histories and prepares display/context messages.
- `QueryReformulator` (`ai/query_reformulator.py`): Produces concise, resolved queries (JSON output expected from model).
- `QueryClassifier` (`ai/query_classifier.py`): Routes between direct answer vs. document analysis (JSON output expected).
- `TaskPlanner` (`ai/task_planner.py`): Creates and updates a `TaskPlan` with `AgentTask`s.
- `VisionPageSelector` (`ai/page_selector.py`): Vision-based selection over page images, returns indices as JSON.
- `ResponseSynthesizer` (`ai/synthesizer.py`): Merges task analyses into the final answer.
- `prompts.py`: Centralized system and user prompts for the above modules.
- `providers/*`: Implement the `BaseProvider` interface for text and multimodal calls.

## Data Models

Defined in `docpixie/models`:
- `ConversationMessage`: role (`"user"` or `"assistant"`), content, timestamp.
- `AgentTask`: name, description, status, and single assigned document ID.
- `TaskPlan`: a list of tasks, current iteration; helpers to fetch pending/completed tasks.
- `TaskResult`: task, selected pages, analysis; computed `pages_analyzed`.
- `QueryResult` (agent): original query, final answer, selected pages, task results, total iterations, processing time.
- `Document`/`Page`: page images and optional page summaries.

Note: The public `docpixie.docpixie.DocPixie.query` wraps the agent’s result into the user-facing `models.document.QueryResult` type and adds fields like `mode`, `confidence`, and `metadata`.

## Provider Abstraction

All LLM/Vision interactions go through `BaseProvider`:
- `process_text_messages(messages, max_tokens, temperature) -> str`
- `process_multimodal_messages(messages, max_tokens, temperature) -> str`

Implementations:
- `OpenAIProvider` (uses OpenAI Chat Completions with data URLs for images)
- `AnthropicProvider` (uses Claude Messages API with base64 images)
- `OpenRouterProvider` (OpenRouter endpoint, OpenAI-compatible client)

## Configuration Highlights

`DocPixieConfig` controls:
- Provider and model names; API keys; request timeouts.
- Storage backend and path (local vs. in-memory).
- Agent limits: `max_agent_iterations`, `max_pages_per_task`, `max_tasks_per_plan`.
- Conversation thresholds: when to summarize vs. keep turns verbatim.

Create from code or environment (`DocPixieConfig.from_env`). See `docs/configuration.md`.

## Using the Agent Directly

Advanced users can instantiate the agent with a custom provider and storage:

```python
from docpixie.ai.agent import PixieRAGAgent
from docpixie.core.config import DocPixieConfig
from docpixie.providers.factory import create_provider
from docpixie.storage.memory import InMemoryStorage

cfg = DocPixieConfig(provider="openai")
provider = create_provider(cfg)
storage = InMemoryStorage(cfg)
agent = PixieRAGAgent(provider, storage, cfg)

result = await agent.process_query("Find revenue details")
print(result.answer)
```

For most scenarios, prefer the higher-level `DocPixie` API which wraps the agent and provides document processing, storage, and sync helpers.

