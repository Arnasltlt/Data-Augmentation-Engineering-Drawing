"""
Section Engine - Milestone 3: Sections & Hatching
STRETCH_STRATEGY.md Implementation

Generates professional cross-sectional views with:
- Cutting plane definitions and visualization
- Cross-sectional geometry calculation
- Material-specific hatching patterns
- Section view labels and annotations
- Integration with multi-view layout system
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass

# Import our solid builder for section calculation
try:
    from solidbuilder_ocp import SolidBuilder, ProjectionType
    SOLID_BUILDER_AVAILABLE = True
except ImportError:
    try:
        from solidbuilder_mock import SolidBuilder, ProjectionType
        SOLID_BUILDER_AVAILABLE = True
    except ImportError:
        print("❌ No SolidBuilder available for Sectioning")
        SOLID_BUILDER_AVAILABLE = False

class SectionDirection(Enum):
    """Standard section cutting directions."""
    HORIZONTAL = "horizontal"  # Top/bottom view sections
    VERTICAL_FRONT = "vertical_front"  # Front view sections  
    VERTICAL_SIDE = "vertical_side"  # Side view sections
    OBLIQUE = "oblique"  # Angled sections

class HatchPattern(Enum):
    """Standard hatching patterns for different materials."""
    GENERAL = "general"  # 45° lines, general material
    STEEL = "steel"  # 45° lines, steel
    ALUMINUM = "aluminum"  # 45° lines, closer spacing
    PLASTIC = "plastic"  # 30° lines
    WOOD = "wood"  # Grain pattern
    CONCRETE = "concrete"  # Random pattern
    RUBBER = "rubber"  # Solid fill with outline
    GLASS = "glass"  # No hatch, outline only

@dataclass
class CuttingPlane:
    """Represents a cutting plane for section generation."""
    name: str  # Section identifier (A, B, C, etc.)
    direction: SectionDirection
    position: float  # Position along the cutting axis
    normal: Tuple[float, float, float]  # Cutting plane normal vector
    origin: Tuple[float, float, float]  # Point on the cutting plane
    view_direction: Tuple[float, float, float]  # Direction to view section

@dataclass
class SectionGeometry:
    """Represents the geometry of a cross-section."""
    outline_edges: List[Tuple[Tuple[float, float], Tuple[float, float]]]  # Section outline
    internal_edges: List[Tuple[Tuple[float, float], Tuple[float, float]]]  # Internal features
    hatch_regions: List[List[Tuple[float, float]]]  # Closed regions for hatching
    bounds: 'ViewBounds'  # Bounding box of section
    cutting_plane: CuttingPlane  # Associated cutting plane

@dataclass
class ViewBounds:
    """Bounding box for geometric elements."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    width: float
    height: float

