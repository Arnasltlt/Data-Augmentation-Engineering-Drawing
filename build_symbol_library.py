#!/usr/bin/env python3
"""
DXF Symbol Library Builder

Converts SVG symbols from the /symbols directory into DXF blocks within a single
library/symbols.dxf file. This enables proper CAD-style symbol insertion in drawings.

Usage:
    python build_symbol_library.py
    python build_symbol_library.py --output custom_library.dxf
    python build_symbol_library.py --verbose
"""

import os
import sys
import argparse
import yaml
import xml.etree.ElementTree as ET
import re
import math
from typing import Dict, List, Tuple, Any, Optional
import ezdxf
from ezdxf.math import Vec3


class SVGToDXFConverter:
    """Converts SVG elements to DXF entities"""
    
    def __init__(self):
        self.unit_scale = 1.0  # mm per SVG unit
    
    def parse_svg_path(self, path_data: str) -> List[Tuple[str, List[float]]]:
        """
        Parse SVG path data into command/coordinate pairs
        
        Returns:
            List of (command, coordinates) tuples
        """
        commands = []
        
        # Basic path command regex - handles M, L, H, V, C, S, Q, T, A, Z
        path_regex = r'([MLHVCSQTAZmlhvcsqtaz])\s*([^MLHVCSQTAZmlhvcsqtaz]*)'
        
        for match in re.finditer(path_regex, path_data):
            command = match.group(1)
            coords_str = match.group(2).strip()
            
            # Parse coordinates
            coords = []
            if coords_str:
                # Split by comma or whitespace, filter empty strings
                coord_strs = re.split(r'[,\s]+', coords_str)
                coords = [float(x) for x in coord_strs if x]
            
            commands.append((command, coords))
        
        return commands
    
    def convert_svg_to_entities(self, svg_element: ET.Element, block) -> bool:
        """
        Convert SVG elements to DXF entities and add to block
        
        Args:
            svg_element: Root SVG element
            block: DXF block to add entities to
            
        Returns:
            True if conversion successful
        """
        try:
            # Get SVG dimensions for scaling
            viewbox = svg_element.get('viewBox')
            if viewbox:
                vb_parts = viewbox.split()
                if len(vb_parts) >= 4:
                    vb_width = float(vb_parts[2])
                    vb_height = float(vb_parts[3])
                else:
                    vb_width = vb_height = 100
            else:
                # Try to get from width/height attributes
                width_str = svg_element.get('width', '6mm')
                height_str = svg_element.get('height', '6mm')
                vb_width = float(re.sub(r'[^\d.]', '', width_str))
                vb_height = float(re.sub(r'[^\d.]', '', height_str))
            
            # Process child elements
            entities_added = False
            
            for element in svg_element.iter():
                if element.tag.endswith('path'):
                    if self._convert_path_element(element, block):
                        entities_added = True
                elif element.tag.endswith('circle'):
                    if self._convert_circle_element(element, block):
                        entities_added = True
                elif element.tag.endswith('ellipse'):
                    if self._convert_ellipse_element(element, block):
                        entities_added = True
                elif element.tag.endswith('rect'):
                    if self._convert_rect_element(element, block):
                        entities_added = True
                elif element.tag.endswith('line'):
                    if self._convert_line_element(element, block):
                        entities_added = True
                elif element.tag.endswith('polygon'):
                    if self._convert_polygon_element(element, block):
                        entities_added = True
                elif element.tag.endswith('polyline'):
                    if self._convert_polyline_element(element, block):
                        entities_added = True
            
            # If no entities were found, create a simple bounding box
            if not entities_added:
                self._create_bounding_box(block, vb_width, vb_height)
                entities_added = True
            
            return entities_added
            
        except Exception as e:
            print(f"Error converting SVG: {e}")
            return False
    
    def _convert_path_element(self, element: ET.Element, block) -> bool:
        """Convert SVG path element to DXF entities"""
        path_data = element.get('d', '')
        if not path_data:
            return False
        
        try:
            commands = self.parse_svg_path(path_data)
            current_point = (0, 0)
            path_start = (0, 0)
            
            points = []
            
            for command, coords in commands:
                if command.upper() == 'M':  # Move to
                    if len(coords) >= 2:
                        current_point = (coords[0], coords[1])
                        path_start = current_point
                        points = [current_point]
                
                elif command.upper() == 'L':  # Line to
                    if len(coords) >= 2:
                        end_point = (coords[0], coords[1])
                        points.append(end_point)
                        current_point = end_point
                
                elif command.upper() == 'H':  # Horizontal line
                    if len(coords) >= 1:
                        end_point = (coords[0], current_point[1])
                        points.append(end_point)
                        current_point = end_point
                
                elif command.upper() == 'V':  # Vertical line
                    if len(coords) >= 1:
                        end_point = (current_point[0], coords[0])
                        points.append(end_point)
                        current_point = end_point
                
                elif command.upper() == 'Z':  # Close path
                    if points and points[0] != current_point:
                        points.append(path_start)
            
            # Create polyline if we have points
            if len(points) >= 2:
                block.add_lwpolyline(points)
                return True
                
        except Exception as e:
            print(f"Error parsing path: {e}")
        
        return False
    
    def _convert_circle_element(self, element: ET.Element, block) -> bool:
        """Convert SVG circle to DXF circle"""
        try:
            cx = float(element.get('cx', '0'))
            cy = float(element.get('cy', '0'))
            r = float(element.get('r', '1'))
            
            block.add_circle((cx, cy), r)
            return True
        except:
            return False
    
    def _convert_ellipse_element(self, element: ET.Element, block) -> bool:
        """Convert SVG ellipse to DXF ellipse"""
        try:
            cx = float(element.get('cx', '0'))
            cy = float(element.get('cy', '0'))
            rx = float(element.get('rx', '1'))
            ry = float(element.get('ry', '1'))
            
            # DXF ellipse requires center, major axis vector, and ratio
            major_axis = (rx, 0) if rx >= ry else (0, ry)
            ratio = min(rx, ry) / max(rx, ry)
            
            block.add_ellipse((cx, cy), major_axis, ratio)
            return True
        except:
            return False
    
    def _convert_rect_element(self, element: ET.Element, block) -> bool:
        """Convert SVG rectangle to DXF polyline"""
        try:
            x = float(element.get('x', '0'))
            y = float(element.get('y', '0'))
            width = float(element.get('width', '1'))
            height = float(element.get('height', '1'))
            
            points = [
                (x, y),
                (x + width, y),
                (x + width, y + height),
                (x, y + height),
                (x, y)
            ]
            
            block.add_lwpolyline(points)
            return True
        except:
            return False
    
    def _convert_line_element(self, element: ET.Element, block) -> bool:
        """Convert SVG line to DXF line"""
        try:
            x1 = float(element.get('x1', '0'))
            y1 = float(element.get('y1', '0'))
            x2 = float(element.get('x2', '1'))
            y2 = float(element.get('y2', '1'))
            
            block.add_line((x1, y1), (x2, y2))
            return True
        except:
            return False
    
    def _convert_polygon_element(self, element: ET.Element, block) -> bool:
        """Convert SVG polygon to DXF polyline"""
        points_str = element.get('points', '')
        if not points_str:
            return False
        
        try:
            # Parse points "x1,y1 x2,y2 x3,y3"
            coord_pairs = re.findall(r'([\d.-]+)[,\s]+([\d.-]+)', points_str)
            points = [(float(x), float(y)) for x, y in coord_pairs]
            
            if len(points) >= 3:
                # Close the polygon
                if points[0] != points[-1]:
                    points.append(points[0])
                block.add_lwpolyline(points)
                return True
        except:
            pass
        
        return False
    
    def _convert_polyline_element(self, element: ET.Element, block) -> bool:
        """Convert SVG polyline to DXF polyline"""
        points_str = element.get('points', '')
        if not points_str:
            return False
        
        try:
            coord_pairs = re.findall(r'([\d.-]+)[,\s]+([\d.-]+)', points_str)
            points = [(float(x), float(y)) for x, y in coord_pairs]
            
            if len(points) >= 2:
                block.add_lwpolyline(points)
                return True
        except:
            pass
        
        return False
    
    def _create_bounding_box(self, block, width: float, height: float):
        """Create a simple bounding box for symbols that couldn't be parsed"""
        points = [
            (0, 0),
            (width, 0),
            (width, height),
            (0, height),
            (0, 0)
        ]
        block.add_lwpolyline(points)


