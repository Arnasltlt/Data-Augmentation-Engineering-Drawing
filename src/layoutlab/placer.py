"""
LayoutLab Placement Engine
Collision-aware symbol placement for engineering drawings
"""

import random
import math
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from io import BytesIO
import yaml
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, letter
from reportlab.lib.units import mm


@dataclass
class Symbol:
    """Represents a symbol with its properties"""
    name: str
    filename: str
    width_mm: float
    height_mm: float
    params: Dict[str, Any]


@dataclass
class PlacedSymbol:
    """Represents a placed symbol on the drawing"""
    symbol: Symbol
    x: float  # mm from lower-left
    y: float  # mm from lower-left
    rotation: float  # degrees
    instance_params: Dict[str, Any]


class SheetDimensions:
    """Sheet size definitions in mm"""
    SIZES = {
        "A4": (210, 297),
        "A3": (297, 420), 
        "US-Letter": (215.9, 279.4)
    }
    
    @classmethod
    def get_size(cls, sheet_size: str) -> Tuple[float, float]:
        """Get sheet dimensions in mm"""
        if sheet_size not in cls.SIZES:
            raise ValueError(f"Unsupported sheet size: {sheet_size}")
        return cls.SIZES[sheet_size]


class CollisionDetector:
    """Handles collision detection between placed symbols"""
    
    @staticmethod
    def get_bounding_box(placed_symbol: PlacedSymbol) -> Tuple[float, float, float, float]:
        """Get bounding box (x_min, y_min, x_max, y_max) for a placed symbol"""
        # For simplicity, assume no rotation affects bounding box significantly
        # In production, would need proper rotated rectangle calculations
        half_width = placed_symbol.symbol.width_mm / 2
        half_height = placed_symbol.symbol.height_mm / 2
        
        x_min = placed_symbol.x - half_width
        y_min = placed_symbol.y - half_height
        x_max = placed_symbol.x + half_width
        y_max = placed_symbol.y + half_height
        
        return x_min, y_min, x_max, y_max
    
    @staticmethod
    def check_collision(symbol1: PlacedSymbol, symbol2: PlacedSymbol, 
                       min_spacing: float = 2.0) -> bool:
        """Check if two symbols collide with minimum spacing"""
        bbox1 = CollisionDetector.get_bounding_box(symbol1)
        bbox2 = CollisionDetector.get_bounding_box(symbol2)
        
        # Add minimum spacing buffer to first symbol only
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # Expand first bounding box by full spacing
        x1_min -= min_spacing
        y1_min -= min_spacing
        x1_max += min_spacing
        y1_max += min_spacing
        
        # Check for overlap
        return not (x1_max < x2_min or x2_max < x1_min or 
                   y1_max < y2_min or y2_max < y1_min)


class SymbolParameterGenerator:
    """Generates randomized parameters for symbols"""
    
    PARAMETER_TEMPLATES = {
        "gdt_flatness": {
            "tolerance": lambda: round(random.uniform(0.01, 0.5), 3),
            "datum": lambda: random.choice(["A", "B", "C", "-"])
        },
        "surface_finish": {
            "roughness": lambda: random.choice([0.8, 1.6, 3.2, 6.3, 12.5]),
            "process": lambda: random.choice(["machined", "cast", "forged"])
        },
        "thread_callout": {
            "size": lambda: random.choice(["M6", "M8", "M10", "M12", "1/4-20", "3/8-16"]),
            "pitch": lambda: random.choice([1.0, 1.25, 1.5, 2.0]),
            "class": lambda: random.choice(["6H", "6g", "4H6H"])
        },
        "diameter": {
            "value": lambda: round(random.uniform(5.0, 50.0), 1),
            "tolerance": lambda: f"+{random.uniform(0.01, 0.1):.3f}/-{random.uniform(0.01, 0.1):.3f}"
        }
    }
    
    @classmethod
    def generate_params(cls, symbol_name: str) -> Dict[str, Any]:
        """Generate random parameters for a symbol"""
        # Match symbol name to parameter template
        for template_key, template in cls.PARAMETER_TEMPLATES.items():
            if template_key in symbol_name.lower():
                return {key: generator() for key, generator in template.items()}
        
        # Default empty parameters
        return {}


