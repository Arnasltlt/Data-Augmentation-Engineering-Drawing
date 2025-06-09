"""
LayoutLab Agent - Core drawing layout and symbol placement engine
"""

import json
import random
from pathlib import Path
from typing import Any

from .placer import SymbolPlacer


class LayoutLabAgent:
    """
    LayoutLab agent responsible for creating the base drawing layout
    and placing GD&T symbols, dimensions, and other annotations.
    """

    def __init__(self, sheet_size: str = "A4"):
        self.sheet_size = sheet_size
        self.symbols_loaded = False
        self.placer = None

    def load_symbols(self):
        """Load symbols from manifest"""
        print("LayoutLab: Loading symbols from symbols")
        symbols_manifest_path = Path("symbols/symbols_manifest.yaml")
        self.placer = SymbolPlacer(str(symbols_manifest_path) if symbols_manifest_path.exists() else None)
        self.symbols_loaded = True

    def generate_drawing(self, page_id: str, output_dir: Path) -> dict[str, Any]:
        """
        Generate a clean engineering drawing with symbols and annotations.

        Args:
            page_id: Unique identifier for this page
            output_dir: Directory to save output files

        Returns:
            Dictionary containing metadata about the generated drawing
        """
        print(f"LayoutLab: Generating {self.sheet_size} drawing for {page_id}")

        # Initialize placer if not already done
        if not self.placer:
            self.load_symbols()

        # Generate symbol placements
        symbol_count = random.randint(15, 35)  # Random number of symbols
        seed = hash(page_id) % 10000  # Deterministic seed from page_id
        
        placed_symbols = self.placer.place_symbols_randomly(
            sheet_size=self.sheet_size,
            symbol_count=symbol_count, 
            seed=seed
        )

        # Generate PDF
        pdf_bytes = self.placer.generate_pdf(placed_symbols, self.sheet_size)
        
        # Save PDF
        pdf_path = output_dir / f"{page_id}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # Generate annotations
        annotations = self.placer.generate_annotations_json(placed_symbols)

        # Create drawing data structure
        drawing_data = {
            "page_id": page_id,
            "sheet_size": self.sheet_size,
            "symbols": [ps.symbol.name for ps in placed_symbols],
            "symbol_count": len(placed_symbols),
            "annotations": annotations,
            "generated_by": "LayoutLab",
        }

        # Save JSON metadata
        json_path = output_dir / f"{page_id}.json"
        with open(json_path, "w") as f:
            json.dump(drawing_data, f, indent=2)

        return drawing_data
