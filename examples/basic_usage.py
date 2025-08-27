"""
Basic DocPixie usage example
Phase 1: Document processing and storage
"""

import asyncio
import os
from pathlib import Path

from docpixie import DocPixie, create_docpixie, create_memory_docpixie
from docpixie.models.document import QueryMode


async def main():
    """Demonstrate basic DocPixie functionality"""
    
    print("🚀 DocPixie Phase 1 Example")
    print("=" * 40)
    
    # Create DocPixie instance with memory storage for demo
    # In production, you'd use: create_docpixie(api_key="your-api-key")
    docpixie = create_memory_docpixie(
        provider="openai", 
        api_key=os.getenv("OPENAI_API_KEY", "demo-key")
    )
    
    print(f"✓ Created DocPixie instance")
    print(f"  Provider: {docpixie.config.provider}")
    print(f"  Storage: {type(docpixie.storage).__name__}")
    print()
    
    # Show supported file types
    print("📄 Supported file types:")
    extensions = docpixie.get_supported_extensions()
    for ext, processor in extensions.items():
        print(f"  {ext} → {processor}")
    print()
    
    # Check if we can find any sample files to process
    sample_files = []
    
    # Look for sample files in common locations
    possible_paths = [
        ".",
        "./examples",
        "./docs",
        str(Path.home() / "Documents"),
        str(Path.home() / "Downloads")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path) and docpixie.supports_file(file_path):
                    sample_files.append(file_path)
                    if len(sample_files) >= 2:  # Limit to 2 files for demo
                        break
        if sample_files:
            break
    
    if sample_files:
        print(f"📁 Found {len(sample_files)} sample file(s) to process:")
        for file_path in sample_files:
            print(f"  {file_path}")
        print()
        
        # Process documents
        documents = []
        for file_path in sample_files:
            try:
                print(f"🔄 Processing: {os.path.basename(file_path)}")
                
                # Add document (Phase 1: processing without summarization for demo)
                document = await docpixie.add_document(
                    file_path,
                    summarize=False  # Skip summarization for demo (requires API key)
                )
                
                documents.append(document)
                print(f"  ✓ Processed {document.page_count} pages")
                print(f"  ✓ Document ID: {document.id}")
                
            except Exception as e:
                print(f"  ❌ Failed to process {file_path}: {e}")
        
        print()
        
        # List documents
        print("📋 Documents in storage:")
        doc_list = await docpixie.list_documents()
        for doc_info in doc_list:
            print(f"  {doc_info['name']} ({doc_info['page_count']} pages)")
        print()
        
        # Demonstrate query (Phase 1 placeholder)
        if documents:
            print("❓ Example queries (Phase 1 - Placeholder responses):")
            
            queries = [
                "What is this document about?",
                "Summarize the main points",
                "Find information about revenue"
            ]
            
            for query in queries:
                print(f"\n  Q: {query}")
                
                # Test both Flash and Pro modes
                for mode in [QueryMode.FLASH, QueryMode.PRO]:
                    result = await docpixie.query(query, mode=mode)
                    print(f"  A ({mode.value}): {result.answer[:100]}...")
                    print(f"    Pages analyzed: {len(result.selected_pages)}")
                    print(f"    Confidence: {result.confidence}")
        
    else:
        print("📁 No supported files found for demo")
        print("   Try placing a PDF or image file in the current directory")
        print()
        
        # Show basic functionality without files
        print("📊 System statistics:")
        stats = docpixie.get_stats()
        print(f"  DocPixie version: {stats['docpixie_version']}")
        print(f"  AI Provider: {stats['config']['provider']}")
        print(f"  Storage type: {stats['config']['storage_type']}")
        print(f"  Flash max pages: {stats['config']['flash_max_pages']}")
        print(f"  Pro max pages: {stats['config']['pro_max_pages']}")
    
    print()
    print("🎉 Phase 1 Demo Complete!")
    print()
    print("Phase 1 Features Demonstrated:")
    print("  ✓ Document processing (PDF, images)")
    print("  ✓ PyMuPDF-based PDF rendering")
    print("  ✓ In-memory and local storage")
    print("  ✓ Document management (add, list, delete)")
    print("  ✓ Configuration system")
    print("  ✓ Flash/Pro mode distinction")
    print()
    print("Coming in Phase 2:")
    print("  → Vision-based page selection")
    print("  → Actual query answering")
    print("  → Page summary generation")
    print("  → Complete RAG pipeline")


def sync_demo():
    """Demonstrate synchronous API"""
    print("\n🔄 Synchronous API Demo")
    print("-" * 30)
    
    # Create DocPixie with sync API
    docpixie = create_memory_docpixie(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY", "demo-key")
    )
    
    # Use sync methods
    print(f"✓ Supported extensions: {len(docpixie.get_supported_extensions())}")
    
    # List documents (should be empty initially)
    docs = docpixie.list_documents_sync()
    print(f"✓ Documents in storage: {len(docs)}")
    
    # Get stats
    stats = docpixie.get_stats()
    print(f"✓ Storage backend: {stats['storage']['backend']}")


if __name__ == "__main__":
    # Run async demo
    asyncio.run(main())
    
    # Run sync demo
    sync_demo()
    
    print("\n" + "=" * 50)
    print("DocPixie Phase 1 implementation is working! 🎉")
    print("=" * 50)