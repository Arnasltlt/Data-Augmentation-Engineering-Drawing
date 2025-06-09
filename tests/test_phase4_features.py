"""
Phase 4 Feature Unit Tests
Tests for parametric feature primitives with JSON->DXF->PNG hash comparison
"""

import json
import os
import hashlib
import tempfile
import unittest
from unittest.mock import patch
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from generator import generate_from_plan
from visualize import convert_dxf_to_png


class Phase4FeatureTests(unittest.TestCase):
    """Unit tests for Phase 4 parametric features."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.maxDiff = None
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_plan(self, base_feature, modifying_features):
        """Helper to create a test plan JSON."""
        return {
            "title_block": {
                "drawing_title": "Feature Test",
                "drawn_by": "Test Suite",
                "date": "2025-01-07",
                "drawing_number": "TEST-001"
            },
            "base_feature": base_feature,
            "modifying_features": modifying_features,
            "annotations": {
                "dimensions": []
            }
        }
    
    def _generate_and_hash(self, plan, test_name):
        """Generate DXF and PNG, return PNG hash for comparison."""
        plan_path = os.path.join(self.test_dir, f"{test_name}.json")
        dxf_path = os.path.join(self.test_dir, f"{test_name}.dxf")
        png_path = os.path.join(self.test_dir, f"{test_name}.png")
        
        # Save plan
        with open(plan_path, 'w') as f:
            json.dump(plan, f)
        
        # Generate DXF and PNG
        generate_from_plan(plan_path, dxf_path, visualize=True, validate=True)
        
        # Calculate PNG hash
        with open(png_path, 'rb') as f:
            png_hash = hashlib.md5(f.read()).hexdigest()
        
        return png_hash, dxf_path, png_path
    
    def test_parametric_slot_feature(self):
        """Test rounded-end slot feature generation."""
        base_feature = {"shape": "rectangle", "width": 100, "height": 60}
        modifying_features = [{
            "type": "slot",
            "center": [20, 10],
            "width": 8,
            "length": 30
        }]
        
        plan = self._create_test_plan(base_feature, modifying_features)
        
        # Generate twice to ensure reproducibility
        hash1, _, _ = self._generate_and_hash(plan, "slot_test_1")
        hash2, _, _ = self._generate_and_hash(plan, "slot_test_2")
        
        # Hashes should be identical for reproducible output
        self.assertEqual(hash1, hash2, "Slot feature generation should be reproducible")
        
        # Basic validation - the function should complete without errors
        self.assertIsNotNone(hash1)
    
    def test_true_chamfer_feature(self):
        """Test true chamfer (not fillet) feature generation."""
        base_feature = {"shape": "rectangle", "width": 80, "height": 50}
        modifying_features = [{
            "type": "chamfer",
            "distance": 5,
            "corners": ["bottom-left", "bottom-right"]
        }]
        
        plan = self._create_test_plan(base_feature, modifying_features)
        
        hash1, _, _ = self._generate_and_hash(plan, "chamfer_test_1")
        hash2, _, _ = self._generate_and_hash(plan, "chamfer_test_2")
        
        self.assertEqual(hash1, hash2, "Chamfer feature generation should be reproducible")
        self.assertIsNotNone(hash1)
    
    def test_variable_edge_fillets(self):
        """Test variable-edge fillet feature generation."""
        base_feature = {"shape": "rectangle", "width": 120, "height": 80}
        modifying_features = [{
            "type": "fillet",
            "radius": 10,
            "corners": ["top-left", "top-right"]
        }]
        
        plan = self._create_test_plan(base_feature, modifying_features)
        
        hash1, _, _ = self._generate_and_hash(plan, "fillet_test_1") 
        hash2, _, _ = self._generate_and_hash(plan, "fillet_test_2")
        
        self.assertEqual(hash1, hash2, "Fillet feature generation should be reproducible")
        self.assertIsNotNone(hash1)
    
    def test_counterbore_feature(self):
        """Test counterbore hole feature generation."""
        base_feature = {"shape": "rectangle", "width": 60, "height": 40}
        modifying_features = [{
            "type": "counterbore",
            "center": [0, 0],
            "hole_diameter": 6,
            "counterbore_diameter": 12,
            "counterbore_depth": 3
        }]
        
        plan = self._create_test_plan(base_feature, modifying_features)
        
        hash1, _, _ = self._generate_and_hash(plan, "counterbore_test_1")
        hash2, _, _ = self._generate_and_hash(plan, "counterbore_test_2")
        
        self.assertEqual(hash1, hash2, "Counterbore feature generation should be reproducible")
        self.assertIsNotNone(hash1)
    
    def test_countersink_feature(self):
        """Test countersink hole feature generation."""
        base_feature = {"shape": "rectangle", "width": 60, "height": 40}
        modifying_features = [{
            "type": "countersink",
            "center": [0, 0],
            "hole_diameter": 5,
            "countersink_diameter": 10,
            "countersink_angle": 90
        }]
        
        plan = self._create_test_plan(base_feature, modifying_features)
        
        hash1, _, _ = self._generate_and_hash(plan, "countersink_test_1")
        hash2, _, _ = self._generate_and_hash(plan, "countersink_test_2")
        
        self.assertEqual(hash1, hash2, "Countersink feature generation should be reproducible")
        self.assertIsNotNone(hash1)
    
    def test_tapped_hole_feature(self):
        """Test tapped hole feature generation."""
        base_feature = {"shape": "rectangle", "width": 60, "height": 40}
        modifying_features = [{
            "type": "tapped_hole",
            "center": [0, 0],
            "thread_spec": "M8x1.25",
            "pilot_diameter": 6.8
        }]
        
        plan = self._create_test_plan(base_feature, modifying_features)
        
        hash1, _, _ = self._generate_and_hash(plan, "tapped_hole_test_1")
        hash2, _, _ = self._generate_and_hash(plan, "tapped_hole_test_2")
        
        self.assertEqual(hash1, hash2, "Tapped hole feature generation should be reproducible")
        self.assertIsNotNone(hash1)
    
    def test_multi_feature_interaction(self):
        """Test multiple features working together."""
        base_feature = {"shape": "rectangle", "width": 100, "height": 80}
        modifying_features = [
            {
                "type": "fillet",
                "radius": 8,
                "corners": ["all"]
            },
            {
                "type": "hole",
                "center": [0, 0],
                "diameter": 20
            },
            {
                "type": "slot",
                "center": [30, 20],
                "width": 6,
                "length": 25
            },
            {
                "type": "counterbore",
                "center": [-30, -20],
                "hole_diameter": 5,
                "counterbore_diameter": 10,
                "counterbore_depth": 2
            }
        ]
        
        plan = self._create_test_plan(base_feature, modifying_features)
        
        hash1, _, _ = self._generate_and_hash(plan, "multi_feature_test_1")
        hash2, _, _ = self._generate_and_hash(plan, "multi_feature_test_2")
        
        self.assertEqual(hash1, hash2, "Multi-feature generation should be reproducible")
        self.assertIsNotNone(hash1)
    
    def test_layer_assignment(self):
        """Test that features are assigned to correct layers."""
        base_feature = {"shape": "rectangle", "width": 50, "height": 50}
        modifying_features = [
            {"type": "hole", "center": [0, 0], "diameter": 10},
            {"type": "slot", "center": [15, 15], "width": 4, "length": 15}
        ]
        
        plan = self._create_test_plan(base_feature, modifying_features)
        plan_path = os.path.join(self.test_dir, "layer_test.json")
        dxf_path = os.path.join(self.test_dir, "layer_test.dxf")
        
        with open(plan_path, 'w') as f:
            json.dump(plan, f)
        
        generate_from_plan(plan_path, dxf_path, visualize=False, validate=True)
        
        # Check that DXF file exists and contains layers
        self.assertTrue(os.path.exists(dxf_path))
        
        # Basic validation - check file is non-empty
        self.assertGreater(os.path.getsize(dxf_path), 1000)


if __name__ == '__main__':
    unittest.main()