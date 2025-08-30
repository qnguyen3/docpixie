#!/usr/bin/env python3
"""
DocPixie CLI - Interactive document chat interface
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Add the docpixie package to path if running from source
sys.path.insert(0, str(Path(__file__).parent))

from docpixie import DocPixie, ConversationMessage
from docpixie.core.config import DocPixieConfig
from docpixie.models.document import Document, QueryResult


class DocPixieCLI:
    """Command-line interface for DocPixie document chat"""

    def __init__(self):
        """Initialize the CLI application"""
        self.documents_folder = Path("./documents")
        self.docpixie: Optional[DocPixie] = None
        self.indexed_documents: List[Document] = []
        self.conversation_history: List[ConversationMessage] = []

    def initialize_docpixie(self) -> bool:
        """Initialize DocPixie with OpenRouter and in-memory storage"""
        try:
            # Check for API key
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                print("❌ Error: OPENROUTER_API_KEY environment variable not set")
                print("Please set it with: export OPENROUTER_API_KEY='your-api-key'")
                return False

            # Configure DocPixie
            config = DocPixieConfig(
                provider="openrouter",
                model="openai/gpt-4.1-mini",
                vision_model="google/gemini-2.5-flash",
                storage_type="memory",
                openrouter_api_key=api_key,
                jpeg_quality=85,  # Slightly lower quality for faster processing
                max_pages_per_task=4  # Limit pages per task for efficiency
            )

            # Initialize DocPixie
            self.docpixie = DocPixie(config=config)
            print("✅ DocPixie initialized with OpenRouter (Gemini 2.5 Flash)")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize DocPixie: {e}")
            return False

    def scan_documents(self) -> List[Path]:
        """Scan the documents folder for PDF files"""
        # Create documents folder if it doesn't exist
        if not self.documents_folder.exists():
            self.documents_folder.mkdir(parents=True)
            print(f"📁 Created documents folder: {self.documents_folder.absolute()}")

        # Find all PDF files
        pdf_files = list(self.documents_folder.glob("*.pdf"))

        if not pdf_files:
            print(f"📭 No PDF files found in {self.documents_folder.absolute()}")
            print("Please add PDF files to the documents folder and restart the program.")
            return []

        print(f"\n📚 Found {len(pdf_files)} PDF file(s):")
        for i, pdf in enumerate(pdf_files, 1):
            print(f"  {i}. {pdf.name}")

        return pdf_files

    def index_documents(self, pdf_files: List[Path]) -> bool:
        """Index all PDF documents"""
        if not pdf_files:
            return False

        print(f"\n🔄 Starting document indexing...")

        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                print(f"\n📄 Processing ({i}/{len(pdf_files)}): {pdf_file.name}")

                # Add document to DocPixie
                document = self.docpixie.add_document_sync(
                    file_path=str(pdf_file),
                    document_name=pdf_file.stem
                )

                self.indexed_documents.append(document)
                print(f"   ✅ Indexed: {document.page_count} pages")

                if document.summary:
                    print(f"   📝 Summary: {document.summary[:100]}...")

            except Exception as e:
                print(f"   ❌ Failed to index {pdf_file.name}: {e}")
                continue

        successful = len(self.indexed_documents)
        if successful > 0:
            print(f"\n✅ Successfully indexed {successful}/{len(pdf_files)} document(s)")
            return True
        else:
            print(f"\n❌ Failed to index any documents")
            return False

    def display_welcome_message(self):
        """Display welcome message and instructions"""
        print("\n" + "="*60)
        print("🧚 DocPixie Chat Interface")
        print("="*60)
        print("\nYou can now chat with your documents!")
        print("Commands:")
        print("  /new  - Start a new conversation")
        print("  /exit - Exit the program")
        print("  Ctrl+C - Force exit")
        print("\n" + "-"*60)

    def format_answer(self, result: QueryResult) -> str:
        """Format the query result for display"""
        output = []

        # Add the answer
        output.append(f"\n🤖 Assistant: {result.answer}")

        # Add metadata if available
        if result.page_numbers:
            output.append(f"\n📄 Analyzed pages: {result.page_numbers}")

        if result.confidence > 0:
            confidence_pct = int(result.confidence * 100)
            output.append(f"💡 Confidence: {confidence_pct}%")

        if result.processing_time > 0:
            output.append(f"⏱️ Processing time: {result.processing_time:.2f}s")

        return "\n".join(output)

    def chat_loop(self):
        """Main chat interaction loop"""
        self.display_welcome_message()

        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()

                # Check for commands
                if not user_input:
                    continue

                if user_input.lower() == "/exit":
                    print("\n👋 Goodbye!")
                    break

                if user_input.lower() == "/new":
                    self.conversation_history = []
                    print("\n🔄 Started new conversation")
                    continue

                # Process the query
                print("\n⏳ Thinking...")

                # Query with conversation history
                result = self.docpixie.query_sync(
                    question=user_input,
                    conversation_history=self.conversation_history
                )

                # Display the result
                print(self.format_answer(result))

                # Update conversation history
                self.conversation_history.append(
                    ConversationMessage(role="user", content=user_input)
                )
                self.conversation_history.append(
                    ConversationMessage(role="assistant", content=result.answer)
                )

                # Limit conversation history to last 10 turns
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break

            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Please try again or use /new to start fresh.")

    def run(self):
        """Main entry point for the CLI application"""
        print("\n🧚 DocPixie CLI - Document Chat Interface")
        print("="*60)

        # Initialize DocPixie
        if not self.initialize_docpixie():
            return 1

        # Scan for documents
        pdf_files = self.scan_documents()
        if not pdf_files:
            return 1

        # Ask user to confirm indexing
        print(f"\n❓ Index these {len(pdf_files)} document(s)? (y/n): ", end="")
        response = input().strip().lower()

        if response != 'y':
            print("📭 Indexing cancelled")
            return 0

        # Index documents
        if not self.index_documents(pdf_files):
            return 1

        # Start chat loop
        self.chat_loop()

        return 0


def main():
    """Main entry point"""
    cli = DocPixieCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
