"""Internal documents ingestion module.

This module handles processing and ingesting internal PDF documents
into the unified Chroma vector store for retrieval.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document

from open_deep_research.chunks import process_pdf
from open_deep_research.vector_store import (
    internal_documents_store,
    internal_documents_retriever,
)


########################################################
# Search Internal Documents Logic
########################################################
load_dotenv()

# Get the project root directory (2 levels up from this file: src/open_deep_research -> src -> root)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
docs_dir = project_root / "docs"

file_paths = [
    str(docs_dir / "Brand Plan OAD August 2016.pdf"),
    str(docs_dir / "DRC Fish Oil Persuadable claims research RSO_7310_Fish Oil_V3.pdf"),
    str(docs_dir / "Zena Banner EnteriCare technology description.pdf"),
]

# Process all PDFs and create Document objects
all_splits = []
processed_files = 0

for pdf_path in file_paths:
    if not os.path.exists(pdf_path):
        continue

    try:
        # Process PDF and get chunks
        chunks = process_pdf(
            pdf_path=pdf_path,
            chunk_size=512,
            chunk_overlap=100,
        )

        # Get filename for metadata
        filename = Path(pdf_path).name

        # Convert chunks to LangChain Document objects
        for chunk in chunks:
            doc = Document(
                page_content=chunk["chunk_text"],
                metadata={
                    "source": pdf_path,
                    "filename": filename,
                    "page_number": chunk.get("page_number"),
                    "chunk_index": chunk.get("chunk_index"),
                    "start_char": chunk.get("start_char"),
                    "end_char": chunk.get("end_char"),
                    "token_count": chunk.get("token_count"),
                },
            )
            all_splits.append(doc)
        
        processed_files += 1
    except Exception as e:
        print(f"❌ Error processing {pdf_path}: {e}")

# Add documents to vector store if any were processed
if all_splits:
    try:
        document_ids = internal_documents_store.add_documents(documents=all_splits)
    except Exception as e:
        print(f"❌ Error adding documents to vector store: {e}")
elif processed_files == 0:
    print("⚠️  No documents were processed. Check that PDF files exist in the docs/ directory.")

# Export retriever for backward compatibility
retriever = internal_documents_retriever
