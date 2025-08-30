import unittest
import asyncio
import sys
import types
from pathlib import Path
from typing import List, Dict, Any

# Avoid importing docpixie/__init__.py (which pulls optional heavy deps) during tests
# by stubbing the top-level package and pointing its __path__ to the source dir.
_pkg_root = Path(__file__).resolve().parents[1] / "docpixie"

# Stub top-level package to avoid executing real __init__.py
_pkg = types.ModuleType("docpixie")
_pkg.__path__ = [str(_pkg_root)]  # type: ignore[attr-defined]
sys.modules.setdefault("docpixie", _pkg)

# Stub subpackages whose __init__ import optional deps
_storage_pkg = types.ModuleType("docpixie.storage")
_storage_pkg.__path__ = [str(_pkg_root / "storage")]  # type: ignore[attr-defined]
sys.modules.setdefault("docpixie.storage", _storage_pkg)

_providers_pkg = types.ModuleType("docpixie.providers")
_providers_pkg.__path__ = [str(_pkg_root / "providers")]  # type: ignore[attr-defined]
sys.modules.setdefault("docpixie.providers", _providers_pkg)

from docpixie.ai.agent import PixieRAGAgent
from docpixie.core.config import DocPixieConfig
from docpixie.models.agent import ConversationMessage
from docpixie.models.document import Document, Page, DocumentStatus
from docpixie.providers.base import BaseProvider


class DummyProvider(BaseProvider):
    """Simple stubbed provider for tests (no network calls)."""

    def __init__(self, config: DocPixieConfig, *, needs_documents: bool = False, tasks_count: int = 1):
        super().__init__(config)
        self.needs_documents = needs_documents
        self.tasks_count = max(1, tasks_count)

    async def process_text_messages(
        self,
        messages: List[dict],
        max_tokens: int = 300,
        temperature: float = 0.3,
    ) -> str:
        # Extract user content when present
        user_content = ""
        if len(messages) > 1:
            user_content = messages[1].get("content", "")

        # Query classification prompt (expects JSON with needs_documents)
        if isinstance(user_content, str) and '"needs_documents"' in user_content:
            return (
                '{"reasoning": "Simple routing decision", "needs_documents": %s}'
                % ("true" if self.needs_documents else "false")
            )

        # Query reformulation prompt (expects JSON with reformulated_query)
        if isinstance(user_content, str) and "reformulated_query" in user_content:
            return '{"reformulated_query": "reformulated query"}'

        # Initial task planning prompt (expects JSON with tasks)
        if isinstance(user_content, str) and "Create 2-4 focused tasks" in user_content:
            # Parse document ID from the format "doc_1: Document Name"
            assigned_doc = ""
            for line in user_content.splitlines():
                # Look for lines with doc_id format: doc_X: Name
                if line.startswith("doc_") and ":" in line and not line.strip().startswith("Summary"):
                    assigned_doc = line.split(":", 1)[0].strip()
                    if assigned_doc:
                        break
            tasks = []
            for i in range(self.tasks_count):
                tasks.append(
                    {
                        "name": f"Task {i+1}",
                        "description": "Find relevant details",
                        "document": assigned_doc,
                    }
                )
            return ("{" + f"\"tasks\": {tasks}" + "}").replace("'", '"')

        # Plan update prompt (we keep plan unchanged)
        if isinstance(user_content, str) and "OUTPUT FORMAT - Choose ONE" in user_content:
            return '{"action": "continue", "reason": "Plan is fine"}'

        # Synthesis prompt fallback (not used when patched, but safe default)
        if isinstance(user_content, str) and "SYNTHESIS GUIDELINES" in user_content:
            return "Synthesized answer"

        # Default stub
        return "OK"

    async def process_multimodal_messages(
        self,
        messages: List[dict],
        max_tokens: int = 300,
        temperature: float = 0.3,
    ) -> str:
        # Page selection prompt looks for JSON with selected_pages
        # The page selection user content is a list with text + many images
        if len(messages) > 1 and isinstance(messages[1].get("content", []), list):
            text_chunks = [c.get("text", "") for c in messages[1]["content"] if c.get("type") == "text"]
            combined_text = "\n".join(text_chunks)
            if "selected_pages" in combined_text:
                return '{"selected_pages": [1, 2], "reasoning": "First two pages look relevant"}'

        # Otherwise treat it as per-task analysis over page images
        return "Found relevant information on provided pages."


