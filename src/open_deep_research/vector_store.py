"""Unified vector store module using Chroma for document storage and retrieval.

This module provides centralized vector store management for:
1. Internal documents (PDFs and other company documents)
2. Research findings (embedded research results from deep research sessions)
"""

import chromadb
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# Initialize environment variables
load_dotenv()

# Initialize shared embeddings model
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Initialize in-memory Chroma client (shared across collections)
chroma_client = chromadb.Client()

########################################################
# Internal Documents Collection
# Used for storing and retrieving internal PDF documents
########################################################

internal_documents_store = Chroma(
    client=chroma_client,
    collection_name="internal_documents",
    embedding_function=embeddings,
)
internal_documents_retriever = internal_documents_store.as_retriever()

########################################################
# Research Findings Collection
# Used for storing and retrieving research findings from deep research sessions
########################################################

research_findings_store = Chroma(
    client=chroma_client,
    collection_name="research_findings",
    embedding_function=embeddings,
)
research_findings_retriever = research_findings_store.as_retriever()

