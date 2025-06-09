"""
3-D Solid Build-up and Validation System
Phase 6: Builds lightweight solids from feature lists to detect intersections and clashes
"""

import numpy as np
import json
from typing import List, Dict, Any, Tuple, Optional
import tempfile
import os


class SimpleGeometry:
    """Base class for simple 3D geometry."""
    
    def __init__(self, center: Tuple[float, float, float] = (0, 0, 0)):
        self.center = np.array(center)
    
    def intersects(self, other: 'SimpleGeometry') -> bool:
        """Check if this geometry intersects with another."""
        raise NotImplementedError
    
    def get_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get bounding box as (min_point, max_point)."""
        raise NotImplementedError


class Box(SimpleGeometry):
    """Simple 3D box geometry."""
    
    def __init__(self, center: Tuple[float, float, float], width: float, height: float, depth: float):
        super().__init__(center)
        self.width = width
        self.height = height
        self.depth = depth
        
        # Calculate half-extents
        self.half_extents = np.array([width/2, height/2, depth/2])
    
    def intersects(self, other: 'SimpleGeometry') -> bool:
        """Check if this box intersects with another geometry."""
        if isinstance(other, Box):
            return self._intersects_box(other)
        elif isinstance(other, Cylinder):
            return other.intersects(self)  # Delegate to cylinder
        elif isinstance(other, Sphere):
            return other.intersects(self)  # Delegate to sphere
        return False
    
    def _intersects_box(self, other: 'Box') -> bool:
        """Check if this box intersects with another box (AABB test)."""
        distance = np.abs(self.center - other.center)
        sum_extents = self.half_extents + other.half_extents
        
        # Boxes intersect if distance is less than sum of extents in all dimensions
        return np.all(distance <= sum_extents)
    
    def get_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get bounding box."""
        min_point = self.center - self.half_extents
        max_point = self.center + self.half_extents
        return min_point, max_point


class Cylinder(SimpleGeometry):
    """Simple 3D cylinder geometry."""
    
    def __init__(self, center: Tuple[float, float, float], radius: float, height: float):
        super().__init__(center)
        self.radius = radius
        self.height = height
    
    def intersects(self, other: 'SimpleGeometry') -> bool:
        """Check if this cylinder intersects with another geometry."""
        if isinstance(other, Cylinder):
            return self._intersects_cylinder(other)
        elif isinstance(other, Box):
            return self._intersects_box(other)
        elif isinstance(other, Sphere):
            return other.intersects(self)  # Delegate to sphere
        return False
    
    def _intersects_cylinder(self, other: 'Cylinder') -> bool:
        """Check if this cylinder intersects with another cylinder."""
        # Check Z-axis overlap
        z_distance = abs(self.center[2] - other.center[2])
        z_overlap = z_distance < (self.height/2 + other.height/2)
        
        if not z_overlap:
            return False
        
        # Check radial overlap in XY plane
        xy_distance = np.sqrt((self.center[0] - other.center[0])**2 + 
                             (self.center[1] - other.center[1])**2)
        radial_overlap = xy_distance < (self.radius + other.radius)
        
        return radial_overlap
    
    def _intersects_box(self, other: 'Box') -> bool:
        """Check if this cylinder intersects with a box (simplified)."""
        # Simplified cylinder-box intersection test
        # Check if cylinder center is within box bounds plus radius
        distance = np.abs(self.center - other.center)
        expanded_extents = other.half_extents + np.array([self.radius, self.radius, self.height/2])
        
        return np.all(distance <= expanded_extents)
    
    def get_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get bounding box."""
        min_point = self.center - np.array([self.radius, self.radius, self.height/2])
        max_point = self.center + np.array([self.radius, self.radius, self.height/2])
        return min_point, max_point


class Sphere(SimpleGeometry):
    """Simple 3D sphere geometry."""
    
    def __init__(self, center: Tuple[float, float, float], radius: float):
        super().__init__(center)
        self.radius = radius
    
    def intersects(self, other: 'SimpleGeometry') -> bool:
        """Check if this sphere intersects with another geometry."""
        if isinstance(other, Sphere):
            return self._intersects_sphere(other)
        elif isinstance(other, (Box, Cylinder)):
            # Simplified sphere-other intersection
            distance = np.linalg.norm(self.center - other.center)
            return distance < self.radius  # Very simplified
        return False
    
    def _intersects_sphere(self, other: 'Sphere') -> bool:
        """Check if this sphere intersects with another sphere."""
        distance = np.linalg.norm(self.center - other.center)
        return distance < (self.radius + other.radius)
    
    def get_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get bounding box."""
        radius_vec = np.array([self.radius, self.radius, self.radius])
        min_point = self.center - radius_vec
        max_point = self.center + radius_vec
        return min_point, max_point


