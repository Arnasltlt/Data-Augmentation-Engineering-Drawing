"""
Mock SolidBuilder - Demonstrates 3D Solid Kernel concepts without OCP dependency
Milestone 1: 3D Core for Engineering Drawing Generator (Demo Version)

This is a demonstration version that shows the concept and interface
without requiring the heavy OCP/CadQuery installation.
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum

class ProjectionType(Enum):
    """Standard engineering projection types."""
    ISOMETRIC = "isometric"
    FRONT = "front"
    TOP = "top"  
    RIGHT = "right"
    BACK = "back"
    BOTTOM = "bottom"
    LEFT = "left"

class MockSolidBuilder:
    """
    Mock 3D Solid modeling kernel for demonstration.
    
    This demonstrates the interface and concepts of the real SolidBuilder
    without requiring OCP/CadQuery dependencies.
    """
    
    def __init__(self):
        self.solid_data = None
        self.construction_history = []
        self.bounding_box = {"x_min": 0, "x_max": 0, "y_min": 0, "y_max": 0, "z_min": 0, "z_max": 0}
        self.removed_area = 0  # Track area removed by holes, slots etc.
        
    def build_from_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Build a 3D solid from a feature-based plan (mock implementation).
        """
        try:
            # Clear previous solid
            self.solid_data = {}
            self.construction_history = []
            self.removed_area = 0
            
            # Create base feature
            base_feature = plan.get("base_feature")
            if not base_feature:
                print("❌ No base_feature found in plan")
                return False
                
            if not self._create_base_feature(base_feature):
                return False
                
            # Apply modifying features
            modifying_features = plan.get("modifying_features", [])
            for i, feature in enumerate(modifying_features):
                try:
                    if not self._apply_modifying_feature(feature):
                        print(f"⚠️ Failed to apply modifying feature {i}: {feature.get('type')}")
                        # Continue with other features instead of failing completely
                except Exception as e:
                    print(f"⚠️ Error applying feature {i}: {e}")
                    continue
                    
            print(f"✅ Successfully built mock 3D solid with {len(modifying_features)} features")
            return True
            
        except Exception as e:
            print(f"❌ Failed to build solid from plan: {e}")
            return False
    
    def _create_base_feature(self, base_feature: Dict[str, Any]) -> bool:
        """Create the base solid feature (mock)."""
        shape_type = base_feature.get("shape")
        
        try:
            if shape_type == "rectangle":
                width = base_feature.get("width", 100)
                height = base_feature.get("height", 100) 
                thickness = base_feature.get("thickness", 10)
                
                # Mock solid data
                self.solid_data = {
                    "type": "box",
                    "width": width,
                    "height": height,
                    "thickness": thickness
                }
                
                # Update bounding box
                self.bounding_box = {
                    "x_min": -width/2, "x_max": width/2,
                    "y_min": -height/2, "y_max": height/2,
                    "z_min": 0, "z_max": thickness
                }
                
                self.construction_history.append(f"Base plate: {width}x{height}x{thickness}")
                print(f"✅ Created mock base plate: {width}x{height}x{thickness} mm")
                return True
                
            elif shape_type == "circle":
                diameter = base_feature.get("diameter", 100)
                thickness = base_feature.get("thickness", 10)
                
                self.solid_data = {
                    "type": "cylinder",
                    "diameter": diameter,
                    "thickness": thickness
                }
                
                # Update bounding box
                radius = diameter / 2
                self.bounding_box = {
                    "x_min": -radius, "x_max": radius,
                    "y_min": -radius, "y_max": radius,
                    "z_min": 0, "z_max": thickness
                }
                
                self.construction_history.append(f"Base cylinder: ⌀{diameter}x{thickness}")
                print(f"✅ Created mock base cylinder: ⌀{diameter}x{thickness} mm")
                return True
                
            else:
                print(f"❌ Unsupported base feature shape: {shape_type}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to create base feature: {e}")
            return False
    
    def _apply_modifying_feature(self, feature: Dict[str, Any]) -> bool:
        """Apply a modifying feature to the solid (mock)."""
        if not self.solid_data:
            print("❌ No base solid to modify")
            return False
            
        feature_type = feature.get("type")
        
        try:
            if feature_type == "hole":
                return self._apply_hole(feature)
            elif feature_type == "slot":
                return self._apply_slot(feature)
            elif feature_type == "fillet":
                return self._apply_fillet(feature)
            elif feature_type == "chamfer":
                return self._apply_chamfer(feature)
            elif feature_type == "counterbore":
                return self._apply_counterbore(feature)
            elif feature_type == "countersink":
                return self._apply_countersink(feature)
            elif feature_type == "tapped_hole":
                return self._apply_tapped_hole(feature)
            else:
                print(f"⚠️ Unsupported feature type: {feature_type}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to apply {feature_type} feature: {e}")
            return False
    
    def _apply_hole(self, feature: Dict[str, Any]) -> bool:
        """Apply a through hole feature (mock)."""
        center = feature.get("center", [0, 0])
        diameter = feature.get("diameter", 6)
        
        # Calculate removed area
        radius = diameter / 2
        hole_area = math.pi * radius * radius
        self.removed_area += hole_area
        
        self.construction_history.append(f"Through hole: ⌀{diameter} at {center}")
        print(f"  > Applied mock through hole: ⌀{diameter} at {center}")
        return True
    
    def _apply_slot(self, feature: Dict[str, Any]) -> bool:
        """Apply a slot feature (mock)."""
        center = feature.get("center", [0, 0])
        width = feature.get("width", 6)
        length = feature.get("length", 20)
        
        # Calculate removed area (rounded rectangle)
        slot_area = width * length + math.pi * (width/2) * (width/2)
        self.removed_area += slot_area
        
        self.construction_history.append(f"Slot: {length}x{width} at {center}")
        print(f"  > Applied mock slot: {length}x{width} at {center}")
        return True
    
    def _apply_fillet(self, feature: Dict[str, Any]) -> bool:
        """Apply fillet to edges (mock)."""
        radius = feature.get("radius", 2)
        corners = feature.get("corners", ["all"])
        
        self.construction_history.append(f"Fillet: R{radius} on {corners}")
        print(f"  > Applied mock fillet: R{radius} on {corners}")
        return True
    
    def _apply_chamfer(self, feature: Dict[str, Any]) -> bool:
        """Apply chamfer to edges (mock)."""
        distance = feature.get("distance", 1)
        corners = feature.get("corners", ["all"])
        
        self.construction_history.append(f"Chamfer: {distance}mm on {corners}")
        print(f"  > Applied mock chamfer: {distance}mm on {corners}")
        return True
    
    def _apply_counterbore(self, feature: Dict[str, Any]) -> bool:
        """Apply counterbore hole feature (mock)."""
        center = feature.get("center", [0, 0])
        hole_diameter = feature.get("hole_diameter", 6)
        counterbore_diameter = feature.get("counterbore_diameter", 12)
        counterbore_depth = feature.get("counterbore_depth", 3)
        
        self.construction_history.append(f"Counterbore: ⌀{hole_diameter}/⌀{counterbore_diameter}x{counterbore_depth} at {center}")
        print(f"  > Applied mock counterbore: ⌀{hole_diameter}/⌀{counterbore_diameter}x{counterbore_depth} at {center}")
        return True
    
    def _apply_countersink(self, feature: Dict[str, Any]) -> bool:
        """Apply countersink hole feature (mock)."""
        center = feature.get("center", [0, 0])
        hole_diameter = feature.get("hole_diameter", 6)
        countersink_diameter = feature.get("countersink_diameter", 12)
        countersink_angle = feature.get("countersink_angle", 90)
        
        self.construction_history.append(f"Countersink: ⌀{hole_diameter}/⌀{countersink_diameter}x{countersink_angle}° at {center}")
        print(f"  > Applied mock countersink: ⌀{hole_diameter}/⌀{countersink_diameter}x{countersink_angle}° at {center}")
        return True
    
    def _apply_tapped_hole(self, feature: Dict[str, Any]) -> bool:
        """Apply tapped hole feature (mock)."""
        center = feature.get("center", [0, 0])
        pilot_diameter = feature.get("pilot_diameter", 5)
        thread_spec = feature.get("thread_spec", "M6")
        
        self.construction_history.append(f"Tapped hole: {thread_spec} (⌀{pilot_diameter}) at {center}")
        print(f"  > Applied mock tapped hole: {thread_spec} (⌀{pilot_diameter}) at {center}")
        return True
    
    def get_projection_edges(self, projection_type: ProjectionType) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """
        Get 2D projection edges with mock hidden line removal.
        """
        if not self.solid_data:
            print("❌ No solid available for projection")
            return []
            
        try:
            edges = []
            
            # Generate mock projection based on solid type and view
            if self.solid_data.get("type") == "box":
                edges = self._generate_box_projection(projection_type)
            elif self.solid_data.get("type") == "cylinder":
                edges = self._generate_cylinder_projection(projection_type)
            
            print(f"✅ Generated {len(edges)} mock projection edges for {projection_type.value} view")
            return edges
            
        except Exception as e:
            print(f"❌ Failed to generate projection: {e}")
            return []
    
    def _generate_box_projection(self, projection_type: ProjectionType) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Generate projection edges for a box."""
        width = self.solid_data["width"]
        height = self.solid_data["height"]
        thickness = self.solid_data["thickness"]
        
        edges = []
        
        if projection_type == ProjectionType.ISOMETRIC:
            # Isometric projection of a box
            # Front face
            edges.extend([
                ((-width/2, -height/2), (width/2, -height/2)),
                ((width/2, -height/2), (width/2, height/2)),
                ((width/2, height/2), (-width/2, height/2)),
                ((-width/2, height/2), (-width/2, -height/2))
            ])
            
            # Add some isometric depth lines
            offset_x = thickness * 0.5
            offset_y = thickness * 0.866
            
            # Back face edges (offset)
            edges.extend([
                ((-width/2 + offset_x, -height/2 + offset_y), (width/2 + offset_x, -height/2 + offset_y)),
                ((width/2 + offset_x, -height/2 + offset_y), (width/2 + offset_x, height/2 + offset_y)),
                ((width/2 + offset_x, height/2 + offset_y), (-width/2 + offset_x, height/2 + offset_y)),
                ((-width/2 + offset_x, height/2 + offset_y), (-width/2 + offset_x, -height/2 + offset_y))
            ])
            
            # Connection lines
            edges.extend([
                ((-width/2, -height/2), (-width/2 + offset_x, -height/2 + offset_y)),
                ((width/2, -height/2), (width/2 + offset_x, -height/2 + offset_y)),
                ((width/2, height/2), (width/2 + offset_x, height/2 + offset_y)),
                ((-width/2, height/2), (-width/2 + offset_x, height/2 + offset_y))
            ])
            
        elif projection_type == ProjectionType.FRONT:
            # Front view (XZ plane)
            edges.extend([
                ((-width/2, 0), (width/2, 0)),
                ((width/2, 0), (width/2, thickness)),
                ((width/2, thickness), (-width/2, thickness)),
                ((-width/2, thickness), (-width/2, 0))
            ])
            
        elif projection_type == ProjectionType.TOP:
            # Top view (XY plane)
            edges.extend([
                ((-width/2, -height/2), (width/2, -height/2)),
                ((width/2, -height/2), (width/2, height/2)),
                ((width/2, height/2), (-width/2, height/2)),
                ((-width/2, height/2), (-width/2, -height/2))
            ])
            
        elif projection_type == ProjectionType.RIGHT:
            # Right view (YZ plane)
            edges.extend([
                ((-height/2, 0), (height/2, 0)),
                ((height/2, 0), (height/2, thickness)),
                ((height/2, thickness), (-height/2, thickness)),
                ((-height/2, thickness), (-height/2, 0))
            ])
        
        return edges
    
    def _generate_cylinder_projection(self, projection_type: ProjectionType) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Generate projection edges for a cylinder."""
        diameter = self.solid_data["diameter"]
        thickness = self.solid_data["thickness"]
        radius = diameter / 2
        
        edges = []
        
        if projection_type == ProjectionType.ISOMETRIC:
            # Isometric view of cylinder - simplified as hexagon
            angles = [i * 60 for i in range(6)]
            points = [(radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a))) for a in angles]
            
            # Bottom hexagon
            for i in range(6):
                start = points[i]
                end = points[(i + 1) % 6]
                edges.append((start, end))
            
            # Top hexagon (offset for isometric)
            offset_x = thickness * 0.5
            offset_y = thickness * 0.866
            for i in range(6):
                start = (points[i][0] + offset_x, points[i][1] + offset_y)
                end = (points[(i + 1) % 6][0] + offset_x, points[(i + 1) % 6][1] + offset_y)
                edges.append((start, end))
            
            # Connecting lines
            for i in range(0, 6, 2):  # Only show some connecting lines
                start = points[i]
                end = (points[i][0] + offset_x, points[i][1] + offset_y)
                edges.append((start, end))
                
        elif projection_type == ProjectionType.FRONT:
            # Front view - rectangle
            edges.extend([
                ((-radius, 0), (radius, 0)),
                ((radius, 0), (radius, thickness)),
                ((radius, thickness), (-radius, thickness)),
                ((-radius, thickness), (-radius, 0))
            ])
            
        elif projection_type == ProjectionType.TOP:
            # Top view - circle (simplified as octagon)
            angles = [i * 45 for i in range(8)]
            points = [(radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a))) for a in angles]
            
            for i in range(8):
                start = points[i]
                end = points[(i + 1) % 8]
                edges.append((start, end))
        
        return edges
    
    def get_solid_info(self) -> Dict[str, Any]:
        """Get information about the current solid (mock)."""
        if not self.solid_data:
            return {"error": "No solid available"}
            
        try:
            # Calculate mock volume
            if self.solid_data.get("type") == "box":
                volume = (self.solid_data["width"] * 
                         self.solid_data["height"] * 
                         self.solid_data["thickness"])
                surface_area = 2 * (
                    self.solid_data["width"] * self.solid_data["height"] +
                    self.solid_data["width"] * self.solid_data["thickness"] +
                    self.solid_data["height"] * self.solid_data["thickness"]
                )
                # Calculate net XY area (base area minus removed area)
                base_area = self.solid_data["width"] * self.solid_data["height"]
                net_xy_area = max(0, base_area - self.removed_area)
                
            elif self.solid_data.get("type") == "cylinder":
                radius = self.solid_data["diameter"] / 2
                volume = math.pi * radius * radius * self.solid_data["thickness"]
                surface_area = 2 * math.pi * radius * (radius + self.solid_data["thickness"])
                # Calculate net XY area (base area minus removed area)
                base_area = math.pi * radius * radius
                net_xy_area = max(0, base_area - self.removed_area)
            else:
                volume = 0
                surface_area = 0
                net_xy_area = 0
            
            # Update bounding box to reflect net area
            if self.solid_data.get("type") == "box":
                # For area comparison, we need the net area, not just bounding box
                bbox_area = ((self.bounding_box["x_max"] - self.bounding_box["x_min"]) * 
                           (self.bounding_box["y_max"] - self.bounding_box["y_min"]))
                self.bounding_box["net_xy_area"] = net_xy_area
            
            return {
                "volume": volume,
                "surface_area": surface_area,
                "bounding_box": self.bounding_box,
                "construction_history": self.construction_history,
                "removed_area": self.removed_area,
                "net_xy_area": net_xy_area,
                "mock": True
            }
        except Exception as e:
            return {"error": f"Failed to get solid info: {e}"}
    
    def export_step(self, filepath: str) -> bool:
        """Export solid as STEP file (mock)."""
        if not self.solid_data:
            print("❌ No solid to export")
            return False
            
        try:
            # Write a mock STEP file
            with open(filepath, 'w') as f:
                f.write("ISO-10303-21;\n")
                f.write("HEADER;\n")
                f.write("FILE_DESCRIPTION(('Mock STEP file from SolidBuilder'),('2;1'));\n")
                f.write("FILE_NAME('mock.step','2024-01-15T12:00:00',('SolidBuilder'),('Mock'),'Mock','Mock','');\n")
                f.write("FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\n")
                f.write("ENDSEC;\n")
                f.write("DATA;\n")
                f.write(f"#1 = SOLID() /* Mock solid: {self.construction_history} */;\n")
                f.write("ENDSEC;\n")
                f.write("END-ISO-10303-21;\n")
                
            print(f"✅ Exported mock STEP file: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Failed to export STEP: {e}")
            return False
    
    def export_stl(self, filepath: str) -> bool:
        """Export solid as STL file (mock)."""
        if not self.solid_data:
            print("❌ No solid to export")
            return False
            
        try:
            # Write a mock STL file
            with open(filepath, 'w') as f:
                f.write("solid MockSolid\n")
                f.write("  facet normal 0.0 0.0 1.0\n")
                f.write("    outer loop\n")
                f.write("      vertex 0.0 0.0 0.0\n")
                f.write("      vertex 1.0 0.0 0.0\n")
                f.write("      vertex 0.0 1.0 0.0\n")
                f.write("    endloop\n")
                f.write("  endfacet\n")
                f.write("endsolid MockSolid\n")
                
            print(f"✅ Exported mock STL file: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Failed to export STL: {e}")
            return False

# Alias for compatibility
SolidBuilder = MockSolidBuilder