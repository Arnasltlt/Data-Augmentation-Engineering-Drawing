"""Command-line interface for GrungeWorks agent."""

import argparse
import logging
import os
import sys
from pathlib import Path

from .grungeworks_agent import GrungeWorksAgent


def setup_logging(debug: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def find_pdf_json_pairs(input_dir: str) -> list[tuple]:
    """Find matching PDF and JSON file pairs.

    Args:
        input_dir: Directory to search for files

    Returns:
        List of (pdf_path, json_path) tuples
    """
    input_path = Path(input_dir)
    pairs = []

    # Look for page_<sha>_*.pdf files
    for pdf_file in input_path.glob("page_*.pdf"):
        # Extract SHA prefix from filename
        name_parts = pdf_file.stem.split("_")
        if len(name_parts) >= 2:
            sha_prefix = name_parts[1]

            # Look for corresponding JSON file
            json_file = input_path / f"page_{sha_prefix}.json"
            if json_file.exists():
                pairs.append((str(pdf_file), str(json_file)))
            else:
                logging.warning(f"No JSON file found for {pdf_file}")

    return pairs


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GrungeWorks - Add scanner-style noise to PDF drawings"
    )

    parser.add_argument(
        "input", help="Input PDF file or directory containing PDF files"
    )

    parser.add_argument(
        "--noise-level",
        type=int,
        choices=[0, 1, 2, 3],
        default=1,
        help="Noise level preset (0=none, 1=light, 2=medium, 3=heavy)",
    )

    parser.add_argument(
        "--output-dir", help="Output directory (default: same as input)"
    )

    parser.add_argument(
        "--dpi", type=int, default=300, help="DPI for PDF rasterization (default: 300)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (saves intermediate images)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible noise (overrides NOISE_SEED env var)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    # Set random seed if provided
    if args.seed is not None:
        os.environ["NOISE_SEED"] = str(args.seed)

    # Initialize agent
    agent = GrungeWorksAgent(debug=args.debug)

    # Determine input files
    input_path = Path(args.input)

    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        # Single PDF file
        pdf_path = str(input_path)
        json_path = str(input_path.with_suffix(".json"))

        if not Path(json_path).exists():
            logger.error(f"JSON file not found: {json_path}")
            sys.exit(1)

        pairs = [(pdf_path, json_path)]

    elif input_path.is_dir():
        # Directory with multiple files
        pairs = find_pdf_json_pairs(str(input_path))

        if not pairs:
            logger.error(f"No PDF/JSON pairs found in {input_path}")
            sys.exit(1)

    else:
        logger.error(f"Input must be a PDF file or directory: {args.input}")
        sys.exit(1)

    # Process each PDF/JSON pair
    success_count = 0
    total_count = len(pairs)

    logger.info(f"Processing {total_count} file(s) with noise level {args.noise_level}")

    for pdf_path, json_path in pairs:
        logger.info(f"Processing: {Path(pdf_path).name}")

        try:
            if agent.process_page(pdf_path, json_path, args.noise_level):
                success_count += 1
                logger.info(f"✓ Successfully processed {Path(pdf_path).name}")
            else:
                logger.error(f"✗ Failed to process {Path(pdf_path).name}")

        except Exception as e:
            logger.error(f"✗ Error processing {Path(pdf_path).name}: {e}")

    # Print summary
    logger.info(
        f"Completed: {success_count}/{total_count} files processed successfully"
    )

    if success_count < total_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
