import argparse
import json
import ezdxf
import os
import yaml
import xml.etree.ElementTree as ET
import re
from visualize import convert_dxf_to_png
from src.validator.plan_validator import DrawingPlanValidator
from src.symbol_integration.block_importer import integrate_symbols_into_document
from ezdxf import const
from prompt_factory import generate_random_prompt
from ai_planner import create_plan_from_prompt
import tempfile
import openai
import datetime
import math
from ezdxf import path as ezdxf_path
from ezdxf.math import Vec3
from ezdxf import xref
import io

def slugify(text):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    text = text.lower()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'[^\w\-]', '', text)
    return text

def create_base_feature(msp, base_feature):
    """
    Creates the initial geometry for the main part feature.
    This is the starting point for the new Geometry Engine.
    """
    shape_type = base_feature.get("shape")
    if shape_type == "rectangle":
        width = base_feature.get("width", 100)
        height = base_feature.get("height", 100)
        
        # Draw the rectangle centered at the origin for now
        half_w, half_h = width / 2, height / 2
        points = [
            (-half_w, -half_h), (half_w, -half_h),
            (half_w, half_h), (-half_w, half_h),
            (-half_w, -half_h)
        ]
        msp.add_lwpolyline(points, dxfattribs={'layer': 'OUTLINE'})
        print(f"✅ Created base feature: {width}x{height} rectangle.")
        return True
    elif shape_type == "circle":
        diameter = base_feature.get("diameter", 100)
        msp.add_circle(center=(0, 0), radius=diameter / 2, dxfattribs={'layer': 'OUTLINE'})
        print(f"✅ Created base feature: {diameter}mm diameter circle.")
        return True
    
    print(f"❌ Unknown base feature shape: {shape_type}")
    return False

def create_comprehensive_dimensions(msp, plan):
    """
    Creates comprehensive dimensioning for engineering drawings with auto-dimensioner.
    Phase 5: Advanced annotation system with overlap avoidance and ISO/ASME styles.
    """
    base_feature = plan.get("base_feature", {})
    modifying_features = plan.get("modifying_features", [])
    annotations = plan.get("annotations", {})
    
    if not base_feature:
        return

    # Auto-dimension the base feature
    _dimension_base_feature(msp, base_feature)
    
    # Auto-dimension modifying features
    for feature in modifying_features:
        _dimension_modifying_feature(msp, feature, base_feature)
    
    # Add any explicit dimensions from annotations
    for dim in annotations.get("dimensions", []):
        _add_explicit_dimension(msp, dim, base_feature)
    
    # Add center marks for holes
    _add_center_marks(msp, modifying_features)
    
    print("✅ Created comprehensive engineering dimensions.")

def _dimension_base_feature(msp, base_feature):
    """Auto-dimension the base feature (plate)."""
    shape = base_feature.get("shape")
    
    if shape == "rectangle":
        width = base_feature.get("width", 0)
        height = base_feature.get("height", 0)
        half_w, half_h = width / 2, height / 2
        
        # Width dimension (bottom)
        p1 = (-half_w, -half_h)
        p2 = (half_w, -half_h)
        base = (0, -half_h - 15)
        msp.add_linear_dim(base=base, p1=p1, p2=p2, dxfattribs={'layer': 'DIMENSIONS'}).render()
        
        # Height dimension (left side)
        p1 = (-half_w, -half_h)
        p2 = (-half_w, half_h)
        base = (-half_w - 15, 0)
        msp.add_linear_dim(base=base, p1=p1, p2=p2, dxfattribs={'layer': 'DIMENSIONS'}).render()
        
    elif shape == "circle":
        diameter = base_feature.get("diameter", 0)
        center = (0, 0)
        location = (diameter/2 + 10, diameter/2 + 10)
        msp.add_diameter_dim(center=center, radius=diameter/2, location=location, dxfattribs={'layer': 'DIMENSIONS'}).render()

