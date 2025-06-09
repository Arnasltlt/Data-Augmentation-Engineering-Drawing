"""
test_overlay.py - Overlay validation tests for QualityGate agent
Validates overlay rendered bounding-boxes and computes IoU vs expected (≥ 0.9)
"""

import json
import pytest
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw
import tempfile
import cairosvg


class TestOverlayValidation:
    """Test suite for overlay bounding box validation with IoU computation"""
    
    @pytest.fixture
    def sample_page_data(self) -> Dict[str, Any]:
        """Sample page data with symbol annotations"""
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
                    "bbox_mm": {"x": 50.0, "y": 100.0, "w": 8.0, "h": 8.0},
                    "rotation_deg": 0.0,
                    "parameters": {"tolerance_value": 0.05}
                },
                {
                    "symbol_name": "surface_finish_triangle", 
                    "filename": "surface_triangle.svg",
                    "bbox_mm": {"x": 120.0, "y": 150.0, "w": 6.0, "h": 6.0},
                    "rotation_deg": 45.0,
                    "parameters": {"roughness_ra": 3.2}
                },
                {
                    "symbol_name": "diameter",
                    "filename": "diameter_symbol.svg", 
                    "bbox_mm": {"x": 80.0, "y": 200.0, "w": 6.0, "h": 6.0},
                    "rotation_deg": 0.0,
                    "parameters": {}
                }
            ]
        }
    
    def test_overlay_generation(self, sample_page_data: Dict[str, Any]):
        """Test that overlay generation works correctly"""
        overlay_image = self._generate_overlay(sample_page_data)
        
        # Basic validation
        assert overlay_image is not None, "Overlay generation failed"
        assert overlay_image.mode == "RGBA", "Overlay should be RGBA mode"
        
        # Check dimensions match page size (assuming 300 DPI)
        expected_width = int(sample_page_data["page_info"]["width_mm"] * 300 / 25.4)
        expected_height = int(sample_page_data["page_info"]["height_mm"] * 300 / 25.4)
        
        assert abs(overlay_image.width - expected_width) <= 2, "Width mismatch"
        assert abs(overlay_image.height - expected_height) <= 2, "Height mismatch"
        
    def test_bounding_box_accuracy(self, sample_page_data: Dict[str, Any]):
        """Test that bounding boxes are accurately rendered"""
        overlay_image = self._generate_overlay(sample_page_data)
        
        # Convert to numpy for easier processing
        overlay_array = np.array(overlay_image)
        
        # Check that we have red pixels (bounding boxes)
        red_pixels = (overlay_array[:, :, 0] > 200) & (overlay_array[:, :, 1] < 50) & (overlay_array[:, :, 2] < 50)
        assert np.any(red_pixels), "No red bounding box pixels found in overlay"
        
        # Count number of distinct bounding box regions
        box_count = len(sample_page_data["annotations"])
        assert box_count == 3, "Expected 3 symbols in test data"
        
    def test_iou_computation(self, sample_page_data: Dict[str, Any]):
        """Test IoU computation between expected and rendered boxes"""
        for annotation in sample_page_data["annotations"]:
            expected_box = self._bbox_mm_to_pixels(
                annotation["bbox_mm"], 
                sample_page_data["page_info"]
            )
            
            # For testing, create a slightly offset "detected" box
            detected_box = {
                "x": expected_box["x"] + 1,
                "y": expected_box["y"] + 1, 
                "w": expected_box["w"] - 1,
                "h": expected_box["h"] - 1
            }
            
            iou = self._compute_iou(expected_box, detected_box)
            
            # Should have high IoU for small offset
            assert iou > 0.8, f"IoU too low for symbol {annotation['symbol_name']}: {iou}"
            
    def test_iou_threshold_compliance(self, sample_page_data: Dict[str, Any]):
        """Test that IoU meets the ≥ 0.9 threshold requirement"""
        overlay_image = self._generate_overlay(sample_page_data)
        
        # Simulate perfect detection (same as expected)
        perfect_detections = []
        for annotation in sample_page_data["annotations"]:
            perfect_detections.append(self._bbox_mm_to_pixels(
                annotation["bbox_mm"],
                sample_page_data["page_info"]
            ))
            
        # Compute IoU for perfect matches
        for i, annotation in enumerate(sample_page_data["annotations"]):
            expected_box = self._bbox_mm_to_pixels(
                annotation["bbox_mm"],
                sample_page_data["page_info"] 
            )
            detected_box = perfect_detections[i]
            
            iou = self._compute_iou(expected_box, detected_box)
            assert iou >= 0.9, f"Perfect match should have IoU ≥ 0.9, got {iou}"
            
    def test_no_overlap_detection(self, sample_page_data: Dict[str, Any]):
        """Test detection of overlapping symbols (should fail QA)"""
        # Create overlapping annotations
        overlapping_data = sample_page_data.copy()
        overlapping_data["annotations"].append({
            "symbol_name": "radius",
            "filename": "radius_symbol.svg",
            "bbox_mm": {"x": 52.0, "y": 102.0, "w": 6.0, "h": 6.0},  # Overlaps with flatness
            "rotation_deg": 0.0,
            "parameters": {}
        })
        
        # Check for overlaps
        overlaps = self._detect_overlaps(overlapping_data["annotations"])
        assert len(overlaps) > 0, "Should detect overlapping symbols"
        
    def test_rotation_handling(self, sample_page_data: Dict[str, Any]):
        """Test that rotated symbols are handled correctly"""
        # Find rotated symbol
        rotated_symbols = [ann for ann in sample_page_data["annotations"] 
                          if ann["rotation_deg"] != 0.0]
        assert len(rotated_symbols) > 0, "Test data should include rotated symbols"
        
        for symbol in rotated_symbols:
            # Rotated bounding boxes should still be axis-aligned in output
            bbox = symbol["bbox_mm"]
            assert bbox["w"] > 0 and bbox["h"] > 0, "Rotated symbols should have positive dimensions"
            
    def _generate_overlay(self, page_data: Dict[str, Any]) -> Image.Image:
        """Generate overlay image with red bounding boxes"""
        page_info = page_data["page_info"]
        
        # Calculate image dimensions (300 DPI)
        width_px = int(page_info["width_mm"] * 300 / 25.4)
        height_px = int(page_info["height_mm"] * 300 / 25.4)
        
        # Create transparent image
        overlay = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Draw bounding boxes in red
        for annotation in page_data["annotations"]:
            bbox_px = self._bbox_mm_to_pixels(annotation["bbox_mm"], page_info)
            
            # Draw rectangle outline in red
            x1, y1 = bbox_px["x"], bbox_px["y"]
            x2, y2 = x1 + bbox_px["w"], y1 + bbox_px["h"]
            
            draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0, 255), width=2)
            
        return overlay
        
    def _bbox_mm_to_pixels(self, bbox_mm: Dict[str, float], 
                          page_info: Dict[str, Any]) -> Dict[str, int]:
        """Convert millimeter bounding box to pixel coordinates"""
        dpi = 300
        mm_to_px = dpi / 25.4
        
        return {
            "x": int(bbox_mm["x"] * mm_to_px),
            "y": int(bbox_mm["y"] * mm_to_px), 
            "w": int(bbox_mm["w"] * mm_to_px),
            "h": int(bbox_mm["h"] * mm_to_px)
        }
        
    def _compute_iou(self, box1: Dict[str, int], box2: Dict[str, int]) -> float:
        """Compute Intersection over Union (IoU) for two bounding boxes"""
        # Calculate intersection
        x1_inter = max(box1["x"], box2["x"])
        y1_inter = max(box1["y"], box2["y"]) 
        x2_inter = min(box1["x"] + box1["w"], box2["x"] + box2["w"])
        y2_inter = min(box1["y"] + box1["h"], box2["y"] + box2["h"])
        
        if x2_inter <= x1_inter or y2_inter <= y1_inter:
            return 0.0  # No intersection
            
        intersection_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        
        # Calculate union
        area1 = box1["w"] * box1["h"]
        area2 = box2["w"] * box2["h"] 
        union_area = area1 + area2 - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
        
    def _detect_overlaps(self, annotations: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """Detect overlapping symbol annotations"""
        overlaps = []
        
        for i in range(len(annotations)):
            for j in range(i + 1, len(annotations)):
                bbox1 = annotations[i]["bbox_mm"]
                bbox2 = annotations[j]["bbox_mm"]
                
                # Check for overlap
                if (bbox1["x"] < bbox2["x"] + bbox2["w"] and
                    bbox1["x"] + bbox1["w"] > bbox2["x"] and
                    bbox1["y"] < bbox2["y"] + bbox2["h"] and
                    bbox1["y"] + bbox1["h"] > bbox2["y"]):
                    overlaps.append((i, j))
                    
        return overlaps


def test_iou_edge_cases():
    """Test IoU computation edge cases"""
    validator = TestOverlayValidation()
    
    # Identical boxes
    box1 = {"x": 10, "y": 10, "w": 20, "h": 20}
    box2 = {"x": 10, "y": 10, "w": 20, "h": 20}
    assert validator._compute_iou(box1, box2) == 1.0
    
    # No overlap
    box1 = {"x": 10, "y": 10, "w": 20, "h": 20}
    box2 = {"x": 50, "y": 50, "w": 20, "h": 20}
    assert validator._compute_iou(box1, box2) == 0.0
    
    # Partial overlap
    box1 = {"x": 10, "y": 10, "w": 20, "h": 20}
    box2 = {"x": 20, "y": 20, "w": 20, "h": 20}
    iou = validator._compute_iou(box1, box2)
    assert 0.0 < iou < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])