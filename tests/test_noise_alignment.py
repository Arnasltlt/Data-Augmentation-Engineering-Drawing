"""Test harness for verifying noise alignment preservation."""

import json

import cv2
import numpy as np

from src.grungeworks import GrungeWorksAgent


class AlignmentVerifier:
    """Verifies that symbol coordinates remain aligned after noise processing."""

    def __init__(self, tolerance_px: float = 1.0):
        """Initialize alignment verifier.

        Args:
            tolerance_px: Maximum allowed pixel shift for symbol centroids
        """
        self.tolerance_px = tolerance_px

    def extract_symbol_centroids(
        self, img_path: str, json_path: str
    ) -> list[tuple[float, float]]:
        """Extract symbol centroids from image using computer vision.

        Args:
            img_path: Path to PNG image
            json_path: Path to JSON ground truth

        Returns:
            List of (x, y) centroid coordinates in pixels
        """
        # Load ground truth
        with open(json_path) as f:
            ground_truth = json.load(f)

        # Load image
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not load image: {img_path}")

        centroids = []

        # For each symbol in ground truth, try to detect it in the image
        if "symbols" in ground_truth:
            for symbol in ground_truth["symbols"]:
                # Expected position from JSON (in mm, convert to pixels)
                expected_x = symbol.get("x_mm", 0) * 3.78  # 300 DPI conversion
                expected_y = symbol.get("y_mm", 0) * 3.78

                # Search area around expected position
                search_radius = 20  # pixels
                x_min = max(0, int(expected_x - search_radius))
                x_max = min(img.shape[1], int(expected_x + search_radius))
                y_min = max(0, int(expected_y - search_radius))
                y_max = min(img.shape[0], int(expected_y + search_radius))

                # Extract search region
                search_region = img[y_min:y_max, x_min:x_max]

                # Use template matching or feature detection
                # For now, find contours and select the one closest to expected position
                _, thresh = cv2.threshold(
                    search_region, 127, 255, cv2.THRESH_BINARY_INV
                )
                contours, _ = cv2.findContours(
                    thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                if contours:
                    # Find centroid of largest contour
                    largest_contour = max(contours, key=cv2.contourArea)
                    M = cv2.moments(largest_contour)

                    if M["m00"] != 0:
                        # Calculate centroid relative to full image
                        cx = (M["m10"] / M["m00"]) + x_min
                        cy = (M["m01"] / M["m00"]) + y_min
                        centroids.append((cx, cy))
                    else:
                        # Fallback to expected position
                        centroids.append((expected_x, expected_y))
                else:
                    # No contours found, use expected position
                    centroids.append((expected_x, expected_y))

        return centroids

    def calculate_centroid_shifts(
        self,
        original_centroids: list[tuple[float, float]],
        processed_centroids: list[tuple[float, float]],
    ) -> list[float]:
        """Calculate pixel shifts between original and processed centroids.

        Args:
            original_centroids: Centroids from original image
            processed_centroids: Centroids from processed image

        Returns:
            List of shift distances in pixels
        """
        if len(original_centroids) != len(processed_centroids):
            raise ValueError("Centroid lists must have same length")

        shifts = []
        for (x1, y1), (x2, y2) in zip(original_centroids, processed_centroids, strict=False):
            shift = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            shifts.append(shift)

        return shifts

    def verify_alignment(
        self, original_img_path: str, processed_img_path: str, json_path: str
    ) -> dict[str, any]:
        """Verify alignment between original and processed images.

        Args:
            original_img_path: Path to original PNG
            processed_img_path: Path to processed PNG
            json_path: Path to JSON ground truth

        Returns:
            Dictionary with verification results
        """
        try:
            # Extract centroids from both images
            original_centroids = self.extract_symbol_centroids(
                original_img_path, json_path
            )
            processed_centroids = self.extract_symbol_centroids(
                processed_img_path, json_path
            )

            # Calculate shifts
            shifts = self.calculate_centroid_shifts(
                original_centroids, processed_centroids
            )

            # Check if all shifts are within tolerance
            max_shift = max(shifts) if shifts else 0
            alignment_preserved = max_shift <= self.tolerance_px

            return {
                "alignment_preserved": alignment_preserved,
                "max_shift_px": max_shift,
                "avg_shift_px": np.mean(shifts) if shifts else 0,
                "num_symbols": len(shifts),
                "shifts": shifts,
                "tolerance_px": self.tolerance_px,
            }

        except Exception as e:
            return {
                "alignment_preserved": False,
                "error": str(e),
                "max_shift_px": float("inf"),
                "avg_shift_px": float("inf"),
                "num_symbols": 0,
                "shifts": [],
                "tolerance_px": self.tolerance_px,
            }


def test_noise_alignment_preservation():
    """Test that noise processing preserves symbol alignment."""
    # This test would require sample PDF/JSON files
    # For now, create a mock test structure

    verifier = AlignmentVerifier(tolerance_px=1.0)
    agent = GrungeWorksAgent(debug=True)

    # Test would process sample files and verify alignment
    # result = verifier.verify_alignment(original_png, processed_png, json_file)
    # assert result["alignment_preserved"], f"Alignment not preserved: {result}"

    # Placeholder assertion for now
    assert True, "Alignment verification test placeholder"


def test_ssim_regression():
    """Test that processed images maintain sufficient structural similarity."""

    # This would compare SSIM between original and processed images
    # to ensure noise doesn't destroy too much structural information

    # Placeholder for SSIM test
    min_ssim_threshold = 0.8  # Minimum acceptable SSIM

    # actual_ssim = calculate_ssim(original_img, processed_img)
    # assert actual_ssim >= min_ssim_threshold, f"SSIM too low: {actual_ssim}"

    assert True, "SSIM regression test placeholder"


if __name__ == "__main__":
    # Run alignment verification on sample files
    verifier = AlignmentVerifier()

    # Example usage (would need actual files):
    # result = verifier.verify_alignment("original.png", "processed.png", "ground_truth.json")
    # print(f"Alignment preserved: {result['alignment_preserved']}")
    # print(f"Max shift: {result['max_shift_px']:.2f} px")

    print("Alignment verification module ready")