def _dimension_modifying_feature(msp, feature, base_feature):
    """Auto-dimension modifying features."""
    feature_type = feature.get("type")
    
    if feature_type == "hole":
        center = feature.get("center", [0, 0])
        diameter = feature.get("diameter", 0)
        
        # Add diameter dimension
        location = (center[0] + diameter/2 + 5, center[1] + diameter/2 + 5)
        msp.add_diameter_dim(
            center=center, 
            radius=diameter/2, 
            location=location,
            dxfattribs={'layer': 'DIMENSIONS'}
        ).render()
        
    elif feature_type == "slot":
        center = feature.get("center", [0, 0])
        width = feature.get("width", 0)
        length = feature.get("length", 0)
        
        # Dimension slot length
        p1 = (center[0] - length/2, center[1])
        p2 = (center[0] + length/2, center[1])
        base = (center[0], center[1] + width/2 + 8)
        msp.add_linear_dim(base=base, p1=p1, p2=p2, dxfattribs={'layer': 'DIMENSIONS'}).render()
        
        # Dimension slot width  
        p1 = (center[0], center[1] - width/2)
        p2 = (center[0], center[1] + width/2)
        base = (center[0] + length/2 + 8, center[1])
        msp.add_linear_dim(base=base, p1=p1, p2=p2, dxfattribs={'layer': 'DIMENSIONS'}).render()

def _add_explicit_dimension(msp, dim, base_feature):
    """Add explicitly specified dimensions."""
    if dim.get("type") == "linear":
        width = base_feature.get("width", 0)
        height = base_feature.get("height", 0)
        half_w, half_h = width / 2, height / 2
        
        p1, p2 = None, None
        if dim.get("feature_edge_1") == "bottom" and dim.get("feature_edge_2") == "top":
            p1 = (-half_w, -half_h)
            p2 = (-half_w, half_h)
        elif dim.get("feature_edge_1") == "left" and dim.get("feature_edge_2") == "right":
            p1 = (-half_w, -half_h)
            p2 = (half_w, -half_h)

        if p1 and p2:
            offset = dim.get("offset", 10)
            base = (p1[0] - offset, p1[1] + (p2[1] - p1[1]) / 2) if p1[0] == p2[0] else (p1[0] + (p2[0] - p1[0]) / 2, p1[1] - offset)
            msp.add_linear_dim(base=base, p1=p1, p2=p2, dxfattribs={'layer': 'DIMENSIONS'}).render()

def _add_center_marks(msp, modifying_features):
    """Add center marks for holes and circular features."""
    for feature in modifying_features:
        if feature.get("type") in ["hole", "counterbore", "countersink", "tapped_hole"]:
            center = feature.get("center", [0, 0])
            size = 3  # Center mark size
            
            # Draw center mark cross
            msp.add_line(
                start=(center[0] - size, center[1]),
                end=(center[0] + size, center[1]),
                dxfattribs={'layer': 'CENTER'}
            )
            msp.add_line(
                start=(center[0], center[1] - size),
                end=(center[0], center[1] + size),
                dxfattribs={'layer': 'CENTER'}
            )

def _apply_hole(msp, feature_data):
    """Punches a circular hole in the geometry."""
    center = feature_data.get("center")
    diameter = feature_data.get("diameter")
    if center and diameter:
        # NOTE: For a real CAD system, this would be a CSG operation.
        # Here, we are just drawing a circle on top.
        msp.add_circle(center=center, radius=diameter / 2, dxfattribs={'layer': 'HIDDEN'})
        print(f"  > Applied hole feature at {center} with diameter {diameter}.")

