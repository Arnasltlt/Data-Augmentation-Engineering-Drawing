"""
Test fixtures and mock data for comprehensive testing across all agents.
Provides consistent test data for VectorForge, LayoutLab, GrungeWorks, and integration tests.
"""

from pathlib import Path
from typing import Any, Dict, List
import tempfile
import json
import yaml
from dataclasses import dataclass
from PIL import Image, ImageDraw


@dataclass
class MockSymbol:
    """Mock symbol definition for testing"""
    name: str
    filename: str
    w_mm: float
    h_mm: float
    params: Dict[str, Any]
    svg_content: str = ""


class TestFixtures:
    """Centralized test fixtures for all agents"""
    
    @staticmethod
    def get_mock_symbols_manifest() -> Dict[str, Any]:
        """Get mock symbols manifest YAML data"""
        return {
            "schema_version": "1.0",
            "symbols": [
                {
                    "name": "flatness",
                    "filename": "gdt_flatness.svg",
                    "w_mm": 8.0,
                    "h_mm": 8.0,
                    "params": {
                        "tolerance_value": {
                            "type": "float",
                            "min": 0.001,
                            "max": 1.0,
                            "default": 0.05
                        }
                    }
                },
                {
                    "name": "straightness",
                    "filename": "gdt_straightness.svg", 
                    "w_mm": 8.0,
                    "h_mm": 8.0,
                    "params": {
                        "tolerance_value": {
                            "type": "float",
                            "min": 0.001,
                            "max": 1.0,
                            "default": 0.02
                        }
                    }
                },
                {
                    "name": "circularity",
                    "filename": "gdt_circularity.svg",
                    "w_mm": 8.0,
                    "h_mm": 8.0,
                    "params": {
                        "tolerance_value": {
                            "type": "float",
                            "min": 0.001,
                            "max": 1.0,
                            "default": 0.03
                        }
                    }
                },
                {
                    "name": "surface_finish_triangle",
                    "filename": "surface_triangle.svg",
                    "w_mm": 6.0,
                    "h_mm": 6.0,
                    "params": {
                        "roughness_ra": {
                            "type": "float",
                            "min": 0.1,
                            "max": 50.0,
                            "default": 3.2
                        },
                        "machining_allowance": {
                            "type": "float", 
                            "min": 0.0,
                            "max": 10.0,
                            "default": 0.0
                        }
                    }
                },
                {
                    "name": "diameter",
                    "filename": "diameter_symbol.svg",
                    "w_mm": 6.0,
                    "h_mm": 6.0,
                    "params": {
                        "diameter_value": {
                            "type": "float",
                            "min": 0.1,
                            "max": 1000.0,
                            "default": 10.0
                        }
                    }
                },
                {
                    "name": "radius",
                    "filename": "radius_symbol.svg",
                    "w_mm": 6.0,
                    "h_mm": 6.0,
                    "params": {
                        "radius_value": {
                            "type": "float",
                            "min": 0.1,
                            "max": 500.0,
                            "default": 5.0
                        }
                    }
                },
                {
                    "name": "thread_metric",
                    "filename": "thread_m.svg",
                    "w_mm": 10.0,
                    "h_mm": 4.0,
                    "params": {
                        "thread_size": {
                            "type": "enum",
                            "values": ["M3", "M4", "M5", "M6", "M8", "M10", "M12"],
                            "default": "M6"
                        },
                        "thread_pitch": {
                            "type": "float",
                            "min": 0.2,
                            "max": 2.0,
                            "default": 1.0
                        }
                    }
                },
                {
                    "name": "weld_symbol",
                    "filename": "weld_fillet.svg",
                    "w_mm": 8.0,
                    "h_mm": 8.0,
                    "params": {
                        "weld_size": {
                            "type": "float",
                            "min": 1.0,
                            "max": 20.0,
                            "default": 6.0
                        },
                        "weld_length": {
                            "type": "float",
                            "min": 5.0,
                            "max": 200.0,
                            "default": 50.0
                        }
                    }
                }
            ]
        }
    
    @staticmethod
    def get_mock_svg_content(symbol_name: str) -> str:
        """Get mock SVG content for symbol"""
        svg_templates = {
            "flatness": '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="8mm" height="8mm" viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg">
    <rect x="1" y="1" width="6" height="6" stroke="black" stroke-width="0.2" fill="none"/>
    <line x1="3" y1="4" x2="5" y2="4" stroke="black" stroke-width="0.15"/>
</svg>''',
            "diameter": '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="6mm" height="6mm" viewBox="0 0 6 6" xmlns="http://www.w3.org/2000/svg">
    <circle cx="3" cy="3" r="2.5" stroke="black" stroke-width="0.2" fill="none"/>
    <line x1="1" y1="1" x2="5" y2="5" stroke="black" stroke-width="0.15"/>
</svg>''',
            "surface_finish_triangle": '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="6mm" height="6mm" viewBox="0 0 6 6" xmlns="http://www.w3.org/2000/svg">
    <polygon points="3,1 1,5 5,5" stroke="black" stroke-width="0.2" fill="none"/>
</svg>'''
        }
        return svg_templates.get(symbol_name, svg_templates["diameter"])
    
    @staticmethod
    def get_mock_page_data() -> Dict[str, Any]:
        """Get mock page data for LayoutLab JSON output"""
        return {
            "page_info": {
                "sheet_size": "A4",
                "width_mm": 210.0,
                "height_mm": 297.0,
                "commit_sha": "abcd1234",
                "creation_timestamp": "2024-01-15T10:30:00Z",
                "generator_version": "1.0.0"
            },
            "annotations": [
                {
                    "id": "symbol_001",
                    "symbol_name": "flatness",
                    "filename": "gdt_flatness.svg",
                    "position": {"x": 50.0, "y": 100.0},
                    "rotation": 0.0,
                    "bounding_box": {"x_min": 46.0, "y_min": 96.0, "x_max": 54.0, "y_max": 104.0},
                    "parameters": {"tolerance_value": 0.05}
                },
                {
                    "id": "symbol_002", 
                    "symbol_name": "surface_finish_triangle",
                    "filename": "surface_triangle.svg",
                    "position": {"x": 120.0, "y": 150.0},
                    "rotation": 45.0,
                    "bounding_box": {"x_min": 117.0, "y_min": 147.0, "x_max": 123.0, "y_max": 153.0},
                    "parameters": {"roughness_ra": 3.2, "machining_allowance": 0.0}
                },
                {
                    "id": "symbol_003",
                    "symbol_name": "diameter", 
                    "filename": "diameter_symbol.svg",
                    "position": {"x": 80.0, "y": 200.0},
                    "rotation": 0.0,
                    "bounding_box": {"x_min": 77.0, "y_min": 197.0, "x_max": 83.0, "y_max": 203.0},
                    "parameters": {"diameter_value": 25.0}
                }
            ]
        }
    
    @staticmethod
    def get_mock_license_data() -> List[Dict[str, str]]:
        """Get mock license data for VectorForge compliance"""
        return [
            {"filename": "gdt_flatness.svg", "licence": "CC0-1.0", "source-URL": ""},
            {"filename": "gdt_straightness.svg", "licence": "MIT", "source-URL": "https://github.com/freecad/symbols"},
            {"filename": "surface_triangle.svg", "licence": "CC0-1.0", "source-URL": ""},
            {"filename": "diameter_symbol.svg", "licence": "CC-BY-4.0", "source-URL": "https://openclipart.org/detail/12345"},
            {"filename": "radius_symbol.svg", "licence": "CC0-1.0", "source-URL": ""},
            {"filename": "thread_m.svg", "licence": "MIT", "source-URL": "https://github.com/iso-standards/symbols"},
            {"filename": "weld_fillet.svg", "licence": "CC0-1.0", "source-URL": ""}
        ]
    
    @staticmethod
    def create_mock_pdf_bytes() -> bytes:
        """Create mock PDF content for testing"""
        # Simple mock PDF header + minimal content
        mock_pdf = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj

xref
0 4
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
199
%%EOF"""
        return mock_pdf
    
    @staticmethod
    def create_mock_png_image(width: int = 400, height: int = 300) -> Image.Image:
        """Create mock PNG image for testing"""
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw some mock symbols
        draw.rectangle([50, 50, 150, 100], outline='black', width=2)
        draw.ellipse([200, 80, 280, 160], outline='black', width=2)
        draw.polygon([(100, 200), (150, 180), (200, 200), (175, 240)], outline='black', width=2)
        
        return img
    
    @staticmethod
    def create_temporary_files():
        """Create temporary files for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create mock symbols directory structure
        symbols_dir = temp_dir / "symbols"
        symbols_dir.mkdir()
        
        # Create mock manifest
        manifest_path = symbols_dir / "symbols_manifest.yaml"
        with open(manifest_path, 'w') as f:
            yaml.dump(TestFixtures.get_mock_symbols_manifest(), f)
        
        # Create mock SVG files
        manifest = TestFixtures.get_mock_symbols_manifest()
        for symbol in manifest["symbols"]:
            svg_path = symbols_dir / symbol["filename"]
            with open(svg_path, 'w') as f:
                f.write(TestFixtures.get_mock_svg_content(symbol["name"]))
        
        # Create mock license CSV
        license_path = symbols_dir / "symbol_licences.csv"
        with open(license_path, 'w') as f:
            f.write("filename,licence,source-URL\n")
            for license_data in TestFixtures.get_mock_license_data():
                f.write(f"{license_data['filename']},{license_data['licence']},{license_data['source-URL']}\n")
        
        # Create mock examples directory
        examples_dir = temp_dir / "examples"
        examples_dir.mkdir()
        
        # Create mock page JSON
        page_json_path = examples_dir / "page_abcd1234.json"
        with open(page_json_path, 'w') as f:
            json.dump(TestFixtures.get_mock_page_data(), f, indent=2)
        
        # Create mock PDF
        pdf_path = examples_dir / "page_abcd1234.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(TestFixtures.create_mock_pdf_bytes())
        
        # Create mock PNG
        png_path = examples_dir / "page_abcd1234.png"
        TestFixtures.create_mock_png_image().save(png_path)
        
        return temp_dir


class PerformanceFixtures:
    """Fixtures for performance and stress testing"""
    
    @staticmethod
    def get_large_symbol_set(count: int = 100) -> List[Dict[str, Any]]:
        """Generate large symbol set for stress testing"""
        base_symbols = TestFixtures.get_mock_symbols_manifest()["symbols"]
        large_set = []
        
        for i in range(count):
            # Cycle through base symbols and create variations
            base_symbol = base_symbols[i % len(base_symbols)]
            variant = base_symbol.copy()
            variant["name"] = f"{base_symbol['name']}_variant_{i}"
            variant["filename"] = f"{base_symbol['filename'].replace('.svg', f'_v{i}.svg')}"
            large_set.append(variant)
        
        return large_set
    
    @staticmethod
    def get_stress_test_pages(page_count: int = 100) -> List[Dict[str, Any]]:
        """Generate multiple pages for stress testing"""
        base_page = TestFixtures.get_mock_page_data()
        pages = []
        
        for i in range(page_count):
            page = base_page.copy()
            page["page_info"]["commit_sha"] = f"sha{i:04d}"
            # Vary number of symbols per page (10-60)
            symbol_count = 10 + (i % 51)
            # Truncate or extend annotations as needed
            if symbol_count <= len(page["annotations"]):
                page["annotations"] = page["annotations"][:symbol_count]
            else:
                # Duplicate annotations to reach target count
                while len(page["annotations"]) < symbol_count:
                    page["annotations"].extend(base_page["annotations"])
                page["annotations"] = page["annotations"][:symbol_count]
            
            pages.append(page)
        
        return pages


class MockFileSystem:
    """Mock file system operations for testing"""
    
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.symbols_dir = temp_dir / "symbols"
        self.examples_dir = temp_dir / "examples"
        self.tests_dir = temp_dir / "tests"
    
    def setup_complete_environment(self):
        """Set up complete mock environment"""
        self.symbols_dir.mkdir(exist_ok=True)
        self.examples_dir.mkdir(exist_ok=True)
        self.tests_dir.mkdir(exist_ok=True)
        
        # Create all necessary files
        fixtures = TestFixtures.create_temporary_files()
        return fixtures
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)