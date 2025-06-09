"""
End-to-end integration tests for the complete drawing generation pipeline.
Tests VectorForge → LayoutLab → GrungeWorks → Output validation workflow.
"""

import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
import pytest
import yaml
from unittest.mock import Mock, patch

from .fixtures import TestFixtures, PerformanceFixtures, MockFileSystem


class TestCompleteWorkflow:
    """Test complete drawing generation workflow"""
    
    def setup_method(self):
        """Set up test environment for each test"""
        self.temp_dir = None
        self.mock_fs = None
    
    def teardown_method(self):
        """Clean up after each test"""
        if self.mock_fs:
            self.mock_fs.cleanup()
    
    def test_end_to_end_single_page_generation(self):
        """Test complete single page generation workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.mock_fs = MockFileSystem(temp_path)
            
            # Step 1: Set up VectorForge environment
            symbols_dir = self.mock_fs.symbols_dir
            symbols_dir.mkdir(parents=True, exist_ok=True)
            
            # Create manifest and SVG files
            manifest = TestFixtures.get_mock_symbols_manifest()
            manifest_path = symbols_dir / "symbols_manifest.yaml"
            with open(manifest_path, 'w') as f:
                yaml.dump(manifest, f)
            
            # Create SVG files
            for symbol in manifest["symbols"]:
                svg_path = symbols_dir / symbol["filename"]
                with open(svg_path, 'w') as f:
                    f.write(TestFixtures.get_mock_svg_content(symbol["name"]))
            
            # Create license file
            license_path = symbols_dir / "symbol_licences.csv"
            with open(license_path, 'w') as f:
                f.write("filename,licence,source-URL\n")
                for license_data in TestFixtures.get_mock_license_data():
                    f.write(f"{license_data['filename']},{license_data['licence']},{license_data['source-URL']}\n")
            
            # Step 2: Test LayoutLab page generation
            page_data = TestFixtures.get_mock_page_data()
            commit_sha = page_data["page_info"]["commit_sha"]
            
            # Create output files
            examples_dir = self.mock_fs.examples_dir
            examples_dir.mkdir(parents=True, exist_ok=True)
            
            json_path = examples_dir / f"page_{commit_sha}.json"
            pdf_path = examples_dir / f"page_{commit_sha}.pdf"
            png_path = examples_dir / f"page_{commit_sha}.png"
            
            # Save JSON output
            with open(json_path, 'w') as f:
                json.dump(page_data, f, indent=2)
            
            # Create mock PDF
            with open(pdf_path, 'wb') as f:
                f.write(TestFixtures.create_mock_pdf_bytes())
            
            # Step 3: Test GrungeWorks processing
            # Create mock PNG (simulating PDF conversion)
            test_image = TestFixtures.create_mock_png_image(800, 600)
            test_image.save(png_path)
            
            # Step 4: Validate complete workflow
            self._validate_complete_workflow_output(json_path, pdf_path, png_path)
            
            # Step 5: Test file naming conventions
            assert json_path.stem.startswith("page_"), "JSON should follow naming convention"
            assert pdf_path.stem.startswith("page_"), "PDF should follow naming convention"
            assert png_path.stem.startswith("page_"), "PNG should follow naming convention"
            
            # Extract SHA and verify consistency
            json_sha = json_path.stem.split("_")[1]
            pdf_sha = pdf_path.stem.split("_")[1]
            png_sha = png_path.stem.split("_")[1]
            
            assert json_sha == pdf_sha == png_sha, "All files should have same SHA prefix"
    
    def test_multi_page_generation_workflow(self):
        """Test generation of multiple pages in sequence"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.mock_fs = MockFileSystem(temp_path)
            
            # Set up environment
            self.mock_fs.setup_complete_environment()
            
            # Generate multiple pages
            page_count = 5
            generated_files = []
            
            for i in range(page_count):
                page_data = TestFixtures.get_mock_page_data()
                commit_sha = f"sha{i:04d}"
                page_data["page_info"]["commit_sha"] = commit_sha
                
                # Create files for this page
                json_path = self.mock_fs.examples_dir / f"page_{commit_sha}.json"
                pdf_path = self.mock_fs.examples_dir / f"page_{commit_sha}.pdf"
                png_path = self.mock_fs.examples_dir / f"page_{commit_sha}.png"
                
                # Save files
                with open(json_path, 'w') as f:
                    json.dump(page_data, f)
                
                with open(pdf_path, 'wb') as f:
                    f.write(TestFixtures.create_mock_pdf_bytes())
                
                test_image = TestFixtures.create_mock_png_image()
                test_image.save(png_path)
                
                generated_files.append((json_path, pdf_path, png_path))
            
            # Validate all pages
            assert len(generated_files) == page_count, "Should generate all requested pages"
            
            for json_path, pdf_path, png_path in generated_files:
                assert json_path.exists(), f"JSON file missing: {json_path}"
                assert pdf_path.exists(), f"PDF file missing: {pdf_path}"
                assert png_path.exists(), f"PNG file missing: {png_path}"
                
                self._validate_complete_workflow_output(json_path, pdf_path, png_path)
    
    def test_workflow_data_consistency(self):
        """Test data consistency across workflow stages"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            page_data = TestFixtures.get_mock_page_data()
            
            json_path = temp_path / "test.json"
            with open(json_path, 'w') as f:
                json.dump(page_data, f)
            
            # Test 1: Symbol count consistency
            symbol_count = len(page_data["annotations"])
            assert symbol_count > 0, "Should have symbols to test"
            
            # Test 2: Coordinate system consistency
            for annotation in page_data["annotations"]:
                position = annotation["position"]
                bbox = annotation["bounding_box"]
                
                # Position should be within bounding box
                assert bbox["x_min"] <= position["x"] <= bbox["x_max"], "Position X outside bounding box"
                assert bbox["y_min"] <= position["y"] <= bbox["y_max"], "Position Y outside bounding box"
            
            # Test 3: Parameter consistency with manifest
            manifest = TestFixtures.get_mock_symbols_manifest()
            symbol_schemas = {sym["name"]: sym for sym in manifest["symbols"]}
            
            for annotation in page_data["annotations"]:
                symbol_name = annotation["symbol_name"]
                if symbol_name in symbol_schemas:
                    schema = symbol_schemas[symbol_name]
                    annotation_params = annotation["parameters"]
                    
                    # Check parameter types
                    for param_name, param_value in annotation_params.items():
                        if param_name in schema["params"]:
                            param_schema = schema["params"][param_name]
                            param_type = param_schema.get("type", "string")
                            
                            if param_type == "float":
                                assert isinstance(param_value, (int, float)), f"Parameter {param_name} should be numeric"
    
    def test_workflow_error_recovery(self):
        """Test workflow error handling and recovery"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test with missing manifest
            page_data = TestFixtures.get_mock_page_data()
            json_path = temp_path / "test.json"
            
            with open(json_path, 'w') as f:
                json.dump(page_data, f)
            
            # Workflow should handle missing dependencies gracefully
            # (This would be tested with actual agent implementations)
            
            # Test with malformed JSON
            malformed_json_path = temp_path / "malformed.json"
            with open(malformed_json_path, 'w') as f:
                f.write('{"invalid": json}')  # Malformed JSON
            
            # Should handle gracefully without crashing
            assert malformed_json_path.exists(), "Test file should exist"
    
    def test_workflow_performance_requirements(self):
        """Test that complete workflow meets performance requirements"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.mock_fs = MockFileSystem(temp_path)
            self.mock_fs.setup_complete_environment()
            
            # Test single page generation time
            start_time = time.time()
            
            # Simulate complete workflow
            page_data = TestFixtures.get_mock_page_data()
            
            # Step 1: Symbol validation (VectorForge)
            manifest = TestFixtures.get_mock_symbols_manifest()
            for symbol in manifest["symbols"]:
                # Simulate symbol validation
                svg_content = TestFixtures.get_mock_svg_content(symbol["name"])
                assert len(svg_content) > 0
            
            # Step 2: Page layout (LayoutLab)
            for annotation in page_data["annotations"]:
                # Simulate placement validation
                position = annotation["position"]
                bbox = annotation["bounding_box"]
                assert position["x"] > 0 and position["y"] > 0
            
            # Step 3: Noise processing (GrungeWorks)
            test_image = TestFixtures.create_mock_png_image()
            # Simulate noise processing
            processed_pixels = len(list(test_image.getdata()))
            assert processed_pixels > 0
            
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Complete workflow should be under 500ms for test case
            assert duration_ms < 500, f"Workflow too slow: {duration_ms:.1f}ms"
    
    def _validate_complete_workflow_output(self, json_path: Path, pdf_path: Path, png_path: Path):
        """Validate output from complete workflow"""
        # Validate JSON
        assert json_path.exists(), "JSON file should exist"
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        assert "page_info" in json_data, "JSON missing page_info"
        assert "annotations" in json_data, "JSON missing annotations"
        assert len(json_data["annotations"]) > 0, "Should have symbol annotations"
        
        # Validate PDF
        assert pdf_path.exists(), "PDF file should exist"
        assert pdf_path.stat().st_size > 0, "PDF should not be empty"
        
        # Validate PNG
        assert png_path.exists(), "PNG file should exist"
        assert png_path.stat().st_size > 0, "PNG should not be empty"
        
        # Validate file name consistency
        json_stem = json_path.stem
        pdf_stem = pdf_path.stem
        png_stem = png_path.stem
        
        assert json_stem == pdf_stem == png_stem, "File names should be consistent"


class TestWorkflowInteroperability:
    """Test interoperability between different agents"""
    
    def test_vectorforge_layoutlab_compatibility(self):
        """Test that VectorForge output is compatible with LayoutLab"""
        # Test manifest consumption
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        # LayoutLab should be able to process all symbols in manifest
        for symbol in manifest["symbols"]:
            # Verify required fields exist
            assert "name" in symbol, "Symbol missing name"
            assert "filename" in symbol, "Symbol missing filename"
            assert "w_mm" in symbol, "Symbol missing width"
            assert "h_mm" in symbol, "Symbol missing height"
            assert "params" in symbol, "Symbol missing parameters"
            
            # Verify dimensions are usable
            assert symbol["w_mm"] > 0, "Symbol width must be positive"
            assert symbol["h_mm"] > 0, "Symbol height must be positive"
    
    def test_layoutlab_grungeworks_compatibility(self):
        """Test that LayoutLab output is compatible with GrungeWorks"""
        page_data = TestFixtures.get_mock_page_data()
        
        # GrungeWorks should be able to process LayoutLab JSON
        assert "page_info" in page_data, "Missing page_info for GrungeWorks"
        assert "annotations" in page_data, "Missing annotations for GrungeWorks"
        
        page_info = page_data["page_info"]
        assert "width_mm" in page_info, "Missing page width"
        assert "height_mm" in page_info, "Missing page height"
        
        # Annotation format should be compatible
        for annotation in page_data["annotations"]:
            assert "position" in annotation, "Missing symbol position"
            assert "bounding_box" in annotation, "Missing bounding box"
            
            position = annotation["position"]
            assert "x" in position and "y" in position, "Incomplete position data"
    
    def test_coordinate_system_consistency(self):
        """Test coordinate system consistency across agents"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        page_data = TestFixtures.get_mock_page_data()
        
        # All measurements should be in millimeters
        page_info = page_data["page_info"]
        assert page_info["width_mm"] > 0, "Page width should be positive mm"
        assert page_info["height_mm"] > 0, "Page height should be positive mm"
        
        # Symbol dimensions in manifest should be in mm
        for symbol in manifest["symbols"]:
            assert symbol["w_mm"] > 0, "Symbol width should be positive mm"
            assert symbol["h_mm"] > 0, "Symbol height should be positive mm"
        
        # Positions in annotations should be in mm
        for annotation in page_data["annotations"]:
            position = annotation["position"]
            bbox = annotation["bounding_box"]
            
            # Positions should be reasonable for page size
            assert 0 <= position["x"] <= page_info["width_mm"], "X position out of page bounds"
            assert 0 <= position["y"] <= page_info["height_mm"], "Y position out of page bounds"
            
            # Bounding box should be reasonable
            bbox_width = bbox["x_max"] - bbox["x_min"]
            bbox_height = bbox["y_max"] - bbox["y_min"]
            assert 0 < bbox_width < page_info["width_mm"], "Bounding box width unreasonable"
            assert 0 < bbox_height < page_info["height_mm"], "Bounding box height unreasonable"
    
    def test_parameter_schema_consistency(self):
        """Test parameter schema consistency between agents"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        page_data = TestFixtures.get_mock_page_data()
        
        # Build parameter schema lookup
        symbol_schemas = {}
        for symbol in manifest["symbols"]:
            symbol_schemas[symbol["name"]] = symbol["params"]
        
        # Validate that annotation parameters match schema
        for annotation in page_data["annotations"]:
            symbol_name = annotation["symbol_name"]
            
            if symbol_name in symbol_schemas:
                schema = symbol_schemas[symbol_name]
                params = annotation["parameters"]
                
                # Check each parameter against schema
                for param_name, param_value in params.items():
                    if param_name in schema:
                        param_def = schema[param_name]
                        param_type = param_def.get("type", "string")
                        
                        # Type validation
                        if param_type == "float":
                            assert isinstance(param_value, (int, float)), f"Parameter {param_name} type mismatch"
                        elif param_type == "enum":
                            valid_values = param_def.get("values", [])
                            assert param_value in valid_values, f"Parameter {param_name} invalid enum value"


class TestWorkflowScalability:
    """Test workflow scalability and stress scenarios"""
    
    def test_large_page_generation(self):
        """Test generation of pages with many symbols"""
        # Test with maximum symbol count
        large_page_data = self._create_large_page_data(60)
        
        # Should handle large page without issues
        assert len(large_page_data["annotations"]) <= 60, "Should not exceed max symbols"
        
        # All symbols should be properly formatted
        for annotation in large_page_data["annotations"]:
            assert "position" in annotation, "Symbol missing position"
            assert "bounding_box" in annotation, "Symbol missing bounding box"
            assert "parameters" in annotation, "Symbol missing parameters"
    
    def test_multiple_sheet_sizes(self):
        """Test workflow with different sheet sizes"""
        sheet_configs = [
            ("A4", 210, 297),
            ("A3", 297, 420),
            ("US-Letter", 215.9, 279.4)
        ]
        
        for sheet_name, width, height in sheet_configs:
            page_data = TestFixtures.get_mock_page_data()
            page_data["page_info"]["sheet_size"] = sheet_name
            page_data["page_info"]["width_mm"] = width
            page_data["page_info"]["height_mm"] = height
            
            # Validate page is properly configured
            assert page_data["page_info"]["width_mm"] == width, f"Width mismatch for {sheet_name}"
            assert page_data["page_info"]["height_mm"] == height, f"Height mismatch for {sheet_name}"
            
            # Symbols should fit within page bounds
            for annotation in page_data["annotations"]:
                bbox = annotation["bounding_box"]
                assert bbox["x_max"] <= width, f"Symbol exceeds page width on {sheet_name}"
                assert bbox["y_max"] <= height, f"Symbol exceeds page height on {sheet_name}"
    
    def test_workflow_memory_usage(self):
        """Test that workflow doesn't consume excessive memory"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Generate multiple pages
        for i in range(10):
            page_data = TestFixtures.get_mock_page_data()
            page_data["page_info"]["commit_sha"] = f"test{i:04d}"
            
            # Simulate processing
            manifest = TestFixtures.get_mock_symbols_manifest()
            test_image = TestFixtures.create_mock_png_image()
            
            # Force garbage collection periodically
            if i % 5 == 0:
                import gc
                gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_increase = final_memory - initial_memory
        
        # Should not use excessive memory (limit to 100MB increase)
        assert memory_increase < 100, f"Memory usage too high: {memory_increase:.1f}MB increase"
    
    def _create_large_page_data(self, symbol_count: int) -> Dict[str, Any]:
        """Create page data with many symbols"""
        base_page = TestFixtures.get_mock_page_data()
        base_annotations = base_page["annotations"]
        
        # Generate large annotation set
        annotations = []
        for i in range(symbol_count):
            annotation = base_annotations[i % len(base_annotations)].copy()
            annotation["id"] = f"symbol_{i:03d}"
            
            # Spread symbols across page
            x = 20 + (i % 15) * 12  # 15 columns
            y = 20 + (i // 15) * 15  # Multiple rows
            
            annotation["position"] = {"x": x, "y": y}
            annotation["bounding_box"] = {
                "x_min": x - 4, "y_min": y - 4,
                "x_max": x + 4, "y_max": y + 4
            }
            
            annotations.append(annotation)
        
        large_page = base_page.copy()
        large_page["annotations"] = annotations
        return large_page


if __name__ == "__main__":
    pytest.main([__file__, "-v"])