class SymbolPlacer:
    """Main placement engine"""
    
    def __init__(self, symbols_manifest_path: Optional[str] = None):
        self.symbols: Dict[str, Symbol] = {}
        self.load_symbols_manifest(symbols_manifest_path)
    
    def load_symbols_manifest(self, manifest_path: Optional[str]):
        """Load symbols from manifest file"""
        if manifest_path and os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
                for symbol_data in manifest.get('symbols', []):
                    symbol = Symbol(
                        name=symbol_data['name'],
                        filename=symbol_data['filename'],
                        width_mm=symbol_data['w_mm'],
                        height_mm=symbol_data['h_mm'],
                        params=symbol_data.get('params', {})
                    )
                    self.symbols[symbol.name] = symbol
        else:
            # Create mock symbols for testing
            self._create_mock_symbols()
    
    def _create_mock_symbols(self):
        """Create mock symbols for testing when manifest is not available"""
        mock_symbols = [
            {"name": "gdt_flatness", "width": 8.0, "height": 4.0},
            {"name": "gdt_parallelism", "width": 8.0, "height": 4.0},
            {"name": "surface_finish_triangle", "width": 3.0, "height": 3.0},
            {"name": "thread_callout_m6", "width": 12.0, "height": 3.0},
            {"name": "diameter_symbol", "width": 4.0, "height": 4.0},
            {"name": "radius_symbol", "width": 4.0, "height": 4.0},
            {"name": "weld_symbol", "width": 6.0, "height": 6.0},
        ]
        
        for mock in mock_symbols:
            symbol = Symbol(
                name=mock["name"],
                filename=f"{mock['name']}.svg",
                width_mm=mock["width"],
                height_mm=mock["height"],
                params={}
            )
            self.symbols[symbol.name] = symbol
    
    def place_symbols_randomly(self, sheet_size: str, symbol_count: int, 
                              seed: int) -> List[PlacedSymbol]:
        """Place symbols randomly on sheet with collision avoidance"""
        random.seed(seed)
        
        sheet_width, sheet_height = SheetDimensions.get_size(sheet_size)
        margin = 10.0  # mm margin from edges
        
        placed_symbols = []
        symbol_names = list(self.symbols.keys())
        
        # Define safe placement area
        safe_x_min = margin
        safe_x_max = sheet_width - margin
        safe_y_min = margin
        safe_y_max = sheet_height - margin
        
        max_attempts = symbol_count * 10  # Prevent infinite loops
        attempts = 0
        
        while len(placed_symbols) < symbol_count and attempts < max_attempts:
            attempts += 1
            
            # Select random symbol
            symbol_name = random.choice(symbol_names)
            symbol = self.symbols[symbol_name]
            
            # Generate random position within safe area
            x = random.uniform(safe_x_min + symbol.width_mm/2, 
                              safe_x_max - symbol.width_mm/2)
            y = random.uniform(safe_y_min + symbol.height_mm/2, 
                              safe_y_max - symbol.height_mm/2)
            
            # Random rotation (multiples of 90 degrees for simplicity)
            rotation = random.choice([0, 90, 180, 270])
            
            # Generate instance parameters
            instance_params = SymbolParameterGenerator.generate_params(symbol_name)
            
            # Create placed symbol
            placed_symbol = PlacedSymbol(
                symbol=symbol,
                x=x,
                y=y,
                rotation=rotation,
                instance_params=instance_params
            )
            
            # Check for collisions with existing symbols
            collision_found = False
            for existing_symbol in placed_symbols:
                if CollisionDetector.check_collision(placed_symbol, existing_symbol):
                    collision_found = True
                    break
            
            # If no collision, add to placed symbols
            if not collision_found:
                placed_symbols.append(placed_symbol)
        
        if len(placed_symbols) < symbol_count:
            print(f"Warning: Only placed {len(placed_symbols)} of {symbol_count} symbols due to space constraints")
        
        return placed_symbols
    
    def generate_pdf(self, placed_symbols: List[PlacedSymbol], 
                    sheet_size: str) -> bytes:
        """Generate PDF with placed symbols"""
        buffer = BytesIO()
        
        # Get ReportLab page size
        if sheet_size == "A4":
            page_size = A4
        elif sheet_size == "A3":
            page_size = A3
        elif sheet_size == "US-Letter":
            page_size = letter
        else:
            page_size = A4
        
        c = canvas.Canvas(buffer, pagesize=page_size)
        
        # Draw symbols (simplified representation)
        for placed_symbol in placed_symbols:
            # Convert mm to points (ReportLab uses points)
            x_points = placed_symbol.x * mm
            y_points = placed_symbol.y * mm
            width_points = placed_symbol.symbol.width_mm * mm
            height_points = placed_symbol.symbol.height_mm * mm
            
            # Draw rectangle to represent symbol
            c.rect(x_points - width_points/2, y_points - height_points/2,
                   width_points, height_points)
            
            # Add symbol name as text
            c.drawString(x_points - width_points/2, y_points,
                        placed_symbol.symbol.name[:8])  # Truncate for space
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_annotations_json(self, placed_symbols: List[PlacedSymbol]) -> List[Dict]:
        """Generate JSON annotations for placed symbols"""
        annotations = []
        
        for i, placed_symbol in enumerate(placed_symbols):
            bbox = CollisionDetector.get_bounding_box(placed_symbol)
            
            annotation = {
                "id": i,
                "symbol_name": placed_symbol.symbol.name,
                "position": {
                    "x": placed_symbol.x,
                    "y": placed_symbol.y
                },
                "rotation": placed_symbol.rotation,
                "bounding_box": {
                    "x_min": bbox[0],
                    "y_min": bbox[1],
                    "x_max": bbox[2],
                    "y_max": bbox[3]
                },
                "parameters": placed_symbol.instance_params
            }
            annotations.append(annotation)
        
        return annotations


def generate_page(sheet_size: str = "A3", symbol_count: int = 40, seed: int = 42) -> Dict[str, Any]:
    """
    Main API function to generate a page with symbols
    
    Args:
        sheet_size: "A4", "A3", or "US-Letter"
        symbol_count: Number of symbols to place (will try up to this many)
        seed: Random seed for reproducible results
    
    Returns:
        Dictionary with "pdf_bytes" and "annotations" keys
    """
    placer = SymbolPlacer()
    
    # Place symbols
    placed_symbols = placer.place_symbols_randomly(sheet_size, symbol_count, seed)
    
    # Generate PDF
    pdf_bytes = placer.generate_pdf(placed_symbols, sheet_size)
    
    # Generate annotations
    annotations = placer.generate_annotations_json(placed_symbols)
    
    return {
        "pdf_bytes": pdf_bytes,
        "annotations": annotations
    }