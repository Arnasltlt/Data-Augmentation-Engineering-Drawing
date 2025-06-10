"""
Multi-View Layout Engine - Milestone 2: Multi-View Sheet
STRETCH_STRATEGY.md Implementation

Generates professional multi-view engineering drawing sheets with:
- Orthographic projections (Front/Top/Right)
- Isometric view
- Auto-scaling and positioning
- A3/A4 paper space with borders
- Title blocks and view labels
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass

# Import our solid builder for generating views
try:
    from solidbuilder_ocp import SolidBuilder, ProjectionType
    SOLID_BUILDER_AVAILABLE = True
except ImportError:
    try:
        from solidbuilder_mock import SolidBuilder, ProjectionType
        SOLID_BUILDER_AVAILABLE = True
    except ImportError:
        print("❌ No SolidBuilder available for MultiView")
        SOLID_BUILDER_AVAILABLE = False

# Import the new section engine
try:
    from section_engine import SectionEngine, SectionDirection, HatchPattern, CuttingPlane, SectionGeometry
    SECTION_ENGINE_AVAILABLE = True
except ImportError:
    print("❌ SectionEngine not available")
    SECTION_ENGINE_AVAILABLE = False

class PaperSize(Enum):
    """ISO paper sizes for multi-view layouts."""
    A4 = "A4"
    A3 = "A3"
    A2 = "A2"
    A1 = "A1"

@dataclass
class PaperSpecs:
    """Paper size specifications in mm."""
    width: float
    height: float
    margin: float
    title_block_width: float
    title_block_height: float

class PaperSizeManager:
    """Manages paper size specifications for different sheet formats."""
    
    SPECS = {
        PaperSize.A4: PaperSpecs(210, 297, 10, 180, 50),
        PaperSize.A3: PaperSpecs(297, 420, 15, 250, 60),
        PaperSize.A2: PaperSpecs(420, 594, 20, 350, 70),
        PaperSize.A1: PaperSpecs(594, 841, 25, 500, 80)
    }
    
    @classmethod
    def get_specs(cls, paper_size: PaperSize) -> PaperSpecs:
        """Get paper specifications for given size."""
        return cls.SPECS[paper_size]

@dataclass
class ViewPlacement:
    """Represents a view's position and scale on the sheet."""
    projection_type: ProjectionType
    x: float  # X position on sheet (mm)
    y: float  # Y position on sheet (mm)
    scale_factor: float  # Scaling factor for the view
    label: str  # View label (e.g., "FRONT VIEW")
    edges: List[Tuple[Tuple[float, float], Tuple[float, float]]]  # Projected edges
    # Section support (Milestone 3)
    is_section: bool = False  # Whether this is a section view
    section_geometry: Optional['SectionGeometry'] = None  # Section data if applicable
    hatch_lines: List[Tuple[Tuple[float, float], Tuple[float, float]]] = None  # Hatching lines
    cutting_plane_indicators: Dict[str, Any] = None  # Cutting plane indicators for parent views

