"""
DocPixie integration manager for CLI application
"""

import asyncio
from typing import TYPE_CHECKING, Optional, Any, Callable
from pathlib import Path

from docpixie import DocPixie, ConversationMessage
from docpixie.core.config import DocPixieConfig
from docpixie.models.document import Document

from .config import get_config_manager
from .state_manager import AppStateManager
from .widgets import ChatArea, DocumentManagerDialog

if TYPE_CHECKING:
    from .app import DocPixieTUI


class DocPixieManager:
    """Manages DocPixie instance and all related operations"""

    def __init__(self, app: 'DocPixieTUI', state_manager: AppStateManager):
        self.app = app
        self.state_manager = state_manager
        self.config_manager = get_config_manager()
        self.docpixie: Optional[DocPixie] = None

    async def create_docpixie_instance(self) -> bool:
        try:
            api_key = self.config_manager.get_api_key()
            if not api_key:
                return False

            text_model, vision_model = self.config_manager.get_models()

            config = DocPixieConfig(
                provider="openrouter",
                model=text_model,
                vision_model=vision_model,
                storage_type="local",
                local_storage_path="./.docpixie/documents",
                openrouter_api_key=api_key,
                jpeg_quality=85,
                max_pages_per_task=4
            )

            self.docpixie = DocPixie(config=config)
            self.app.docpixie = self.docpixie
            return True

        except Exception as e:
            try:
                chat_log = self.app.query_one("#chat-log", ChatArea)
                chat_log.write(f"[error]❌ Failed to create DocPixie instance: {e}[/error]")
            except:
                pass
            return False

    async def initialize_docpixie(self, show_welcome: bool = True) -> None:
        chat_log = self.app.query_one("#chat-log", ChatArea)

        if not await self.create_docpixie_instance():
            chat_log.write("[error]❌ No API key configured. Please restart and configure.[/error]")
            return

        try:
            await self.check_and_prompt_for_documents()
            await self.load_or_create_conversation()

            if show_welcome:
                self.app.show_welcome_message()

            if self.state_manager.current_conversation_id and self.state_manager.conversation_history:
                chat_log.add_static_text("[dim]━━━ Restored previous conversation ━━━[/dim]\n\n")

                for msg in self.state_manager.conversation_history:
                    if msg.role == "user":
                        chat_log.add_user_message(msg.content)
                    else:
                        chat_log.add_assistant_message(msg.content)

                chat_log.add_static_text("[dim]━━━ Continue your conversation below ━━━[/dim]\n\n")

        except Exception as e:
            chat_log.write(f"[error]❌ Failed to initialize: {e}[/error]")

    async def switch_models(self) -> None:
        await self.create_docpixie_instance()

    async def check_and_prompt_for_documents(self) -> None:
        chat_log = self.app.query_one("#chat-log", ChatArea)

        if not self.state_manager.documents_folder.exists():
            self.state_manager.documents_folder.mkdir(parents=True)
            chat_log.write(f"[green bold]●[/green bold] Created documents folder: {self.state_manager.documents_folder.absolute()}\n")
            chat_log.write("[blue bold]●[/blue bold] Add PDF files to the documents folder and use /documents to manage them.\n")
            return

        self.state_manager.clear_documents()

        try:
            existing_docs = await self.docpixie.list_documents()
            indexed_names = {doc['name'] for doc in existing_docs}

            for doc_meta in existing_docs:
                doc = await self.docpixie.get_document(doc_meta['id'])
                if doc:
                    self.state_manager.add_document(doc)

        except Exception as e:
            indexed_names = set()
            chat_log.write(f"[dim]Note: Could not load existing documents: {e}[/dim]\\n")

        pdf_files = list(self.state_manager.documents_folder.glob("*.pdf"))

        if not pdf_files:
            return

        new_pdf_files = [
            pdf for pdf in pdf_files
            if pdf.stem not in indexed_names
        ]

        if new_pdf_files:
            chat_log.write(f"[blue bold]●[/blue bold] Found {len(new_pdf_files)} new PDF file(s)\n")
            await self.app.push_screen(DocumentManagerDialog(
                self.state_manager.documents_folder,
                self.docpixie
            ))

    async def load_or_create_conversation(self) -> None:
        try:
            doc_ids = [doc.id for doc in self.state_manager.indexed_documents]
            last_conversation_id = self.state_manager.get_last_conversation_id()

            if last_conversation_id:
                if self.state_manager.load_conversation(last_conversation_id):
                    status_label = self.app.query_one("#status-label")
                    status_label.update(self.state_manager.get_status_text())
                    return

            self.state_manager.create_new_conversation()
            status_label = self.app.query_one("#status-label")
            status_label.update(self.state_manager.get_status_text())

        except Exception as e:
            print(f"Error loading conversation: {e}")
            self.state_manager.set_current_conversation(None)

    async def process_query(self, query: str, task_callback: Optional[Callable] = None) -> None:
        chat_log = self.app.query_one("#chat-log", ChatArea)

        if not self.docpixie:
            chat_log.write("[error]❌ DocPixie not initialized[/error]\\n")
            return

        if not self.state_manager.has_documents():
            chat_log.write("[warning]⚠️ No documents indexed yet. Use /documents to add and index documents first.[/warning]\\n")
            return

        self.state_manager.set_processing(True)

        try:
            chat_log.show_processing_status()

            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.docpixie.query_sync,
                query,
                None,  # mode
                None,  # document_ids
                None,  # max_pages
                self.state_manager.conversation_history,
                task_callback
            )

            chat_log.add_assistant_message(result.answer)

            if hasattr(result, 'get_pages_by_document'):
                pages_by_doc = result.get_pages_by_document()
                if pages_by_doc:
                    chat_log.write("[dim]Analyzed documents:[/dim]\n")
                    for doc_name, page_nums in pages_by_doc.items():
                        pages_str = ", ".join(str(p) for p in page_nums)
                        chat_log.write(f"[dim]  • {doc_name}: Pages {pages_str}[/dim]\n")
            elif hasattr(result, 'page_numbers') and result.page_numbers:
                chat_log.write(f"[dim]Analyzed pages: {result.page_numbers}[/dim]\n")

            if hasattr(result, 'processing_time') and result.processing_time > 0:
                chat_log.write(f"[dim]Processing time: {result.processing_time:.2f}s[/dim]\n")

            cost = getattr(result, 'total_cost', 0.0) or 0.0
            if cost < 0.01:
                chat_log.write(f"[dim]Cost: ${cost:.6f}[/dim]\n")
            else:
                chat_log.write(f"[dim]Cost: ${cost:.4f}[/dim]\n")

            chat_log.write("\n")

            self.state_manager.add_conversation_message(
                ConversationMessage(role="user", content=query)
            )
            self.state_manager.add_conversation_message(
                ConversationMessage(role="assistant", content=result.answer,
                                  cost=getattr(result, 'total_cost', 0.0) or 0.0)
            )

            self.state_manager.limit_conversation_history()
            self.state_manager.save_current_conversation()

            status_label = self.app.query_one("#status-label")
            status_label.update(self.state_manager.get_status_text())

        except Exception as e:
            chat_log.write(f"[red bold]●[/red bold] Error: {e}\n\n")
        finally:
            self.state_manager.set_processing(False)

    def delete_document_sync(self, document_id: str) -> bool:
        if self.docpixie:
            try:
                return self.docpixie.delete_document_sync(document_id)
            except Exception:
                return False
        return False
