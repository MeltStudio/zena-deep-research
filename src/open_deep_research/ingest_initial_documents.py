"""Internal documents ingestion module.

This module handles processing and ingesting internal PDF documents
into the unified PostgreSQL pgvector store for retrieval.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from langchain_core.documents import Document

from open_deep_research.document_ingester import ingest_documents
from open_deep_research.vector_store import get_internal_documents_store


########################################################
# Search Internal Documents Logic
########################################################
load_dotenv()

# Get the project root directory (2 levels up from this file: src/open_deep_research -> src -> root)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
docs_dir = project_root / "docs"

# Default file paths for processing
DEFAULT_FILE_PATHS = [
    str(docs_dir / "Brand Plan OAD August 2016.pdf"),
    str(docs_dir / "DRC Fish Oil Persuadable claims research RSO_7310_Fish Oil_V3.pdf"),
    #str(docs_dir / "Zena Banner EnteriCare technology description.pdf"),
]


async def process_documents_async(file_paths: List[str] = None) -> List[Document]:
    """Process all PDFs asynchronously and create Document objects.
    
    Args:
        file_paths: List of file paths to process. If None, uses DEFAULT_FILE_PATHS.
        
    Returns:
        List of processed Document objects.
    """
    if file_paths is None:
        file_paths = DEFAULT_FILE_PATHS
    
    all_splits = []
    processed_files = 0

    for pdf_path in file_paths:
        if not os.path.exists(pdf_path):
            print(f"⚠️  File not found: {pdf_path}")
            continue

        try:
            # Process PDF and get chunks
            chunk_iter, chunker = await ingest_documents(pdf_path)

            # Convert chunks to LangChain Document objects
            for chunk in chunk_iter:
                # Extract metadata from chunk.meta
                meta = chunk.meta

                # Extract filename from origin
                filename = (
                    meta.origin.filename
                    if hasattr(meta, "origin") and hasattr(meta.origin, "filename")
                    else None
                )

                # Extract headings
                headings = (
                    meta.headings if hasattr(meta, "headings") and meta.headings else []
                )

                # Extract page_no from doc_items provenance
                page_no = None
                if hasattr(meta, "doc_items") and meta.doc_items:
                    # Get page_no from the first provenance item that has it
                    for doc_item in meta.doc_items:
                        if hasattr(doc_item, "prov") and doc_item.prov:
                            for prov_item in doc_item.prov:
                                if (
                                    hasattr(prov_item, "page_no")
                                    and prov_item.page_no is not None
                                ):
                                    page_no = prov_item.page_no
                                    break
                        if page_no is not None:
                            break

                # Extract uri from origin
                uri = (
                    meta.origin.uri
                    if hasattr(meta, "origin") and hasattr(meta.origin, "uri")
                    else None
                )

                doc = Document(
                    page_content=chunker.contextualize(chunk=chunk),
                    metadata={
                        "filename": filename,
                        "headings": headings,
                        "page_no": page_no,
                        "uri": uri,
                    },
                )
                all_splits.append(doc)

            processed_files += 1
            print(f"✅ Processed: {pdf_path}")
        except Exception as e:
            print(f"❌ Error processing {pdf_path}: {e}")

    if processed_files == 0:
        print(
            "⚠️  No documents were processed. Check that PDF files exist in the docs/ directory."
        )
    
    return all_splits


async def ingest_documents_to_store(file_paths: List[str] = None) -> List[str]:
    """Process documents and add them to the vector store.
    
    This is the main entry point for document ingestion.
    
    Args:
        file_paths: List of file paths to process. If None, uses DEFAULT_FILE_PATHS.
        
    Returns:
        List of document IDs that were added to the store.
    """
    # Process documents
    documents = await process_documents_async(file_paths)
    
    if not documents:
        return []
    
    # Add to vector store
    try:
        internal_documents_store = await get_internal_documents_store()
        document_ids = await internal_documents_store.aadd_documents(documents=documents)
        print(f"✅ Added {len(document_ids)} documents to vector store")
        return document_ids
    except Exception as e:
        print(f"❌ Error adding documents to vector store: {e}")
        return []