@dataclass
class ViewBounds:
    """Bounding box for a set of edges."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    width: float
    height: float

class MultiViewLayout:
    """
    Multi-view layout engine for professional engineering drawings.
    Implements Milestone 2 requirements from STRETCH_STRATEGY.md.
    """
    
    def __init__(self, paper_size: PaperSize = PaperSize.A3):
        self.paper_size = paper_size
        self.paper_specs = PaperSizeManager.get_specs(paper_size)
        self.view_placements: List[ViewPlacement] = []
        self.border_offset = 5  # mm from paper edge
        # Section support (Milestone 3)
        self.section_engine = SectionEngine() if SECTION_ENGINE_AVAILABLE else None
        self.sections_enabled = False
        
    def enable_sections(self, sections: List[Dict[str, Any]]) -> bool:
        """
        Enable section generation with specified cutting planes.
        
        Args:
            sections: List of section definitions
            Example: [{"name": "A", "direction": "vertical_front", "position": 0.5, "material": "steel"}]
            
        Returns:
            True if sections were successfully enabled
        """
        if not SECTION_ENGINE_AVAILABLE:
            print("❌ Section engine not available")
            return False
        
        if not self.section_engine:
            self.section_engine = SectionEngine()
        
        print(f"🔧 Enabling {len(sections)} section(s)...")
        for section_def in sections:
            name = section_def.get("name", "A")
            direction_str = section_def.get("direction", "vertical_front")
            position = section_def.get("position", 0.5)
            
            # Convert string to enum
            try:
                direction = SectionDirection(direction_str)
            except ValueError:
                print(f"⚠️ Invalid section direction: {direction_str}, using vertical_front")
                direction = SectionDirection.VERTICAL_FRONT
            
            # Mock solid bounds for section plane calculation
            solid_bounds = {
                "x_min": -40, "x_max": 40,
                "y_min": -30, "y_max": 30, 
                "z_min": 0, "z_max": 10
            }
            
            self.section_engine.add_cutting_plane(name, direction, position, solid_bounds)
        
        self.sections_enabled = True
        print("✅ Section generation enabled")
        return True
    
    def generate_sectioned_multiview_sheet(self, plan: Dict[str, Any], 
                                         sections: List[Dict[str, Any]] = None) -> Tuple[List[ViewPlacement], Dict[str, Any]]:
        """
        Generate a complete multi-view sheet including sectional views.
        Enhanced version of generate_four_view_sheet for Milestone 3.
        
        Args:
            plan: Feature-based drawing plan
            sections: Section definitions for cutting planes
            
        Returns:
            Tuple of (view_placements, sheet_metadata)
        """
        if not SOLID_BUILDER_AVAILABLE:
            raise RuntimeError("SolidBuilder required for multi-view generation")
        
        print("🏗️ Generating sectioned multi-view sheet layout...")
        
        # Enable sections if provided
        if sections:
            self.enable_sections(sections)
        
        # Step 1: Build 3D solid and generate projections
        solid_builder = SolidBuilder()
        if not solid_builder.build_from_plan(plan):
            raise RuntimeError("Failed to build 3D solid from plan")
        
        # Step 2: Generate standard orthographic views
        standard_views = [
            (ProjectionType.FRONT, "FRONT VIEW"),
            (ProjectionType.TOP, "TOP VIEW"), 
            (ProjectionType.RIGHT, "RIGHT VIEW"),
            (ProjectionType.ISOMETRIC, "ISOMETRIC VIEW")
        ]
        
        view_data = []
        for proj_type, label in standard_views:
            edges = solid_builder.get_projection_edges(proj_type)
            if edges:
                view_data.append({
                    'projection_type': proj_type,
                    'label': label,
                    'edges': edges,
                    'bounds': self._calculate_view_bounds(edges),
                    'is_section': False
                })
                print(f"  ✅ Generated {label}: {len(edges)} edges")
        
        # Step 3: Generate section views if enabled
        section_views = []
        if self.sections_enabled and self.section_engine:
            section_views = self._generate_section_views(solid_builder)
            view_data.extend(section_views)
        
        # Step 4: Calculate layout with sections
        if self.sections_enabled and section_views:
            self.view_placements = self._calculate_sectioned_layout(view_data)
        else:
            # Fall back to standard 4-view layout
            self.view_placements = self._calculate_optimal_layout(view_data)
        
        # Step 5: Generate cutting plane indicators for parent views
        if self.sections_enabled:
            self._add_cutting_plane_indicators()
        
        # Step 6: Generate sheet metadata
        solid_info = solid_builder.get_solid_info()
        sheet_metadata = {
            'paper_size': self.paper_size.value,
            'paper_width': self.paper_specs.width,
            'paper_height': self.paper_specs.height,
            'view_count': len(self.view_placements),
            'section_count': len(section_views),
            'solid_volume': solid_info.get('volume', 0),
            'construction_history': solid_info.get('construction_history', []),
            'layout_method': 'sectioned_multiview' if self.sections_enabled else 'auto_scaled_orthographic',
            'sections_enabled': self.sections_enabled
        }
        
        total_views = len(self.view_placements)
        section_count = len([vp for vp in self.view_placements if vp.is_section])
        print(f"✅ Generated {total_views}-view layout ({section_count} sections) on {self.paper_size.value}")
        return self.view_placements, sheet_metadata
    
    def _calculate_view_bounds(self, edges: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> ViewBounds:
        """Calculate bounding box for a set of projection edges."""
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
    
    def _calculate_optimal_layout(self, view_data: List[Dict]) -> List[ViewPlacement]:
        """
        Calculate optimal layout for the four views with automatic scaling.
        
        Uses standard engineering drawing layout:
        +-------------+-------------+
        |             |             |
        |  TOP VIEW   | ISOMETRIC   |
        |             |    VIEW     |
        +-------------+-------------+
        |             |             |
        | FRONT VIEW  | RIGHT VIEW  |
        |             |             |
        +-------------+-------------+
        """
        if len(view_data) < 4:
            return self._calculate_fallback_layout(view_data)
        
        # Available drawing area (excluding margins and title block)
        available_width = self.paper_specs.width - 2 * self.paper_specs.margin
        available_height = (self.paper_specs.height - 2 * self.paper_specs.margin - 
                          self.paper_specs.title_block_height)
        
        # Divide into quadrants with spacing
        spacing = 10  # mm between views
        quadrant_width = (available_width - spacing) / 2
        quadrant_height = (available_height - spacing) / 2
        
        # Map view types to quadrant positions
        layout_map = {
            ProjectionType.TOP: (0, 1),      # Top-left
            ProjectionType.ISOMETRIC: (1, 1), # Top-right
            ProjectionType.FRONT: (0, 0),    # Bottom-left
            ProjectionType.RIGHT: (1, 0)     # Bottom-right
        }
        
        view_placements = []
        
        for view in view_data:
            proj_type = view['projection_type']
            if proj_type not in layout_map:
                continue
                
            quad_x, quad_y = layout_map[proj_type]
            bounds = view['bounds']
            
            # Calculate scale factor to fit in quadrant
            scale_x = quadrant_width / bounds.width if bounds.width > 0 else 1.0
            scale_y = quadrant_height / bounds.height if bounds.height > 0 else 1.0
            scale_factor = min(scale_x, scale_y, 2.0) * 0.8  # Max 2x scale, 80% utilization
            
            # Calculate position (center of quadrant)
            base_x = self.paper_specs.margin + quad_x * (quadrant_width + spacing)
            base_y = self.paper_specs.margin + quad_y * (quadrant_height + spacing)
            
            # Center the view in its quadrant
            view_x = base_x + quadrant_width / 2
            view_y = base_y + quadrant_height / 2
            
            # Scale the edges
            scaled_edges = self._scale_edges(view['edges'], scale_factor, bounds)
            
            view_placements.append(ViewPlacement(
                projection_type=proj_type,
                x=view_x,
                y=view_y,
                scale_factor=scale_factor,
                label=view['label'],
                edges=scaled_edges
            ))
            
            print(f"  📐 {view['label']}: position=({view_x:.1f}, {view_y:.1f}), scale={scale_factor:.2f}")
        
        return view_placements
    
    def _calculate_fallback_layout(self, view_data: List[Dict]) -> List[ViewPlacement]:
        """Fallback layout for when we have fewer than 4 views."""
        available_width = self.paper_specs.width - 2 * self.paper_specs.margin
        available_height = (self.paper_specs.height - 2 * self.paper_specs.margin - 
                          self.paper_specs.title_block_height)
        
        view_placements = []
        views_per_row = min(2, len(view_data))
        rows = math.ceil(len(view_data) / views_per_row)
        
        spacing = 10
        view_width = (available_width - (views_per_row - 1) * spacing) / views_per_row
        view_height = (available_height - (rows - 1) * spacing) / rows
        
        for i, view in enumerate(view_data):
            row = i // views_per_row
            col = i % views_per_row
            
            bounds = view['bounds']
            scale_x = view_width / bounds.width if bounds.width > 0 else 1.0
            scale_y = view_height / bounds.height if bounds.height > 0 else 1.0
            scale_factor = min(scale_x, scale_y, 2.0) * 0.8
            
            view_x = self.paper_specs.margin + col * (view_width + spacing) + view_width / 2
            view_y = self.paper_specs.margin + row * (view_height + spacing) + view_height / 2
            
            scaled_edges = self._scale_edges(view['edges'], scale_factor, bounds)
            
            view_placements.append(ViewPlacement(
                projection_type=view['projection_type'],
                x=view_x,
                y=view_y,
                scale_factor=scale_factor,
                label=view['label'],
                edges=scaled_edges
            ))
        
        return view_placements
    
    def _scale_edges(self, edges: List[Tuple[Tuple[float, float], Tuple[float, float]]], 
                    scale_factor: float, bounds: ViewBounds) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Scale and center edges for placement on sheet."""
        if not edges:
            return []
        
        # Center point of original bounds
        center_x = (bounds.x_min + bounds.x_max) / 2
        center_y = (bounds.y_min + bounds.y_max) / 2
        
        scaled_edges = []
        for edge in edges:
            start, end = edge
            
            # Translate to origin, scale, then position will be handled during DXF generation
            new_start = (
                (start[0] - center_x) * scale_factor,
                (start[1] - center_y) * scale_factor
            )
            new_end = (
                (end[0] - center_x) * scale_factor,
                (end[1] - center_y) * scale_factor
            )
            
            scaled_edges.append((new_start, new_end))
        
        return scaled_edges
    
    def generate_border_and_title_block(self) -> Dict[str, Any]:
        """Generate border and title block geometry for the sheet."""
        border_geom = []
        title_block_geom = []
        
        # Main border
        border_margin = self.border_offset
        border_geom.append({
            'type': 'rectangle',
            'x': border_margin,
            'y': border_margin,
            'width': self.paper_specs.width - 2 * border_margin,
            'height': self.paper_specs.height - 2 * border_margin,
            'layer': 'BORDER'
        })
        
        # Inner margin
        inner_margin = self.paper_specs.margin
        border_geom.append({
            'type': 'rectangle',
            'x': inner_margin,
            'y': inner_margin,
            'width': self.paper_specs.width - 2 * inner_margin,
            'height': self.paper_specs.height - 2 * inner_margin,
            'layer': 'BORDER'
        })
        
        # Title block area
        tb_x = self.paper_specs.width - inner_margin - self.paper_specs.title_block_width
        tb_y = inner_margin
        
        title_block_geom.append({
            'type': 'rectangle',
            'x': tb_x,
            'y': tb_y,
            'width': self.paper_specs.title_block_width,
            'height': self.paper_specs.title_block_height,
            'layer': 'TITLE_BLOCK'
        })
        
        # Title block subdivisions
        # Horizontal lines
        for i in range(1, 4):
            y_pos = tb_y + i * (self.paper_specs.title_block_height / 4)
            title_block_geom.append({
                'type': 'line',
                'start': (tb_x, y_pos),
                'end': (tb_x + self.paper_specs.title_block_width, y_pos),
                'layer': 'TITLE_BLOCK'
            })
        
        # Vertical line
        x_pos = tb_x + self.paper_specs.title_block_width * 0.6
        title_block_geom.append({
            'type': 'line',
            'start': (x_pos, tb_y),
            'end': (x_pos, tb_y + self.paper_specs.title_block_height),
            'layer': 'TITLE_BLOCK'
        })
        
        return {
            'border': border_geom,
            'title_block': title_block_geom,
            'title_block_position': (tb_x, tb_y),
            'title_block_size': (self.paper_specs.title_block_width, self.paper_specs.title_block_height)
        }
    
    def add_view_labels(self) -> List[Dict[str, Any]]:
        """Generate view labels for each placed view."""
        labels = []
        
        for placement in self.view_placements:
            # Position label below the view
            label_x = placement.x
            label_y = placement.y - 30  # 30mm below view center
            
            labels.append({
                'text': placement.label,
                'x': label_x,
                'y': label_y,
                'height': 3.5,
                'layer': 'TEXT',
                'alignment': 'center'
            })
        
        return labels
    
    def get_layout_summary(self) -> Dict[str, Any]:
        """Get summary information about the current layout."""
        return {
            'paper_size': self.paper_size.value,
            'paper_dimensions': f"{self.paper_specs.width}x{self.paper_specs.height}mm",
            'view_count': len(self.view_placements),
            'views': [
                {
                    'label': vp.label,
                    'position': f"({vp.x:.1f}, {vp.y:.1f})",
                    'scale': f"{vp.scale_factor:.2f}",
                    'edge_count': len(vp.edges)
                }
                for vp in self.view_placements
            ]
        }
    
    def _generate_section_views(self, solid_builder: SolidBuilder) -> List[Dict[str, Any]]:
        """Generate section view data for all cutting planes."""
        section_views = []
        
        if not self.section_engine:
            return section_views
        
        for cutting_plane in self.section_engine.cutting_planes:
            try:
                # Generate section geometry
                section_geometry = self.section_engine.generate_section(solid_builder, cutting_plane)
                
                if not section_geometry:
                    print(f"⚠️ No section geometry generated for {cutting_plane.name}")
                    continue
                
                # Generate hatching based on material
                material = self._get_material_from_plan()  # Get from plan or default
                hatch_pattern = self._material_to_hatch_pattern(material)
                hatch_lines = self.section_engine.generate_hatching(section_geometry, hatch_pattern)
                
                # Combine section outline and internal edges
                all_edges = section_geometry.outline_edges + section_geometry.internal_edges
                
                section_view = {
                    'projection_type': f"SECTION_{cutting_plane.name}",
                    'label': f"SECTION {cutting_plane.name}-{cutting_plane.name}",
                    'edges': all_edges,
                    'bounds': section_geometry.bounds,
                    'is_section': True,
                    'section_geometry': section_geometry,
                    'hatch_lines': hatch_lines,
                    'cutting_plane': cutting_plane
                }
                
                section_views.append(section_view)
                print(f"  ✅ Generated {section_view['label']}: {len(all_edges)} edges, {len(hatch_lines)} hatch lines")
                
            except Exception as e:
                print(f"❌ Failed to generate section {cutting_plane.name}: {e}")
                continue
        
        return section_views
    
    def _calculate_sectioned_layout(self, view_data: List[Dict]) -> List[ViewPlacement]:
        """
        Calculate layout for views including sections.
        Uses adaptive grid layout to accommodate variable number of views.
        """
        total_views = len(view_data)
        if total_views == 0:
            return []
        
        # Available drawing area
        available_width = self.paper_specs.width - 2 * self.paper_specs.margin
        available_height = (self.paper_specs.height - 2 * self.paper_specs.margin - 
                          self.paper_specs.title_block_height)
        
        # Calculate grid layout
        if total_views <= 4:
            # 2x2 grid for 4 or fewer views
            cols, rows = 2, 2
        elif total_views <= 6:
            # 3x2 grid for 5-6 views
            cols, rows = 3, 2
        elif total_views <= 8:
            # 4x2 grid for 7-8 views
            cols, rows = 4, 2
        else:
            # 3x3 grid for more views
            cols, rows = 3, 3
        
        # Calculate cell dimensions
        spacing = 10  # mm between views
        cell_width = (available_width - (cols - 1) * spacing) / cols
        cell_height = (available_height - (rows - 1) * spacing) / rows
        
        view_placements = []
        
        # Organize views: sections go in the bottom row
        standard_views = [v for v in view_data if not v.get('is_section', False)]
        section_views = [v for v in view_data if v.get('is_section', False)]
        
        # Place standard views first
        for i, view in enumerate(standard_views):
            if i >= cols * (rows - 1):  # Reserve bottom row for sections
                break
                
            row = i // cols
            col = i % cols
            
            bounds = view['bounds']
            scale_x = cell_width / bounds.width if bounds.width > 0 else 1.0
            scale_y = cell_height / bounds.height if bounds.height > 0 else 1.0
            scale_factor = min(scale_x, scale_y, 2.0) * 0.8
            
            view_x = self.paper_specs.margin + col * (cell_width + spacing) + cell_width / 2
            view_y = self.paper_specs.margin + row * (cell_height + spacing) + cell_height / 2
            
            scaled_edges = self._scale_edges(view['edges'], scale_factor, bounds)
            
            view_placements.append(ViewPlacement(
                projection_type=view['projection_type'],
                x=view_x,
                y=view_y,
                scale_factor=scale_factor,
                label=view['label'],
                edges=scaled_edges,
                is_section=False
            ))
        
        # Place section views in bottom row
        for i, view in enumerate(section_views):
            if i >= cols:  # Only one row for sections
                break
                
            row = rows - 1  # Bottom row
            col = i % cols
            
            bounds = view['bounds']
            scale_x = cell_width / bounds.width if bounds.width > 0 else 1.0
            scale_y = cell_height / bounds.height if bounds.height > 0 else 1.0
            scale_factor = min(scale_x, scale_y, 2.0) * 0.8
            
            view_x = self.paper_specs.margin + col * (cell_width + spacing) + cell_width / 2
            view_y = self.paper_specs.margin + row * (cell_height + spacing) + cell_height / 2
            
            scaled_edges = self._scale_edges(view['edges'], scale_factor, bounds)
            
            # Scale hatch lines if present
            scaled_hatch_lines = []
            if view.get('hatch_lines'):
                for hatch_line in view['hatch_lines']:
                    start, end = hatch_line
                    scaled_start = (
                        (start[0] - bounds.x_min - bounds.width/2) * scale_factor,
                        (start[1] - bounds.y_min - bounds.height/2) * scale_factor
                    )
                    scaled_end = (
                        (end[0] - bounds.x_min - bounds.width/2) * scale_factor,
                        (end[1] - bounds.y_min - bounds.height/2) * scale_factor
                    )
                    scaled_hatch_lines.append((scaled_start, scaled_end))
            
            view_placements.append(ViewPlacement(
                projection_type=view['projection_type'],
                x=view_x,
                y=view_y,
                scale_factor=scale_factor,
                label=view['label'],
                edges=scaled_edges,
                is_section=True,
                section_geometry=view.get('section_geometry'),
                hatch_lines=scaled_hatch_lines
            ))
            
            print(f"  📐 {view['label']}: position=({view_x:.1f}, {view_y:.1f}), scale={scale_factor:.2f}")
        
        return view_placements
    
    def _add_cutting_plane_indicators(self):
        """Add cutting plane indicators to parent views."""
        if not self.section_engine:
            return
        
        for view_placement in self.view_placements:
            if view_placement.is_section:
                continue  # Skip section views themselves
            
            # Find relevant cutting planes for this view
            for cutting_plane in self.section_engine.cutting_planes:
                # Generate indicators based on cutting plane direction and view type
                if self._should_show_cutting_plane(view_placement, cutting_plane):
                    # Calculate view bounds for indicator placement
                    view_bounds = self._get_view_bounds_from_edges(view_placement.edges, view_placement.scale_factor)
                    
                    # Generate cutting plane indicators
                    indicators = self.section_engine.generate_cutting_plane_indicators(cutting_plane, view_bounds)
                    
                    # Store indicators in view placement
                    if view_placement.cutting_plane_indicators is None:
                        view_placement.cutting_plane_indicators = {}
                    view_placement.cutting_plane_indicators[cutting_plane.name] = indicators
    
    def _should_show_cutting_plane(self, view_placement: ViewPlacement, cutting_plane: CuttingPlane) -> bool:
        """Determine if a cutting plane should be shown in a given view."""
        view_type = str(view_placement.projection_type).upper()
        
        if cutting_plane.direction == SectionDirection.VERTICAL_FRONT:
            # Show in TOP and ISOMETRIC views
            return 'TOP' in view_type or 'ISOMETRIC' in view_type
        elif cutting_plane.direction == SectionDirection.HORIZONTAL:
            # Show in FRONT and RIGHT views
            return 'FRONT' in view_type or 'RIGHT' in view_type
        elif cutting_plane.direction == SectionDirection.VERTICAL_SIDE:
            # Show in TOP and FRONT views
            return 'TOP' in view_type or 'FRONT' in view_type
        
        return False
    
    def _get_view_bounds_from_edges(self, edges: List[Tuple[Tuple[float, float], Tuple[float, float]]], 
                                   scale_factor: float) -> 'ViewBounds':
        """Calculate view bounds from scaled edges."""
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
    
    def _get_material_from_plan(self) -> str:
        """Extract material specification from drawing plan."""
        # This would read from the plan's title block or material specification
        # For now, return a default
        return "steel"
    
    def _material_to_hatch_pattern(self, material: str) -> 'HatchPattern':
        """Convert material string to hatch pattern enum."""
        material_lower = material.lower()
        
        if 'steel' in material_lower or 'iron' in material_lower:
            return HatchPattern.STEEL
        elif 'aluminum' in material_lower or 'aluminium' in material_lower:
            return HatchPattern.ALUMINUM
        elif 'plastic' in material_lower or 'polymer' in material_lower:
            return HatchPattern.PLASTIC
        elif 'wood' in material_lower:
            return HatchPattern.WOOD
        elif 'concrete' in material_lower or 'masonry' in material_lower:
            return HatchPattern.CONCRETE
        elif 'rubber' in material_lower or 'elastomer' in material_lower:
            return HatchPattern.RUBBER
        elif 'glass' in material_lower:
            return HatchPattern.GLASS
        else:
            return HatchPattern.GENERAL

    def generate_four_view_sheet(self, plan: Dict[str, Any]) -> Tuple[List[ViewPlacement], Dict[str, Any]]:
        """
        Generate a complete four-view engineering drawing sheet.
        Backward compatibility wrapper for the original functionality.
        
        Args:
            plan: Feature-based drawing plan
            
        Returns:
            Tuple of (view_placements, sheet_metadata)
        """
        # Use the new sectioned method without sections for backward compatibility
        return self.generate_sectioned_multiview_sheet(plan, sections=None)