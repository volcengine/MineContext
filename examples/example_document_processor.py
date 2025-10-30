#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Example 2: Document Processor - Process various document formats
This example demonstrates how to use the DocumentProcessor to process different document formats
including PDF, DOCX, XLSX, CSV, Markdown, images, and text content without storing them in the database.

Supported formats:
- Visual documents: PDF, DOCX, DOC, PPTX, PPT, PNG, JPG, JPEG, GIF, BMP, WEBP, MD (Markdown)
- Structured documents: XLSX, XLS, CSV, JSONL
- Text files: TXT, MD (Markdown with images)

Usage:
    # Scan a directory for documents
    python example_document_processor.py /path/to/documents/

    # Process specific files
    python example_document_processor.py /path/to/file1.pdf /path/to/file2.docx /path/to/file3.md

    # Process with limit
    python example_document_processor.py /path/to/documents/ 5
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import opencontext modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from opencontext.context_processing.processor.document_processor import DocumentProcessor
from opencontext.models.context import ContentFormat, ContextSource, RawContextProperties
from opencontext.utils.logging_utils import get_logger, setup_logging

# Initialize logging first
setup_logging({"level": "INFO", "log_path": None})  # Only console output for this example

logger = get_logger(__name__)

# Supported document extensions
DOCUMENT_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
    ".docx", ".doc", ".pptx", ".ppt",
    ".xlsx", ".xls", ".csv", ".jsonl",
    ".md", ".txt"
}


def scan_directory_for_documents(directory_path: str, limit: int = None) -> list[str]:
    """
    Scan a directory for document files.

    Args:
        directory_path: Path to the directory to scan
        limit: Maximum number of documents to return (None for all)

    Returns:
        List of document file paths
    """
    document_paths = []

    try:
        directory = Path(directory_path)
        if not directory.exists():
            print(f"Error: Directory does not exist: {directory_path}")
            return []

        if not directory.is_dir():
            print(f"Error: Not a directory: {directory_path}")
            return []

        # Scan for document files
        for file_path in sorted(directory.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in DOCUMENT_EXTENSIONS:
                document_paths.append(str(file_path))
                if limit and len(document_paths) >= limit:
                    break

        print(f"Found {len(document_paths)} documents")

    except Exception as e:
        print(f"Error scanning directory: {e}")

    return document_paths


def process_documents_example(document_paths: list[str]):
    """
    Process documents and extract content without storing in database.

    Args:
        document_paths: List of paths to document files
    """
    print("=" * 80)
    print("Document Processor - Process Various Document Formats")
    print("=" * 80)

    # Validate document paths
    valid_paths = []
    for path in document_paths:
        if os.path.exists(path):
            valid_paths.append(path)
        else:
            print(f"Warning: File not found: {path}")

    if len(valid_paths) == 0:
        print("\nNo valid document files found.")
        return

    print(f"\nProcessing {len(valid_paths)} documents...\n")

    # Initialize the document processor
    processor = DocumentProcessor()

    # Process each document
    processed_count = 0
    for i, document_path in enumerate(valid_paths, 1):
        print(f"\n[{i}/{len(valid_paths)}] Processing: {document_path}")
        print("-" * 80)

        # Determine content format based on file extension
        file_ext = Path(document_path).suffix.lower()
        if file_ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
            content_format = ContentFormat.IMAGE
        elif file_ext in {".pdf", ".docx", ".doc", ".pptx", ".ppt"}:
            content_format = ContentFormat.FILE
        elif file_ext in {".xlsx", ".xls", ".csv", ".jsonl"}:
            content_format = ContentFormat.FILE
        else:
            content_format = ContentFormat.FILE

        # Create RawContextProperties for the document
        raw_context = RawContextProperties(
            source=ContextSource.LOCAL_FILE,
            content_path=document_path,
            content_format=content_format,
            create_time=datetime.now(),
            content_text="",
        )

        # Check if processor can handle this file
        if not processor.can_process(raw_context):
            print(f"Error: Processor cannot handle this file type: {file_ext}")
            continue

        # Process the document (adds to queue)
        try:
            contexts = processor.real_process(raw_context)
            if contexts:
                print(f"Successfully queued document: {Path(document_path).name}")
                processed_count += 1
                chunk_result = []
                for context in contexts:
                    chunk_result.append(context.extracted_data.summary)
                    print('----------------chunk-------------\n')
                    print(f"{context.extracted_data.summary}")

                # Dump chunk_result to JSON file
                output_filename = f"{Path(document_path).stem}_chunks.json"
                output_path = Path(document_path).parent / output_filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(chunk_result, f, ensure_ascii=False, indent=2)
                print(f"\nChunk results saved to: {output_path}")

            else:
                print(f"Failed to queue document: {Path(document_path).name}")

        except Exception as e:
            print(f"Error processing document: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"Processing Summary")
    print("=" * 80)
    print(f"Total documents queued: {processed_count}/{len(valid_paths)}")
    print("\nNote: Documents are being processed in the background.")
    print("Check the storage for processed contexts after processing completes.")
    print("The processor uses async processing, so results will appear shortly.")

    # Give some time for processing to complete
    # Shutdown processor
    print("\nShutting down processor...")
    processor.shutdown(_graceful=True)
    print("Done!")



def main():
    """Main entry point for the example."""
    document_paths = []

    if len(sys.argv) > 1:
        input_path = sys.argv[1]

        # Check if it's a directory or file
        if os.path.isdir(input_path):
            # Scan directory for documents
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
            document_paths = scan_directory_for_documents(input_path, limit=limit)
        else:
            # Treat as individual file paths
            document_paths = sys.argv[1:]
    else:
        print("Usage:")
        print("  # Process documents from a directory")
        print("  python example_document_processor.py /path/to/documents/")
        print("")
        print("  # Process documents from a directory with limit")
        print("  python example_document_processor.py /path/to/documents/ 5")
        print("")
        print("  # Process specific files")
        print("  python example_document_processor.py file1.pdf file2.docx file3.md")
        print("")
        print("Supported formats:")
        print("  - Visual: PDF, DOCX, DOC, PPTX, PPT, PNG, JPG, JPEG, GIF, BMP, WEBP")
        print("  - Structured: XLSX, XLS, CSV, JSONL")
        print("  - Text: TXT, MD (Markdown)")
        return

    if not document_paths:
        print("No valid document files found.")
        return

    # Process the documents
    process_documents_example(document_paths)


if __name__ == "__main__":
    main()
