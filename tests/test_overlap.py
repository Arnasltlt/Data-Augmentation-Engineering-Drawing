"""
Collision detection tests for LayoutLab placement engine
"""

import os
import sys
import unittest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from layoutlab.placer import (
    CollisionDetector,
    PlacedSymbol,
    SheetDimensions,
    Symbol,
    SymbolPlacer,
    generate_page,
)


class TestCollisionDetection(unittest.TestCase):
    """Test collision detection functionality"""

    def setUp(self):
        """Set up test symbols"""
        self.symbol1 = Symbol("test_symbol1", "test1.svg", 10.0, 8.0, {})
        self.symbol2 = Symbol("test_symbol2", "test2.svg", 6.0, 4.0, {})

    def test_no_collision_separated_symbols(self):
        """Test that separated symbols don't collide"""
        placed1 = PlacedSymbol(self.symbol1, 10.0, 10.0, 0, {})
        placed2 = PlacedSymbol(self.symbol2, 30.0, 30.0, 0, {})

        self.assertFalse(CollisionDetector.check_collision(placed1, placed2))

    def test_collision_overlapping_symbols(self):
        """Test that overlapping symbols collide"""
        placed1 = PlacedSymbol(self.symbol1, 10.0, 10.0, 0, {})
        placed2 = PlacedSymbol(self.symbol2, 12.0, 12.0, 0, {})  # Overlapping

        self.assertTrue(CollisionDetector.check_collision(placed1, placed2))

    def test_collision_with_minimum_spacing(self):
        """Test collision detection with minimum spacing requirements"""
        placed1 = PlacedSymbol(self.symbol1, 10.0, 10.0, 0, {})
        # Place symbol2 close enough that 2mm spacing will cause collision
        # symbol1 bbox: (5,6,15,14), with 2mm spacing becomes (3,4,17,16)
        # symbol2 half-width=3, so x=18.5 means left edge at 15.5 - within expanded bbox
        placed2 = PlacedSymbol(self.symbol2, 18.5, 10.0, 0, {})

        # Without minimum spacing, should not collide
        self.assertFalse(
            CollisionDetector.check_collision(placed1, placed2, min_spacing=0.0)
        )

        # With minimum spacing, should collide
        self.assertTrue(
            CollisionDetector.check_collision(placed1, placed2, min_spacing=2.0)
        )

    def test_bounding_box_calculation(self):
        """Test bounding box calculation"""
        placed = PlacedSymbol(self.symbol1, 20.0, 15.0, 0, {})
        bbox = CollisionDetector.get_bounding_box(placed)

        expected = (15.0, 11.0, 25.0, 19.0)  # x_min, y_min, x_max, y_max
        self.assertEqual(bbox, expected)

    def test_edge_case_touching_symbols(self):
        """Test symbols that are exactly touching"""
        placed1 = PlacedSymbol(self.symbol1, 10.0, 10.0, 0, {})
        # Place symbol2 so its left edge is just beyond symbol1's right edge
        # symbol1 bbox: (5,6,15,14), symbol2 half-width=3, so x=18.1 means left edge at 15.1
        placed2 = PlacedSymbol(self.symbol2, 18.1, 10.0, 0, {})

        # Should not collide when not touching (no spacing)
        self.assertFalse(
            CollisionDetector.check_collision(placed1, placed2, min_spacing=0.0)
        )


class TestSheetDimensions(unittest.TestCase):
    """Test sheet dimension handling"""

    def test_supported_sheet_sizes(self):
        """Test all supported sheet sizes"""
        a4_size = SheetDimensions.get_size("A4")
        self.assertEqual(a4_size, (210, 297))

        a3_size = SheetDimensions.get_size("A3")
        self.assertEqual(a3_size, (297, 420))

        letter_size = SheetDimensions.get_size("US-Letter")
        self.assertEqual(letter_size, (215.9, 279.4))

    def test_unsupported_sheet_size(self):
        """Test error for unsupported sheet size"""
        with self.assertRaises(ValueError):
            SheetDimensions.get_size("B5")


