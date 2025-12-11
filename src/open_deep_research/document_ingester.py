import asyncio
import logging
from pathlib import Path
from typing import Iterator, Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
)
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
import tiktoken

from open_deep_research.configuration import Configuration
from open_deep_research.utils import get_api_key_for_model

logger = logging.getLogger(__name__)

# Default prompt for image description
IMAGE_DESCRIPTION_PROMPT: str = (
    "List only the objects, elements, and text visible in this image."
    "Be concise and factual. Do not provide explanations, context, or additional commentary."
)


def get_output_file_path() -> Path:
    """Get the output directory path for ingested documents."""
    return Path(__file__).parent.resolve()

tokenizer = OpenAITokenizer(
    tokenizer=tiktoken.encoding_for_model("text-embedding-3-small"),
    max_tokens=8000,
)

def create_picture_description_options(
) -> Optional[PictureDescriptionApiOptions]:
    """Create PictureDescriptionApiOptions from LangChain model configuration.
    
    This function maps LangChain model configurations to Docling's native
    PictureDescriptionApiOptions for supported providers (OpenAI, Anthropic, Google).
    
    Args:
        config: Runtime configuration containing model settings
        
    Returns:
        PictureDescriptionApiOptions if the provider is supported, None otherwise
    """
    configurable = Configuration.from_runnable_config()
    model_name = configurable.document_ingestion_model.lower()
    api_key = get_api_key_for_model(configurable.document_ingestion_model)
    max_tokens = configurable.document_ingestion_model_max_tokens
    
    # OpenAI models (gpt-4o, gpt-4-vision, etc.)
    if model_name.startswith("openai:"):
        model_id = model_name.replace("openai:", "")
        result = PictureDescriptionApiOptions(
            url="https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            params={
                "model": model_id,
                "max_completion_tokens": max_tokens,
            },
            prompt=IMAGE_DESCRIPTION_PROMPT,
            timeout=90,
        )
        
        return result
    
    # Anthropic models (claude-3, claude-3.5, etc.)
    elif model_name.startswith("anthropic:"):
        model_id = model_name.replace("anthropic:", "")
        return PictureDescriptionApiOptions(
            url="https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            params={
                "model": model_id,
                "max_tokens": max_tokens,
            },
            prompt=IMAGE_DESCRIPTION_PROMPT,
            timeout=90,
        )
    
    # Google/Gemini models
    elif model_name.startswith("google:") or model_name.startswith("gemini:"):
        model_id = model_name.replace("google:", "").replace("gemini:", "")
        return PictureDescriptionApiOptions(
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent",
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            params={
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                }
            },
            prompt=IMAGE_DESCRIPTION_PROMPT,
            timeout=90,
        )
    
    # Provider not supported for native Docling integration
    # Will fall back to manual LangChain approach
    logger.info(
        f"Model '{model_name}' not supported for native Docling integration. "
        "Will use manual LangChain approach."
    )
    return None

# =============================================================================
# Main Ingestion Functions
# =============================================================================


async def ingest_documents(path: str) -> tuple[Iterator[BaseChunk], HybridChunker]:
    """Ingest documents using Docling's native picture description.
    
    Uses PictureDescriptionApiOptions for automatic image description
    during document conversion.
    
    Args:
        path: Path to the PDF file
        
    Returns:
        chunks of the document
    """
    logger.info(f"Ingesting documents (native method) from: {path}")
    path_obj = Path(path)
    
    # Create picture description options
    picture_options = create_picture_description_options()
    
    if picture_options is None:
        raise ValueError("image description provider not supported")
    
    # Configure pipeline with native picture description
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_page_images = False
    pipeline_options.generate_picture_images = True
    pipeline_options.enable_remote_services = True  # Required for remote VLM
    pipeline_options.do_picture_description = True
    pipeline_options.picture_description_options = picture_options
    
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    # Convert - descriptions are generated automatically during conversion
    result = converter.convert(path_obj)

    chunker = HybridChunker(
        tokenizer=tokenizer,
        merge_peers=True,
    )
    
    

    chunk_iter = chunker.chunk(dl_doc=result.document)
    return chunk_iter, chunker



# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    # Get project root (2 levels up from this file)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    pdf_path = project_root / "docs" / "Zena Banner EnteriCare technology description.pdf"
    
    async def test_ingest():
        """Test document ingestion asynchronously."""
        try:
            logger.info(f"Starting test ingestion of: {pdf_path}")
            output_path = await ingest_documents(str(pdf_path))
            logger.info(f"Test completed successfully. Output: {output_path}")
        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)
    
    # Run the async test
    asyncio.run(test_ingest())