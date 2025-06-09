"""
test_schema.py - JSON schema validation tests for QualityGate agent
Validates that JSON outputs conform to symbols_manifest.yaml schema
"""

import json
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any, List


class TestSchemaValidation:
    """Test suite for JSON schema validation against symbols manifest"""
    
    @pytest.fixture
    def symbols_manifest(self) -> Dict[str, Any]:
        """Load symbols manifest from VectorForge"""
        manifest_path = Path(__file__).parent.parent / "symbols" / "symbols_manifest.yaml"
        
        if not manifest_path.exists():
            pytest.skip("symbols_manifest.yaml not found - VectorForge not ready")
            
        with open(manifest_path, 'r') as f:
            return yaml.safe_load(f)
    
    @pytest.fixture
    def sample_json_output(self) -> Dict[str, Any]:
        """Sample JSON output from LayoutLab for testing"""
        return {
            "page_info": {
                "sheet_size": "A4",
                "width_mm": 210.0,
                "height_mm": 297.0,
                "commit_sha": "abcd1234"
            },
            "annotations": [
                {
                    "symbol_name": "flatness",
                    "filename": "gdt_flatness.svg",
                    "bbox_mm": {
                        "x": 50.0,
                        "y": 100.0,
                        "w": 8.0,
                        "h": 8.0
                    },
                    "rotation_deg": 0.0,
                    "parameters": {
                        "tolerance_value": 0.05
                    }
                },
                {
                    "symbol_name": "surface_finish_triangle",
                    "filename": "surface_triangle.svg",
                    "bbox_mm": {
                        "x": 120.0,
                        "y": 150.0,
                        "w": 6.0,
                        "h": 6.0
                    },
                    "rotation_deg": 45.0,
                    "parameters": {
                        "roughness_ra": 3.2,
                        "machining_allowance": 0.0
                    }
                }
            ]
        }
    
    def test_manifest_structure(self, symbols_manifest: Dict[str, Any]):
        """Test that symbols manifest has required structure"""
        assert "symbols" in symbols_manifest, "Manifest must have 'symbols' key"
        assert "schema_version" in symbols_manifest, "Manifest must have 'schema_version' key"
        assert isinstance(symbols_manifest["symbols"], list), "symbols must be a list"
        
    def test_symbol_definitions(self, symbols_manifest: Dict[str, Any]):
        """Test that each symbol has required fields"""
        for symbol in symbols_manifest["symbols"]:
            required_fields = ["name", "filename", "w_mm", "h_mm", "params"]
            for field in required_fields:
                assert field in symbol, f"Symbol missing required field: {field}"
                
            # Validate data types
            assert isinstance(symbol["name"], str), "name must be string"
            assert isinstance(symbol["filename"], str), "filename must be string"
            assert isinstance(symbol["w_mm"], (int, float)), "w_mm must be numeric"
            assert isinstance(symbol["h_mm"], (int, float)), "h_mm must be numeric"
            assert isinstance(symbol["params"], dict), "params must be dict"
            
    def test_json_page_structure(self, sample_json_output: Dict[str, Any]):
        """Test that JSON output has required page structure"""
        required_keys = ["page_info", "annotations"]
        for key in required_keys:
            assert key in sample_json_output, f"JSON missing required key: {key}"
            
        page_info = sample_json_output["page_info"]
        page_required = ["sheet_size", "width_mm", "height_mm", "commit_sha"]
        for key in page_required:
            assert key in page_info, f"page_info missing required key: {key}"
            
    def test_annotation_structure(self, sample_json_output: Dict[str, Any]):
        """Test that each annotation has required structure"""
        annotations = sample_json_output["annotations"]
        assert isinstance(annotations, list), "annotations must be a list"
        
        for annotation in annotations:
            required_fields = ["symbol_name", "filename", "bbox_mm", "rotation_deg", "parameters"]
            for field in required_fields:
                assert field in annotation, f"Annotation missing required field: {field}"
                
            # Test bbox structure
            bbox = annotation["bbox_mm"]
            bbox_required = ["x", "y", "w", "h"]
            for coord in bbox_required:
                assert coord in bbox, f"bbox_mm missing coordinate: {coord}"
                assert isinstance(bbox[coord], (int, float)), f"{coord} must be numeric"
                
    def test_symbol_parameter_compliance(self, symbols_manifest: Dict[str, Any], 
                                       sample_json_output: Dict[str, Any]):
        """Test that symbol parameters comply with manifest schema"""
        # Create lookup dict for symbols
        symbol_schemas = {sym["name"]: sym for sym in symbols_manifest["symbols"]}
        
        for annotation in sample_json_output["annotations"]:
            symbol_name = annotation["symbol_name"]
            
            # Check symbol exists in manifest
            assert symbol_name in symbol_schemas, f"Unknown symbol: {symbol_name}"
            
            symbol_schema = symbol_schemas[symbol_name]
            annotation_params = annotation["parameters"]
            
            # Validate each parameter
            for param_name, param_value in annotation_params.items():
                assert param_name in symbol_schema["params"], f"Unknown parameter: {param_name}"
                
                param_schema = symbol_schema["params"][param_name]
                self._validate_parameter(param_name, param_value, param_schema)
                
    def test_bbox_dimensions_match_manifest(self, symbols_manifest: Dict[str, Any],
                                          sample_json_output: Dict[str, Any]):
        """Test that bounding box dimensions match manifest specifications"""
        symbol_schemas = {sym["name"]: sym for sym in symbols_manifest["symbols"]}
        
        for annotation in sample_json_output["annotations"]:
            symbol_name = annotation["symbol_name"]
            symbol_schema = symbol_schemas[symbol_name]
            bbox = annotation["bbox_mm"]
            
            # Allow for small floating point differences
            assert abs(bbox["w"] - symbol_schema["w_mm"]) < 0.001, \
                f"Width mismatch for {symbol_name}: {bbox['w']} != {symbol_schema['w_mm']}"
            assert abs(bbox["h"] - symbol_schema["h_mm"]) < 0.001, \
                f"Height mismatch for {symbol_name}: {bbox['h']} != {symbol_schema['h_mm']}"
                
    def _validate_parameter(self, param_name: str, param_value: Any, 
                          param_schema: Dict[str, Any]):
        """Validate individual parameter against schema"""
        param_type = param_schema.get("type", "string")
        
        if param_type == "float":
            assert isinstance(param_value, (int, float)), \
                f"Parameter {param_name} must be numeric"
            if "min" in param_schema:
                assert param_value >= param_schema["min"], \
                    f"Parameter {param_name} below minimum: {param_value} < {param_schema['min']}"
            if "max" in param_schema:
                assert param_value <= param_schema["max"], \
                    f"Parameter {param_name} above maximum: {param_value} > {param_schema['max']}"
                    
        elif param_type == "enum":
            assert param_value in param_schema["values"], \
                f"Parameter {param_name} not in allowed values: {param_value}"
                
        elif param_type == "string":
            assert isinstance(param_value, str), \
                f"Parameter {param_name} must be string"


def test_manifest_coverage():
    """Test that manifest covers all expected symbol categories"""
    manifest_path = Path(__file__).parent.parent / "symbols" / "symbols_manifest.yaml"
    
    if not manifest_path.exists():
        pytest.skip("symbols_manifest.yaml not found")
        
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)
        
    symbol_names = [sym["name"] for sym in manifest["symbols"]]
    
    # Check we have symbols from major categories
    expected_categories = {
        "gdt": ["flatness", "straightness", "circularity"],
        "surface": ["surface_finish_triangle"],
        "geometry": ["diameter", "radius"],
        "threads": ["thread_metric"]
    }
    
    for category, expected_symbols in expected_categories.items():
        found_symbols = [name for name in symbol_names if any(exp in name for exp in expected_symbols)]
        assert len(found_symbols) > 0, f"No symbols found for category: {category}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])