class TestPixieRAGAgentE2E(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Minimal config with test API key bypass
        self.config = DocPixieConfig(provider="openai", openai_api_key="test-key")

    async def test_direct_answer_no_documents_needed_with_conversation(self):
        provider = DummyProvider(self.config, needs_documents=False)
        storage = SimpleMemoryStorage(self.config)
        agent = PixieRAGAgent(provider, storage, self.config)

        history = [
            ConversationMessage(role="user", content="Hi"),
            ConversationMessage(role="assistant", content="Hello!"),
        ]

        result = await agent.process_query("How are you?", conversation_history=history)

        self.assertIn("doesn't require document analysis", result.answer)
        self.assertEqual(result.total_iterations, 0)
        self.assertEqual(len(result.task_results), 0)
        self.assertEqual(len(result.selected_pages), 0)

    async def test_no_documents_available_but_needed(self):
        provider = DummyProvider(self.config, needs_documents=True)
        storage = SimpleMemoryStorage(self.config)
        agent = PixieRAGAgent(provider, storage, self.config)

        result = await agent.process_query("What are Q3 revenues?")

        self.assertIn("don't have any documents", result.answer)
        self.assertEqual(len(result.task_results), 0)
        self.assertEqual(len(result.selected_pages), 0)

    async def test_end_to_end_single_task_flow(self):
        provider = DummyProvider(self.config, needs_documents=True, tasks_count=1)
        storage = SimpleMemoryStorage(self.config)
        agent = PixieRAGAgent(provider, storage, self.config)

        # Prepare one document with a few pages
        doc = Document(
            id="doc_1",
            name="Sample Report",
            pages=[
                Page(page_number=1, image_path="/tmp/page1.jpg"),
                Page(page_number=2, image_path="/tmp/page2.jpg"),
                Page(page_number=3, image_path="/tmp/page3.jpg"),
            ],
            summary="Contains revenue and expense information",
            status=DocumentStatus.COMPLETED,
        )
        await storage.save_document(doc)

        # Patch synthesizer to avoid reliance on internal attributes
        async def fake_synthesize_response(original_query: str, task_results):
            return "SYNTH ANSWER"

        agent.synthesizer.synthesize_response = fake_synthesize_response  # type: ignore

        result = await agent.process_query("Find revenue details")

        self.assertEqual(result.answer, "SYNTH ANSWER")
        self.assertEqual(result.total_iterations, 1)
        self.assertEqual(len(result.task_results), 1)
        self.assertEqual(len(result.selected_pages), 2)  # Should return 2 pages as configured


if __name__ == "__main__":
    unittest.main()


class SimpleMemoryStorage:
    """Minimal in-memory storage implementing BaseStorage API used by agent."""

    def __init__(self, config: DocPixieConfig):
        self.config = config
        self._docs: Dict[str, Document] = {}
        self._summaries: Dict[str, str] = {}

    async def save_document(self, document: Document) -> str:
        self._docs[document.id] = document
        if document.summary:
            self._summaries[document.id] = document.summary
        return document.id

    async def get_document(self, document_id: str):
        return self._docs.get(document_id)

    async def list_documents(self, limit=None):
        docs = []
        for doc in self._docs.values():
            docs.append({
                'id': doc.id,
                'name': doc.name,
                'summary': self._summaries.get(doc.id),
                'page_count': len(doc.pages),
                'created_at': doc.created_at.isoformat(),
                'status': doc.status.value,
            })
        return docs[:limit] if limit else docs

    async def delete_document(self, document_id: str) -> bool:
        existed = document_id in self._docs
        self._docs.pop(document_id, None)
        self._summaries.pop(document_id, None)
        return existed

    async def document_exists(self, document_id: str) -> bool:
        return document_id in self._docs

    async def get_document_summary(self, document_id: str):
        return self._summaries.get(document_id)

    async def update_document_summary(self, document_id: str, summary: str) -> bool:
        if document_id not in self._docs:
            return False
        self._summaries[document_id] = summary
        self._docs[document_id].summary = summary
        return True

    async def get_all_documents(self) -> List[Document]:
        return list(self._docs.values())

    async def get_all_pages(self) -> List[Page]:
        pages: List[Page] = []
        for d in self._docs.values():
            pages.extend(d.pages)
        return pages
