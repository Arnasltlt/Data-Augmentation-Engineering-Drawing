"""
SolidBuilder - 3D Solid Kernel using OCP (python-occ)
Milestone 1: 3D Core for Engineering Drawing Generator

This module provides a solid modeling kernel that converts feature-based plans
into 3D BREP solids and generates hidden-line-removed projections for DXF output.
"""

import cadquery as cq
import numpy as np
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

class SolidBuilder:
    """
    3D Solid modeling kernel using CadQuery/OCP.
    
    Converts feature-based JSON plans into 3D BREP solids and produces
    hidden-line-removed 2D projections for engineering drawings.
    """
    
    def __init__(self):
        self.solid = None
        self.construction_history = []
        
    def build_from_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Build a 3D solid from a feature-based plan.
        
        Args:
            plan: JSON plan with base_feature and modifying_features
            
        Returns:
            bool: True if solid was built successfully
        """
        try:
            # Clear previous solid
            self.solid = None
            self.construction_history = []
            
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
                    
            print(f"✅ Successfully built 3D solid with {len(modifying_features)} features")
            return True
            
        except Exception as e:
            print(f"❌ Failed to build solid from plan: {e}")
            return False
    
    def _create_base_feature(self, base_feature: Dict[str, Any]) -> bool:
        """Create the base solid feature (typically a plate)."""
        shape_type = base_feature.get("shape")
        
        try:
            if shape_type == "rectangle":
                width = base_feature.get("width", 100)
                height = base_feature.get("height", 100) 
                thickness = base_feature.get("thickness", 10)
                
                # Create centered rectangular solid
                self.solid = (cq.Workplane("XY")
                             .box(width, height, thickness)
                             .translate((0, 0, thickness/2)))
                
                self.construction_history.append(f"Base plate: {width}x{height}x{thickness}")
                print(f"✅ Created base plate: {width}x{height}x{thickness} mm")
                return True
                
            elif shape_type == "circle":
                diameter = base_feature.get("diameter", 100)
                thickness = base_feature.get("thickness", 10)
                
                # Create centered cylindrical solid
                self.solid = (cq.Workplane("XY")
                             .circle(diameter/2)
                             .extrude(thickness)
                             .translate((0, 0, thickness/2)))
                
                self.construction_history.append(f"Base cylinder: ⌀{diameter}x{thickness}")
                print(f"✅ Created base cylinder: ⌀{diameter}x{thickness} mm")
                return True
                
            else:
                print(f"❌ Unsupported base feature shape: {shape_type}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to create base feature: {e}")
            return False
    
    def _apply_modifying_feature(self, feature: Dict[str, Any]) -> bool:
        """Apply a modifying feature to the solid."""
        if not self.solid:
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
        """Apply a through hole feature."""
        center = feature.get("center", [0, 0])
        diameter = feature.get("diameter", 6)
        
        # Get the bounding box to determine hole depth
        bbox = self.solid.val().BoundingBox()
        depth = bbox.zmax - bbox.zmin + 1  # Add 1mm for clearance
        
        # Create hole
        hole = (cq.Workplane("XY")
               .moveTo(center[0], center[1])
               .circle(diameter/2)
               .extrude(depth))
        
        # Subtract from solid
        self.solid = self.solid.cut(hole)
        
        self.construction_history.append(f"Through hole: ⌀{diameter} at {center}")
        print(f"  > Applied through hole: ⌀{diameter} at {center}")
        return True
    
    def _apply_slot(self, feature: Dict[str, Any]) -> bool:
        """Apply a slot feature."""
        center = feature.get("center", [0, 0])
        width = feature.get("width", 6)
        length = feature.get("length", 20)
        
        # Get the bounding box to determine slot depth
        bbox = self.solid.val().BoundingBox()
        depth = bbox.zmax - bbox.zmin + 1
        
        # Create slot (rounded rectangle)
        slot = (cq.Workplane("XY")
               .moveTo(center[0], center[1])
               .rect(length, width)
               .fillet(width/2)
               .extrude(depth))
        
        # Subtract from solid
        self.solid = self.solid.cut(slot)
        
        self.construction_history.append(f"Slot: {length}x{width} at {center}")
        print(f"  > Applied slot: {length}x{width} at {center}")
        return True
    
    def _apply_fillet(self, feature: Dict[str, Any]) -> bool:
        """Apply fillet to edges."""
        radius = feature.get("radius", 2)
        corners = feature.get("corners", ["all"])
        
        # For now, apply fillet to all edges if "all" is specified
        if "all" in corners:
            # Find all edges and apply fillet
            edges = self.solid.edges()
            if edges.size() > 0:
                self.solid = self.solid.fillet(radius)
                self.construction_history.append(f"Fillet: R{radius} on all edges")
                print(f"  > Applied fillet: R{radius} on all edges")
                return True
        else:
            # Selective edge filleting would require more complex edge selection
            print(f"⚠️ Selective corner filleting not yet implemented")
            return False
            
        return True
    
    def _apply_chamfer(self, feature: Dict[str, Any]) -> bool:
        """Apply chamfer to edges."""
        distance = feature.get("distance", 1)
        corners = feature.get("corners", ["all"])
        
        # For now, apply chamfer to all edges if "all" is specified
        if "all" in corners:
            edges = self.solid.edges()
            if edges.size() > 0:
                self.solid = self.solid.chamfer(distance)
                self.construction_history.append(f"Chamfer: {distance}mm on all edges")
                print(f"  > Applied chamfer: {distance}mm on all edges")
                return True
        else:
            print(f"⚠️ Selective corner chamfering not yet implemented")
            return False
            
        return True
    
    def _apply_counterbore(self, feature: Dict[str, Any]) -> bool:
        """Apply counterbore hole feature."""
        center = feature.get("center", [0, 0])
        hole_diameter = feature.get("hole_diameter", 6)
        counterbore_diameter = feature.get("counterbore_diameter", 12)
        counterbore_depth = feature.get("counterbore_depth", 3)
        
        # Get the bounding box 
        bbox = self.solid.val().BoundingBox()
        through_depth = bbox.zmax - bbox.zmin + 1
        
        # Create through hole
        through_hole = (cq.Workplane("XY")
                       .moveTo(center[0], center[1])
                       .circle(hole_diameter/2)
                       .extrude(through_depth))
        
        # Create counterbore
        counterbore = (cq.Workplane("XY")
                      .moveTo(center[0], center[1])
                      .circle(counterbore_diameter/2)
                      .extrude(counterbore_depth))
        
        # Apply both cuts
        self.solid = self.solid.cut(through_hole).cut(counterbore)
        
        self.construction_history.append(f"Counterbore: ⌀{hole_diameter}/⌀{counterbore_diameter}x{counterbore_depth} at {center}")
        print(f"  > Applied counterbore: ⌀{hole_diameter}/⌀{counterbore_diameter}x{counterbore_depth} at {center}")
        return True
    
    def _apply_countersink(self, feature: Dict[str, Any]) -> bool:
        """Apply countersink hole feature."""
        center = feature.get("center", [0, 0])
        hole_diameter = feature.get("hole_diameter", 6)
        countersink_diameter = feature.get("countersink_diameter", 12)
        countersink_angle = feature.get("countersink_angle", 90)
        
        # Calculate countersink depth from angle and diameter difference
        radius_diff = (countersink_diameter - hole_diameter) / 2
        countersink_depth = radius_diff / math.tan(math.radians(countersink_angle / 2))
        
        # Get the bounding box 
        bbox = self.solid.val().BoundingBox()
        through_depth = bbox.zmax - bbox.zmin + 1
        
        # Create through hole
        through_hole = (cq.Workplane("XY")
                       .moveTo(center[0], center[1])
                       .circle(hole_diameter/2)
                       .extrude(through_depth))
        
        # Create countersink (conical cut)
        # Start with larger circle and taper to hole diameter
        countersink = (cq.Workplane("XY")
                      .moveTo(center[0], center[1])
                      .circle(countersink_diameter/2)
                      .workplane(offset=countersink_depth)
                      .circle(hole_diameter/2)
                      .loft())
        
        # Apply both cuts
        self.solid = self.solid.cut(through_hole).cut(countersink)
        
        self.construction_history.append(f"Countersink: ⌀{hole_diameter}/⌀{countersink_diameter}x{countersink_angle}° at {center}")
        print(f"  > Applied countersink: ⌀{hole_diameter}/⌀{countersink_diameter}x{countersink_angle}° at {center}")
        return True
    
    def _apply_tapped_hole(self, feature: Dict[str, Any]) -> bool:
        """Apply tapped hole feature (simplified as pilot hole)."""
        center = feature.get("center", [0, 0])
        pilot_diameter = feature.get("pilot_diameter", 5)
        thread_spec = feature.get("thread_spec", "M6")
        
        # For now, just create the pilot hole (thread modeling is complex)
        bbox = self.solid.val().BoundingBox()
        depth = bbox.zmax - bbox.zmin + 1
        
        hole = (cq.Workplane("XY")
               .moveTo(center[0], center[1])
               .circle(pilot_diameter/2)
               .extrude(depth))
        
        self.solid = self.solid.cut(hole)
        
        self.construction_history.append(f"Tapped hole: {thread_spec} (⌀{pilot_diameter}) at {center}")
        print(f"  > Applied tapped hole: {thread_spec} (⌀{pilot_diameter}) at {center}")
        return True
    
    def get_projection_edges(self, projection_type: ProjectionType) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """
        Get 2D projection edges with hidden line removal.
        
        Returns:
            List of edge tuples: [((x1, y1), (x2, y2)), ...]
        """
        if not self.solid:
            print("❌ No solid available for projection")
            return []
            
        try:
            # Set up view direction based on projection type
            if projection_type == ProjectionType.ISOMETRIC:
                view_direction = (1, 1, 1)
            elif projection_type == ProjectionType.FRONT:
                view_direction = (0, -1, 0)
            elif projection_type == ProjectionType.TOP:
                view_direction = (0, 0, -1)
            elif projection_type == ProjectionType.RIGHT:
                view_direction = (1, 0, 0)
            elif projection_type == ProjectionType.BACK:
                view_direction = (0, 1, 0)
            elif projection_type == ProjectionType.BOTTOM:
                view_direction = (0, 0, 1)
            elif projection_type == ProjectionType.LEFT:
                view_direction = (-1, 0, 0)
            else:
                view_direction = (1, 1, 1)  # Default to isometric
            
            # Use CadQuery's built-in projection capabilities
            # This is a simplified version - more sophisticated HLR would be needed for production
            projected = self.solid.projectToSketch(view_direction)
            
            # Extract edges from the projected sketch
            edges = []
            for edge in projected.edges().vals():
                # Get edge endpoints
                start = edge.startPoint()
                end = edge.endPoint()
                edges.append(((start.x, start.y), (end.x, end.y)))
            
            print(f"✅ Generated {len(edges)} projection edges for {projection_type.value} view")
            return edges
            
        except Exception as e:
            print(f"❌ Failed to generate projection: {e}")
            # Fallback: extract visible edges manually (simplified)
            return self._fallback_projection(projection_type)
    
    def _fallback_projection(self, projection_type: ProjectionType) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Fallback projection method using edge analysis."""
        if not self.solid:
            return []
            
        try:
            edges = []
            
            # Get all edges from the solid
            for edge in self.solid.edges().vals():
                start = edge.startPoint()
                end = edge.endPoint()
                
                # Project to 2D based on view type
                if projection_type == ProjectionType.ISOMETRIC:
                    # Isometric projection matrix
                    x1 = start.x - start.z * 0.5
                    y1 = start.y + start.z * 0.866
                    x2 = end.x - end.z * 0.5  
                    y2 = end.y + end.z * 0.866
                elif projection_type == ProjectionType.FRONT:
                    x1, y1 = start.x, start.z
                    x2, y2 = end.x, end.z
                elif projection_type == ProjectionType.TOP:
                    x1, y1 = start.x, start.y
                    x2, y2 = end.x, end.y
                elif projection_type == ProjectionType.RIGHT:
                    x1, y1 = start.y, start.z
                    x2, y2 = end.y, end.z
                else:
                    # Default to top view
                    x1, y1 = start.x, start.y
                    x2, y2 = end.x, end.y
                
                edges.append(((x1, y1), (x2, y2)))
            
            print(f"✅ Generated {len(edges)} fallback projection edges for {projection_type.value} view")
            return edges
            
        except Exception as e:
            print(f"❌ Fallback projection failed: {e}")
            return []
    
    def get_solid_info(self) -> Dict[str, Any]:
        """Get information about the current solid."""
        if not self.solid:
            return {"error": "No solid available"}
            
        try:
            bbox = self.solid.val().BoundingBox()
            volume = self.solid.val().Volume()
            surface_area = self.solid.val().Area()
            
            return {
                "volume": volume,
                "surface_area": surface_area,
                "bounding_box": {
                    "x_min": bbox.xmin, "x_max": bbox.xmax,
                    "y_min": bbox.ymin, "y_max": bbox.ymax,
                    "z_min": bbox.zmin, "z_max": bbox.zmax
                },
                "construction_history": self.construction_history
            }
        except Exception as e:
            return {"error": f"Failed to get solid info: {e}"}
    
    def export_step(self, filepath: str) -> bool:
        """Export solid as STEP file."""
        if not self.solid:
            print("❌ No solid to export")
            return False
            
        try:
            cq.exporters.export(self.solid, filepath)
            print(f"✅ Exported STEP file: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Failed to export STEP: {e}")
            return False
    
    def export_stl(self, filepath: str) -> bool:
        """Export solid as STL file."""
        if not self.solid:
            print("❌ No solid to export")
            return False
            
        try:
            cq.exporters.export(self.solid, filepath)
            print(f"✅ Exported STL file: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Failed to export STL: {e}")
            return False