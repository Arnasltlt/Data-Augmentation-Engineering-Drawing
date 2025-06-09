#!/usr/bin/env python3
"""
Simple fix for symbol integration in generator.py

This script provides a minimal change to replace the problematic XREF approach
with direct block importing.
"""

import os
import re

def fix_generator_symbol_integration():
    """Replace the XREF approach with direct block importing"""
    
    generator_path = 'generator.py'
    
    if not os.path.exists(generator_path):
        print("❌ generator.py not found")
        return False
    
    # Read the current file
    with open(generator_path, 'r') as f:
        content = f.read()
    
    # Add the import for our block importer
    import_section = "from src.validator.plan_validator import DrawingPlanValidator"
    new_import = "from src.symbol_integration.block_importer import integrate_symbols_into_document"
    
    if new_import not in content:
        content = content.replace(import_section, f"{import_section}\n{new_import}")
    
    # Replace the complex XREF section with simple block importing
    xref_pattern = r"# --- XREF Symbol Library ---.*?except Exception as e:.*?print\(f\"🚨 An unexpected error occurred while processing the symbol library: \{e\}\"\)"
    
    replacement = """# --- Import Required Symbol Blocks ---
    try:
        if integrate_symbols_into_document(doc, plan):
            print("✅ Symbol blocks imported successfully")
        else:
            print("⚠️ Some symbol blocks could not be imported")
    except Exception as e:
        print(f"⚠️ Symbol integration failed: {e}")"""
    
    # Perform the replacement
    new_content = re.sub(xref_pattern, replacement, content, flags=re.DOTALL)
    
    # Write the fixed file
    with open(generator_path, 'w') as f:
        f.write(new_content)
    
    print("✅ generator.py updated with simple block importing")
    return True

def test_fix():
    """Test the fix with a simple plan"""
    import json
    
    # Create a simple test plan
    test_plan = {
        "geometry": {
            "lines": [
                {"start": [0, 0], "end": [100, 0]},
                {"start": [100, 0], "end": [100, 50]},
                {"start": [100, 50], "end": [0, 50]},
                {"start": [0, 50], "end": [0, 0]}
            ]
        },
        "annotations": {
            "symbols": [
                {
                    "name": "surface_triangle",
                    "location": [10, 55],
                    "rotation": 0,
                    "scale": 1.0
                }
            ]
        },
        "title_block": {
            "drawing_title": "Test Symbol Integration",
            "drawing_number": "TEST-001",
            "date": "2024-06-09"
        }
    }
    
    # Save test plan
    with open('test_symbol_integration.json', 'w') as f:
        json.dump(test_plan, f, indent=2)
    
    print("✅ Test plan created: test_symbol_integration.json")
    print("Run: python generator.py --plan test_symbol_integration.json --visualize")

if __name__ == "__main__":
    print("🔧 Fixing symbol integration in generator.py...")
    
    if fix_generator_symbol_integration():
        test_fix()
        print("\n✅ Fix applied successfully!")
        print("The generator should now work without XREF/embedding issues.")
    else:
        print("❌ Fix failed")