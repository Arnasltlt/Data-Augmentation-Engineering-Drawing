"""
Simple Block Importer

Directly imports block definitions from the symbol library into the main document.
This ensures the blocks are available for both DXF generation and visualization.
"""

import ezdxf
import os
from typing import Dict, Set


class SymbolBlockImporter:
    """Imports symbol blocks directly into documents"""
    
    def __init__(self, symbol_library_path: str = 'library/symbols.dxf'):
        self.library_path = symbol_library_path
        self.library_doc = None
        self._load_library()
    
    def _load_library(self):
        """Load the symbol library document"""
        if not os.path.exists(self.library_path):
            print(f"Warning: Symbol library not found at {self.library_path}")
            return
        
        try:
            self.library_doc = ezdxf.readfile(self.library_path)
            print(f"✅ Loaded symbol library with {len(self.library_doc.blocks)} blocks")
        except Exception as e:
            print(f"Error loading symbol library: {e}")
            self.library_doc = None
    
    def import_symbols(self, target_doc, required_symbols: Set[str]) -> bool:
        """
        Import specific symbol blocks into the target document
        
        Args:
            target_doc: The DXF document to import blocks into
            required_symbols: Set of symbol names to import
            
        Returns:
            True if all symbols were imported successfully
        """
        if not self.library_doc:
            print("❌ No symbol library available")
            return False
        
        success_count = 0
        
        for symbol_name in required_symbols:
            if self._import_single_block(target_doc, symbol_name):
                success_count += 1
        
        print(f"✅ Imported {success_count}/{len(required_symbols)} symbol blocks")
        return success_count == len(required_symbols)
    
    def _import_single_block(self, target_doc, block_name: str) -> bool:
        """Import a single block definition"""
        try:
            # Check if block exists in library
            if block_name not in self.library_doc.blocks:
                print(f"Warning: Block '{block_name}' not found in library")
                return False
            
            # Check if block already exists in target
            if block_name in target_doc.blocks:
                return True  # Already imported
            
            # Get the source block
            source_block = self.library_doc.blocks[block_name]
            
            # Create new block in target document
            target_block = target_doc.blocks.new(block_name)
            
            # Copy entities from source to target
            for entity in source_block:
                # Clone the entity to the target block
                target_block.add_entity(entity.copy())
            
            return True
            
        except Exception as e:
            print(f"Error importing block '{block_name}': {e}")
            return False
    
    def get_available_symbols(self) -> Set[str]:
        """Get list of available symbol names in the library"""
        if not self.library_doc:
            return set()
        
        # Filter out built-in blocks
        return {name for name in self.library_doc.blocks.keys() 
                if not name.startswith('*')}


def extract_required_symbols(plan: Dict) -> Set[str]:
    """Extract symbol names from a drawing plan"""
    symbols = set()
    
    # Check legacy annotations
    annotations = plan.get('annotations', {})
    if annotations.get('symbols'):
        for symbol in annotations['symbols']:
            symbols.add(symbol['name'])
    
    # Could add feature-based symbol extraction here in the future
    
    return symbols


# Simple integration function for generator.py
def integrate_symbols_into_document(doc, plan: Dict) -> bool:
    """
    Simple function to integrate required symbols into a document
    
    Args:
        doc: The target DXF document
        plan: The drawing plan containing symbol references
        
    Returns:
        True if integration successful
    """
    importer = SymbolBlockImporter()
    required_symbols = extract_required_symbols(plan)
    
    if not required_symbols:
        return True  # No symbols needed
    
    return importer.import_symbols(doc, required_symbols)


if __name__ == "__main__":
    # Test the importer
    importer = SymbolBlockImporter()
    available = importer.get_available_symbols()
    print(f"Available symbols: {sorted(list(available))}")