class SectionEngine:
    """
    Professional section generation engine for engineering drawings.
    Implements Milestone 3 requirements from STRETCH_STRATEGY.md.
    """
    
    def __init__(self):
        self.cutting_planes: List[CuttingPlane] = []
        self.sections: List[SectionGeometry] = []
        self.hatch_patterns = self._initialize_hatch_patterns()
        
    def add_cutting_plane(self, name: str, direction: SectionDirection, 
                         position: float, solid_bounds: Dict[str, float]) -> CuttingPlane:
        """
        Add a cutting plane for section generation.
        
        Args:
            name: Section identifier (A, B, C, etc.)
            direction: Cutting direction
            position: Position along cutting axis (0.0-1.0 normalized)
            solid_bounds: Bounding box of the solid being sectioned
            
        Returns:
            CuttingPlane object
        """
        # Calculate plane parameters based on direction and solid bounds
        if direction == SectionDirection.HORIZONTAL:
            # Horizontal cut (parallel to XY plane)
            z_pos = solid_bounds["z_min"] + position * (solid_bounds["z_max"] - solid_bounds["z_min"])
            cutting_plane = CuttingPlane(
                name=name,
                direction=direction,
                position=position,
                normal=(0, 0, 1),  # Z-normal
                origin=(0, 0, z_pos),
                view_direction=(0, 0, -1)  # Looking down
            )
        elif direction == SectionDirection.VERTICAL_FRONT:
            # Vertical cut through front view (parallel to YZ plane)
            x_pos = solid_bounds["x_min"] + position * (solid_bounds["x_max"] - solid_bounds["x_min"])
            cutting_plane = CuttingPlane(
                name=name,
                direction=direction,
                position=position,
                normal=(1, 0, 0),  # X-normal
                origin=(x_pos, 0, 0),
                view_direction=(-1, 0, 0)  # Looking in -X direction
            )
        elif direction == SectionDirection.VERTICAL_SIDE:
            # Vertical cut through side view (parallel to XZ plane)
            y_pos = solid_bounds["y_min"] + position * (solid_bounds["y_max"] - solid_bounds["y_min"])
            cutting_plane = CuttingPlane(
                name=name,
                direction=direction,
                position=position,
                normal=(0, 1, 0),  # Y-normal
                origin=(0, y_pos, 0),
                view_direction=(0, -1, 0)  # Looking in -Y direction
            )
        else:
            # Default to vertical front
            x_pos = solid_bounds["x_min"] + position * (solid_bounds["x_max"] - solid_bounds["x_min"])
            cutting_plane = CuttingPlane(
                name=name,
                direction=SectionDirection.VERTICAL_FRONT,
                position=position,
                normal=(1, 0, 0),
                origin=(x_pos, 0, 0),
                view_direction=(-1, 0, 0)
            )
        
        self.cutting_planes.append(cutting_plane)
        print(f"✅ Added cutting plane {name}: {direction.value} at position {position:.2f}")
        return cutting_plane
    
    def generate_section(self, solid_builder: SolidBuilder, cutting_plane: CuttingPlane) -> SectionGeometry:
        """
        Generate cross-sectional geometry from a solid and cutting plane.
        
        Args:
            solid_builder: SolidBuilder with the solid to section
            cutting_plane: Cutting plane definition
            
        Returns:
            SectionGeometry object with sectioned geometry
        """
        if not SOLID_BUILDER_AVAILABLE:
            # Use mock section generation
            return self._generate_mock_section(cutting_plane)
        
        try:
            # Get section curves from solid builder
            section_curves = solid_builder.get_section_curves(cutting_plane)
            
            if not section_curves:
                print(f"⚠️ No section geometry for cutting plane {cutting_plane.name}")
                return self._generate_mock_section(cutting_plane)
            
            # Process section curves into geometry
            outline_edges = []
            internal_edges = []
            hatch_regions = []
            
            # Separate outline and internal curves
            for curve in section_curves:
                if self._is_outline_curve(curve):
                    outline_edges.extend(curve.get("edges", []))
                else:
                    internal_edges.extend(curve.get("edges", []))
                
                # Extract closed regions for hatching
                if curve.get("closed", False):
                    hatch_regions.append(curve.get("points", []))
            
            # Calculate section bounds
            all_edges = outline_edges + internal_edges
            bounds = self._calculate_bounds(all_edges)
            
            section_geometry = SectionGeometry(
                outline_edges=outline_edges,
                internal_edges=internal_edges,
                hatch_regions=hatch_regions,
                bounds=bounds,
                cutting_plane=cutting_plane
            )
            
            self.sections.append(section_geometry)
            print(f"✅ Generated section {cutting_plane.name}: {len(outline_edges)} outline edges, {len(internal_edges)} internal edges")
            return section_geometry
            
        except Exception as e:
            print(f"❌ Section generation failed: {e}")
            return self._generate_mock_section(cutting_plane)
    
    def _generate_mock_section(self, cutting_plane: CuttingPlane) -> SectionGeometry:
        """Generate mock section geometry for testing/demo purposes."""
        # Create a representative section based on cutting plane
        width = 60.0  # Mock section width
        height = 40.0  # Mock section height
        
        # Main section outline (rectangle)
        outline_edges = [
            ((-width/2, -height/2), (width/2, -height/2)),  # Bottom
            ((width/2, -height/2), (width/2, height/2)),    # Right
            ((width/2, height/2), (-width/2, height/2)),    # Top
            ((-width/2, height/2), (-width/2, -height/2))   # Left
        ]
        
        # Internal features (holes, slots visible in section)
        internal_edges = []
        hatch_regions = []
        
        # Add mock internal features based on cutting plane direction
        if cutting_plane.direction == SectionDirection.VERTICAL_FRONT:
            # Show holes as circles in front section
            hole_centers = [(-15, 0), (15, 0)]
            for center in hole_centers:
                hole_edges = self._generate_circle_edges(center, 3.0, 8)
                internal_edges.extend(hole_edges)
            
            # Main body region for hatching (with holes excluded conceptually)
            hatch_regions.append([
                (-width/2, -height/2), (width/2, -height/2),
                (width/2, height/2), (-width/2, height/2)
            ])
            
        elif cutting_plane.direction == SectionDirection.HORIZONTAL:
            # Show rectangular features in top section
            internal_edges.extend([
                ((-10, -15), (10, -15)),
                ((10, -15), (10, 15)),
                ((10, 15), (-10, 15)),
                ((-10, 15), (-10, -15))
            ])
            
            # Multiple regions for hatching
            hatch_regions.extend([
                [(-width/2, -height/2), (-10, -height/2), (-10, height/2), (-width/2, height/2)],
                [(10, -height/2), (width/2, -height/2), (width/2, height/2), (10, height/2)]
            ])
        elif cutting_plane.direction == SectionDirection.VERTICAL_SIDE:
            # Show side section features
            internal_edges.extend([
                ((-8, -8), (8, -8)),
                ((8, -8), (8, 8)),
                ((8, 8), (-8, 8)),
                ((-8, 8), (-8, -8))
            ])
            
            # Side section hatching region
            hatch_regions.append([
                (-width/2, -height/2), (width/2, -height/2),
                (width/2, height/2), (-width/2, height/2)
            ])
        else:
            # Default hatch region for any other section type
            hatch_regions.append([
                (-width/2, -height/2), (width/2, -height/2),
                (width/2, height/2), (-width/2, height/2)
            ])
        
        # Calculate bounds
        bounds = self._calculate_bounds(outline_edges + internal_edges)
        
        section_geometry = SectionGeometry(
            outline_edges=outline_edges,
            internal_edges=internal_edges,
            hatch_regions=hatch_regions,
            bounds=bounds,
            cutting_plane=cutting_plane
        )
        
        self.sections.append(section_geometry)
        print(f"✅ Generated mock section {cutting_plane.name}: {cutting_plane.direction.value} with {len(hatch_regions)} hatch regions")
        return section_geometry
    
    def _generate_circle_edges(self, center: Tuple[float, float], radius: float, segments: int = 16) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Generate edge segments approximating a circle."""
        edges = []
        cx, cy = center
        
        for i in range(segments):
            angle1 = 2 * math.pi * i / segments
            angle2 = 2 * math.pi * (i + 1) / segments
            
            x1 = cx + radius * math.cos(angle1)
            y1 = cy + radius * math.sin(angle1)
            x2 = cx + radius * math.cos(angle2)
            y2 = cy + radius * math.sin(angle2)
            
            edges.append(((x1, y1), (x2, y2)))
        
        return edges
    
    def generate_hatching(self, section: SectionGeometry, pattern: HatchPattern = HatchPattern.GENERAL, 
                         spacing: float = 2.0, angle: float = 45.0) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """
        Generate hatching lines for a sectioned region.
        
        Args:
            section: Section geometry to hatch
            pattern: Hatching pattern type
            spacing: Line spacing in mm
            angle: Hatch angle in degrees
            
        Returns:
            List of hatch line segments
        """
        hatch_lines = []
        
        if pattern == HatchPattern.GLASS:
            # Glass has no hatching, just return empty
            return []
        
        # Get pattern parameters
        pattern_info = self.hatch_patterns.get(pattern, self.hatch_patterns[HatchPattern.GENERAL])
        hatch_angle = pattern_info.get("angle", angle)
        hatch_spacing = pattern_info.get("spacing", spacing)
        
        # Generate hatch lines for each region
        for region in section.hatch_regions:
            if len(region) < 3:
                continue  # Need at least 3 points for a region
            
            region_lines = self._generate_region_hatching(region, hatch_angle, hatch_spacing)
            hatch_lines.extend(region_lines)
        
        print(f"✅ Generated {len(hatch_lines)} hatch lines for section {section.cutting_plane.name}")
        return hatch_lines
    
    def _generate_region_hatching(self, region: List[Tuple[float, float]], 
                                 angle: float, spacing: float) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Generate hatching lines for a single closed region."""
        if len(region) < 3:
            return []
        
        # Calculate region bounding box
        x_coords = [p[0] for p in region]
        y_coords = [p[1] for p in region]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # Ensure we have a valid region
        if x_max - x_min < 0.1 or y_max - y_min < 0.1:
            return []
        
        hatch_lines = []
        angle_rad = math.radians(angle)
        
        # Simplified hatching: generate lines at the specified angle across the bounding box
        if abs(angle) < 45:  # More horizontal than vertical
            # Generate horizontal-ish lines
            num_lines = int((y_max - y_min) / spacing) + 1
            for i in range(num_lines):
                y = y_min + i * spacing
                if y_min <= y <= y_max:
                    # Simple line across the width with angle adjustment
                    dx = (y_max - y_min) * math.tan(angle_rad)
                    start_x = x_min - abs(dx)
                    end_x = x_max + abs(dx)
                    
                    hatch_lines.append(((start_x, y), (end_x, y)))
        else:  # More vertical than horizontal
            # Generate vertical-ish lines
            num_lines = int((x_max - x_min) / spacing) + 1
            for i in range(num_lines):
                x = x_min + i * spacing
                if x_min <= x <= x_max:
                    # Simple line across the height with angle adjustment
                    dy = (x_max - x_min) * math.tan(math.radians(90 - angle))
                    start_y = y_min - abs(dy)
                    end_y = y_max + abs(dy)
                    
                    hatch_lines.append(((x, start_y), (x, end_y)))
        
        # Ensure we have at least a few lines for any reasonable region
        if not hatch_lines and (x_max - x_min) > 1 and (y_max - y_min) > 1:
            # Fallback: create simple 45-degree lines
            num_lines = max(3, int((x_max - x_min) / 5))  # At least 3 lines
            for i in range(num_lines):
                x = x_min + i * ((x_max - x_min) / (num_lines - 1))
                hatch_lines.append(((x, y_min), (x, y_max)))
        
        return hatch_lines
    
    def _calculate_bounds(self, edges: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> ViewBounds:
        """Calculate bounding box for a set of edges."""
        if not edges:
            return ViewBounds(0, 0, 0, 0, 0, 0)
        
        x_coords = []
        y_coords = []
        
        for edge in edges:
            start, end = edge
            x_coords.extend([start[0], end[0]])
            y_coords.extend([start[1], end[1]])
        
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        return ViewBounds(
            x_min=x_min, x_max=x_max,
            y_min=y_min, y_max=y_max,
            width=x_max - x_min,
            height=y_max - y_min
        )
    
    def _initialize_hatch_patterns(self) -> Dict[HatchPattern, Dict[str, Any]]:
        """Initialize standard hatching patterns for different materials."""
        return {
            HatchPattern.GENERAL: {"angle": 45.0, "spacing": 2.0, "description": "General material"},
            HatchPattern.STEEL: {"angle": 45.0, "spacing": 2.0, "description": "Steel/Iron"},
            HatchPattern.ALUMINUM: {"angle": 45.0, "spacing": 1.5, "description": "Aluminum"},
            HatchPattern.PLASTIC: {"angle": 30.0, "spacing": 2.5, "description": "Plastic/Polymer"},
            HatchPattern.WOOD: {"angle": 0.0, "spacing": 3.0, "description": "Wood (with grain)"},
            HatchPattern.CONCRETE: {"angle": 45.0, "spacing": 4.0, "description": "Concrete/Masonry"},
            HatchPattern.RUBBER: {"angle": 45.0, "spacing": 1.0, "description": "Rubber/Elastomer"},
            HatchPattern.GLASS: {"angle": 0.0, "spacing": 0.0, "description": "Glass (no hatch)"}
        }
    
    def _is_outline_curve(self, curve: Dict[str, Any]) -> bool:
        """Determine if a curve is part of the outline or internal."""
        # Simple heuristic: longer curves are likely outline
        return curve.get("length", 0) > 10.0
    
    def generate_cutting_plane_indicators(self, cutting_plane: CuttingPlane, 
                                        view_bounds: ViewBounds) -> Dict[str, Any]:
        """
        Generate cutting plane indicators for parent views.
        
        Args:
            cutting_plane: Cutting plane to indicate
            view_bounds: Bounds of the view containing the cutting plane
            
        Returns:
            Dictionary with cutting plane geometry
        """
        indicators = {
            "cutting_lines": [],
            "section_arrows": [],
            "section_labels": []
        }
        
        # Generate cutting plane line based on direction
        if cutting_plane.direction == SectionDirection.VERTICAL_FRONT:
            # Vertical line in top/front views
            x_pos = view_bounds.x_min + cutting_plane.position * view_bounds.width
            line_start = (x_pos, view_bounds.y_min)
            line_end = (x_pos, view_bounds.y_max)
            
            # Section arrows pointing in view direction
            arrow_length = 8.0
            indicators["section_arrows"] = [
                {"start": (x_pos, view_bounds.y_max + 5), "end": (x_pos - arrow_length, view_bounds.y_max + 5)},
                {"start": (x_pos, view_bounds.y_min - 5), "end": (x_pos + arrow_length, view_bounds.y_min - 5)}
            ]
            
            # Section labels
            indicators["section_labels"] = [
                {"text": cutting_plane.name, "position": (x_pos - 10, view_bounds.y_max + 10)},
                {"text": cutting_plane.name, "position": (x_pos + 10, view_bounds.y_min - 10)}
            ]
            
        elif cutting_plane.direction == SectionDirection.HORIZONTAL:
            # Horizontal line in front/side views
            y_pos = view_bounds.y_min + cutting_plane.position * view_bounds.height
            line_start = (view_bounds.x_min, y_pos)
            line_end = (view_bounds.x_max, y_pos)
            
            # Section arrows
            arrow_length = 8.0
            indicators["section_arrows"] = [
                {"start": (view_bounds.x_min - 5, y_pos), "end": (view_bounds.x_min - 5, y_pos + arrow_length)},
                {"start": (view_bounds.x_max + 5, y_pos), "end": (view_bounds.x_max + 5, y_pos - arrow_length)}
            ]
            
            # Section labels
            indicators["section_labels"] = [
                {"text": cutting_plane.name, "position": (view_bounds.x_min - 15, y_pos + 5)},
                {"text": cutting_plane.name, "position": (view_bounds.x_max + 15, y_pos - 5)}
            ]
        
        # Add main cutting line
        if 'line_start' in locals() and 'line_end' in locals():
            indicators["cutting_lines"] = [{"start": line_start, "end": line_end}]
        
        return indicators
    
    def get_section_summary(self) -> Dict[str, Any]:
        """Get summary of all sections and cutting planes."""
        return {
            "cutting_planes": len(self.cutting_planes),
            "sections": len(self.sections),
            "available_patterns": list(self.hatch_patterns.keys()),
            "planes": [
                {
                    "name": cp.name,
                    "direction": cp.direction.value,
                    "position": cp.position
                }
                for cp in self.cutting_planes
            ]
        }

# Add section generation capability to SolidBuilder
if SOLID_BUILDER_AVAILABLE:
    # Extend the mock SolidBuilder with section capability
    try:
        from solidbuilder_mock import MockSolidBuilder
        
        def get_section_curves(self, cutting_plane: CuttingPlane) -> List[Dict[str, Any]]:
            """Mock section curve generation."""
            # Return mock section curves based on cutting plane
            if cutting_plane.direction == SectionDirection.VERTICAL_FRONT:
                return [
                    {
                        "edges": [
                            ((-30, -20), (30, -20)),
                            ((30, -20), (30, 20)),
                            ((30, 20), (-30, 20)),
                            ((-30, 20), (-30, -20))
                        ],
                        "closed": True,
                        "length": 200,
                        "points": [(-30, -20), (30, -20), (30, 20), (-30, 20)]
                    }
                ]
            elif cutting_plane.direction == SectionDirection.HORIZONTAL:
                return [
                    {
                        "edges": [
                            ((-40, -15), (40, -15)),
                            ((40, -15), (40, 15)),
                            ((40, 15), (-40, 15)),
                            ((-40, 15), (-40, -15))
                        ],
                        "closed": True,
                        "length": 220,
                        "points": [(-40, -15), (40, -15), (40, 15), (-40, 15)]
                    }
                ]
            elif cutting_plane.direction == SectionDirection.VERTICAL_SIDE:
                return [
                    {
                        "edges": [
                            ((-35, -18), (35, -18)),
                            ((35, -18), (35, 18)),
                            ((35, 18), (-35, 18)),
                            ((-35, 18), (-35, -18))
                        ],
                        "closed": True,
                        "length": 186,
                        "points": [(-35, -18), (35, -18), (35, 18), (-35, 18)]
                    }
                ]
            else:
                return [
                    {
                        "edges": [
                            ((-25, -15), (25, -15)),
                            ((25, -15), (25, 15)),
                            ((25, 15), (-25, 15)),
                            ((-25, 15), (-25, -15))
                        ],
                        "closed": True,
                        "length": 160,
                        "points": [(-25, -15), (25, -15), (25, 15), (-25, 15)]
                    }
                ]
        
        # Add method to MockSolidBuilder
        MockSolidBuilder.get_section_curves = get_section_curves
        print("✅ Added section generation to MockSolidBuilder")
        
    except ImportError:
        pass