class SolidValidator:
    """Validates 3D solids built from drawing plans."""
    
    def __init__(self):
        self.geometries: List[SimpleGeometry] = []
        self.default_thickness = 10.0  # Default thickness for 2D features
    
    def build_solid_from_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Build a 3D solid representation from a drawing plan.
        
        Args:
            plan: Drawing plan dictionary
            
        Returns:
            True if build successful, False otherwise
        """
        
        try:
            self.geometries = []
            
            # Build base feature
            base_feature = plan.get('base_feature', {})
            if base_feature:
                base_geometry = self._create_base_geometry(base_feature)
                if base_geometry:
                    self.geometries.append(base_geometry)
            
            # Build modifying features
            modifying_features = plan.get('modifying_features', [])
            for feature in modifying_features:
                feature_geometry = self._create_feature_geometry(feature, base_feature)
                if feature_geometry:
                    self.geometries.append(feature_geometry)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to build solid: {e}")
            return False
    
    def _create_base_geometry(self, base_feature: Dict[str, Any]) -> Optional[SimpleGeometry]:
        """Create geometry for base feature."""
        
        shape = base_feature.get('shape')
        
        if shape == 'rectangle':
            width = base_feature.get('width', 100)
            height = base_feature.get('height', 100)
            depth = self.default_thickness
            
            return Box(center=(0, 0, 0), width=width, height=height, depth=depth)
            
        elif shape == 'circle':
            diameter = base_feature.get('diameter', 100)
            radius = diameter / 2
            height = self.default_thickness
            
            return Cylinder(center=(0, 0, 0), radius=radius, height=height)
        
        return None
    
    def _create_feature_geometry(self, feature: Dict[str, Any], base_feature: Dict[str, Any]) -> Optional[SimpleGeometry]:
        """Create geometry for modifying feature."""
        
        feature_type = feature.get('type')
        center = feature.get('center', [0, 0])
        
        # Convert 2D center to 3D
        center_3d = (center[0], center[1], 0)
        
        if feature_type in ['hole', 'counterbore', 'countersink', 'tapped_hole']:
            # Create cylinder for holes
            diameter = feature.get('diameter', 0)
            if diameter == 0:
                diameter = feature.get('hole_diameter', 10)
            
            radius = diameter / 2
            height = self.default_thickness + 2  # Slightly taller to ensure intersection
            
            return Cylinder(center=center_3d, radius=radius, height=height)
            
        elif feature_type == 'slot':
            # Create box for slots
            width = feature.get('width', 10)
            length = feature.get('length', 20)
            height = self.default_thickness + 2
            
            return Box(center=center_3d, width=length, height=width, depth=height)
        
        # Fillets and chamfers don't create separate geometries in this simplified model
        return None
    
    def detect_collisions(self) -> List[Dict[str, Any]]:
        """
        Detect collisions between geometries.
        
        Returns:
            List of collision reports
        """
        
        collisions = []
        
        for i in range(len(self.geometries)):
            for j in range(i + 1, len(self.geometries)):
                geom1 = self.geometries[i]
                geom2 = self.geometries[j]
                
                if geom1.intersects(geom2):
                    collision = {
                        'geometry1_index': i,
                        'geometry2_index': j,
                        'geometry1_type': type(geom1).__name__,
                        'geometry2_type': type(geom2).__name__,
                        'geometry1_center': geom1.center.tolist(),
                        'geometry2_center': geom2.center.tolist(),
                        'severity': 'collision'
                    }
                    collisions.append(collision)
        
        return collisions
    
    def validate_plan(self, plan: Dict[str, Any]) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """
        Validate a drawing plan for 3D geometric consistency.
        
        Args:
            plan: Drawing plan dictionary
            
        Returns:
            Tuple of (is_valid, error_messages, collision_reports)
        """
        
        # Build the solid
        if not self.build_solid_from_plan(plan):
            return False, ["Failed to build 3D solid from plan"], []
        
        # Detect collisions
        collisions = self.detect_collisions()
        
        # Generate error messages
        errors = []
        for collision in collisions:
            error_msg = (f"Collision detected between {collision['geometry1_type']} "
                        f"at {collision['geometry1_center']} and {collision['geometry2_type']} "
                        f"at {collision['geometry2_center']}")
            errors.append(error_msg)
        
        is_valid = len(collisions) == 0
        
        return is_valid, errors, collisions


def validate_drawing_plan_3d(plan_path: str) -> Dict[str, Any]:
    """
    Validate a drawing plan for 3D geometric consistency.
    
    Args:
        plan_path: Path to JSON plan file
        
    Returns:
        Dictionary with validation results
    """
    
    try:
        with open(plan_path, 'r') as f:
            plan = json.load(f)
        
        validator = SolidValidator()
        is_valid, errors, collisions = validator.validate_plan(plan)
        
        return {
            'is_valid': is_valid,
            'collision_count': len(collisions),
            'errors': errors,
            'collisions': collisions,
            'geometry_count': len(validator.geometries)
        }
        
    except Exception as e:
        return {
            'is_valid': False,
            'collision_count': -1,
            'errors': [f"Failed to validate plan: {str(e)}"],
            'collisions': [],
            'geometry_count': 0
        }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python solid_validator.py <plan_file>")
        sys.exit(1)
    
    plan_file = sys.argv[1]
    results = validate_drawing_plan_3d(plan_file)
    
    print(f"🔍 3D Solid Validation Report")
    print(f"=" * 40)
    print(f"Valid: {'✅ Yes' if results['is_valid'] else '❌ No'}")
    print(f"Geometries Built: {results['geometry_count']}")
    print(f"Collisions Found: {results['collision_count']}")
    
    if results['errors']:
        print(f"\n❌ Issues:")
        for error in results['errors']:
            print(f"  - {error}")
    
    if results['collisions']:
        print(f"\n⚠️ Collision Details:")
        for i, collision in enumerate(results['collisions'], 1):
            print(f"  {i}. {collision['geometry1_type']} ↔ {collision['geometry2_type']}")
    
    if results['is_valid']:
        print(f"\n✅ No geometric conflicts detected")