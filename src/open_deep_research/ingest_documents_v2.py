import base64
import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    ConversionResult,
    DocumentConverter,
    PdfFormatOption,
)
from docling_core.types.doc import PictureItem
from PIL import Image

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

"""
ImportError: libGL.so.1: cannot open shared object file: No such file or directory
sudo apt install libgl1
- sudo apt install libgl1-mesa-glx
"""


def get_output_file_path() -> Path:
    return Path(__file__).parent.resolve()


bedrock_client = None
max_tokens: int = 10000
prompt: str = (
    "You are an expert assistant in documents. "
    "Describe this image from a PDF in detail, "
    "focusing on what a human needs to know to understand it. "
    "Respond in English."
)


def get_bedrock_client(region: str = "us-east-1"):
    global bedrock_client
    if bedrock_client is None:
        import boto3

        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region,
        )
    return bedrock_client


def describe_image_with_bedrock(
    image: Image.Image,
) -> str:

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64_image,
                    },
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        }
    ]

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
        }
    )

    try:
        bedrock_client = get_bedrock_client()
        response = bedrock_client.invoke_model(
            modelId="global.anthropic.claude-haiku-4-5-20251001-v1:0",
            body=body,
        )
    except ClientError as e:
        logger.error("Error llamando a Bedrock: %s", e)
        return f"[ERROR] Bedrock: {e}"

    response_body = json.loads(response.get("body").read())

    text_chunks = [
        block["text"]
        for block in response_body.get("content", [])
        if block.get("type") == "text"
    ]
    return "".join(text_chunks).strip()


def describe_pictures(pictures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for idx, pic in enumerate(pictures, start=1):
        logger.info("Generating description for image %d / %d", idx, len(pictures))
        description = describe_image_with_bedrock(
            image=pic["image"],
        )

        results.append(
            {
                "ref": pic["ref"],
                "caption": pic["caption"],
                "description": description,
            }
        )

    return results


def extract_images_from_document(conv_res: ConversionResult) -> List[Dict[str, Any]]:
    pictures: List[Dict[str, Any]] = []

    for element, _level in conv_res.document.iterate_items():
        if isinstance(element, PictureItem):
            try:
                pil_img = element.get_image(conv_res.document)
                print(pil_img)
            except Exception as e:
                logger.warning(
                    "Could not obtain image from %s: %s", element.self_ref, e
                )
                continue

            caption = element.caption_text(doc=conv_res.document)
            pictures.append(
                {
                    "ref": str(element.self_ref),
                    "caption": caption,
                    "image": pil_img,
                }
            )
    logger.info("Total images (PictureItem) found: %d", len(pictures))
    return pictures


def insert_description_in_place(markdown_text, pictures):
    output = markdown_text
    for pic in pictures:
        placeholder = "<!-- image -->"
        replacement = (
            f"<!-- image: {pic['ref']} -->\n"
            f"{pic['description']}\n"
            f"<!-- endimage -->"
        )
        output = output.replace(placeholder, replacement, 1)
    return output


def ingest_documents(path: str):
    logger.info(f"Ingesting documents from: {path}")
    path_obj = Path(path)
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_page_images = False
    pipeline_options.generate_picture_images = True
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(path_obj)

    imgs = extract_images_from_document(result)
    imgs_descriptions = describe_pictures(imgs)
    md = result.document.export_to_markdown()
    md = insert_description_in_place(md, imgs_descriptions)
    output_path = get_output_file_path() / "ingested_documents.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    logger.info(f"Ingested documents written to: {output_path}")


def main(path: str):
    ingest_documents(path)


if __name__ == "__main__":
    import argparse

    logger.info("Starting document ingestion script.")
    parser = argparse.ArgumentParser(description="Ingest documents into the system.")
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="The path to the documents to be ingested.",
    )
    args = parser.parse_args()
    main(path=args.path)
