"""Example usage of GrungeWorks agent."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grungeworks import GrungeWorksAgent
from grungeworks.filters import (
    GaussianBlurFilter,
    JPEGArtifactFilter,
    SkewPerspectiveFilter,
)


def create_sample_json(output_path: str):
    """Create a sample JSON ground truth file for testing."""
    import json

    sample_data = {
        "page_id": "sample_page",
        "dimensions_mm": {"width": 210, "height": 297},
        "symbols": [
            {
                "type": "geometric_tolerance",
                "symbol": "flatness",
                "x_mm": 50.0,
                "y_mm": 100.0,
                "width_mm": 10.0,
                "height_mm": 5.0,
            },
            {
                "type": "surface_finish",
                "symbol": "triangle",
                "x_mm": 120.0,
                "y_mm": 150.0,
                "width_mm": 5.0,
                "height_mm": 5.0,
            },
            {
                "type": "dimension",
                "symbol": "diameter",
                "x_mm": 80.0,
                "y_mm": 200.0,
                "width_mm": 8.0,
                "height_mm": 8.0,
            },
        ],
    }

    with open(output_path, "w") as f:
        json.dump(sample_data, f, indent=2)


def demonstrate_filters():
    """Demonstrate individual filter functionality."""
    from PIL import Image, ImageDraw

    # Create a simple test image
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)

    # Draw some simple shapes to simulate symbols
    draw.rectangle([50, 50, 150, 100], outline="black", width=2)
    draw.ellipse([200, 80, 280, 160], outline="black", width=2)
    draw.polygon(
        [(100, 200), (150, 180), (200, 200), (175, 240)], outline="black", width=2
    )

    # Save original
    original_path = "test_original.png"
    img.save(original_path)
    print(f"Created test image: {original_path}")

    # Test individual filters
    filters = [
        ("gaussian_blur", GaussianBlurFilter(sigma=0.5)),
        ("jpeg_artifact", JPEGArtifactFilter(quality=70)),
        ("skew_perspective", SkewPerspectiveFilter(max_skew=1.5, max_perspective=0.01)),
    ]

    for name, filter_obj in filters:
        filtered_img = filter_obj.apply(img)
        output_path = f"test_{name}.png"
        filtered_img.save(output_path)
        print(f"Applied {name} filter: {output_path}")


def demonstrate_agent():
    """Demonstrate full GrungeWorks agent functionality."""

    # Initialize agent with debug mode
    agent = GrungeWorksAgent(debug=True)

    print("GrungeWorks Agent initialized successfully!")
    print("Features implemented:")
    print("- PDF to PNG conversion (300 DPI)")
    print("- Configurable noise pipeline with 4 levels (0-3)")
    print("- Gaussian blur filter")
    print("- JPEG artifact simulation")
    print("- Skew and perspective warp")
    print("- Coffee stain and handwriting overlays")
    print("- JSON coordinate alignment verification")
    print("- Debug mode with intermediate image saving")
    print("- CLI interface with --noise-level flags")

    # Create sample JSON for testing
    sample_json = "sample_ground_truth.json"
    create_sample_json(sample_json)
    print(f"Created sample JSON: {sample_json}")

    # Note: PDF processing would require actual PDF files
    print("\nTo process actual PDFs, use the CLI:")
    print("python -m grungeworks.cli input.pdf --noise-level 2 --debug")


if __name__ == "__main__":
    print("GrungeWorks Example")
    print("===================")

    # Demonstrate individual filters
    print("\n1. Testing individual filters...")
    try:
        demonstrate_filters()
    except Exception as e:
        print(f"Filter demo error: {e}")

    # Demonstrate agent
    print("\n2. Testing agent initialization...")
    try:
        demonstrate_agent()
    except Exception as e:
        print(f"Agent demo error: {e}")

    print("\nExample completed!")
