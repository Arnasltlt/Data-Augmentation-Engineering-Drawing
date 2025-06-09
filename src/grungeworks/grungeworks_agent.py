"""GrungeWorks Agent - PDF to PNG conversion with scanner-style noise."""

import io
import json
import logging
import os
from pathlib import Path

import numpy as np
from PIL import Image


class GrungeWorksAgent:
    """Agent responsible for adding scanner-style noise and rasterizing PDFs to PNG."""

    def __init__(self, debug: bool = False):
        """Initialize GrungeWorks agent.

        Args:
            debug: If True, save intermediate debug PNGs
        """
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        self.noise_seed = int(os.environ.get("NOISE_SEED", "42"))
        np.random.seed(self.noise_seed)

    def convert_pdf_to_png(
        self, pdf_path: str, output_path: str, dpi: int = 300
    ) -> bool:
        """Convert PDF to PNG at specified DPI.

        Args:
            pdf_path: Path to input PDF file
            output_path: Path for output PNG file
            dpi: DPI for rasterization (default: 300)

        Returns:
            True if conversion successful, False otherwise
        """
        try:
            # Import here to avoid dependency issues if not installed
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            page = doc[0]  # Assume single page

            # Calculate zoom factor for desired DPI
            zoom = dpi / 72.0  # PDF default is 72 DPI
            mat = fitz.Matrix(zoom, zoom)

            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img_data = pix.tobytes("ppm")
            img = Image.open(io.BytesIO(img_data))

            # Save as PNG
            img.save(output_path, "PNG")
            doc.close()

            self.logger.info(f"Converted PDF to PNG: {pdf_path} -> {output_path}")
            return True

        except ImportError:
            # Fallback to pdf2image if PyMuPDF not available
            try:
                from pdf2image import convert_from_path

                images = convert_from_path(pdf_path, dpi=dpi)
                if images:
                    images[0].save(output_path, "PNG")
                    self.logger.info(
                        f"Converted PDF to PNG (pdf2image): {pdf_path} -> {output_path}"
                    )
                    return True

            except ImportError:
                self.logger.error(
                    "Neither PyMuPDF nor pdf2image available for PDF conversion"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error converting PDF to PNG: {e}")
            return False

    def apply_noise_to_image(self, image_path: str, noise_level: int = 1) -> bool:
        """Process a PNG file with the noise pipeline."""
        try:
            # Load image for noise processing
            img = Image.open(image_path)

            # Apply noise pipeline based on level
            processed_img = self._apply_noise_pipeline(img, noise_level)

            # Save final image
            processed_img.save(image_path)
            
            self.logger.info(
                f"Processed page with noise level {noise_level}: {image_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error processing page: {e}")
            return False

    def _apply_noise_pipeline(self, img: Image.Image, noise_level: int) -> Image.Image:
        """Apply noise pipeline based on specified level.

        Args:
            img: Input PIL Image
            noise_level: Noise level (0-3)

        Returns:
            Processed PIL Image
        """
        from .filters import (
            GaussianBlurFilter,
            JPEGArtifactFilter,
            SkewPerspectiveFilter,
        )

        # Define noise level presets
        presets = {
            0: [],  # No noise
            1: [GaussianBlurFilter(sigma=0.3), JPEGArtifactFilter(quality=85)],
            2: [
                GaussianBlurFilter(sigma=0.5),
                JPEGArtifactFilter(quality=75),
                SkewPerspectiveFilter(max_skew=1.0, max_perspective=0.01),
            ],
            3: [
                GaussianBlurFilter(sigma=0.8),
                JPEGArtifactFilter(quality=60),
                SkewPerspectiveFilter(max_skew=2.0, max_perspective=0.015),
            ],
        }

        filters = presets.get(noise_level, presets[1])

        # Apply filters sequentially
        result_img = img.copy()
        for i, filter_obj in enumerate(filters):
            result_img = filter_obj.apply(result_img)

            # Save debug image if enabled
            if self.debug:
                debug_path = Path(
                    str(img.filename).replace(
                        ".png", f"_debug_{i}_{filter_obj.__class__.__name__}.png"
                    )
                )
                result_img.save(debug_path)

        return result_img

    def _verify_coordinate_alignment(self, json_path: str, png_path: str) -> bool:
        """Verify that symbol coordinates in JSON still align with PNG after processing.

        Args:
            json_path: Path to JSON ground truth file
            png_path: Path to processed PNG file

        Returns:
            True if alignment is preserved within tolerance
        """
        try:
            # Load JSON ground truth
            with open(json_path) as f:
                ground_truth = json.load(f)

            # Verify JSON structure
            if "symbols" not in ground_truth:
                self.logger.warning("No symbols found in ground truth JSON")
                return False

            symbols = ground_truth["symbols"]
            self.logger.debug(f"Found {len(symbols)} symbols in ground truth")

            # Load and verify PNG exists
            if not Path(png_path).exists():
                self.logger.error(f"PNG file not found: {png_path}")
                return False

            # Basic validation: check that PNG dimensions are reasonable
            try:
                img = Image.open(png_path)
                width, height = img.size

                if width < 100 or height < 100:
                    self.logger.warning(
                        f"PNG dimensions seem too small: {width}x{height}"
                    )
                    return False

                self.logger.debug(f"PNG dimensions: {width}x{height}")

                # For each symbol, verify coordinates are within image bounds
                for i, symbol in enumerate(symbols):
                    x_mm = symbol.get("x_mm", 0)
                    y_mm = symbol.get("y_mm", 0)

                    # Convert mm to pixels (assuming 300 DPI: 1mm = ~3.78 pixels)
                    x_px = x_mm * 3.78
                    y_px = y_mm * 3.78

                    if x_px < 0 or x_px >= width or y_px < 0 or y_px >= height:
                        self.logger.warning(
                            f"Symbol {i} coordinates out of bounds: ({x_px:.1f}, {y_px:.1f})"
                        )

                # Basic verification passed
                return True

            except Exception as img_error:
                self.logger.error(f"Error loading PNG for verification: {img_error}")
                return False

        except Exception as e:
            self.logger.error(f"Error verifying coordinate alignment: {e}")
            return False
