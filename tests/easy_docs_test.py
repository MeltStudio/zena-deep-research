import asyncio
from open_deep_research.vector_store import get_internal_documents_store
from open_deep_research.ingest_initial_documents import ingest_documents_to_store


async def test_easy_docs():
    # Uncomment to ingest documents first:
    await ingest_documents_to_store()
    
    # Get the vector store (lazy initialization)
    internal_documents_store = await get_internal_documents_store()
    
    # Search for documents
    results = await internal_documents_store.asimilarity_search("What is fish oil?")
    print(results[0].page_content[:100] + "...")


asyncio.run(test_easy_docs())