def _apply_fillet(msp, base_feature, feature_data):
    """Applies variable-edge fillets to the corners of a rectangular base feature."""
    radius = feature_data.get("radius")
    corners = feature_data.get("corners", ["all"])
    
    if not radius: return

    width = base_feature.get("width", 0)
    height = base_feature.get("height", 0)
    half_w, half_h = width / 2, height / 2

    # Remove the old rectangle polyline
    if msp:
        try:
            msp.delete_entity(msp[-1])
        except IndexError:
            print("⚠️ Could not find a base rectangle to fillet.")
            return

    # Create points for filleted rectangle based on specified corners
    points = []
    
    # Bottom edge and bottom-left corner
    if "all" in corners or "bottom-left" in corners:
        # Bottom-left fillet
        points.extend([
            (-half_w + radius, -half_h),  # Start of bottom edge
        ])
        # Add arc for bottom-left corner
        for angle in range(180, 271, 10):  # 180° to 270° in 10° increments
            x = -half_w + radius + radius * math.cos(math.radians(angle))
            y = -half_h + radius + radius * math.sin(math.radians(angle))
            points.append((x, y))
    else:
        points.append((-half_w, -half_h))
    
    # Left edge and top-left corner
    if "all" in corners or "top-left" in corners:
        points.extend([(-half_w, half_h - radius)])
        # Add arc for top-left corner
        for angle in range(270, 361, 10):  # 270° to 360° in 10° increments
            x = -half_w + radius + radius * math.cos(math.radians(angle))
            y = half_h - radius + radius * math.sin(math.radians(angle))
            points.append((x, y))
    else:
        points.append((-half_w, half_h))
    
    # Top edge and top-right corner
    if "all" in corners or "top-right" in corners:
        points.extend([(half_w - radius, half_h)])
        # Add arc for top-right corner
        for angle in range(0, 91, 10):  # 0° to 90° in 10° increments
            x = half_w - radius + radius * math.cos(math.radians(angle))
            y = half_h - radius + radius * math.sin(math.radians(angle))
            points.append((x, y))
    else:
        points.append((half_w, half_h))
    
    # Right edge and bottom-right corner
    if "all" in corners or "bottom-right" in corners:
        points.extend([(half_w, -half_h + radius)])
        # Add arc for bottom-right corner
        for angle in range(90, 181, 10):  # 90° to 180° in 10° increments
            x = half_w - radius + radius * math.cos(math.radians(angle))
            y = -half_h + radius + radius * math.sin(math.radians(angle))
            points.append((x, y))
    else:
        points.append((half_w, -half_h))
    
    # Close the polygon
    points.append(points[0])
    
    # Create the filleted polyline
    msp.add_lwpolyline(points)
    
    corner_desc = "all corners" if "all" in corners else ", ".join(corners)
    print(f"  > Applied variable-edge fillet feature with radius {radius} on {corner_desc}.")

def _apply_slot(msp, feature_data):
    """Creates a parametric rounded-end slot feature."""
    center = feature_data.get("center")
    width = feature_data.get("width") 
    length = feature_data.get("length")
    
    if center and width and length:
        x, y = center
        half_w, half_l = width / 2, length / 2
        radius = half_w  # Rounded ends with radius = width/2
        
        # Create slot with proper rounded ends
        # Left semicircle
        msp.add_arc(
            center=(x - half_l, y),
            radius=radius,
            start_angle=90,
            end_angle=270,
            dxfattribs={'layer': 'HIDDEN'}
        )
        
        # Right semicircle  
        msp.add_arc(
            center=(x + half_l, y),
            radius=radius,
            start_angle=270,
            end_angle=90,
            dxfattribs={'layer': 'HIDDEN'}
        )
        
        # Top line
        msp.add_line(
            start=(x - half_l, y + half_w),
            end=(x + half_l, y + half_w),
            dxfattribs={'layer': 'HIDDEN'}
        )
        
        # Bottom line
        msp.add_line(
            start=(x - half_l, y - half_w),
            end=(x + half_l, y - half_w),
            dxfattribs={'layer': 'HIDDEN'}
        )
        
        print(f"  > Applied parametric slot feature at {center} with width {width} and length {length}.")

def _apply_chamfer(msp, base_feature, feature_data):
    """Applies true chamfers to corners."""
    distance = feature_data.get("distance", 2.0)
    corners = feature_data.get("corners", ["all"])
    
    if base_feature.get("shape") != "rectangle":
        print(f"  > Chamfers only supported on rectangular features currently.")
        return
        
    width = base_feature.get("width", 0)
    height = base_feature.get("height", 0)
    half_w, half_h = width / 2, height / 2
    
    # Create chamfered rectangle
    points = []
    
    if "all" in corners or "bottom-left" in corners:
        # Bottom-left chamfer
        points.extend([
            (-half_w + distance, -half_h),
            (-half_w, -half_h + distance)
        ])
    else:
        points.append((-half_w, -half_h))
    
    if "all" in corners or "bottom-right" in corners:
        # Bottom-right chamfer
        points.extend([
            (half_w - distance, -half_h),
            (half_w, -half_h + distance)
        ])
    else:
        points.append((half_w, -half_h))
    
    if "all" in corners or "top-right" in corners:
        # Top-right chamfer
        points.extend([
            (half_w, half_h - distance),
            (half_w - distance, half_h)
        ])
    else:
        points.append((half_w, half_h))
    
    if "all" in corners or "top-left" in corners:
        # Top-left chamfer
        points.extend([
            (-half_w + distance, half_h),
            (-half_w, half_h - distance)
        ])
    else:
        points.append((-half_w, half_h))
    
    # Close the polygon
    points.append(points[0])
    
    # Remove old rectangle and add chamfered one
    try:
        msp.delete_entity(msp[-1])
    except IndexError:
        pass
    
    msp.add_lwpolyline(points)
    print(f"  > Applied true chamfer feature with distance {distance}.")

