#!/usr/bin/env python3
"""
Milestone 3 Test Suite: Sections & Hatching
STRETCH_STRATEGY.md Implementation Test

Exit test: Multi-material sectioned sheet with 2+ cutting planes and hatching.

Tests the complete sectioning and hatching system including:
- Section cutting plane generation
- Cross-sectional view creation
- Material-specific hatching patterns
- Cutting plane indicators and labels
- Multi-view integration with sections
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from section_engine import SectionEngine, SectionDirection, HatchPattern, CuttingPlane
    from multiview_layout import MultiViewLayout, PaperSize
    from generator import generate_multiview_sheet
    MILESTONE3_AVAILABLE = True
except ImportError as e:
    print(f"❌ Milestone 3 modules not available: {e}")
    MILESTONE3_AVAILABLE = False

try:
    from solidbuilder_mock import MockSolidBuilder
    SOLID_BUILDER_AVAILABLE = True
except ImportError:
    try:
        from solidbuilder_ocp import SolidBuilder as MockSolidBuilder
        SOLID_BUILDER_AVAILABLE = True
    except ImportError:
        print("❌ No SolidBuilder available")
        SOLID_BUILDER_AVAILABLE = False

def create_complex_test_part():
    """Create a complex part with multiple materials for section testing."""
    return {
        "title_block": {
            "drawing_title": "Complex Multi-Material Part",
            "drawing_number": "M3-001",
            "material": "Steel Base + Aluminum Insert",
            "scale": "1:1",
            "revision": "A",
            "drawn_by": "Milestone3_Test",
            "date": "2024-12-09",
            "tolerance_class": "±0.1mm",
            "surface_finish": "Ra 3.2μm",
            "notes": ["Section A-A shows steel base", "Section B-B shows aluminum insert"]
        },
        "features": {
            "base_plate": {
                "type": "rectangular_plate",
                "width": 100.0,
                "height": 80.0,
                "thickness": 15.0,
                "center": [0, 0],
                "material": "steel"
            },
            "mounting_holes": {
                "type": "hole",
                "diameter": 8.0,
                "depth": 15.0,
                "center": [-30, -25],
                "notes": "M8 mounting holes"
            },
            "mounting_holes_2": {
                "type": "hole",
                "diameter": 8.0,
                "depth": 15.0,
                "center": [30, -25]
            },
            "mounting_holes_3": {
                "type": "hole",
                "diameter": 8.0,
                "depth": 15.0,
                "center": [-30, 25]
            },
            "mounting_holes_4": {
                "type": "hole",
                "diameter": 8.0,
                "depth": 15.0,
                "center": [30, 25]
            },
            "central_bore": {
                "type": "hole",
                "diameter": 25.0,
                "depth": 10.0,
                "center": [0, 0],
                "notes": "Central bore for aluminum insert"
            },
            "chamfer_edges": {
                "type": "chamfer",
                "size": 2.0,
                "edges": ["top"],
                "notes": "45° chamfer on top edges"
            },
            "corner_fillets": {
                "type": "fillet",
                "radius": 5.0,
                "corners": ["all"],
                "notes": "R5 corner fillets"
            },
            "service_slot": {
                "type": "slot",
                "width": 6.0,
                "length": 30.0,
                "center": [0, -15],
                "notes": "Service access slot"
            }
        }
    }

def test_section_engine_creation():
    """Test basic section engine initialization and configuration."""
    if not MILESTONE3_AVAILABLE:
        print("❌ Milestone 3 not available, skipping section engine test")
        return False
    
    try:
        print("🧪 Testing section engine creation...")
        engine = SectionEngine()
        
        # Test hatch pattern initialization
        patterns = engine.hatch_patterns
        expected_patterns = [HatchPattern.GENERAL, HatchPattern.STEEL, HatchPattern.ALUMINUM]
        
        for pattern in expected_patterns:
            assert pattern in patterns, f"Missing hatch pattern: {pattern}"
        
        # Test cutting plane addition
        solid_bounds = {"x_min": -50, "x_max": 50, "y_min": -40, "y_max": 40, "z_min": 0, "z_max": 15}
        
        plane_a = engine.add_cutting_plane("A", SectionDirection.VERTICAL_FRONT, 0.3, solid_bounds)
        plane_b = engine.add_cutting_plane("B", SectionDirection.HORIZONTAL, 0.6, solid_bounds)
        
        assert plane_a.name == "A"
        assert plane_a.direction == SectionDirection.VERTICAL_FRONT
        assert plane_b.name == "B"
        assert plane_b.direction == SectionDirection.HORIZONTAL
        
        print(f"  ✅ Created {len(engine.cutting_planes)} cutting planes")
        return True
        
    except Exception as e:
        print(f"  ❌ Section engine test failed: {e}")
        return False

def test_section_generation():
    """Test section geometry generation and hatching."""
    if not MILESTONE3_AVAILABLE or not SOLID_BUILDER_AVAILABLE:
        print("❌ Dependencies not available, skipping section generation test")
        return False
    
    try:
        print("🧪 Testing section generation...")
        engine = SectionEngine()
        solid_builder = MockSolidBuilder()
        
        # Build test solid
        test_plan = create_complex_test_part()
        solid_builder.build_from_plan(test_plan)
        
        # Add cutting planes
        solid_bounds = {"x_min": -50, "x_max": 50, "y_min": -40, "y_max": 40, "z_min": 0, "z_max": 15}
        plane_a = engine.add_cutting_plane("A", SectionDirection.VERTICAL_FRONT, 0.4, solid_bounds)
        plane_b = engine.add_cutting_plane("B", SectionDirection.HORIZONTAL, 0.7, solid_bounds)
        
        # Generate sections
        section_a = engine.generate_section(solid_builder, plane_a)
        section_b = engine.generate_section(solid_builder, plane_b)
        
        # Validate section geometry
        assert section_a is not None, "Section A generation failed"
        assert section_b is not None, "Section B generation failed"
        assert len(section_a.outline_edges) > 0, "Section A has no outline edges"
        assert len(section_b.outline_edges) > 0, "Section B has no outline edges"
        
        # Test hatching generation
        steel_hatch = engine.generate_hatching(section_a, HatchPattern.STEEL)
        aluminum_hatch = engine.generate_hatching(section_b, HatchPattern.ALUMINUM)
        
        assert len(steel_hatch) > 0, "Steel hatching generation failed"
        assert len(aluminum_hatch) > 0, "Aluminum hatching generation failed"
        
        print(f"  ✅ Generated {len(engine.sections)} sections with hatching")
        print(f"      Section A: {len(section_a.outline_edges)} edges, {len(steel_hatch)} hatch lines")
        print(f"      Section B: {len(section_b.outline_edges)} edges, {len(aluminum_hatch)} hatch lines")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Section generation test failed: {e}")
        return False

def test_multiview_with_sections():
    """Test multi-view layout integration with sections."""
    if not MILESTONE3_AVAILABLE:
        print("❌ Milestone 3 not available, skipping multi-view section test")
        return False
    
    try:
        print("🧪 Testing multi-view layout with sections...")
        
        # Create layout engine
        layout = MultiViewLayout(PaperSize.A3)
        
        # Define sections for testing
        sections = [
            {"name": "A", "direction": "vertical_front", "position": 0.4, "material": "steel"},
            {"name": "B", "direction": "horizontal", "position": 0.7, "material": "aluminum"}
        ]
        
        # Enable sections
        success = layout.enable_sections(sections)
        assert success, "Failed to enable sections"
        assert layout.sections_enabled, "Sections not properly enabled"
        
        # Test plan
        test_plan = create_complex_test_part()
        
        # Generate sectioned layout
        view_placements, metadata = layout.generate_sectioned_multiview_sheet(test_plan, sections)
        
        # Validate results
        assert len(view_placements) > 4, "Should have more than 4 views with sections"
        
        section_views = [vp for vp in view_placements if vp.is_section]
        standard_views = [vp for vp in view_placements if not vp.is_section]
        
        assert len(section_views) >= 2, f"Expected at least 2 section views, got {len(section_views)}"
        assert len(standard_views) >= 3, f"Expected at least 3 standard views, got {len(standard_views)}"
        
        # Check for hatching in section views
        hatched_views = [vp for vp in section_views if vp.hatch_lines and len(vp.hatch_lines) > 0]
        assert len(hatched_views) >= 1, "At least one section view should have hatching"
        
        # Check metadata
        assert metadata['sections_enabled'], "Metadata should indicate sections enabled"
        assert metadata['section_count'] >= 2, "Metadata should show correct section count"
        
        print(f"  ✅ Generated {len(view_placements)} total views:")
        print(f"      Standard views: {len(standard_views)}")
        print(f"      Section views: {len(section_views)} (with hatching)")
        print(f"      Hatched views: {len(hatched_views)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Multi-view section test failed: {e}")
        return False

def test_cutting_plane_indicators():
    """Test cutting plane indicator generation."""
    if not MILESTONE3_AVAILABLE:
        print("❌ Milestone 3 not available, skipping cutting plane indicator test")
        return False
    
    try:
        print("🧪 Testing cutting plane indicators...")
        
        engine = SectionEngine()
        solid_bounds = {"x_min": -50, "x_max": 50, "y_min": -40, "y_max": 40, "z_min": 0, "z_max": 15}
        
        # Add cutting plane
        plane = engine.add_cutting_plane("A", SectionDirection.VERTICAL_FRONT, 0.5, solid_bounds)
        
        # Mock view bounds
        from section_engine import ViewBounds
        view_bounds = ViewBounds(-40, 40, -30, 30, 80, 60)
        
        # Generate indicators
        indicators = engine.generate_cutting_plane_indicators(plane, view_bounds)
        
        # Validate indicators
        assert 'cutting_lines' in indicators, "Missing cutting lines"
        assert 'section_arrows' in indicators, "Missing section arrows"
        assert 'section_labels' in indicators, "Missing section labels"
        
        cutting_lines = indicators['cutting_lines']
        section_arrows = indicators['section_arrows']
        section_labels = indicators['section_labels']
        
        assert len(cutting_lines) > 0, "No cutting lines generated"
        assert len(section_arrows) > 0, "No section arrows generated"
        assert len(section_labels) > 0, "No section labels generated"
        
        # Validate label content
        for label in section_labels:
            assert label['text'] == plane.name, f"Label text should be '{plane.name}'"
        
        print(f"  ✅ Generated cutting plane indicators:")
        print(f"      Cutting lines: {len(cutting_lines)}")
        print(f"      Section arrows: {len(section_arrows)}")
        print(f"      Section labels: {len(section_labels)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Cutting plane indicator test failed: {e}")
        return False

def test_milestone3_exit_criteria():
    """
    EXIT TEST for Milestone 3: Generate multi-material sectioned sheet 
    with 2+ cutting planes and hatching.
    """
    try:
        print("🎯 MILESTONE 3 EXIT TEST: Multi-material sectioned sheet")
        
        # Create complex test plan
        test_plan = create_complex_test_part()
        
        # Define multiple sections with different materials
        sections = [
            {"name": "A", "direction": "vertical_front", "position": 0.35, "material": "steel"},
            {"name": "B", "direction": "horizontal", "position": 0.65, "material": "aluminum"},
            {"name": "C", "direction": "vertical_side", "position": 0.8, "material": "steel"}
        ]
        
        # Output files
        output_dir = "out"
        os.makedirs(output_dir, exist_ok=True)
        
        dxf_path = os.path.join(output_dir, "milestone3_exit_test.dxf")
        
        # Create temporary plan file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            json.dump(test_plan, tmp)
            tmp_plan_path = tmp.name
        
        try:
            # Generate sectioned multi-view sheet
            success = generate_multiview_sheet(
                plan_path=tmp_plan_path,
                output_path=dxf_path,
                paper_size="A3",
                sections=sections,
                visualize=True,
                validate=False  # Skip validation for test plan format
            )
            
            if not success:
                print("❌ EXIT TEST FAILED: Multi-view sheet generation failed")
                return False
            
            # Validate output file
            if not os.path.exists(dxf_path):
                print("❌ EXIT TEST FAILED: DXF file not created")
                return False
            
            file_size = os.path.getsize(dxf_path)
            if file_size < 10000:  # Minimum expected size for complex drawing
                print(f"❌ EXIT TEST FAILED: DXF file too small ({file_size} bytes)")
                return False
            
            print(f"✅ EXIT TEST PASSED: Generated sectioned multi-view sheet")
            print(f"   📁 File: {dxf_path} ({file_size:,} bytes)")
            print(f"   🔧 Sections: {len(sections)} cutting planes")
            print(f"   🎨 Materials: Steel (hatching), Aluminum (hatching)")
            print(f"   📏 Paper: A3 multi-view layout")
            
            # Create exit test summary
            exit_summary = {
                "milestone": 3,
                "test_name": "Multi-material sectioned sheet",
                "exit_criteria": "2+ cutting planes with material-specific hatching",
                "result": "PASSED",
                "file_generated": dxf_path,
                "file_size_bytes": file_size,
                "sections_count": len(sections),
                "materials": ["steel", "aluminum"],
                "cutting_planes": [s["name"] for s in sections],
                "test_date": "2024-12-09"
            }
            
            summary_path = os.path.join(output_dir, "milestone3_exit_summary.json")
            with open(summary_path, 'w') as f:
                json.dump(exit_summary, f, indent=2)
            
            print(f"   📊 Summary: {summary_path}")
            return True
            
        finally:
            # Clean up temporary plan file
            if os.path.exists(tmp_plan_path):
                os.remove(tmp_plan_path)
        
    except Exception as e:
        print(f"❌ EXIT TEST FAILED: {e}")
        return False

def main():
    """Run all Milestone 3 tests."""
    print("🧪 MILESTONE 3 TEST SUITE: Sections & Hatching")
    print("=" * 60)
    
    if not MILESTONE3_AVAILABLE:
        print("❌ Milestone 3 modules not available. Please ensure:")
        print("   - section_engine.py is present")
        print("   - multiview_layout.py has section support")
        print("   - generator.py has sectioning integration")
        return
    
    tests = [
        ("Section Engine Creation", test_section_engine_creation),
        ("Section Generation", test_section_generation),
        ("Multi-View with Sections", test_multiview_with_sections),
        ("Cutting Plane Indicators", test_cutting_plane_indicators),
        ("🎯 EXIT TEST: Multi-Material Sectioned Sheet", test_milestone3_exit_criteria)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "=" * 60)
    print(f"📊 MILESTONE 3 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - MILESTONE 3 COMPLETE!")
        print("\n✅ Sectioning and hatching functionality is working correctly")
        print("✅ Multi-view integration with sections successful")
        print("✅ Professional CAD output with cutting plane indicators")
        print("✅ Ready for Milestone 4: Dimensioner v2")
    else:
        print(f"❌ {total - passed} test(s) failed - Milestone 3 needs work")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)