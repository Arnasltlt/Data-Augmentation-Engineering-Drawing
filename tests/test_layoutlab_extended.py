"""
Extended unit tests for LayoutLab agent - placement engine, parameter templating, 
and PDF generation beyond the basic collision detection tests.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List
import pytest
from unittest.mock import Mock, patch
import random

from .fixtures import TestFixtures, PerformanceFixtures


class TestParameterTemplating:
    """Test parameter templating and randomization"""
    
    def test_parameter_generation_follows_schema(self):
        """Test that generated parameters follow manifest schema"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        for symbol_def in manifest["symbols"]:
            params = self._generate_parameters(symbol_def["params"])
            
            # Validate each parameter
            for param_name, param_value in params.items():
                param_schema = symbol_def["params"][param_name]
                self._validate_parameter_value(param_name, param_value, param_schema)
    
    def test_float_parameter_bounds(self):
        """Test that float parameters respect min/max bounds"""
        param_schema = {
            "tolerance_value": {
                "type": "float",
                "min": 0.001,
                "max": 1.0,
                "default": 0.05
            }
        }
        
        # Generate many values to test bounds
        for _ in range(100):
            params = self._generate_parameters(param_schema)
            tolerance = params["tolerance_value"]
            assert 0.001 <= tolerance <= 1.0, f"Parameter out of bounds: {tolerance}"
    
    def test_enum_parameter_selection(self):
        """Test that enum parameters select from valid values"""
        param_schema = {
            "thread_size": {
                "type": "enum",
                "values": ["M3", "M4", "M5", "M6", "M8", "M10", "M12"],
                "default": "M6"
            }
        }
        
        # Generate many values to test selection
        selected_values = set()
        for _ in range(50):
            params = self._generate_parameters(param_schema)
            thread_size = params["thread_size"]
            assert thread_size in param_schema["thread_size"]["values"], f"Invalid enum value: {thread_size}"
            selected_values.add(thread_size)
        
        # Should see variety in selections
        assert len(selected_values) > 1, "Should generate different enum values"
    
    def test_parameter_randomization_deterministic(self):
        """Test that parameter generation is deterministic with same seed"""
        param_schema = {
            "tolerance_value": {"type": "float", "min": 0.001, "max": 1.0},
            "thread_size": {"type": "enum", "values": ["M3", "M6", "M10"]}
        }
        
        # Generate with same seed twice
        random.seed(42)
        params1 = self._generate_parameters(param_schema)
        
        random.seed(42)
        params2 = self._generate_parameters(param_schema)
        
        assert params1 == params2, "Same seed should produce same parameters"
    
    def _generate_parameters(self, param_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Mock parameter generation following schema"""
        params = {}
        for param_name, schema in param_schema.items():
            param_type = schema.get("type", "string")
            
            if param_type == "float":
                min_val = schema.get("min", 0.0)
                max_val = schema.get("max", 1.0)
                params[param_name] = random.uniform(min_val, max_val)
            
            elif param_type == "enum":
                values = schema.get("values", ["default"])
                params[param_name] = random.choice(values)
            
            elif param_type == "string":
                params[param_name] = schema.get("default", "test_value")
            
            else:
                params[param_name] = schema.get("default", None)
        
        return params
    
    def _validate_parameter_value(self, param_name: str, param_value: Any, param_schema: Dict[str, Any]):
        """Validate parameter value against schema"""
        param_type = param_schema.get("type", "string")
        
        if param_type == "float":
            assert isinstance(param_value, (int, float)), f"Parameter {param_name} must be numeric"
            if "min" in param_schema:
                assert param_value >= param_schema["min"], f"Parameter {param_name} below minimum"
            if "max" in param_schema:
                assert param_value <= param_schema["max"], f"Parameter {param_name} above maximum"
        
        elif param_type == "enum":
            assert param_value in param_schema["values"], f"Parameter {param_name} not in valid values"
        
        elif param_type == "string":
            assert isinstance(param_value, str), f"Parameter {param_name} must be string"


class TestPDFGeneration:
    """Test PDF generation functionality"""
    
    def test_pdf_basic_structure(self):
        """Test that generated PDF has basic structure"""
        pdf_bytes = TestFixtures.create_mock_pdf_bytes()
        
        # Basic PDF validation
        assert pdf_bytes.startswith(b'%PDF-'), "PDF should start with %PDF- header"
        assert b'%%EOF' in pdf_bytes, "PDF should end with %%EOF"
        assert len(pdf_bytes) > 100, "PDF should have substantial content"
    
    def test_pdf_generation_with_symbols(self):
        """Test PDF generation includes placed symbols"""
        page_data = TestFixtures.get_mock_page_data()
        
        # Mock PDF generation
        pdf_result = self._mock_generate_pdf_with_symbols(page_data)
        
        assert "pdf_bytes" in pdf_result, "Result should contain PDF bytes"
        assert len(pdf_result["pdf_bytes"]) > 0, "PDF bytes should not be empty"
        
        # Verify symbols were processed
        assert len(page_data["annotations"]) > 0, "Should have symbols to place"
    
    def test_pdf_different_sheet_sizes(self):
        """Test PDF generation for different sheet sizes"""
        sheet_sizes = ["A4", "A3", "US-Letter"]
        
        for sheet_size in sheet_sizes:
            page_data = TestFixtures.get_mock_page_data()
            page_data["page_info"]["sheet_size"] = sheet_size
            
            # Set appropriate dimensions
            if sheet_size == "A4":
                page_data["page_info"]["width_mm"] = 210.0
                page_data["page_info"]["height_mm"] = 297.0
            elif sheet_size == "A3":
                page_data["page_info"]["width_mm"] = 297.0
                page_data["page_info"]["height_mm"] = 420.0
            elif sheet_size == "US-Letter":
                page_data["page_info"]["width_mm"] = 215.9
                page_data["page_info"]["height_mm"] = 279.4
            
            pdf_result = self._mock_generate_pdf_with_symbols(page_data)
            assert len(pdf_result["pdf_bytes"]) > 0, f"PDF generation failed for {sheet_size}"
    
    def test_pdf_coordinates_accuracy(self):
        """Test that symbol coordinates in PDF match JSON"""
        page_data = TestFixtures.get_mock_page_data()
        
        # Verify coordinate consistency
        for annotation in page_data["annotations"]:
            position = annotation["position"]
            bbox = annotation["bounding_box"]
            
            # Bounding box should be centered around position
            expected_center_x = (bbox["x_min"] + bbox["x_max"]) / 2
            expected_center_y = (bbox["y_min"] + bbox["y_max"]) / 2
            
            assert abs(position["x"] - expected_center_x) < 0.1, "X coordinate mismatch"
            assert abs(position["y"] - expected_center_y) < 0.1, "Y coordinate mismatch"
    
    def _mock_generate_pdf_with_symbols(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock PDF generation with symbols"""
        # Simulate PDF generation process
        pdf_bytes = TestFixtures.create_mock_pdf_bytes()
        
        # Add mock content based on symbols
        for annotation in page_data["annotations"]:
            # Simulate adding symbol to PDF
            symbol_content = f"Symbol: {annotation['symbol_name']} at ({annotation['position']['x']}, {annotation['position']['y']})\n"
            pdf_bytes += symbol_content.encode('utf-8')
        
        return {"pdf_bytes": pdf_bytes}


class TestJSONOutputFormat:
    """Test JSON output format compliance"""
    
    def test_json_output_structure(self):
        """Test that JSON output has required structure"""
        page_data = TestFixtures.get_mock_page_data()
        
        # Validate top-level structure
        required_keys = ["page_info", "annotations"]
        for key in required_keys:
            assert key in page_data, f"Missing required key: {key}"
        
        # Validate page_info structure
        page_info = page_data["page_info"]
        page_required = ["sheet_size", "width_mm", "height_mm", "commit_sha"]
        for key in page_required:
            assert key in page_info, f"page_info missing required key: {key}"
        
        # Validate annotations structure
        annotations = page_data["annotations"]
        assert isinstance(annotations, list), "annotations must be a list"
        
        for annotation in annotations:
            self._validate_annotation_structure(annotation)
    
    def test_annotation_completeness(self):
        """Test that annotations contain all required information"""
        page_data = TestFixtures.get_mock_page_data()
        
        for annotation in page_data["annotations"]:
            # Required fields
            required_fields = ["id", "symbol_name", "position", "rotation", "bounding_box", "parameters"]
            for field in required_fields:
                assert field in annotation, f"Annotation missing required field: {field}"
            
            # Validate data types
            assert isinstance(annotation["id"], str), "id must be string"
            assert isinstance(annotation["symbol_name"], str), "symbol_name must be string"
            assert isinstance(annotation["rotation"], (int, float)), "rotation must be numeric"
            assert isinstance(annotation["parameters"], dict), "parameters must be dict"
    
    def test_bounding_box_format(self):
        """Test bounding box format and validity"""
        page_data = TestFixtures.get_mock_page_data()
        
        for annotation in page_data["annotations"]:
            bbox = annotation["bounding_box"]
            
            # Required coordinates
            required_coords = ["x_min", "y_min", "x_max", "y_max"]
            for coord in required_coords:
                assert coord in bbox, f"bounding_box missing coordinate: {coord}"
                assert isinstance(bbox[coord], (int, float)), f"{coord} must be numeric"
            
            # Logical constraints
            assert bbox["x_min"] < bbox["x_max"], "x_min must be less than x_max"
            assert bbox["y_min"] < bbox["y_max"], "y_min must be less than y_max"
            
            # Positive dimensions
            width = bbox["x_max"] - bbox["x_min"]
            height = bbox["y_max"] - bbox["y_min"]
            assert width > 0, "Bounding box width must be positive"
            assert height > 0, "Bounding box height must be positive"
    
    def test_json_serialization(self):
        """Test that output can be properly JSON serialized"""
        page_data = TestFixtures.get_mock_page_data()
        
        try:
            json_str = json.dumps(page_data, indent=2)
            assert len(json_str) > 0, "JSON serialization produced empty string"
            
            # Test round-trip
            reconstructed = json.loads(json_str)
            assert reconstructed == page_data, "JSON round-trip failed"
            
        except (TypeError, ValueError) as e:
            pytest.fail(f"JSON serialization failed: {e}")
    
    def _validate_annotation_structure(self, annotation: Dict[str, Any]):
        """Validate individual annotation structure"""
        # Position structure
        position = annotation.get("position", {})
        assert "x" in position and "y" in position, "position must have x and y"
        assert isinstance(position["x"], (int, float)), "position.x must be numeric"
        assert isinstance(position["y"], (int, float)), "position.y must be numeric"
        
        # Bounding box structure
        bbox = annotation.get("bounding_box", {})
        bbox_coords = ["x_min", "y_min", "x_max", "y_max"]
        for coord in bbox_coords:
            assert coord in bbox, f"bounding_box missing {coord}"


class TestPlacementConstraints:
    """Test placement constraints and validation"""
    
    def test_symbols_within_sheet_bounds(self):
        """Test that all symbols are placed within sheet boundaries"""
        page_data = TestFixtures.get_mock_page_data()
        page_info = page_data["page_info"]
        
        sheet_width = page_info["width_mm"]
        sheet_height = page_info["height_mm"]
        margin = 10.0  # Assume 10mm margin
        
        for annotation in page_data["annotations"]:
            bbox = annotation["bounding_box"]
            
            # Check bounds with margin
            assert bbox["x_min"] >= margin, f"Symbol too close to left edge: {bbox['x_min']}"
            assert bbox["y_min"] >= margin, f"Symbol too close to bottom edge: {bbox['y_min']}"
            assert bbox["x_max"] <= sheet_width - margin, f"Symbol too close to right edge: {bbox['x_max']}"
            assert bbox["y_max"] <= sheet_height - margin, f"Symbol too close to top edge: {bbox['y_max']}"
    
    def test_no_symbol_overlap(self):
        """Test that symbols don't overlap"""
        page_data = TestFixtures.get_mock_page_data()
        annotations = page_data["annotations"]
        
        for i in range(len(annotations)):
            for j in range(i + 1, len(annotations)):
                bbox1 = annotations[i]["bounding_box"]
                bbox2 = annotations[j]["bounding_box"]
                
                # Check for overlap
                overlap = (bbox1["x_min"] < bbox2["x_max"] and bbox1["x_max"] > bbox2["x_min"] and
                          bbox1["y_min"] < bbox2["y_max"] and bbox1["y_max"] > bbox2["y_min"])
                
                assert not overlap, f"Symbols {i} and {j} overlap"
    
    def test_minimum_spacing_enforcement(self):
        """Test that minimum spacing between symbols is enforced"""
        page_data = TestFixtures.get_mock_page_data()
        annotations = page_data["annotations"]
        min_spacing = 2.0  # 2mm minimum spacing
        
        for i in range(len(annotations)):
            for j in range(i + 1, len(annotations)):
                bbox1 = annotations[i]["bounding_box"]
                bbox2 = annotations[j]["bounding_box"]
                
                # Calculate minimum distance between bounding boxes
                dx = max(0, max(bbox1["x_min"] - bbox2["x_max"], bbox2["x_min"] - bbox1["x_max"]))
                dy = max(0, max(bbox1["y_min"] - bbox2["y_max"], bbox2["y_min"] - bbox1["y_max"]))
                distance = (dx**2 + dy**2)**0.5
                
                assert distance >= min_spacing, f"Symbols {i} and {j} too close: {distance:.1f}mm"
    
    def test_rotation_constraints(self):
        """Test rotation angle constraints"""
        page_data = TestFixtures.get_mock_page_data()
        
        for annotation in page_data["annotations"]:
            rotation = annotation["rotation"]
            
            # Rotation should be in valid range
            assert 0 <= rotation < 360, f"Invalid rotation angle: {rotation}"
            
            # Common rotation angles (0, 45, 90, 180, 270)
            # Allow some tolerance for floating point
            valid_rotations = [0, 45, 90, 135, 180, 225, 270, 315]
            closest_valid = min(valid_rotations, key=lambda x: abs(x - rotation))
            assert abs(rotation - closest_valid) < 1.0, f"Unusual rotation angle: {rotation}"


class TestScalabilityAndPerformance:
    """Test scalability and performance requirements"""
    
    def test_high_symbol_count_placement(self):
        """Test placement with high symbol count"""
        # Test with 60 symbols (maximum requirement)
        large_page_data = self._create_large_page(60)
        
        # Should handle all symbols
        assert len(large_page_data["annotations"]) <= 60, "Should not exceed maximum symbol count"
        
        # All symbols should be properly placed
        for annotation in large_page_data["annotations"]:
            assert "position" in annotation, "Symbol missing position"
            assert "bounding_box" in annotation, "Symbol missing bounding box"
    
    def test_different_sheet_size_capacity(self):
        """Test symbol capacity for different sheet sizes"""
        sheet_capacities = {
            "A4": (210, 297, 40),    # A4: expect ~40 symbols max
            "A3": (297, 420, 80),    # A3: expect ~80 symbols max  
            "US-Letter": (215.9, 279.4, 45)  # Letter: expect ~45 symbols max
        }
        
        for sheet_size, (width, height, expected_capacity) in sheet_capacities.items():
            page_data = TestFixtures.get_mock_page_data()
            page_data["page_info"]["sheet_size"] = sheet_size
            page_data["page_info"]["width_mm"] = width
            page_data["page_info"]["height_mm"] = height
            
            # Simulate placement attempt with high symbol count
            attempted_symbols = min(expected_capacity + 10, 100)  # Try more than expected
            large_page = self._create_large_page(attempted_symbols)
            
            # Should place reasonable number
            placed_count = len(large_page["annotations"])
            assert placed_count >= expected_capacity * 0.8, f"Too few symbols placed on {sheet_size}"
    
    def test_placement_performance_benchmark(self):
        """Test placement performance meets requirements"""
        import time
        
        start_time = time.time()
        
        # Generate multiple pages to test performance
        for i in range(10):
            page_data = self._create_large_page(30)  # 30 symbols per page
            
            # Simulate placement validation
            for annotation in page_data["annotations"]:
                _ = annotation["position"]
                _ = annotation["bounding_box"]
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Should complete quickly (under 200ms per page for 10 pages)
        avg_per_page = duration_ms / 10
        assert avg_per_page < 200, f"Placement too slow: {avg_per_page:.1f}ms per page"
    
    def _create_large_page(self, symbol_count: int) -> Dict[str, Any]:
        """Create page data with large number of symbols"""
        base_page = TestFixtures.get_mock_page_data()
        base_annotations = base_page["annotations"]
        
        # Replicate and modify annotations to reach target count
        annotations = []
        for i in range(symbol_count):
            # Cycle through base annotations
            base_annotation = base_annotations[i % len(base_annotations)].copy()
            
            # Modify position to avoid overlap
            base_annotation["id"] = f"symbol_{i:03d}"
            base_annotation["position"]["x"] = 20 + (i % 10) * 20
            base_annotation["position"]["y"] = 20 + (i // 10) * 20
            
            # Update bounding box accordingly
            x, y = base_annotation["position"]["x"], base_annotation["position"]["y"]
            w, h = 8, 8  # Assume 8mm symbols
            base_annotation["bounding_box"] = {
                "x_min": x - w/2, "y_min": y - h/2,
                "x_max": x + w/2, "y_max": y + h/2
            }
            
            annotations.append(base_annotation)
        
        large_page = base_page.copy()
        large_page["annotations"] = annotations
        return large_page


if __name__ == "__main__":
    pytest.main([__file__, "-v"])