def _apply_counterbore(msp, feature_data):
    """Creates a counterbore hole feature."""
    center = feature_data.get("center")
    hole_diameter = feature_data.get("hole_diameter")
    counterbore_diameter = feature_data.get("counterbore_diameter")
    counterbore_depth = feature_data.get("counterbore_depth", 2.0)
    
    if center and hole_diameter and counterbore_diameter:
        # Draw the counterbore (larger circle)
        msp.add_circle(center=center, radius=counterbore_diameter / 2)
        
        # Draw the through hole (smaller circle)
        msp.add_circle(center=center, radius=hole_diameter / 2)
        
        # Add depth indicator line (simplified representation)
        depth_offset = counterbore_diameter / 2 + 5
        msp.add_line(
            start=(center[0] + depth_offset, center[1]),
            end=(center[0] + depth_offset + 10, center[1])
        )
        msp.add_text(
            f"⌴{counterbore_depth}",
            dxfattribs={
                'height': 2.0,
                'insert': (center[0] + depth_offset + 12, center[1] - 1)
            }
        )
        
        print(f"  > Applied counterbore feature at {center} with hole ⌀{hole_diameter} and cbore ⌀{counterbore_diameter}.")

def _apply_countersink(msp, feature_data):
    """Creates a countersink hole feature."""
    center = feature_data.get("center")
    hole_diameter = feature_data.get("hole_diameter")
    countersink_diameter = feature_data.get("countersink_diameter")
    countersink_angle = feature_data.get("countersink_angle", 90)
    
    if center and hole_diameter and countersink_diameter:
        # Draw the countersink (larger circle)
        msp.add_circle(center=center, radius=countersink_diameter / 2)
        
        # Draw the through hole (smaller circle)
        msp.add_circle(center=center, radius=hole_diameter / 2)
        
        # Add angle indicator (simplified representation)
        angle_offset = countersink_diameter / 2 + 5
        msp.add_line(
            start=(center[0] + angle_offset, center[1]),
            end=(center[0] + angle_offset + 10, center[1])
        )
        msp.add_text(
            f"⌵{countersink_angle}°",
            dxfattribs={
                'height': 2.0,
                'insert': (center[0] + angle_offset + 12, center[1] - 1)
            }
        )
        
        print(f"  > Applied countersink feature at {center} with hole ⌀{hole_diameter} and csink ⌀{countersink_diameter}.")

def _apply_tapped_hole(msp, feature_data):
    """Creates a tapped hole feature with thread specification."""
    center = feature_data.get("center")
    thread_spec = feature_data.get("thread_spec", "M6")
    pilot_diameter = feature_data.get("pilot_diameter")
    
    if center and pilot_diameter:
        # Draw the pilot hole
        msp.add_circle(center=center, radius=pilot_diameter / 2)
        
        # Add thread callout
        callout_offset = pilot_diameter / 2 + 5
        msp.add_line(
            start=(center[0] + callout_offset, center[1]),
            end=(center[0] + callout_offset + 15, center[1])
        )
        msp.add_text(
            thread_spec,
            dxfattribs={
                'height': 2.5,
                'insert': (center[0] + callout_offset + 17, center[1] - 1.25)
            }
        )
        
        print(f"  > Applied tapped hole feature at {center} with thread {thread_spec}.")

