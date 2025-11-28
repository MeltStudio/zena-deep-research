import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

from open_deep_research.chunks import process_pdf


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

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Process all PDFs and create Document objects
all_splits = []
for pdf_path in file_paths:
    if not os.path.exists(pdf_path):
        print(f"⚠️  Warning: File not found: {pdf_path}")
        continue

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

vector_store = InMemoryVectorStore(embeddings)
document_ids = vector_store.add_documents(documents=all_splits)

retriever = vector_store.as_retriever()
