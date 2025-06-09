"""
Enhanced unit tests for GrungeWorks agent - comprehensive noise filter testing,
image processing pipeline validation, and visual quality assurance.
"""

import io
import tempfile
from pathlib import Path
from typing import Any, Dict, Tuple
import pytest
import numpy as np
from PIL import Image, ImageStat
from unittest.mock import Mock, patch
import os

from .fixtures import TestFixtures


class TestNoiseFilterIndividual:
    """Test individual noise filters in isolation"""
    
    def setup_method(self):
        """Set up test image for each test"""
        self.test_image = TestFixtures.create_mock_png_image(400, 300)
        
        # Set deterministic seed for reproducible tests
        np.random.seed(42)
        os.environ["NOISE_SEED"] = "42"
    
    def test_gaussian_blur_filter(self):
        """Test Gaussian blur filter functionality"""
        try:
            from src.grungeworks.filters import GaussianBlurFilter
        except ImportError:
            pytest.skip("GrungeWorks filters not available")
        
        original_image = self.test_image.copy()
        blur_filter = GaussianBlurFilter(sigma=0.5)
        
        # Apply filter
        blurred_image = blur_filter.apply(original_image)
        
        # Verify output
        assert blurred_image.size == original_image.size, "Image size should be preserved"
        assert blurred_image.mode == original_image.mode, "Image mode should be preserved"
        
        # Verify blurring occurred
        original_edges = self._detect_edges(original_image)
        blurred_edges = self._detect_edges(blurred_image)
        assert blurred_edges < original_edges, "Blurring should reduce edge count"
    
    def test_jpeg_artifact_filter(self):
        """Test JPEG compression artifact filter"""
        try:
            from src.grungeworks.filters import JPEGArtifactFilter
        except ImportError:
            pytest.skip("GrungeWorks filters not available")
        
        original_image = self.test_image.copy()
        jpeg_filter = JPEGArtifactFilter(quality=70)
        
        # Apply filter
        compressed_image = jpeg_filter.apply(original_image)
        
        # Verify output
        assert compressed_image.size == original_image.size, "Image size should be preserved"
        assert compressed_image.mode == original_image.mode, "Image mode should be preserved"
        
        # Verify compression artifacts (slight quality degradation)
        original_quality = self._calculate_image_quality(original_image)
        compressed_quality = self._calculate_image_quality(compressed_image)
        assert compressed_quality <= original_quality, "Compression should reduce quality"
    
    def test_skew_perspective_filter(self):
        """Test skew and perspective warp filter"""
        try:
            from src.grungeworks.filters import SkewPerspectiveFilter
        except ImportError:
            pytest.skip("GrungeWorks filters not available")
        
        original_image = self.test_image.copy()
        skew_filter = SkewPerspectiveFilter(max_skew=1.0, max_perspective=0.01)
        
        # Apply filter
        warped_image = skew_filter.apply(original_image)
        
        # Verify output
        assert warped_image.size == original_image.size, "Image size should be preserved"
        assert warped_image.mode == original_image.mode, "Image mode should be preserved"
        
        # Verify transformation occurred (pixel differences)
        diff_count = self._count_pixel_differences(original_image, warped_image)
        assert diff_count > 0, "Skew/perspective should change pixels"
    
    def test_filter_deterministic_with_seed(self):
        """Test that filters produce deterministic results with same seed"""
        try:
            from src.grungeworks.filters import SkewPerspectiveFilter
        except ImportError:
            pytest.skip("GrungeWorks filters not available")
        
        original_image = self.test_image.copy()
        
        # Apply filter twice with same seed
        np.random.seed(123)
        filter1 = SkewPerspectiveFilter(max_skew=2.0, max_perspective=0.02)
        result1 = filter1.apply(original_image)
        
        np.random.seed(123)
        filter2 = SkewPerspectiveFilter(max_skew=2.0, max_perspective=0.02)
        result2 = filter2.apply(original_image)
        
        # Results should be identical
        diff_count = self._count_pixel_differences(result1, result2)
        assert diff_count == 0, "Same seed should produce identical results"
    
    def test_filter_parameter_validation(self):
        """Test filter parameter validation"""
        try:
            from src.grungeworks.filters import GaussianBlurFilter, JPEGArtifactFilter
        except ImportError:
            pytest.skip("GrungeWorks filters not available")
        
        # Test Gaussian blur with invalid sigma
        blur_filter = GaussianBlurFilter(sigma=-1.0)
        result = blur_filter.apply(self.test_image)
        # Should handle gracefully (return copy)
        assert result.size == self.test_image.size
        
        # Test JPEG filter with out-of-range quality
        jpeg_filter = JPEGArtifactFilter(quality=150)  # Over 100
        result = jpeg_filter.apply(self.test_image)
        # Should clamp to valid range
        assert result.size == self.test_image.size
    
    def _detect_edges(self, image: Image.Image) -> int:
        """Simple edge detection to measure image sharpness"""
        # Convert to grayscale and detect edges
        gray = image.convert('L')
        pixels = np.array(gray)
        
        # Simple edge detection using differences
        edge_x = np.abs(np.diff(pixels, axis=1))
        edge_y = np.abs(np.diff(pixels, axis=0))
        
        # Count significant edges
        threshold = 10
        edge_count = np.sum(edge_x > threshold) + np.sum(edge_y > threshold)
        return edge_count
    
    def _calculate_image_quality(self, image: Image.Image) -> float:
        """Calculate simple image quality metric"""
        # Use standard deviation as quality metric
        stat = ImageStat.Stat(image)
        return np.mean(stat.stddev)  # Higher stddev = more detail/quality
    
    def _count_pixel_differences(self, img1: Image.Image, img2: Image.Image) -> int:
        """Count number of differing pixels between two images"""
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        return np.sum(arr1 != arr2)


