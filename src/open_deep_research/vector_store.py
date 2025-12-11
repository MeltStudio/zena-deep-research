"""Unified vector store module using PostgreSQL with pgvector for document storage and retrieval.

This module provides centralized vector store management for:
1. Internal documents (PDFs and other company documents)
2. Research findings (embedded research results from deep research sessions)

Uses lazy initialization pattern to avoid async issues at import time.
"""

import logging
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGEngine, PGVectorStore
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)

# Initialize environment variables
load_dotenv()


class VectorStoreManager:
    """Singleton manager for vector stores with lazy async initialization."""
    
    _instance: Optional["VectorStoreManager"] = None
    _initialized: bool = False
    _internal_documents_store: Optional[PGVectorStore] = None
    _research_findings_store: Optional[PGVectorStore] = None
    _pg_engine: Optional[PGEngine] = None
    
    def __new__(cls) -> "VectorStoreManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def _init_table_if_not_exists(self, table_name: str, vector_size: int) -> None:
        """Initialize a vector store table, ignoring if it already exists."""
        try:
            await self._pg_engine.ainit_vectorstore_table(
                table_name=table_name,
                vector_size=vector_size,
            )
            logger.info(f"Created table '{table_name}'")
        except ProgrammingError as e:
            # Check if it's a "table already exists" error
            if "already exists" in str(e):
                logger.debug(f"Table '{table_name}' already exists, skipping creation")
            else:
                raise
    
    async def _initialize(self) -> None:
        """Initialize vector stores if not already initialized."""
        if self._initialized:
            return
        
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # PostgreSQL connection string
        # Default to localhost:5432 if POSTGRES_CONNECTION_STRING is not set
        postgres_connection_string = os.getenv(
            "POSTGRES_CONNECTION_STRING",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/vectorstore"
        )

        engine = create_async_engine(
            postgres_connection_string,
        )

        self._pg_engine = PGEngine.from_engine(engine=engine)

        # Initialize tables, ignoring if they already exist
        await self._init_table_if_not_exists("internal_documents", 1536)
        await self._init_table_if_not_exists("research_findings", 1536)
        
        self._internal_documents_store = await PGVectorStore.create(
            engine=self._pg_engine,
            embedding_service=embeddings,
            table_name="internal_documents",
        )
        self._research_findings_store = await PGVectorStore.create(
            engine=self._pg_engine,
            embedding_service=embeddings,
            table_name="research_findings",
        )
        
        self._initialized = True
    
    async def get_internal_documents_store(self) -> PGVectorStore:
        """Get the internal documents vector store, initializing if needed."""
        await self._initialize()
        return self._internal_documents_store
    
    async def get_research_findings_store(self) -> PGVectorStore:
        """Get the research findings vector store, initializing if needed."""
        await self._initialize()
        return self._research_findings_store
    
    async def get_pg_engine(self) -> PGEngine:
        """Get the PGEngine instance, initializing if needed."""
        await self._initialize()
        return self._pg_engine


# Global singleton instance
_manager = VectorStoreManager()


async def get_internal_documents_store() -> PGVectorStore:
    """Get the internal documents vector store.
    
    This function handles lazy initialization of the vector store,
    ensuring it's only created when first needed.
    
    Returns:
        PGVectorStore: The initialized internal documents vector store.
    """
    return await _manager.get_internal_documents_store()


async def get_research_findings_store() -> PGVectorStore:
    """Get the research findings vector store.
    
    This function handles lazy initialization of the vector store,
    ensuring it's only created when first needed.
    
    Returns:
        PGVectorStore: The initialized research findings vector store.
    """
    return await _manager.get_research_findings_store()


async def get_pg_engine() -> PGEngine:
    """Get the PGEngine instance.
    
    This function handles lazy initialization of the engine,
    ensuring it's only created when first needed.
    
    Returns:
        PGEngine: The initialized PGEngine instance.
    """
    return await _manager.get_pg_engine()
