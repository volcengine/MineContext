import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path to allow sibling imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from opencontext.context_capture.web_link_capture import WebLinkCapture
from opencontext.context_processing.processor.document_processor import DocumentProcessor
from opencontext.utils.logging_utils import setup_logging


def main(url: str, mode: str):
    """
    Initializes components, captures a web link, and processes the result.
    """
    setup_logging({"level": "INFO"})
    logger = logging.getLogger(__name__)

    # 1. Initialize components
    logger.info(f"Initializing WebLinkCapture (mode: {mode}) and DocumentProcessor...")
    web_link_capturer = WebLinkCapture()
    document_processor = DocumentProcessor()

    # Initialize with configuration for the selected mode
    capture_config = {"mode": mode}
    web_link_capturer.initialize(capture_config)
    document_processor.initialize({})

    # Start the capturer component (part of the component lifecycle)
    web_link_capturer.start()

    logger.info(f"Submitting URL for capture: {url}")

    # 2. Capture the URL by passing it as a list to the capture method
    raw_contexts = web_link_capturer.capture(urls=[url])

    if not raw_contexts:
        logger.error("Failed to capture any context from the URL.")
        web_link_capturer.stop()
        return

    logger.info(f"Successfully captured {len(raw_contexts)} raw context(s) as {mode.upper()}.")

    # 3. Process the captured file context
    for raw_context in raw_contexts:
        # Check if the document processor can handle this type of context
        if document_processor.can_process(raw_context):
            logger.info(f"Processing content from: {raw_context.content_path}")
            processed_contexts = document_processor.real_process(raw_context)

            if processed_contexts:
                for p_ctx in processed_contexts:
                    # Print out some of the extracted data
                    logger.info("=" * 20 + " Processed Context " + "=" * 20)
                    extracted_data = p_ctx.extracted_data
                    logger.info(f"Title: {extracted_data.title}")
                    logger.info(f"Summary: {extracted_data.summary}")
                    logger.info(f"Keywords: {extracted_data.keywords}")
                    logger.info(f"Doc ID: {p_ctx.id}")
                    logger.info("=" * 58)
            else:
                logger.warning("Document processor did not return any processed context.")
        else:
            logger.warning(
                f"Document processor cannot process this context source: {raw_context.source}"
            )

    # Stop the component
    web_link_capturer.stop()
    logger.info("Processing finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Example of capturing and processing a single web link."
    )
    parser.add_argument(
        "url", type=str, help="The URL to capture and process.", default="https://www.doubao.com"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="markdown",
        choices=["pdf", "markdown"],
        help="The capture mode ('pdf' or 'markdown').",
    )
    # args={}
    # args['url'] = 'https://www.doubao.com'
    # args['mode'] = 'markdown'

    main("https://zhuanlan.zhihu.com/p/1972449094321550376", "markdown")
