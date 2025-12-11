"""
Test script for search_research_findings tool.

This script validates that the search_research_findings tool works correctly by:
1. Loading sample content (simulating LLM compressed research output)
2. Chunking the content using the same parameters as compress_research
3. Adding chunks to the in-memory vector store
4. Running search queries and printing results
"""

import asyncio
import os
import uuid
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig

# Import chunking function
from open_deep_research.chunks import chunk_text

# Import vector store and search tool
from open_deep_research.vector_store import get_research_findings_store
from open_deep_research.utils import search_research_findings


def load_sample_content() -> str:
    """Load the sample.txt content simulating compressed research output."""
    sample_path = Path(__file__).parent / "sample.txt"
    
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample file not found at: {sample_path}")
    
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"✅ Loaded sample content: {len(content)} characters")
    return content


def simulate_compress_research(content: str, research_topic: str) -> list[Document]:
    """
    Simulate the chunking and document creation process from compress_research.
    
    Uses the same parameters:
    - chunk_size: 512 tokens
    - chunk_overlap: 100 tokens
    """
    # Create page_info structure matching compress_research
    full_research_text = f"# Research Topic: {research_topic}\n\n## Compressed Findings\n\n{content}"
    
    page_info = [{
        "page_number": 1,
        "text": full_research_text,
        "start_char": 0,
        "end_char": len(full_research_text)
    }]
    
    # Configure chunking parameters (same as compress_research)
    chunk_size = 512  # tokens per chunk
    chunk_overlap = 100  # token overlap for context continuity
    
    print(f"\n📦 Chunking content...")
    print(f"   Total content length: {len(full_research_text)} characters")
    
    # Generate chunks
    chunks = chunk_text(
        text=full_research_text,
        page_info=page_info,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    print(f"   ✅ Created {len(chunks)} chunks")
    
    # Generate a unique session ID for this test
    session_id = str(uuid.uuid4())
    
    # Convert chunks to Document objects with metadata matching compress_research
    document_objects = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk["chunk_text"],
            metadata={
                "research_session_id": session_id,
                "source": "research_findings",
                "chunk_type": "compressed_research",
                "chunk_index": chunk.get("chunk_index"),
                "start_char": chunk.get("start_char"),
                "end_char": chunk.get("end_char"),
                "token_count": chunk.get("token_count"),
                "page_number": chunk.get("page_number"),
                "research_topic": research_topic,
                "total_chunks": len(chunks),
            },
        )
        document_objects.append(doc)
    
    return document_objects


async def add_documents_to_store(documents: list[Document]) -> None:
    """Add documents to the research vector store."""
    if documents:
        research_findings_store = await get_research_findings_store()
        document_ids = await research_findings_store.aadd_documents(documents=documents)
        print(f"\n✅ Added {len(documents)} chunks to vector store")
        print(f"   Document IDs: {document_ids[:3]}..." if len(document_ids) > 3 else f"   Document IDs: {document_ids}")
    else:
        print("⚠️ No documents to add")


async def run_test_searches(config: RunnableConfig) -> None:
    """Execute test searches and print results."""
    
    # Test queries based on sample.txt content
    test_queries = [
        ["omega-3 fish oil absorption bioavailability"],
        ["fishy burps enteric coating control"],
        ["Bayer Aspirin heart health positioning"],
        ["consumer segments adults 50+ supplements"],
    ]
    
    print("\n" + "=" * 80)
    print("🔍 RUNNING TEST SEARCHES")
    print("=" * 80)
    
    for queries in test_queries:
        print(f"\n{'─' * 60}")
        print(f"📌 Query: {queries}")
        print("─" * 60)
        
        try:
            # search_research_findings is a StructuredTool, use .ainvoke()
            result = await search_research_findings.ainvoke(
                {"queries": queries}, 
                config=config
            )
            print(result)
        except Exception as e:
            print(f"❌ Error searching: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main test function."""
    print("\n" + "=" * 80)
    print("🧪 TEST: search_research_findings")
    print("=" * 80)
    
    # Check for required API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please set it before running this test")
        return
    
    # Step 1: Load sample content
    print("\n📄 STEP 1: Loading sample content")
    content = load_sample_content()
    
    # Step 2: Simulate compress_research chunking
    print("\n📦 STEP 2: Simulating compress_research chunking")
    research_topic = "U.S. Omega-3 Fish Oil Market Analysis and Consumer Insights"
    documents = simulate_compress_research(content, research_topic)
    
    # Print sample of chunks
    print("\n📋 Sample chunks:")
    for i, doc in enumerate(documents[:2]):  # Show first 2 chunks
        print(f"\n   Chunk {i}:")
        print(f"   - Token count: {doc.metadata.get('token_count')}")
        print(f"   - Content preview: {doc.page_content[:150]}...")
    
    # Step 3: Add documents to vector store
    print("\n📥 STEP 3: Adding documents to vector store")
    await add_documents_to_store(documents)
    
    # Step 4: Create configuration for search
    print("\n⚙️ STEP 4: Creating configuration")
    config: RunnableConfig = {
        "configurable": {
            "summarization_model": "openai:gpt-4.1-mini",
            "summarization_model_max_tokens": 8192,
            "max_content_length": 50000,
            "max_structured_output_retries": 3,
        }
    }
    print("   Config created with default summarization settings")
    
    # Step 5: Run test searches
    print("\n🔍 STEP 5: Running test searches")
    await run_test_searches(config)
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

