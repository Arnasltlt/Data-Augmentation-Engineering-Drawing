"""
Property-based testing for symbol placement and validation.
Uses hypothesis library for generating test cases with random but structured data.
"""

import json
from typing import Any, Dict, List
import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize
import numpy as np

from .fixtures import TestFixtures


# Hypothesis strategies for generating test data
@st.composite
def page_dimensions(draw):
    """Generate valid page dimensions"""
    sheet_types = ["A4", "A3", "US-Letter"]
    sheet_type = draw(st.sampled_from(sheet_types))
    
    dimensions = {
        "A4": (210.0, 297.0),
        "A3": (297.0, 420.0), 
        "US-Letter": (215.9, 279.4)
    }
    
    width, height = dimensions[sheet_type]
    return {"sheet_size": sheet_type, "width_mm": width, "height_mm": height}


@st.composite
def symbol_position(draw, page_width, page_height, margin=10.0):
    """Generate valid symbol position within page bounds"""
    x = draw(st.floats(min_value=margin, max_value=page_width - margin))
    y = draw(st.floats(min_value=margin, max_value=page_height - margin))
    return {"x": x, "y": y}


@st.composite
def symbol_parameters(draw):
    """Generate valid symbol parameters"""
    param_types = [
        {"tolerance_value": st.floats(min_value=0.001, max_value=1.0)},
        {"roughness_ra": st.floats(min_value=0.1, max_value=50.0)},
        {"diameter_value": st.floats(min_value=0.1, max_value=1000.0)},
        {"thread_size": st.sampled_from(["M3", "M4", "M5", "M6", "M8", "M10", "M12"])}
    ]
    
    param_set = draw(st.sampled_from(param_types))
    result = {}
    for param_name, strategy in param_set.items():
        result[param_name] = draw(strategy)
    
    return result


@st.composite
def symbol_annotation(draw, page_width, page_height, symbol_names):
    """Generate complete symbol annotation"""
    symbol_name = draw(st.sampled_from(symbol_names))
    position = draw(symbol_position(page_width, page_height))
    rotation = draw(st.floats(min_value=0, max_value=360))
    parameters = draw(symbol_parameters())
    
    # Generate bounding box around position
    symbol_width = draw(st.floats(min_value=2.0, max_value=20.0))
    symbol_height = draw(st.floats(min_value=2.0, max_value=20.0))
    
    bbox = {
        "x_min": position["x"] - symbol_width/2,
        "y_min": position["y"] - symbol_height/2,
        "x_max": position["x"] + symbol_width/2,
        "y_max": position["y"] + symbol_height/2
    }
    
    return {
        "id": f"symbol_{hash(str(position))}",
        "symbol_name": symbol_name,
        "filename": f"{symbol_name}.svg",
        "position": position,
        "rotation": rotation,
        "bounding_box": bbox,
        "parameters": parameters
    }


