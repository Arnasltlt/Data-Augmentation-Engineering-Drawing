#!/usr/bin/env python3
"""
Symbol-Heavy Drawing Generator CLI
CLI-Ops Agent - Command-line interface for generating engineering drawings
"""

import argparse
import multiprocessing
import sys
import time
from pathlib import Path

# Optional import for parallel processing
try:
    import ray

    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    print("Warning: Ray not available, parallel processing disabled")


def main():
    parser = argparse.ArgumentParser(
        description="Generate symbol-heavy engineering drawings with GD&T annotations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-n",
        "--num-pages",
        type=int,
        default=1,
        help="Number of pages to generate (default: 1)",
    )

    parser.add_argument(
        "--sheet-size",
        choices=["A4", "A3", "Letter"],
        default="A4",
        help="Sheet size for generated drawings (default: A4)",
    )

    parser.add_argument(
        "--noise-level",
        type=int,
        choices=[0, 1, 2, 3],
        default=1,
        help="Noise level for grunge effects (0-3, default: 1)",
    )

    parser.add_argument(
        "--jobs",
        type=int,
        default=multiprocessing.cpu_count(),
        help=f"Number of parallel jobs (default: {multiprocessing.cpu_count()})",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="./out",
        help="Output directory for generated files (default: ./out)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.num_pages <= 0:
        print("Error: Number of pages must be positive", file=sys.stderr)
        sys.exit(1)

    if args.jobs <= 0:
        print("Error: Number of jobs must be positive", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.num_pages} page(s) with {args.jobs} parallel job(s)")
    print(f"Sheet size: {args.sheet_size}")
    print(f"Noise level: {args.noise_level}")
    print(f"Output directory: {output_dir.absolute()}")

    # TODO: Implement orchestration calls to LayoutLab and GrungeWorks
    generate_pages(args)


def generate_pages(args):
    """Generate the requested number of pages"""
    try:
        from src.grungeworks import GrungeWorksAgent
        from src.layoutlab import LayoutLabAgent
    except ImportError as e:
        print(f"Error: Required modules not found: {e}", file=sys.stderr)
        print(
            "Make sure LayoutLab and GrungeWorks agents are implemented",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir = Path(args.output_dir)

    if args.jobs == 1 or not RAY_AVAILABLE:
        # Sequential processing (or Ray not available)
        if args.jobs > 1 and not RAY_AVAILABLE:
            print("Warning: Ray not available, falling back to sequential processing")
        generate_pages_sequential(args, output_dir)
    else:
        # Parallel processing with Ray
        generate_pages_parallel(args, output_dir)


def generate_pages_sequential(args, output_dir: Path):
    """Generate pages sequentially (single-threaded)"""
    from src.grungeworks import GrungeWorksAgent
    from src.layoutlab import LayoutLabAgent

    # Initialize agents
    layoutlab = LayoutLabAgent(sheet_size=args.sheet_size)
    grungeworks = GrungeWorksAgent() if args.noise_level > 0 else None

    # Load symbols if available
    layoutlab.load_symbols()

    for i in range(args.num_pages):
        page_id = f"page_{i+1:04d}"
        print(f"Generating page {i+1}/{args.num_pages}: {page_id}")

        # Step 1: LayoutLab generates clean drawing
        drawing_data = layoutlab.generate_drawing(page_id, output_dir)

        # Step 2: GrungeWorks applies noise effects (if requested)
        if grungeworks and args.noise_level > 0:
            print(f"  Applying noise level {args.noise_level}")
            grungeworks.apply_effects(
                pdf_path=output_dir / f"{page_id}.pdf",
                output_dir=output_dir,
                noise_level=args.noise_level,
            )

        print(f"  Completed: {page_id}")

    print(f"Successfully generated {args.num_pages} page(s) in {output_dir}")


def generate_pages_parallel(args, output_dir: Path):
    """Generate pages in parallel using Ray"""
    if not RAY_AVAILABLE:
        print("Error: Ray not available for parallel processing")
        return generate_pages_sequential(args, output_dir)

    print(f"Initializing Ray with {args.jobs} workers...")

    # Initialize Ray
    ray.init(num_cpus=args.jobs, ignore_reinit_error=True)

    try:
        start_time = time.time()

        # Create remote function for page generation
        @ray.remote
        def generate_single_page(
            page_num: int, sheet_size: str, noise_level: int, output_dir_str: str
        ):
            """Generate a single page remotely"""
            from src.grungeworks import GrungeWorksAgent
            from src.layoutlab import LayoutLabAgent

            output_dir = Path(output_dir_str)
            page_id = f"page_{page_num:04d}"

            # Initialize agents
            layoutlab = LayoutLabAgent(sheet_size=sheet_size)
            grungeworks = GrungeWorksAgent() if noise_level > 0 else None

            # Load symbols
            layoutlab.load_symbols()

            # Generate drawing
            drawing_data = layoutlab.generate_drawing(page_id, output_dir)

            # Apply noise effects if requested
            if grungeworks and noise_level > 0:
                grungeworks.apply_effects(
                    pdf_path=output_dir / f"{page_id}.pdf",
                    output_dir=output_dir,
                    noise_level=noise_level,
                )

            return page_id

        # Submit all tasks
        futures = []
        for i in range(args.num_pages):
            future = generate_single_page.remote(
                i + 1, args.sheet_size, args.noise_level, str(output_dir.absolute())
            )
            futures.append(future)

        # Wait for all tasks to complete
        print(f"Processing {args.num_pages} page(s) in parallel...")
        completed_pages = ray.get(futures)

        elapsed_time = time.time() - start_time
        pages_per_second = args.num_pages / elapsed_time

        print(
            f"Successfully generated {args.num_pages} page(s) in {elapsed_time:.2f}s ({pages_per_second:.1f} pages/s)"
        )

    finally:
        ray.shutdown()


if __name__ == "__main__":
    main()
