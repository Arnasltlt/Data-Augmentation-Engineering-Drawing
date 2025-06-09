#!/usr/bin/env python3
"""
Test script for Milestone 1: 3D Core functionality
Exit test: Plan with 5 features renders isometric view; area diff <1% vs 2D.
"""

import json
import os
import sys
import tempfile

# Try to import the solid builder with fallback
try:
    from solidbuilder_ocp import SolidBuilder, ProjectionType
    print("✅ Using real OCP-based SolidBuilder for tests")
except ImportError:
    try:
        from solidbuilder_mock import SolidBuilder, ProjectionType
        print("⚠️ Using mock SolidBuilder for tests (install cadquery and OCP for full functionality)")
    except ImportError:
        print("❌ No SolidBuilder available")
        sys.exit(1)

def create_test_plan():
    """Create a test plan with 5 features as specified in Milestone 1 exit test."""
    test_plan = {
        "base_feature": {
            "shape": "rectangle",
            "width": 80,
            "height": 60,
            "thickness": 10
        },
        "modifying_features": [
            {
                "type": "hole",
                "center": [20, 15],
                "diameter": 6
            },
            {
                "type": "hole", 
                "center": [-20, 15],
                "diameter": 6
            },
            {
                "type": "slot",
                "center": [0, -15],
                "width": 8,
                "length": 25
            },
            {
                "type": "fillet",
                "radius": 3,
                "corners": ["all"]
            },
            {
                "type": "chamfer",
                "distance": 1.5,
                "corners": ["all"]
            }
        ],
        "title_block": {
            "drawing_title": "Milestone 1 Test Bracket",
            "drawing_number": "M1-TEST-001",
            "material": "AL 6061-T6",
            "revision": "A"
        }
    }
    return test_plan

def calculate_2d_area(plan):
    """Calculate approximate 2D area from plan geometry."""
    base_feature = plan["base_feature"]
    if base_feature["shape"] == "rectangle":
        base_area = base_feature["width"] * base_feature["height"]
    elif base_feature["shape"] == "circle":
        radius = base_feature["diameter"] / 2
        base_area = 3.14159 * radius * radius
    else:
        return 0
    
    # Subtract hole areas
    hole_area = 0
    for feature in plan.get("modifying_features", []):
        if feature["type"] == "hole":
            radius = feature["diameter"] / 2
            hole_area += 3.14159 * radius * radius
        elif feature["type"] == "slot":
            # Approximate slot area as rectangle with rounded ends
            width = feature["width"]
            length = feature["length"]
            slot_area = width * length + 3.14159 * (width/2)**2
            hole_area += slot_area
    
    return max(0, base_area - hole_area)

def test_solid_building():
    """Test the basic solid building functionality."""
    print("🧪 Testing solid building functionality...")
    
    test_plan = create_test_plan()
    builder = SolidBuilder()
    
    # Test solid building
    success = builder.build_from_plan(test_plan)
    if not success:
        print("❌ Failed to build solid from test plan")
        return False
    
    # Get solid info
    solid_info = builder.get_solid_info()
    print(f"✅ Solid built successfully:")
    print(f"   Volume: {solid_info.get('volume', 0):.2f} mm³")
    print(f"   Features: {len(solid_info.get('construction_history', []))}")
    
    # Verify we have the expected number of features
    expected_features = len(test_plan["modifying_features"]) + 1  # +1 for base feature
    actual_features = len(solid_info.get('construction_history', []))
    
    if actual_features != expected_features:
        print(f"⚠️ Feature count mismatch: expected {expected_features}, got {actual_features}")
    
    return True

def test_projections():
    """Test projection generation for different views."""
    print("🧪 Testing projection generation...")
    
    test_plan = create_test_plan()
    builder = SolidBuilder()
    
    if not builder.build_from_plan(test_plan):
        print("❌ Failed to build solid for projection test")
        return False
    
    # Test different projection types
    projection_types = [
        ProjectionType.ISOMETRIC,
        ProjectionType.FRONT,
        ProjectionType.TOP,
        ProjectionType.RIGHT
    ]
    
    results = {}
    for proj_type in projection_types:
        edges = builder.get_projection_edges(proj_type)
        results[proj_type.value] = len(edges)
        print(f"   {proj_type.value}: {len(edges)} edges")
    
    if results["isometric"] == 0:
        print("❌ Failed to generate isometric projection")
        return False
    
    print("✅ All projection types generated successfully")
    return True

def test_area_comparison():
    """Test area comparison between 2D and 3D projected area."""
    print("🧪 Testing area comparison (Exit Test)...")
    
    test_plan = create_test_plan()
    
    # Calculate 2D theoretical area
    area_2d = calculate_2d_area(test_plan)
    print(f"   2D theoretical area: {area_2d:.2f} mm²")
    
    # Build 3D solid and get projection
    builder = SolidBuilder()
    if not builder.build_from_plan(test_plan):
        print("❌ Failed to build solid for area test")
        return False
    
    # Get solid surface area and net XY projection area
    solid_info = builder.get_solid_info()
    
    # Use the net XY area that accounts for removed features
    net_xy_area = solid_info.get('net_xy_area', 0)
    if net_xy_area == 0:
        # Fallback to bounding box calculation
        bbox = solid_info.get('bounding_box', {})
        net_xy_area = (bbox.get('x_max', 0) - bbox.get('x_min', 0)) * (bbox.get('y_max', 0) - bbox.get('y_min', 0))
    
    print(f"   3D net XY area: {net_xy_area:.2f} mm²")
    print(f"   Removed area: {solid_info.get('removed_area', 0):.2f} mm²")
    
    # Calculate area difference percentage
    if area_2d > 0:
        area_diff_pct = abs(net_xy_area - area_2d) / area_2d * 100
        print(f"   Area difference: {area_diff_pct:.2f}%")
        
        # Exit test requirement: <1% difference
        if area_diff_pct < 1.0:
            print("✅ Area difference <1% - EXIT TEST PASSED")
            return True
        else:
            print(f"❌ Area difference {area_diff_pct:.2f}% exceeds 1% threshold")
            return False
    else:
        print("❌ Invalid 2D area calculation")
        return False

def test_file_export():
    """Test file export functionality."""
    print("🧪 Testing file export...")
    
    test_plan = create_test_plan()
    builder = SolidBuilder()
    
    if not builder.build_from_plan(test_plan):
        print("❌ Failed to build solid for export test")
        return False
    
    # Test STEP export
    with tempfile.NamedTemporaryFile(suffix='.step', delete=False) as tmp:
        step_path = tmp.name
    
    try:
        if builder.export_step(step_path):
            file_size = os.path.getsize(step_path)
            print(f"✅ STEP export successful: {file_size} bytes")
        else:
            print("❌ STEP export failed")
            return False
    finally:
        # Clean up
        if os.path.exists(step_path):
            os.remove(step_path)
    
    return True

def main():
    """Run all Milestone 1 tests."""
    print("🚀 Running Milestone 1: 3D Core Tests")
    print("=" * 50)
    
    tests = [
        ("Solid Building", test_solid_building),
        ("Projection Generation", test_projections),
        ("Area Comparison (Exit Test)", test_area_comparison),
        ("File Export", test_file_export)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All Milestone 1 tests PASSED!")
        print("✅ Ready to proceed to Milestone 2: Multi-View Sheet")
        return 0
    else:
        print("❌ Some tests failed. Review implementation before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())