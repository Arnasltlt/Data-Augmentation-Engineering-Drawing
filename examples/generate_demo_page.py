#!/usr/bin/env python3
"""
Demo script for LayoutLab placement engine
Generates a sample engineering drawing page with symbols
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from layoutlab.placer import generate_page


def main():
    """Generate demo page and save outputs"""
    print("LayoutLab Demo - Generating engineering drawing page...")
    
    # Configuration
    sheet_size = "A3"
    symbol_count = 45
    seed = 42
    
    print(f"Configuration:")
    print(f"  Sheet size: {sheet_size}")
    print(f"  Symbol count: {symbol_count}")
    print(f"  Random seed: {seed}")
    print()
    
    # Generate page
    start_time = datetime.now()
    try:
        result = generate_page(sheet_size, symbol_count, seed)
        end_time = datetime.now()
        
        duration_ms = (end_time - start_time).total_seconds() * 1000
        print(f"Page generated successfully in {duration_ms:.1f}ms")
        
        # Save PDF
        pdf_filename = f"demo_page_{sheet_size.lower()}.pdf"
        pdf_path = os.path.join(os.path.dirname(__file__), pdf_filename)
        with open(pdf_path, 'wb') as f:
            f.write(result["pdf_bytes"])
        print(f"PDF saved: {pdf_filename}")
        
        # Save JSON annotations
        json_filename = f"demo_page_{sheet_size.lower()}_annotations.json"
        json_path = os.path.join(os.path.dirname(__file__), json_filename)
        with open(json_path, 'w') as f:
            json.dump({
                "metadata": {
                    "sheet_size": sheet_size,
                    "symbol_count_requested": symbol_count,
                    "symbol_count_placed": len(result["annotations"]),
                    "generation_time_ms": duration_ms,
                    "random_seed": seed,
                    "generated_at": datetime.now().isoformat()
                },
                "annotations": result["annotations"]
            }, f, indent=2)
        print(f"Annotations saved: {json_filename}")
        
        # Print summary
        print(f"\nSummary:")
        print(f"  Symbols placed: {len(result['annotations'])}/{symbol_count}")
        print(f"  PDF size: {len(result['pdf_bytes']):,} bytes")
        print(f"  Performance: {duration_ms:.1f}ms (target: <200ms)")
        
        # Show symbol distribution
        symbol_counts = {}
        for annotation in result["annotations"]:
            symbol_name = annotation["symbol_name"]
            symbol_counts[symbol_name] = symbol_counts.get(symbol_name, 0) + 1
        
        print(f"\nSymbol distribution:")
        for symbol_name, count in sorted(symbol_counts.items()):
            print(f"  {symbol_name}: {count}")
        
        # Show sample annotations
        print(f"\nSample annotations (first 3):")
        for i, annotation in enumerate(result["annotations"][:3]):
            print(f"  [{i}] {annotation['symbol_name']} at "
                  f"({annotation['position']['x']:.1f}, {annotation['position']['y']:.1f})")
            if annotation['parameters']:
                print(f"      Parameters: {annotation['parameters']}")
        
        if len(result["annotations"]) > 3:
            print(f"  ... and {len(result['annotations']) - 3} more")
        
        return True
        
    except Exception as e:
        print(f"Error generating page: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_sheet_sizes():
    """Test generation with all supported sheet sizes"""
    print("\nTesting all sheet sizes...")
    
    sheet_sizes = ["A4", "A3", "US-Letter"]
    results = {}
    
    for sheet_size in sheet_sizes:
        print(f"\nTesting {sheet_size}...")
        start_time = datetime.now()
        
        try:
            result = generate_page(sheet_size, 20, 123)
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            results[sheet_size] = {
                "success": True,
                "symbols_placed": len(result["annotations"]),
                "duration_ms": duration_ms,
                "pdf_size": len(result["pdf_bytes"])
            }
            
            print(f"  ✓ Success: {len(result['annotations'])} symbols in {duration_ms:.1f}ms")
            
        except Exception as e:
            results[sheet_size] = {
                "success": False,
                "error": str(e)
            }
            print(f"  ✗ Failed: {e}")
    
    print(f"\nSheet size test results:")
    for sheet_size, result in results.items():
        if result["success"]:
            print(f"  {sheet_size}: ✓ {result['symbols_placed']} symbols, "
                  f"{result['duration_ms']:.1f}ms, {result['pdf_size']:,} bytes")
        else:
            print(f"  {sheet_size}: ✗ {result['error']}")
    
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("LayoutLab Demo Script")
    print("=" * 60)
    
    # Generate main demo page
    success = main()
    
    if success:
        # Test all sheet sizes
        test_all_sheet_sizes()
        print(f"\n" + "=" * 60)
        print("Demo completed successfully!")
        print("Check the examples/ directory for generated files.")
    else:
        print(f"\n" + "=" * 60)
        print("Demo failed!")
        sys.exit(1)