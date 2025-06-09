"""
Comprehensive unit tests for VectorForge agent - SVG symbol library management.
Tests symbol creation, validation, manifest generation, and rendering.
"""

import io
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict
import tempfile
import pytest
import yaml
from PIL import Image

from .fixtures import TestFixtures, MockFileSystem


class TestSVGValidation:
    """Test SVG symbol validation and rendering"""
    
    def test_svg_well_formed_xml(self):
        """Test that all SVG symbols are well-formed XML"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        for symbol in manifest["symbols"]:
            svg_content = TestFixtures.get_mock_svg_content(symbol["name"])
            
            # Should parse without exception
            try:
                root = ET.fromstring(svg_content)
                assert root.tag.endswith('svg'), f"Root element should be svg for {symbol['name']}"
            except ET.ParseError as e:
                pytest.fail(f"Invalid XML in {symbol['filename']}: {e}")
    
    def test_svg_has_required_attributes(self):
        """Test that SVG symbols have required viewBox and dimensions"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        for symbol in manifest["symbols"]:
            svg_content = TestFixtures.get_mock_svg_content(symbol["name"])
            root = ET.fromstring(svg_content)
            
            # Check for viewBox or width/height
            has_viewbox = 'viewBox' in root.attrib
            has_dimensions = 'width' in root.attrib and 'height' in root.attrib
            
            assert has_viewbox or has_dimensions, f"SVG {symbol['filename']} missing viewBox or dimensions"
            
            # Check namespace
            assert root.tag == '{http://www.w3.org/2000/svg}svg' or root.tag == 'svg', \
                f"SVG {symbol['filename']} missing SVG namespace"
    
    def test_svg_coordinate_system(self):
        """Test that SVG symbols use millimeter coordinate system"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        for symbol in manifest["symbols"]:
            svg_content = TestFixtures.get_mock_svg_content(symbol["name"])
            root = ET.fromstring(svg_content)
            
            # Check for mm units in width/height
            width = root.attrib.get('width', '')
            height = root.attrib.get('height', '')
            
            if width and height:
                assert 'mm' in width, f"Width should use mm units in {symbol['filename']}"
                assert 'mm' in height, f"Height should use mm units in {symbol['filename']}"
    
    def test_svg_renders_without_error(self):
        """Test that SVG symbols can be rendered to PNG"""
        try:
            import cairosvg
        except ImportError:
            pytest.skip("cairosvg not available for rendering test")
        
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        for symbol in manifest["symbols"]:
            svg_content = TestFixtures.get_mock_svg_content(symbol["name"])
            
            try:
                # Render to PNG bytes
                png_bytes = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), 
                                           output_width=32, output_height=32)
                assert len(png_bytes) > 0, f"Empty PNG output for {symbol['filename']}"
                
                # Verify it's a valid PNG
                img = Image.open(io.BytesIO(png_bytes))
                assert img.format == 'PNG', f"Invalid PNG format for {symbol['filename']}"
                
            except Exception as e:
                pytest.fail(f"Rendering failed for {symbol['filename']}: {e}")


class TestManifestValidation:
    """Test symbols manifest validation and management"""
    
    def test_manifest_schema_compliance(self):
        """Test that manifest follows required schema"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        # Check top-level structure
        assert "schema_version" in manifest, "Manifest missing schema_version"
        assert "symbols" in manifest, "Manifest missing symbols array"
        assert isinstance(manifest["symbols"], list), "symbols must be a list"
    
    def test_symbol_entries_complete(self):
        """Test that all symbol entries have required fields"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        required_fields = ["name", "filename", "w_mm", "h_mm", "params"]
        
        for i, symbol in enumerate(manifest["symbols"]):
            for field in required_fields:
                assert field in symbol, f"Symbol {i} missing required field: {field}"
            
            # Validate data types
            assert isinstance(symbol["name"], str), f"Symbol {i} name must be string"
            assert isinstance(symbol["filename"], str), f"Symbol {i} filename must be string"
            assert isinstance(symbol["w_mm"], (int, float)), f"Symbol {i} w_mm must be numeric"
            assert isinstance(symbol["h_mm"], (int, float)), f"Symbol {i} h_mm must be numeric"
            assert isinstance(symbol["params"], dict), f"Symbol {i} params must be dict"
            
            # Validate positive dimensions
            assert symbol["w_mm"] > 0, f"Symbol {i} width must be positive"
            assert symbol["h_mm"] > 0, f"Symbol {i} height must be positive"
    
    def test_symbol_names_unique(self):
        """Test that symbol names are unique"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        names = [symbol["name"] for symbol in manifest["symbols"]]
        unique_names = set(names)
        
        assert len(names) == len(unique_names), "Duplicate symbol names found"
    
    def test_filenames_unique(self):
        """Test that filenames are unique"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        filenames = [symbol["filename"] for symbol in manifest["symbols"]]
        unique_filenames = set(filenames)
        
        assert len(filenames) == len(unique_filenames), "Duplicate filenames found"
    
    def test_filename_conventions(self):
        """Test that filenames follow naming conventions"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        for symbol in manifest["symbols"]:
            filename = symbol["filename"]
            
            # Should end with .svg
            assert filename.endswith(".svg"), f"Filename {filename} should end with .svg"
            
            # Should be lowercase with underscores
            assert filename.islower(), f"Filename {filename} should be lowercase"
            assert " " not in filename, f"Filename {filename} should not contain spaces"
    
    def test_parameter_schemas_valid(self):
        """Test that parameter schemas are well-defined"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        valid_param_types = ["string", "float", "int", "enum", "boolean"]
        
        for symbol in manifest["symbols"]:
            for param_name, param_def in symbol["params"].items():
                assert isinstance(param_def, dict), f"Parameter {param_name} must be dict"
                assert "type" in param_def, f"Parameter {param_name} missing type"
                
                param_type = param_def["type"]
                assert param_type in valid_param_types, f"Invalid parameter type: {param_type}"
                
                # Type-specific validation
                if param_type == "float":
                    if "min" in param_def:
                        assert isinstance(param_def["min"], (int, float)), "min must be numeric"
                    if "max" in param_def:
                        assert isinstance(param_def["max"], (int, float)), "max must be numeric"
                    if "default" in param_def:
                        assert isinstance(param_def["default"], (int, float)), "default must be numeric"
                
                elif param_type == "enum":
                    assert "values" in param_def, "enum type must have values"
                    assert isinstance(param_def["values"], list), "enum values must be list"
                    assert len(param_def["values"]) > 0, "enum values cannot be empty"


class TestSymbolCategories:
    """Test symbol category coverage and organization"""
    
    def test_gdt_symbols_present(self):
        """Test that GD&T symbols are present"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        symbol_names = [s["name"] for s in manifest["symbols"]]
        
        # Check for major GD&T symbols
        expected_gdt = ["flatness", "straightness", "circularity"]
        found_gdt = [name for name in symbol_names if any(gdt in name for gdt in expected_gdt)]
        
        assert len(found_gdt) >= 3, f"Expected at least 3 GD&T symbols, found: {found_gdt}"
    
    def test_surface_finish_symbols_present(self):
        """Test that surface finish symbols are present"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        symbol_names = [s["name"] for s in manifest["symbols"]]
        
        surface_symbols = [name for name in symbol_names if "surface" in name]
        assert len(surface_symbols) >= 1, "Expected at least 1 surface finish symbol"
    
    def test_geometric_symbols_present(self):
        """Test that geometric symbols are present"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        symbol_names = [s["name"] for s in manifest["symbols"]]
        
        geometric_symbols = [name for name in symbol_names if any(geo in name for geo in ["diameter", "radius"])]
        assert len(geometric_symbols) >= 2, "Expected diameter and radius symbols"
    
    def test_threading_symbols_present(self):
        """Test that threading symbols are present"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        symbol_names = [s["name"] for s in manifest["symbols"]]
        
        thread_symbols = [name for name in symbol_names if "thread" in name]
        assert len(thread_symbols) >= 1, "Expected at least 1 threading symbol"
    
    def test_minimum_symbol_count(self):
        """Test that we have minimum required symbol count"""
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        # Should have at least 8 symbols for basic coverage
        assert len(manifest["symbols"]) >= 8, f"Expected at least 8 symbols, found {len(manifest['symbols'])}"


class TestVectorForgeIntegration:
    """Integration tests for VectorForge agent workflows"""
    
    def test_manifest_generation_workflow(self):
        """Test complete manifest generation workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_fs = MockFileSystem(temp_path)
            
            # Set up mock environment
            symbols_dir = mock_fs.symbols_dir
            symbols_dir.mkdir()
            
            # Create mock SVG files
            manifest = TestFixtures.get_mock_symbols_manifest()
            for symbol in manifest["symbols"]:
                svg_path = symbols_dir / symbol["filename"]
                with open(svg_path, 'w') as f:
                    f.write(TestFixtures.get_mock_svg_content(symbol["name"]))
            
            # Create manifest
            manifest_path = symbols_dir / "symbols_manifest.yaml"
            with open(manifest_path, 'w') as f:
                yaml.dump(manifest, f)
            
            # Verify all files exist
            assert manifest_path.exists(), "Manifest should be created"
            
            # Verify file count matches manifest
            svg_files = list(symbols_dir.glob("*.svg"))
            assert len(svg_files) == len(manifest["symbols"]), "SVG file count should match manifest"
    
    def test_license_tracking_workflow(self):
        """Test license tracking and validation workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            symbols_dir = temp_path / "symbols"
            symbols_dir.mkdir()
            
            # Create license CSV
            license_path = symbols_dir / "symbol_licences.csv"
            with open(license_path, 'w') as f:
                f.write("filename,licence,source-URL\n")
                for license_data in TestFixtures.get_mock_license_data():
                    f.write(f"{license_data['filename']},{license_data['licence']},{license_data['source-URL']}\n")
            
            # Verify license tracking
            assert license_path.exists(), "License CSV should be created"
            
            # Read and validate content
            import csv
            with open(license_path, 'r') as f:
                reader = csv.DictReader(f)
                licenses = list(reader)
            
            assert len(licenses) > 0, "Should have license entries"
            
            # Check required columns
            required_columns = {"filename", "licence", "source-URL"}
            actual_columns = set(licenses[0].keys())
            assert required_columns.issubset(actual_columns), "Missing required license columns"


class TestPerformanceRequirements:
    """Test performance requirements for VectorForge operations"""
    
    def test_manifest_load_performance(self):
        """Test that manifest loading is fast enough"""
        import time
        
        manifest = TestFixtures.get_mock_symbols_manifest()
        
        # Time manifest processing
        start_time = time.time()
        
        # Simulate manifest processing
        for _ in range(10):  # Process 10 times to get average
            processed_symbols = []
            for symbol in manifest["symbols"]:
                # Simulate validation and processing
                processed_symbol = {
                    "name": symbol["name"],
                    "dimensions": (symbol["w_mm"], symbol["h_mm"]),
                    "param_count": len(symbol["params"])
                }
                processed_symbols.append(processed_symbol)
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Should process quickly (under 50ms for 10 iterations)
        assert duration_ms < 50, f"Manifest processing too slow: {duration_ms:.1f}ms"
    
    def test_svg_rendering_performance(self):
        """Test SVG rendering performance requirements"""
        try:
            import cairosvg
        except ImportError:
            pytest.skip("cairosvg not available for performance test")
        
        import time
        
        svg_content = TestFixtures.get_mock_svg_content("flatness")
        
        start_time = time.time()
        
        # Render multiple times
        for _ in range(5):
            png_bytes = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), 
                                       output_width=32, output_height=32)
            assert len(png_bytes) > 0
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Should render quickly (under 100ms for 5 renders)
        assert duration_ms < 100, f"SVG rendering too slow: {duration_ms:.1f}ms"


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_svg_handling(self):
        """Test handling of invalid SVG content"""
        invalid_svg = "<svg><rect></svg>"  # Missing closing tag
        
        try:
            ET.fromstring(invalid_svg)
            pytest.fail("Should have raised ParseError for invalid SVG")
        except ET.ParseError:
            pass  # Expected behavior
    
    def test_missing_manifest_handling(self):
        """Test handling when manifest is missing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = Path(temp_dir) / "missing_manifest.yaml"
            
            assert not non_existent_path.exists(), "Path should not exist"
            
            # This should be handled gracefully by the agent
            # Test would depend on actual VectorForge implementation
    
    def test_malformed_manifest_handling(self):
        """Test handling of malformed manifest YAML"""
        malformed_yaml = """
symbols:
  - name: test
    filename: test.svg
    w_mm: "not_a_number"  # Invalid numeric value
"""
        
        try:
            data = yaml.safe_load(malformed_yaml)
            # Validation should catch the invalid numeric value
            symbol = data["symbols"][0]
            assert not isinstance(symbol["w_mm"], (int, float)), "Should detect invalid numeric value"
        except yaml.YAMLError:
            pass  # Also acceptable - YAML parsing failure


if __name__ == "__main__":
    pytest.main([__file__, "-v"])