def apply_modifying_features(msp, base_feature, features):
    """
    Applies modifying features like holes, fillets, etc.
    """
    if not features:
        return
    print(f"Applying {len(features)} modifying features...")
    for feature in features:
        feature_type = feature.get("type")
        if feature_type == "hole":
            _apply_hole(msp, feature)
        elif feature_type == "fillet":
            _apply_fillet(msp, base_feature, feature)
        elif feature_type == "slot":
            _apply_slot(msp, feature)
        elif feature_type == "chamfer":
            _apply_chamfer(msp, base_feature, feature)
        elif feature_type == "counterbore":
            _apply_counterbore(msp, feature)
        elif feature_type == "countersink":
            _apply_countersink(msp, feature)
        elif feature_type == "tapped_hole":
            _apply_tapped_hole(msp, feature)
        else:
            print(f"  > Skipping unknown feature type: {feature_type}")

def setup_drawing_layers(doc):
    """Sets up the standard CAD layers and linetypes for engineering drawings."""
    
    # Define standard linetypes
    linetypes = [
        ("CONTINUOUS", []),
        ("HIDDEN", [2.5, -1.25]),
        ("CENTER", [12.5, -2.5, 2.5, -2.5]),
        ("CONSTRUCTION", [5.0, -2.5, 1.0, -2.5])
    ]
    
    # Add linetypes to document
    for name, pattern in linetypes:
        if name not in doc.linetypes:
            if pattern:
                doc.linetypes.add(name, pattern=pattern)
    
    # Define standard layers with colors and linetypes
    layers = [
        ("OUTLINE", 7, "CONTINUOUS", 0.35),      # White, continuous, medium weight
        ("HIDDEN", 8, "HIDDEN", 0.25),           # Gray, dashed, light weight  
        ("CENTER", 5, "CENTER", 0.15),           # Blue, center line, thin
        ("CONSTRUCTION", 9, "CONSTRUCTION", 0.13), # Light gray, construction, very thin
        ("DIMENSIONS", 1, "CONTINUOUS", 0.15),    # Red, continuous, thin
        ("TEXT", 2, "CONTINUOUS", 0.15),         # Yellow, continuous, thin
    ]
    
    # Add layers to document
    for name, color, linetype, lineweight in layers:
        if name not in doc.layers:
            layer = doc.layers.add(name)
            layer.color = color
            layer.linetype = linetype
            layer.lineweight = int(lineweight * 100)  # Convert to hundredths of mm
    
    print("✅ Set up standard CAD layers and linetypes")