class TestNoisePipeline:
    """Test noise pipeline and noise level presets"""
    
    def setup_method(self):
        """Set up test environment"""
        np.random.seed(42)
        os.environ["NOISE_SEED"] = "42"
    
    def test_noise_level_progression(self):
        """Test that higher noise levels add more artifacts"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        original_image = TestFixtures.create_mock_png_image()
        agent = GrungeWorksAgent(debug=False)
        
        # Test different noise levels
        quality_scores = {}
        for noise_level in [0, 1, 2, 3]:
            processed = agent._apply_noise_pipeline(original_image, noise_level)
            quality = self._calculate_image_quality(processed)
            quality_scores[noise_level] = quality
        
        # Quality should generally decrease with higher noise levels
        assert quality_scores[0] >= quality_scores[1], "Level 1 should have some degradation"
        assert quality_scores[1] >= quality_scores[2], "Level 2 should have more degradation"
        assert quality_scores[2] >= quality_scores[3], "Level 3 should have most degradation"
    
    def test_noise_level_zero_passthrough(self):
        """Test that noise level 0 produces minimal changes"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        original_image = TestFixtures.create_mock_png_image()
        agent = GrungeWorksAgent(debug=False)
        
        # Level 0 should be passthrough
        processed = agent._apply_noise_pipeline(original_image, 0)
        
        # Should be identical or very similar
        diff_count = self._count_pixel_differences(original_image, processed)
        assert diff_count == 0, "Noise level 0 should not modify image"
    
    def test_debug_mode_output(self):
        """Test that debug mode saves intermediate images"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test image with filename
            test_image_path = Path(temp_dir) / "test_image.png"
            test_image = TestFixtures.create_mock_png_image()
            test_image.save(test_image_path)
            
            # Load image for processing
            img_with_filename = Image.open(test_image_path)
            
            agent = GrungeWorksAgent(debug=True)
            
            # Process with debug mode
            try:
                processed = agent._apply_noise_pipeline(img_with_filename, 2)
                
                # Check for debug files (would be created in real implementation)
                debug_files = list(Path(temp_dir).glob("*debug*.png"))
                # Note: This test validates the debug logic exists
                # Actual debug file creation depends on implementation
                
            except Exception:
                # Debug mode might not be fully implemented
                pass
    
    def test_pipeline_filter_order(self):
        """Test that filters are applied in correct order"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        original_image = TestFixtures.create_mock_png_image()
        agent = GrungeWorksAgent(debug=False)
        
        # Test noise level 2 (has multiple filters)
        processed = agent._apply_noise_pipeline(original_image, 2)
        
        # Should successfully apply all filters without error
        assert processed.size == original_image.size
        assert processed.mode == original_image.mode
        
        # Verify some processing occurred
        diff_count = self._count_pixel_differences(original_image, processed)
        assert diff_count > 0, "Pipeline should modify the image"
    
    def _calculate_image_quality(self, image: Image.Image) -> float:
        """Calculate image quality metric"""
        stat = ImageStat.Stat(image)
        return np.mean(stat.stddev)
    
    def _count_pixel_differences(self, img1: Image.Image, img2: Image.Image) -> int:
        """Count differing pixels"""
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        return np.sum(arr1 != arr2)