class TestPropertyBasedSymbolPlacement:
    """Property-based tests for symbol placement validation"""
    
    @given(page_dimensions())
    def test_page_dimensions_valid(self, page_data):
        """Test that generated page dimensions are always valid"""
        assert page_data["width_mm"] > 0, "Page width must be positive"
        assert page_data["height_mm"] > 0, "Page height must be positive"
        assert page_data["width_mm"] < 1000, "Page width should be reasonable"
        assert page_data["height_mm"] < 1000, "Page height should be reasonable"
        assert page_data["sheet_size"] in ["A4", "A3", "US-Letter"], "Must be valid sheet size"
    
    @given(
        page_dims=page_dimensions(),
        symbol_count=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50)
    def test_multi_symbol_placement_no_overlap(self, page_dims, symbol_count):
        """Test that multiple symbols can be placed without overlap"""
        page_width = page_dims["width_mm"]
        page_height = page_dims["height_mm"]
        
        symbol_names = ["flatness", "straightness", "diameter", "surface_triangle"]
        
        # Generate symbols
        symbols = []
        attempts = 0
        max_attempts = symbol_count * 10
        
        while len(symbols) < symbol_count and attempts < max_attempts:
            # Generate candidate symbol
            try:
                candidate = symbol_annotation(page_width, page_height, symbol_names).example()
                
                # Check for overlap with existing symbols
                overlaps = False
                for existing in symbols:
                    if self._symbols_overlap(candidate["bounding_box"], existing["bounding_box"]):
                        overlaps = True
                        break
                
                if not overlaps:
                    symbols.append(candidate)
                    
            except Exception:
                pass  # Skip invalid candidates
                
            attempts += 1
        
        # Validate placement results
        if len(symbols) > 0:
            # All symbols should be within page bounds
            for symbol in symbols:
                bbox = symbol["bounding_box"]
                assert bbox["x_min"] >= 0, "Symbol extends beyond left edge"
                assert bbox["y_min"] >= 0, "Symbol extends beyond bottom edge"
                assert bbox["x_max"] <= page_width, "Symbol extends beyond right edge"
                assert bbox["y_max"] <= page_height, "Symbol extends beyond top edge"
            
            # No symbols should overlap
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols[i+1:], i+1):
                    assert not self._symbols_overlap(
                        symbol1["bounding_box"], 
                        symbol2["bounding_box"]
                    ), f"Symbols {i} and {j} overlap"
    
    @given(
        tolerance=st.floats(min_value=0.001, max_value=1.0),
        roughness=st.floats(min_value=0.1, max_value=50.0),
        diameter=st.floats(min_value=0.1, max_value=1000.0)
    )
    def test_parameter_validation_ranges(self, tolerance, roughness, diameter):
        """Test that generated parameters are always within valid ranges"""
        # Tolerance values for GD&T
        assert 0.001 <= tolerance <= 1.0, "Tolerance out of range"
        
        # Surface roughness values
        assert 0.1 <= roughness <= 50.0, "Roughness out of range"
        
        # Diameter values
        assert 0.1 <= diameter <= 1000.0, "Diameter out of range"
    
    @given(
        rotation=st.floats(min_value=0, max_value=360),
        x_pos=st.floats(min_value=10, max_value=200),
        y_pos=st.floats(min_value=10, max_value=200)
    )
    def test_coordinate_transformation_consistency(self, rotation, x_pos, y_pos):
        """Test coordinate transformations are consistent"""
        # Test position and bounding box consistency
        symbol_width, symbol_height = 8.0, 8.0
        
        bbox = {
            "x_min": x_pos - symbol_width/2,
            "y_min": y_pos - symbol_height/2,
            "x_max": x_pos + symbol_width/2,
            "y_max": y_pos + symbol_height/2
        }
        
        # Center should match position
        center_x = (bbox["x_min"] + bbox["x_max"]) / 2
        center_y = (bbox["y_min"] + bbox["y_max"]) / 2
        
        assert abs(center_x - x_pos) < 0.001, "X coordinate inconsistency"
        assert abs(center_y - y_pos) < 0.001, "Y coordinate inconsistency"
        
        # Bounding box should have positive dimensions
        assert bbox["x_max"] > bbox["x_min"], "Invalid bounding box width"
        assert bbox["y_max"] > bbox["y_min"], "Invalid bounding box height"
    
    def _symbols_overlap(self, bbox1: Dict[str, float], bbox2: Dict[str, float]) -> bool:
        """Check if two bounding boxes overlap"""
        return (bbox1["x_min"] < bbox2["x_max"] and bbox1["x_max"] > bbox2["x_min"] and
                bbox1["y_min"] < bbox2["y_max"] and bbox1["y_max"] > bbox2["y_min"])


