"""
Snippet: Generate chunks from local PDF.

This script demonstrates the complete process:
1. Extract text from local PDF file
2. Generate chunks using TokenChunker
"""

import os
import re
import sys
from typing import Any

import tiktoken
from chonkie import TokenChunker
from pypdf import PdfReader


def clean_text(text: str) -> str:
    """Clean up text by removing excessive whitespace and formatting issues."""
    if not text:
        return text

    # Remove excessive whitespace between words (keep single spaces)
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive line breaks (keep max 2 consecutive)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading/trailing whitespace from each line
    lines = text.split("\n")
    cleaned_lines = [line.strip() for line in lines]

    # Remove empty lines at the beginning and end
    while cleaned_lines and not cleaned_lines[0]:
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()

    # Join lines back together
    text = "\n".join(cleaned_lines)

    # Remove excessive spaces around punctuation
    text = re.sub(r"\s+([.!?,:;])", r"\1", text)
    text = re.sub(r"([.!?,:;])\s+", r"\1 ", text)

    return text.strip()


def extract_pdf_text(pdf_path: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Extract text from PDF with page information.

    Returns:
        tuple: (full_text, page_info_list)
    """
    try:
        reader = PdfReader(pdf_path)
        full_text = []
        page_info = []

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text:
                full_text.append(text)
                page_info.append(
                    {
                        "page_number": page_num,
                        "text": text,
                        "start_char": sum(len(t) for t in full_text[:-1]),
                        "end_char": sum(len(t) for t in full_text),
                    }
                )

        return "\n".join(full_text), page_info
    except Exception as e:
        raise RuntimeError(f"Error extracting PDF text: {e!s}") from e


def chunk_text(
    text: str,
    page_info: list[dict[str, Any]],
    chunk_size: int = 512,
    chunk_overlap: int = 100,
) -> list[dict[str, Any]]:
    """
    Chunk text using Chonkie with token-based chunking and overlap.

    Args:
        text: Full document text
        page_info: Page information for mapping chunks to pages
        chunk_size: Target tokens per chunk (default: 512)
        chunk_overlap: Token overlap between chunks for context continuity (default: 100)

    Returns:
        List of chunk dictionaries with metadata
    """
    # Initialize tokenizer
    tokenizer = tiktoken.get_encoding("cl100k_base")

    # Initialize TokenChunker with overlap for context continuity
    chunker = TokenChunker(
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,  # Overlap ensures context continuity
    )

    # Create chunks
    chunks = chunker.chunk(text)

    result_chunks = []
    for idx, chunk in enumerate(chunks):
        # Find which page this chunk belongs to
        chunk_start = chunk.start_index if hasattr(chunk, "start_index") else 0
        chunk_end = (
            chunk.end_index if hasattr(chunk, "end_index") else len(chunk.text)
        )

        page_number = None
        for page in page_info:
            if page["start_char"] <= chunk_start < page["end_char"]:
                page_number = page.get("page_number")
                break

        # Clean the chunk text
        cleaned_text = clean_text(chunk.text)

        result_chunks.append(
            {
                "chunk_index": idx,
                "chunk_text": cleaned_text,
                "start_char": chunk_start,
                "end_char": chunk_end,
                "page_number": page_number,
                "token_count": chunk.token_count
                if hasattr(chunk, "token_count")
                else len(tokenizer.encode(cleaned_text)),
            }
        )

    return result_chunks


def process_pdf(
    pdf_path: str,
    chunk_size: int = 512,
    chunk_overlap: int = 100,
) -> list[dict[str, Any]]:
    """
    Extract text from local PDF and generate chunks.

    Args:
        pdf_path: Path to local PDF file
        chunk_size: Target tokens per chunk (default: 512)
        chunk_overlap: Token overlap between chunks (default: 100)

    Returns:
        List of chunk dictionaries
    """
    # Validate file exists
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if not pdf_path.lower().endswith(".pdf"):
        raise ValueError(f"File must be a PDF: {pdf_path}")

    # Step 1: Extract text from PDF
    full_text, page_info = extract_pdf_text(pdf_path)

    # Step 2: Clean the extracted text
    full_text = clean_text(full_text)

    # Step 3: Generate chunks
    chunks = chunk_text(full_text, page_info, chunk_size, chunk_overlap)
    return chunks


# Example usage
if __name__ == "__main__":
    # Get PDF path from command line argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        print("Usage: python chunks.py <path_to_pdf>")  
        sys.exit(1)

    # Process document and get chunks
    chunks = process_pdf(
        pdf_path=pdf_path,
        chunk_size=512,
        chunk_overlap=100,
    )