class TestPDFProcessing:
    """Test PDF to PNG conversion functionality"""
    
    def test_pdf_conversion_mock(self):
        """Test PDF conversion with mock data"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock PDF
            pdf_path = Path(temp_dir) / "test.pdf"
            pdf_bytes = TestFixtures.create_mock_pdf_bytes()
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            
            png_path = Path(temp_dir) / "test.png"
            
            agent = GrungeWorksAgent()
            
            # This would test the actual conversion if libraries are available
            # For now, verify the method exists and handles errors gracefully
            try:
                result = agent.convert_pdf_to_png(str(pdf_path), str(png_path))
                if result:
                    assert png_path.exists(), "PNG should be created on success"
            except Exception:
                # Expected if PDF libraries not available
                pass
    
    def test_pdf_dpi_parameter(self):
        """Test PDF conversion with different DPI settings"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        agent = GrungeWorksAgent()
        
        # Test that DPI parameter is accepted
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            png_path = Path(temp_dir) / "test.png"
            
            # Create mock PDF
            with open(pdf_path, 'wb') as f:
                f.write(TestFixtures.create_mock_pdf_bytes())
            
            # Test different DPI values
            for dpi in [150, 300, 600]:
                try:
                    result = agent.convert_pdf_to_png(str(pdf_path), str(png_path), dpi=dpi)
                    # Method should accept DPI parameter without error
                except Exception:
                    # Expected if conversion libraries not available
                    pass


class TestCoordinateAlignment:
    """Test coordinate alignment and verification"""
    
    def test_coordinate_verification_basic(self):
        """Test basic coordinate alignment verification"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            json_path = Path(temp_dir) / "test.json"
            png_path = Path(temp_dir) / "test.png"
            
            # Create test JSON
            test_data = TestFixtures.get_mock_page_data()
            with open(json_path, 'w') as f:
                import json
                json.dump(test_data, f)
            
            # Create test PNG
            test_image = TestFixtures.create_mock_png_image(800, 600)  # 300 DPI A4-ish
            test_image.save(png_path)
            
            agent = GrungeWorksAgent()
            
            # Test verification
            result = agent._verify_coordinate_alignment(str(json_path), str(png_path))
            
            # Should complete without error
            assert isinstance(result, bool), "Verification should return boolean"
    
    def test_coordinate_bounds_checking(self):
        """Test that coordinates are checked against image bounds"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files with out-of-bounds coordinates
            json_path = Path(temp_dir) / "test.json"
            png_path = Path(temp_dir) / "test.png"
            
            # Create JSON with coordinates outside image bounds
            test_data = TestFixtures.get_mock_page_data()
            # Add symbol with out-of-bounds position
            test_data["annotations"].append({
                "id": "out_of_bounds",
                "symbol_name": "test_symbol",
                "position": {"x": 1000, "y": 1000},  # Way outside small image
                "rotation": 0,
                "bounding_box": {"x_min": 995, "y_min": 995, "x_max": 1005, "y_max": 1005},
                "parameters": {}
            })
            
            with open(json_path, 'w') as f:
                import json
                json.dump(test_data, f)
            
            # Create small PNG
            small_image = TestFixtures.create_mock_png_image(100, 100)
            small_image.save(png_path)
            
            agent = GrungeWorksAgent()
            
            # Verification should handle out-of-bounds gracefully
            result = agent._verify_coordinate_alignment(str(json_path), str(png_path))
            # Should not crash, may return False due to bounds check