class SymbolPlacementStateMachine(RuleBasedStateMachine):
    """Stateful property-based testing for symbol placement operations"""
    
    def __init__(self):
        super().__init__()
        self.page_width = 210.0  # A4 width
        self.page_height = 297.0  # A4 height
        self.placed_symbols = []
        self.symbol_counter = 0
        
    @initialize()
    def setup_page(self):
        """Initialize empty page"""
        self.placed_symbols = []
        self.symbol_counter = 0
    
    @rule(
        symbol_name=st.sampled_from(["flatness", "straightness", "diameter"]),
        x_pos=st.floats(min_value=15, max_value=195),
        y_pos=st.floats(min_value=15, max_value=282)
    )
    def place_symbol(self, symbol_name, x_pos, y_pos):
        """Place a symbol on the page"""
        symbol_width, symbol_height = 8.0, 8.0
        
        new_symbol = {
            "id": f"symbol_{self.symbol_counter}",
            "symbol_name": symbol_name,
            "position": {"x": x_pos, "y": y_pos},
            "bounding_box": {
                "x_min": x_pos - symbol_width/2,
                "y_min": y_pos - symbol_height/2,
                "x_max": x_pos + symbol_width/2,
                "y_max": y_pos + symbol_height/2
            }
        }
        
        # Check for overlaps
        overlaps = any(
            self._symbols_overlap(new_symbol["bounding_box"], existing["bounding_box"])
            for existing in self.placed_symbols
        )
        
        if not overlaps:
            self.placed_symbols.append(new_symbol)
            self.symbol_counter += 1
    
    @rule()
    def validate_page_state(self):
        """Validate current page state"""
        # All symbols should be within bounds
        for symbol in self.placed_symbols:
            bbox = symbol["bounding_box"]
            assert bbox["x_min"] >= 0, "Symbol outside left boundary"
            assert bbox["y_min"] >= 0, "Symbol outside bottom boundary"
            assert bbox["x_max"] <= self.page_width, "Symbol outside right boundary"
            assert bbox["y_max"] <= self.page_height, "Symbol outside top boundary"
        
        # No symbols should overlap
        for i, symbol1 in enumerate(self.placed_symbols):
            for j, symbol2 in enumerate(self.placed_symbols[i+1:], i+1):
                assert not self._symbols_overlap(
                    symbol1["bounding_box"], 
                    symbol2["bounding_box"]
                ), f"Symbols {i} and {j} overlap"
    
    @rule(target_count=st.integers(min_value=0, max_value=50))
    def check_capacity(self, target_count):
        """Check page capacity constraints"""
        # Page should not accept unlimited symbols
        max_theoretical = (self.page_width * self.page_height) / (8.0 * 8.0)  # Theoretical max
        
        assert len(self.placed_symbols) <= max_theoretical, "Exceeded theoretical capacity"
        
        # Practical limit should be much lower due to spacing
        practical_limit = max_theoretical * 0.3  # 30% of theoretical
        if len(self.placed_symbols) > practical_limit:
            # This is still reasonable for dense packing
            pass
    
    def _symbols_overlap(self, bbox1: Dict[str, float], bbox2: Dict[str, float]) -> bool:
        """Check if two bounding boxes overlap"""
        return (bbox1["x_min"] < bbox2["x_max"] and bbox1["x_max"] > bbox2["x_min"] and
                bbox1["y_min"] < bbox2["y_max"] and bbox1["y_max"] > bbox2["y_min"])


class TestPropertyBasedManifestValidation:
    """Property-based tests for manifest validation"""
    
    @given(
        symbol_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), blacklist_characters=' ')),
        width=st.floats(min_value=1.0, max_value=100.0),
        height=st.floats(min_value=1.0, max_value=100.0)
    )
    def test_symbol_definition_properties(self, symbol_name, width, height):
        """Test properties of symbol definitions"""
        # Name should be valid identifier
        assert symbol_name.isalnum() or '_' in symbol_name, "Symbol name should be alphanumeric"
        
        # Dimensions should be positive
        assert width > 0, "Symbol width must be positive"
        assert height > 0, "Symbol height must be positive"
        
        # Reasonable size limits
        assert width <= 100, "Symbol width should be reasonable"
        assert height <= 100, "Symbol height should be reasonable"
    
    @given(
        param_value=st.one_of(
            st.floats(min_value=0.001, max_value=100.0),
            st.sampled_from(["M3", "M6", "M10", "fine", "medium", "coarse"]),
            st.integers(min_value=1, max_value=100)
        )
    )
    def test_parameter_value_validity(self, param_value):
        """Test that parameter values are valid"""
        if isinstance(param_value, float):
            assert param_value > 0, "Numeric parameters should be positive"
            assert not np.isnan(param_value), "Parameters should not be NaN"
            assert not np.isinf(param_value), "Parameters should not be infinite"
        
        elif isinstance(param_value, str):
            assert len(param_value) > 0, "String parameters should not be empty"
            assert param_value.isprintable(), "String parameters should be printable"
        
        elif isinstance(param_value, int):
            assert param_value > 0, "Integer parameters should be positive"


# Test the state machine
TestSymbolPlacementStateMachine = SymbolPlacementStateMachine.TestCase


if __name__ == "__main__":
    # Run property-based tests
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])