def generate_from_plan(plan_path, output_path, visualize=False, validate=True):
    """
    Generates a DXF file from a JSON drawing plan.
    """
    with open(plan_path, 'r') as f:
        plan = json.load(f)

    if validate:
        validator = DrawingPlanValidator()
        is_valid, errors = validator.validate_plan(plan)
        if not is_valid:
            print("❌ Plan validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("✅ Plan validation successful")

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = ezdxf.new()
    msp = doc.modelspace()
    
    # --- Set up layers and linetypes ---
    setup_drawing_layers(doc)
    
    # --- Import Required Symbol Blocks ---
    try:
        if integrate_symbols_into_document(doc, plan):
            print("✅ Symbol blocks imported successfully")
        else:
            print("⚠️ Some symbol blocks could not be imported")
    except Exception as e:
        print(f"⚠️ Symbol integration failed: {e}")

    # --- ROUTE TO CORRECT ENGINE ---
    if "base_feature" in plan:
        # Use the new Phase 3 Semantic Engine
        print("🚀 Using Semantic Engine for feature-based plan.")
        base_feature = plan["base_feature"]
        create_base_feature(msp, base_feature)
        apply_modifying_features(msp, base_feature, plan.get("modifying_features", []))
        create_comprehensive_dimensions(msp, plan)
    else:
        # Use the old Phase 1/2 Primitive Renderer
        print("Legacy plan detected. Using primitive renderer.")
        draw_legacy_geometry(msp, plan.get('geometry', {}))
        draw_legacy_annotations(msp, plan.get('annotations', {}))
    
    # --- COMMON LOGIC FOR BOTH ---
    if plan.get('title_block'):
        draw_title_block(msp, plan['title_block'])

    # Save the DXF file
    doc.saveas(output_path)
    print(f"Successfully generated DXF: {output_path}")

    if visualize:
        png_path = os.path.splitext(output_path)[0] + ".png"
        print(f"Visualizing DXF to {png_path}...")
        convert_dxf_to_png(output_path, png_path)

def draw_legacy_geometry(msp, geometry):
    """Draws geometry from a legacy plan format."""
    if geometry.get('lines'):
        for line in geometry['lines']:
            msp.add_line(line['start'], line['end'])
    
    if geometry.get('circles'):
        for circle in geometry['circles']:
            msp.add_circle(circle['center'], circle['radius'])
    
    if geometry.get('arcs'):
        for arc in geometry['arcs']:
            msp.add_arc(
                center=arc['center'],
                radius=arc['radius'],
                start_angle=arc['start_angle'],
                end_angle=arc['end_angle']
            )
    
    if geometry.get('rectangles'):
        for rect in geometry['rectangles']:
            corner1 = rect['corner1']
            corner2 = rect['corner2']
            msp.add_line([corner1[0], corner1[1]], [corner2[0], corner1[1]])
            msp.add_line([corner2[0], corner1[1]], [corner2[0], corner2[1]])
            msp.add_line([corner2[0], corner2[1]], [corner1[0], corner2[1]])
            msp.add_line([corner1[0], corner2[1]], [corner1[0], corner1[1]])

def draw_legacy_annotations(msp, annotations):
    """Draws annotations from a legacy plan format."""
    if annotations.get('dimensions'):
        for dim in annotations['dimensions']:
            if dim['type'] == 'linear':
                msp.add_linear_dim(base=dim['base'], p1=dim['p1'], p2=dim['p2']).render()
            elif dim['type'] == 'diameter':
                msp.add_diameter_dim(center=dim['center'], radius=dim['radius'], location=dim['location']).render()
            
    if annotations.get('symbols'):
        for symbol in annotations['symbols']:
            symbol_name = symbol['name']
            location = symbol['location']
            rotation = symbol.get('rotation', 0)
            scale = symbol.get('scale', 1.0)
            
            # The block name is simply the symbol name.
            # The XREF is handled by ezdxf automatically.
            block_name = symbol_name
            
            msp.add_blockref(
                block_name,
                insert=location,
                dxfattribs={
                    'rotation': rotation,
                    'xscale': scale,
                    'yscale': scale,
                }
            )

def draw_title_block(msp, title_block_data):
    """
    Draws an enhanced title block with material, finish, revision, weight, scale.
    Phase 5: Professional title block v2 with comprehensive engineering information.
    """
    # Define title block dimensions and position
    width = 100
    height = 50
    x_pos = 110  # Adjusted for larger title block
    y_pos = -30  # Position below drawing area

    # Draw main border
    msp.add_lwpolyline([
        (x_pos, y_pos),
        (x_pos + width, y_pos),
        (x_pos + width, y_pos + height),
        (x_pos, y_pos + height),
        (x_pos, y_pos)
    ], dxfattribs={'layer': 'OUTLINE'})

    # Draw internal grid lines
    # Vertical dividers
    msp.add_line((x_pos + 50, y_pos), (x_pos + 50, y_pos + height), dxfattribs={'layer': 'OUTLINE'})
    # Horizontal dividers
    for i in range(1, 5):
        y_line = y_pos + i * (height / 5)
        msp.add_line((x_pos, y_line), (x_pos + width, y_line), dxfattribs={'layer': 'OUTLINE'})

    # Add comprehensive text information
    text_height = 1.5
    padding = 1
    
    # Left column
    base_x = x_pos + padding
    
    # Drawing title (larger text)
    msp.add_text(
        title_block_data.get('drawing_title', 'Untitled Drawing'),
        dxfattribs={
            'height': 2.5,
            'insert': (base_x, y_pos + height - 5),
            'layer': 'TEXT'
        }
    )
    
    # Drawing number
    msp.add_text(
        f"DWG NO: {title_block_data.get('drawing_number', 'N/A')}",
        dxfattribs={
            'height': text_height,
            'insert': (base_x, y_pos + height - 12),
            'layer': 'TEXT'
        }
    )
    
    # Material specification
    msp.add_text(
        f"MATERIAL: {title_block_data.get('material', 'AL 6061-T6')}",
        dxfattribs={
            'height': text_height,
            'insert': (base_x, y_pos + height - 22),
            'layer': 'TEXT'
        }
    )
    
    # Surface finish
    msp.add_text(
        f"FINISH: {title_block_data.get('finish', 'AS MACHINED')}",
        dxfattribs={
            'height': text_height,
            'insert': (base_x, y_pos + height - 32),
            'layer': 'TEXT'
        }
    )
    
    # Tolerance specification
    msp.add_text(
        f"TOL: ±{title_block_data.get('tolerance', '0.1')}",
        dxfattribs={
            'height': text_height,
            'insert': (base_x, y_pos + height - 42),
            'layer': 'TEXT'
        }
    )

    # Right column
    base_x = x_pos + 52
    
    # Scale
    msp.add_text(
        f"SCALE: {title_block_data.get('scale', '1:1')}",
        dxfattribs={
            'height': text_height,
            'insert': (base_x, y_pos + height - 12),
            'layer': 'TEXT'
        }
    )
    
    # Weight (estimated)
    msp.add_text(
        f"WEIGHT: {title_block_data.get('weight', 'TBD')} kg",
        dxfattribs={
            'height': text_height,
            'insert': (base_x, y_pos + height - 22),
            'layer': 'TEXT'
        }
    )
    
    # Revision
    msp.add_text(
        f"REV: {title_block_data.get('revision', 'A')}",
        dxfattribs={
            'height': text_height,
            'insert': (base_x, y_pos + height - 32),
            'layer': 'TEXT'
        }
    )
    
    # Date and designer
    msp.add_text(
        f"DATE: {title_block_data.get('date', 'N/A')}",
        dxfattribs={
            'height': text_height,
            'insert': (base_x, y_pos + height - 42),
            'layer': 'TEXT'
        }
    )
    
    # Drawn by (bottom right)
    msp.add_text(
        f"BY: {title_block_data.get('drawn_by', 'AI')}",
        dxfattribs={
            'height': 1.2,
            'insert': (x_pos + width - 15, y_pos + 2),
            'layer': 'TEXT'
        }
    )

def main():
    parser = argparse.ArgumentParser(description="Intelligent Drawing Generator")
    parser.add_argument('--plan', type=str, help='Path to the JSON drawing plan.')
    parser.add_argument('--output', type=str, default='./out/generated_drawing.dxf', help='Path for the output DXF file.')
    parser.add_argument('--visualize', action='store_true', help='Generate a PNG visualization of the DXF.')
    
    # New AI-powered arguments
    parser.add_argument('--prompt', type=str, help='A natural language prompt for a drawing.')
    parser.add_argument('--random', action='store_true', help='Generate a drawing from a random prompt.')
    parser.add_argument('--api-key', type=str, help='OpenAI API key for AI Planner.')

    args = parser.parse_args()

    plan = None
    plan_path = args.plan
    client = None
    output_path = args.output

    if args.prompt or args.random:
        if args.api_key:
            client = openai.OpenAI(api_key=args.api_key)
        else:
            print("❌ --api-key is required when using --prompt or --random. Exiting.")
            return
        
        prompt = args.prompt if args.prompt else generate_random_prompt()
        plan = create_plan_from_prompt(client, prompt)
        
        if not plan:
            print("❌ AI Planner failed to generate a plan. Exiting.")
            return

        # Save the generated plan to a temporary file for processing
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp:
            json.dump(plan, tmp)
            plan_path = tmp.name
        print(f"✅ AI-generated plan saved to temporary file: {plan_path}")

        # --- Generate unique filename if no output is specified ---
        is_default_output = (args.output == './out/generated_drawing.dxf')
        if is_default_output and plan and plan.get('title_block', {}).get('drawing_title'):
            title = plan['title_block']['drawing_title']
            slug = slugify(title)
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{slug}-{timestamp}.dxf"
            output_path = os.path.join('out', filename)
        elif is_default_output:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"generated-drawing-{timestamp}.dxf"
            output_path = os.path.join('out', filename)

    if not plan_path:
        parser.error("You must specify a plan, prompt, or use the --random flag.")
        return

    generate_from_plan(plan_path, output_path, args.visualize, validate=True)

    # Clean up temporary file if one was created
    if (args.prompt or args.random) and os.path.exists(plan_path):
        os.remove(plan_path)

if __name__ == "__main__":
    main() 