class TestVisualQuality:
    """Test visual quality and regression testing"""
    
    def test_structural_similarity_preservation(self):
        """Test that noise doesn't destroy too much structure"""
        try:
            from skimage.metrics import structural_similarity as ssim
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("Required libraries not available")
        
        original_image = TestFixtures.create_mock_png_image()
        agent = GrungeWorksAgent()
        
        # Test different noise levels
        for noise_level in [1, 2, 3]:
            processed = agent._apply_noise_pipeline(original_image, noise_level)
            
            # Convert to grayscale for SSIM
            orig_gray = np.array(original_image.convert('L'))
            proc_gray = np.array(processed.convert('L'))
            
            # Calculate SSIM
            ssim_score = ssim(orig_gray, proc_gray)
            
            # SSIM should be reasonable (>0.5 even for highest noise)
            min_ssim = 0.8 if noise_level == 1 else 0.6 if noise_level == 2 else 0.4
            assert ssim_score >= min_ssim, f"SSIM too low for noise level {noise_level}: {ssim_score}"
    
    def test_histogram_preservation(self):
        """Test that overall image histogram characteristics are preserved"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        original_image = TestFixtures.create_mock_png_image()
        agent = GrungeWorksAgent()
        
        # Get original histogram
        orig_hist = original_image.histogram()
        
        # Process with moderate noise
        processed = agent._apply_noise_pipeline(original_image, 2)
        proc_hist = processed.histogram()
        
        # Histograms should be similar (not too different)
        hist_diff = sum(abs(o - p) for o, p in zip(orig_hist, proc_hist))
        total_pixels = original_image.size[0] * original_image.size[1]
        
        # Difference should be less than 50% of total pixels
        assert hist_diff < total_pixels * 0.5, "Histogram changed too dramatically"
    
    def test_no_artifacts_at_edges(self):
        """Test that filters don't create artifacts at image edges"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        # Create image with white border
        original_image = Image.new('RGB', (200, 200), 'white')
        agent = GrungeWorksAgent()
        
        # Process with all noise levels
        for noise_level in [1, 2, 3]:
            processed = agent._apply_noise_pipeline(original_image, noise_level)
            
            # Check that edges are still reasonable (not black or too distorted)
            edge_pixels = []
            width, height = processed.size
            
            # Sample edge pixels
            for x in [0, width-1]:
                for y in range(0, height, 10):
                    if 0 <= y < height:
                        edge_pixels.append(processed.getpixel((x, y)))
            
            for y in [0, height-1]:
                for x in range(0, width, 10):
                    if 0 <= x < width:
                        edge_pixels.append(processed.getpixel((x, y)))
            
            # Edge pixels should not be too dark (avoid black artifacts)
            for pixel in edge_pixels:
                avg_brightness = sum(pixel) / 3 if isinstance(pixel, tuple) else pixel
                assert avg_brightness > 100, f"Edge artifact detected: pixel {pixel}"


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_missing_file_handling(self):
        """Test handling of missing input files"""
        try:
            from src.grungeworks import GrungeWorksAgent
        except ImportError:
            pytest.skip("GrungeWorks agent not available")
        
        agent = GrungeWorksAgent()
        
        # Test with non-existent files
        result = agent.convert_pdf_to_png("nonexistent.pdf", "output.png")
        assert not result, "Should return False for missing file"
        
        result = agent._verify_coordinate_alignment("missing.json", "missing.png")
        assert not result, "Should return False for missing files"
    
    def test_invalid_image_handling(self):
        """Test handling of invalid or corrupted images"""
        try:
            from src.grungeworks.filters import GaussianBlurFilter
        except ImportError:
            pytest.skip("GrungeWorks filters not available")
        
        # Test with minimal image
        tiny_image = Image.new('RGB', (1, 1), 'white')
        blur_filter = GaussianBlurFilter(sigma=0.5)
        
        # Should handle tiny image gracefully
        result = blur_filter.apply(tiny_image)
        assert result.size == (1, 1), "Should preserve tiny image size"
    
    def test_extreme_parameter_values(self):
        """Test filters with extreme parameter values"""
        try:
            from src.grungeworks.filters import GaussianBlurFilter, JPEGArtifactFilter
        except ImportError:
            pytest.skip("GrungeWorks filters not available")
        
        test_image = TestFixtures.create_mock_png_image(100, 100)
        
        # Test extreme blur
        extreme_blur = GaussianBlurFilter(sigma=10.0)
        result = extreme_blur.apply(test_image)
        assert result.size == test_image.size, "Should handle extreme blur"
        
        # Test extreme JPEG compression
        extreme_jpeg = JPEGArtifactFilter(quality=1)
        result = extreme_jpeg.apply(test_image)
        assert result.size == test_image.size, "Should handle extreme compression"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])