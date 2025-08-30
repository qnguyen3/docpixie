#!/usr/bin/env python3
"""
DocPixie Debug Test - Test document processing and querying
"""

import os
import sys
import asyncio
from pathlib import Path
import json
import traceback

# Add the docpixie package to path if running from source
sys.path.insert(0, str(Path(__file__).parent))

from docpixie import DocPixie, ConversationMessage
from docpixie.core.config import DocPixieConfig
from docpixie.models.document import Document, QueryResult


async def test_docpixie():
    """Test DocPixie with documents"""
    
    print("=" * 60)
    print("DocPixie Debug Test")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY environment variable not set")
        return
    
    # Configure DocPixie with debug logging
    config = DocPixieConfig(
        provider="openrouter",
        model="google/gemini-2.5-flash",
        vision_model="google/gemini-2.5-flash",
        storage_type="memory",
        openrouter_api_key=api_key,
        jpeg_quality=85,
        max_pages_per_task=4,
        log_level="DEBUG",  # Enable debug logging
        log_requests=True   # Log API requests
    )
    
    print(f"✅ Config created with model: {config.model}")
    
    # Initialize DocPixie
    try:
        pixie = DocPixie(config=config)
        print("✅ DocPixie initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        traceback.print_exc()
        return
    
    # Find and index documents
    documents_folder = Path("./documents")
    pdf_files = list(documents_folder.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in documents folder")
        return
    
    print(f"\n📚 Found {len(pdf_files)} PDF file(s)")
    
    # Index first document for testing
    pdf_file = pdf_files[0]
    print(f"\n📄 Indexing: {pdf_file.name}")
    
    try:
        document = await pixie.add_document(
            file_path=str(pdf_file),
            document_name=pdf_file.stem
        )
        print(f"✅ Indexed document: {document.name}")
        print(f"   Pages: {document.page_count}")
        if document.summary:
            print(f"   Summary: {document.summary[:200]}...")
    except Exception as e:
        print(f"❌ Failed to index: {e}")
        traceback.print_exc()
        return
    
    # Test a simple query
    print("\n" + "=" * 60)
    print("Testing Query Processing")
    print("=" * 60)
    
    test_query = "What is the main topic of this document?"
    print(f"\n📝 Query: {test_query}")
    
    try:
        # Test without conversation history first
        print("\n1️⃣ Testing without conversation history...")
        result = await pixie.query(
            question=test_query
        )
        print(f"✅ Query succeeded!")
        print(f"   Answer: {result.answer[:200]}...")
        print(f"   Pages analyzed: {result.page_numbers}")
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        traceback.print_exc()
        
        # Try to debug the provider response
        print("\n🔍 Attempting to debug provider response...")
        try:
            # Try calling the agent directly
            from docpixie.ai.agent import PixieRAGAgent
            agent = pixie.agent
            
            # Check if documents are available
            docs = await pixie.list_documents()
            print(f"📚 Available documents: {len(docs)}")
            for doc in docs:
                print(f"   - {doc['name']} ({doc['page_count']} pages)")
            
            # Try to get more details on the error
            print("\n🔍 Testing task planner directly...")
            from docpixie.ai.task_planner import TaskPlanner
            planner = TaskPlanner(pixie.provider, pixie.storage, config)
            
            # Test the actual task planning prompt
            print("\n🔍 Testing actual task planning with documents...")
            documents_str = "\n".join([
                f"{doc['id']}: {doc['name']}\nSummary: {doc.get('summary', 'No summary')[:200]}..."
                for doc in docs
            ])
            
            from docpixie.ai.prompts import SYSTEM_TASK_PLANNER, ADAPTIVE_INITIAL_PLANNING_PROMPT
            
            messages = [
                {"role": "system", "content": SYSTEM_TASK_PLANNER},
                {"role": "user", "content": ADAPTIVE_INITIAL_PLANNING_PROMPT.format(
                    query=test_query,
                    documents=documents_str
                )}
            ]
            
            print("Sending task planning request to provider...")
            response = await pixie.provider.process_text_messages(messages, max_tokens=500)
            print(f"\n📝 Raw task planner response:\n{response}")
            print(f"\n📝 Response type: {type(response)}")
            print(f"📝 Response length: {len(response)}")
            
            # Try to find JSON in the response
            print("\n🔍 Attempting to extract JSON from response...")
            import re
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                print(f"Found potential JSON: {json_str[:100]}...")
                try:
                    parsed = json.loads(json_str)
                    print(f"✅ JSON parsing successful: {parsed}")
                except json.JSONDecodeError as je:
                    print(f"❌ JSON parsing failed: {je}")
            else:
                print("❌ No JSON structure found in response")
                
        except Exception as debug_error:
            print(f"❌ Debug attempt failed: {debug_error}")
            traceback.print_exc()
    
    # Test with conversation history
    print("\n2️⃣ Testing with conversation history...")
    
    conversation_history = [
        ConversationMessage(role="user", content="What's the document about?"),
        ConversationMessage(role="assistant", content="This document is about...")
    ]
    
    try:
        result = await pixie.query(
            question="Can you tell me more details?",
            conversation_history=conversation_history
        )
        print(f"✅ Query with history succeeded!")
        print(f"   Answer: {result.answer[:200]}...")
        
    except Exception as e:
        print(f"❌ Query with history failed: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test
    asyncio.run(test_docpixie())