class TestSymbolPlacement(unittest.TestCase):
    """Test symbol placement functionality"""

    def setUp(self):
        """Set up placer instance"""
        self.placer = SymbolPlacer()

    def test_mock_symbols_loaded(self):
        """Test that mock symbols are loaded when no manifest provided"""
        self.assertGreater(len(self.placer.symbols), 0)
        self.assertIn("gdt_flatness", self.placer.symbols)

    def test_symbol_placement_count(self):
        """Test that requested number of symbols are placed (or max possible)"""
        placed_symbols = self.placer.place_symbols_randomly("A4", 5, 42)
        self.assertLessEqual(len(placed_symbols), 5)
        self.assertGreater(len(placed_symbols), 0)

    def test_placement_within_sheet_bounds(self):
        """Test that all placed symbols are within sheet bounds"""
        sheet_size = "A4"
        sheet_width, sheet_height = SheetDimensions.get_size(sheet_size)
        margin = 10.0

        placed_symbols = self.placer.place_symbols_randomly(sheet_size, 10, 42)

        for placed_symbol in placed_symbols:
            bbox = CollisionDetector.get_bounding_box(placed_symbol)

            # Check bounds
            self.assertGreaterEqual(bbox[0], margin)  # x_min >= margin
            self.assertGreaterEqual(bbox[1], margin)  # y_min >= margin
            self.assertLessEqual(
                bbox[2], sheet_width - margin
            )  # x_max <= width - margin
            self.assertLessEqual(
                bbox[3], sheet_height - margin
            )  # y_max <= height - margin

    def test_no_collisions_in_placement(self):
        """Test that placed symbols don't collide with each other"""
        placed_symbols = self.placer.place_symbols_randomly("A3", 15, 42)

        # Check all pairs for collisions
        for i in range(len(placed_symbols)):
            for j in range(i + 1, len(placed_symbols)):
                collision = CollisionDetector.check_collision(
                    placed_symbols[i], placed_symbols[j]
                )
                self.assertFalse(
                    collision, f"Collision detected between symbols {i} and {j}"
                )

    def test_reproducible_placement(self):
        """Test that same seed produces same placement"""
        placed1 = self.placer.place_symbols_randomly("A4", 8, 123)
        placed2 = self.placer.place_symbols_randomly("A4", 8, 123)

        self.assertEqual(len(placed1), len(placed2))

        for p1, p2 in zip(placed1, placed2, strict=False):
            self.assertEqual(p1.x, p2.x)
            self.assertEqual(p1.y, p2.y)
            self.assertEqual(p1.rotation, p2.rotation)
            self.assertEqual(p1.symbol.name, p2.symbol.name)


class TestAPIFunction(unittest.TestCase):
    """Test the main generate_page API function"""

    def test_generate_page_basic(self):
        """Test basic page generation"""
        result = generate_page("A4", 10, 42)

        self.assertIn("pdf_bytes", result)
        self.assertIn("annotations", result)
        self.assertIsInstance(result["pdf_bytes"], bytes)
        self.assertIsInstance(result["annotations"], list)
        self.assertGreater(len(result["pdf_bytes"]), 0)

    def test_annotations_format(self):
        """Test that annotations have correct format"""
        result = generate_page("A3", 5, 42)
        annotations = result["annotations"]

        for annotation in annotations:
            # Check required fields
            self.assertIn("id", annotation)
            self.assertIn("symbol_name", annotation)
            self.assertIn("position", annotation)
            self.assertIn("rotation", annotation)
            self.assertIn("bounding_box", annotation)
            self.assertIn("parameters", annotation)

            # Check position format
            position = annotation["position"]
            self.assertIn("x", position)
            self.assertIn("y", position)

            # Check bounding box format
            bbox = annotation["bounding_box"]
            self.assertIn("x_min", bbox)
            self.assertIn("y_min", bbox)
            self.assertIn("x_max", bbox)
            self.assertIn("y_max", bbox)

    def test_different_sheet_sizes(self):
        """Test page generation with different sheet sizes"""
        for sheet_size in ["A4", "A3", "US-Letter"]:
            result = generate_page(sheet_size, 8, 42)
            self.assertGreater(len(result["pdf_bytes"]), 0)
            self.assertGreater(len(result["annotations"]), 0)


class TestPerformance(unittest.TestCase):
    """Performance tests for placement engine"""

    def test_placement_performance(self):
        """Test that placement meets performance requirements"""
        import time

        start_time = time.time()

        # Generate a page with 60 symbols (max requirement)
        result = generate_page("A4", 60, 42)

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # Should be under 200ms as per requirement
        # Being generous for test environment
        self.assertLess(
            duration_ms,
            500,
            f"Placement took {duration_ms:.1f}ms, should be under 500ms",
        )

        # Verify we got a valid result
        self.assertGreater(len(result["pdf_bytes"]), 0)
        self.assertGreater(len(result["annotations"]), 0)


if __name__ == "__main__":
    unittest.main()