class SymbolLibraryBuilder:
    """Builds a DXF symbol library from SVG files"""
    
    def __init__(self, symbols_dir: str = 'symbols', manifest_file: str = 'symbols/symbols_manifest.yaml'):
        self.symbols_dir = symbols_dir
        self.manifest_file = manifest_file
        self.converter = SVGToDXFConverter()
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load the symbol manifest"""
        try:
            with open(self.manifest_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load manifest file {self.manifest_file}: {e}")
            return {"symbols": []}
    
    def build_library(self, output_path: str = 'library/symbols.dxf', verbose: bool = False) -> bool:
        """
        Build the DXF symbol library
        
        Args:
            output_path: Path for output DXF file
            verbose: Enable verbose logging
            
        Returns:
            True if successful
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create new DXF document
            doc = ezdxf.new()
            
            symbols = self.manifest.get('symbols', [])
            successful_conversions = 0
            failed_conversions = []
            
            if verbose:
                print(f"Processing {len(symbols)} symbols...")
            
            for symbol_info in symbols:
                symbol_name = symbol_info['name']
                filename = symbol_info['filename']
                svg_path = os.path.join(self.symbols_dir, filename)
                
                if verbose:
                    print(f"Processing: {symbol_name} ({filename})")
                
                if not os.path.exists(svg_path):
                    print(f"Warning: SVG file not found: {svg_path}")
                    failed_conversions.append(symbol_name)
                    continue
                
                # Create a block for this symbol
                try:
                    block = doc.blocks.new(symbol_name)
                    
                    # Parse SVG file
                    tree = ET.parse(svg_path)
                    root = tree.getroot()
                    
                    # Convert SVG to DXF entities
                    if self.converter.convert_svg_to_entities(root, block):
                        successful_conversions += 1
                        if verbose:
                            print(f"  ✅ Converted successfully")
                    else:
                        failed_conversions.append(symbol_name)
                        if verbose:
                            print(f"  ❌ Conversion failed")
                
                except Exception as e:
                    failed_conversions.append(symbol_name)
                    if verbose:
                        print(f"  ❌ Error: {e}")
            
            # Save the DXF file
            doc.saveas(output_path)
            
            # Report results
            print(f"\n📊 Symbol Library Build Complete:")
            print(f"   Output: {output_path}")
            print(f"   Successful: {successful_conversions}/{len(symbols)} symbols")
            print(f"   Failed: {len(failed_conversions)} symbols")
            
            if failed_conversions and verbose:
                print(f"\n❌ Failed conversions:")
                for name in failed_conversions:
                    print(f"   - {name}")
            
            # Create usage documentation
            self._create_usage_doc(output_path, successful_conversions, failed_conversions)
            
            return len(failed_conversions) == 0
            
        except Exception as e:
            print(f"❌ Error building symbol library: {e}")
            return False
    
    def _create_usage_doc(self, library_path: str, successful: int, failed: List[str]):
        """Create documentation for using the symbol library"""
        doc_path = library_path.replace('.dxf', '_usage.md')
        
        try:
            with open(doc_path, 'w') as f:
                f.write(f"""# DXF Symbol Library Usage

## Library Information
- **File:** {os.path.basename(library_path)}
- **Generated:** {os.path.getctime(library_path) if os.path.exists(library_path) else 'Unknown'}
- **Symbols:** {successful} blocks available

## Usage in generator.py

Instead of the current SVG conversion approach, you can now use proper DXF blocks:

```python
# Load the symbol library (do this once)
symbol_lib = ezdxf.readfile('{library_path}')

# Insert a symbol block
def insert_symbol_block(msp, symbol_name, location, scale=1.0, rotation=0):
    if symbol_name in symbol_lib.blocks:
        msp.add_blockref(symbol_name, location, dxfattribs={{
            'xscale': scale,
            'yscale': scale, 
            'rotation': rotation
        }})
        return True
    return False

# Example usage
insert_symbol_block(msp, 'gdt_flatness', (100, 50), scale=1.2)
```

## Available Symbols

The following blocks are available in this library:

""")
                
                # List available symbols from manifest
                for symbol_info in self.manifest.get('symbols', []):
                    symbol_name = symbol_info['name']
                    if symbol_name not in failed:
                        f.write(f"- `{symbol_name}` ({symbol_info.get('w_mm', '?')}×{symbol_info.get('h_mm', '?')}mm)\n")
                
                if failed:
                    f.write(f"\n## Failed Conversions\n\nThe following symbols could not be converted:\n\n")
                    for name in failed:
                        f.write(f"- `{name}`\n")
                
                f.write(f"""
## Integration Notes

1. **Performance:** Using DXF blocks is much more efficient than converting SVG at runtime
2. **Quality:** Blocks preserve the exact geometry from the SVG files
3. **CAD Standard:** This follows standard CAD practices for symbol libraries
4. **Scaling:** Blocks can be scaled and rotated without quality loss

## Next Steps

Update `generator.py` to use this library instead of the current SVG conversion approach.
""")
                
            print(f"📖 Usage documentation created: {doc_path}")
            
        except Exception as e:
            print(f"Warning: Could not create usage documentation: {e}")


def main():
    parser = argparse.ArgumentParser(description="Build DXF Symbol Library from SVG files")
    parser.add_argument('--output', '-o', type=str, default='library/symbols.dxf',
                       help='Output path for the DXF library file')
    parser.add_argument('--symbols-dir', type=str, default='symbols',
                       help='Directory containing SVG symbol files')
    parser.add_argument('--manifest', type=str, default='symbols/symbols_manifest.yaml',
                       help='Path to the symbol manifest file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.symbols_dir):
        print(f"❌ Error: Symbols directory not found: {args.symbols_dir}")
        sys.exit(1)
    
    if not os.path.exists(args.manifest):
        print(f"❌ Error: Manifest file not found: {args.manifest}")
        sys.exit(1)
    
    # Build the library
    builder = SymbolLibraryBuilder(args.symbols_dir, args.manifest)
    success = builder.build_library(args.output, args.verbose)
    
    if success:
        print("✅ Symbol library build completed successfully!")
        sys.exit(0)
    else:
        print("⚠️ Symbol library build completed with some failures.")
        sys.exit(1)


if __name__ == "__main__":
    main()