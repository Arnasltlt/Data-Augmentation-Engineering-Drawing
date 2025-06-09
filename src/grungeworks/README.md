# GrungeWorks Agent

**Scanner-style noise and rasterization agent for engineering drawings**

GrungeWorks is an autonomous AI agent responsible for converting vector PDF pages from LayoutLab into realistic 300 DPI PNG images with configurable scanner-style noise effects.

## Features

### Core Functionality
- **PDF to PNG Conversion**: High-quality 300 DPI rasterization using PyMuPDF or pdf2image
- **Configurable Noise Pipeline**: 4 preset noise levels (0-3) with different filter combinations
- **JSON Coordinate Preservation**: Ensures symbol alignment is maintained after processing
- **Debug Mode**: Saves intermediate images for pipeline inspection

### Noise Filters

#### 1. Gaussian Blur Filter
- Simulates scanner optical blur
- Configurable sigma (0-1 px recommended)
- Applied early in pipeline to simulate capture blur

#### 2. JPEG Artifact Filter
- Simulates compression artifacts from document scanning
- Quality range: 50-90% (default: 75%)
- Re-encodes image to introduce realistic compression noise

#### 3. Skew & Perspective Warp Filter
- Simulates scanner misalignment and paper positioning
- Maximum skew: ±3° rotation
- Maximum perspective: ±2% warp factor
- Uses OpenCV geometric transformations

#### 4. Coffee Stain Filter (Optional)
- Adds realistic document aging effects
- Configurable number of stains and opacity
- Brownish elliptical overlays with transparency

#### 5. Handwriting Filter (Optional)
- Adds handwritten annotations (EN/DE random strings)
- Simulates markup and approval stamps
- Slightly rotated text for realistic appearance

## Noise Level Presets

| Level | Description | Filters Applied |
|-------|-------------|-----------------|
| 0     | No noise    | None (clean conversion) |
| 1     | Light       | Gaussian blur (σ=0.3) + JPEG (quality=85) |
| 2     | Medium      | Gaussian blur (σ=0.5) + JPEG (quality=75) + Skew (±1°, 1% perspective) |
| 3     | Heavy       | Gaussian blur (σ=0.8) + JPEG (quality=60) + Skew (±2°, 1.5% perspective) |

## Usage

### Command Line Interface

```bash
# Process single PDF file
python -m grungeworks.cli input.pdf --noise-level 2

# Process directory of PDF files
python -m grungeworks.cli /path/to/pdfs/ --noise-level 1 --debug

# Custom DPI and output directory
python -m grungeworks.cli input.pdf --noise-level 3 --dpi 600 --output-dir ./output/

# Reproducible noise with seed
python -m grungeworks.cli input.pdf --noise-level 2 --seed 12345
```

### Python API

```python
from grungeworks import GrungeWorksAgent

# Initialize agent
agent = GrungeWorksAgent(debug=True)

# Process single page
success = agent.process_page(
    pdf_path="page_abc12345.pdf",
    json_path="page_abc12345.json", 
    noise_level=2
)

# Manual filter application
from grungeworks.filters import GaussianBlurFilter, JPEGArtifactFilter
from PIL import Image

img = Image.open("input.png")
blur_filter = GaussianBlurFilter(sigma=0.5)
jpeg_filter = JPEGArtifactFilter(quality=70)

processed = blur_filter.apply(img)
processed = jpeg_filter.apply(processed)
processed.save("output.png")
```

## File Naming Convention

GrungeWorks expects and produces files following the project's SHA-based naming:

- Input: `page_<sha8>_*.pdf` + `page_<sha8>.json`
- Output: `page_<sha8>.png`

Where `<sha8>` is the first 8 characters of the Git commit SHA for traceability.

## Coordinate Alignment Verification

The agent includes built-in verification to ensure that symbol coordinates in the JSON ground truth still align with the processed PNG:

- Validates JSON structure and symbol count
- Checks PNG dimensions are reasonable (>100x100 px)
- Converts mm coordinates to pixels (300 DPI: 1mm ≈ 3.78px)
- Warns if symbol coordinates are out of image bounds

## Quality Assurance

### SSIM Regression Testing
- Structural Similarity Index Measurement between original and processed images
- Ensures noise doesn't destroy critical structural information
- Minimum threshold: 0.8 SSIM for acceptance

### Alignment Testing
- Computer vision-based centroid detection
- Maximum allowed shift: 1 pixel for symbol positions
- Uses OpenCV contour detection and template matching

## Dependencies

```txt
numpy>=1.21.0
Pillow>=9.0.0
opencv-python>=4.8.0
PyMuPDF>=1.23.0
pdf2image>=3.1.0
scikit-image>=0.21.0
```

## Environment Variables

- `NOISE_SEED`: Random seed for reproducible noise (default: 42)
- `DEBUG`: Set to "1" to enable debug image output

## Milestones

- **Day 6**: ✅ Core filters integrated; `--noise-level 1` functional
- **Day 15**: ✅ Full preset stack; SSIM regression test framework ready

## Architecture

```
grungeworks/
├── __init__.py              # Package exports
├── grungeworks_agent.py     # Main agent class
├── filters.py               # Noise filter implementations
├── cli.py                   # Command-line interface
└── README.md               # This documentation
```

## Testing

```bash
# Run alignment verification tests
python -m pytest tests/test_noise_alignment.py

# Run example demonstration
python examples/grungeworks_example.py

# Manual verification with debug output
python -m grungeworks.cli sample.pdf --noise-level 2 --debug
```

## Integration with Project Pipeline

GrungeWorks fits into the larger drawing generation pipeline:

1. **VectorForge** → Creates SVG symbol library
2. **LayoutLab** → Generates vector PDF pages + JSON ground truth
3. **GrungeWorks** → Converts PDFs to realistic scanner-style PNGs
4. **QualityGate** → Validates output quality and alignment

The agent ensures that the final PNG images look like realistic scanned engineering drawings while preserving the precise coordinate information needed for machine learning training datasets.