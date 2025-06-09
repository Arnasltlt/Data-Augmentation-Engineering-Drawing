"""
Drawing Plan Validator

Validates JSON drawing plans against the defined schema and provides
detailed error reporting for AI-generated plans.
"""

import json
import os
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator


class DrawingPlanValidator:
    """Validates drawing plans against multiple schemas (legacy and feature-based)"""
    
    def __init__(self, schema_path: Optional[str] = None, feature_schema_path: Optional[str] = None):
        """Initialize validator with both schemas"""
        current_dir = os.path.dirname(__file__)
        
        if schema_path is None:
            schema_path = os.path.join(current_dir, 'drawing_plan_schema.json')
        if feature_schema_path is None:
            feature_schema_path = os.path.join(current_dir, 'feature_plan_schema.json')
        
        with open(schema_path, 'r') as f:
            self.legacy_schema = json.load(f)
        with open(feature_schema_path, 'r') as f:
            self.feature_schema = json.load(f)
        
        self.legacy_validator = Draft7Validator(self.legacy_schema)
        self.feature_validator = Draft7Validator(self.feature_schema)
    
    def validate_plan(self, plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a drawing plan, automatically detecting if it's legacy or feature-based.
        """
        errors = []
        is_feature_based = "base_feature" in plan

        try:
            if is_feature_based:
                print("Detected Feature-Based Plan. Validating against new schema.")
                validate(instance=plan, schema=self.feature_schema)
                # TODO: Add semantic validation for feature-based plans
            else:
                print("Detected Legacy Plan. Validating against old schema.")
                validate(instance=plan, schema=self.legacy_schema)
                semantic_errors = self._validate_semantics(plan)
                errors.extend(semantic_errors)
            
            return len(errors) == 0, errors
            
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            
            # Add path information for better error reporting
            if e.absolute_path:
                path = " -> ".join(str(p) for p in e.absolute_path)
                errors.append(f"Error location: {path}")
            
            return False, errors
    
    def _validate_semantics(self, plan: Dict[str, Any]) -> List[str]:
        """Perform additional semantic validation beyond schema"""
        errors = []
        
        # Validate geometry makes sense
        geometry = plan.get('geometry', {})
        
        # Check for degenerate shapes
        if 'circles' in geometry:
            for i, circle in enumerate(geometry['circles']):
                if circle['radius'] <= 0:
                    errors.append(f"Circle {i}: radius must be positive")
        
        if 'rectangles' in geometry:
            for i, rect in enumerate(geometry['rectangles']):
                corner1, corner2 = rect['corner1'], rect['corner2']
                if corner1[0] == corner2[0] or corner1[1] == corner2[1]:
                    errors.append(f"Rectangle {i}: degenerate rectangle (zero width or height)")
        
        # Validate dimensions reference valid geometry
        annotations = plan.get('annotations', {})
        if 'dimensions' in annotations:
            for i, dim in enumerate(annotations['dimensions']):
                if dim['type'] == 'diameter' and 'radius' in dim:
                    if dim['radius'] <= 0:
                        errors.append(f"Dimension {i}: diameter radius must be positive")
        
        # Validate symbols exist in manifest
        if 'symbols' in annotations:
            errors.extend(self._validate_symbols(annotations['symbols']))
        
        # Validate title block data
        if 'title_block' in plan:
            errors.extend(self._validate_title_block(plan['title_block']))
        
        return errors
    
    def _validate_symbols(self, symbols: List[Dict[str, Any]]) -> List[str]:
        """Validate symbol references"""
        errors = []
        
        # Load symbol manifest for validation
        try:
            manifest_path = os.path.join(os.path.dirname(__file__), '..', '..', 'symbols', 'symbols_manifest.yaml')
            import yaml
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
            
            valid_symbols = {s['name'] for s in manifest['symbols']}
            
            for i, symbol in enumerate(symbols):
                symbol_name = symbol.get('name', '')
                if symbol_name not in valid_symbols:
                    errors.append(f"Symbol {i}: '{symbol_name}' not found in symbol manifest")
                
                # Validate scale and rotation ranges
                scale = symbol.get('scale', 1.0)
                if not (0.1 <= scale <= 10.0):
                    errors.append(f"Symbol {i}: scale {scale} out of range [0.1, 10.0]")
                
                rotation = symbol.get('rotation', 0)
                if not (0 <= rotation <= 360):
                    errors.append(f"Symbol {i}: rotation {rotation} out of range [0, 360]")
        
        except Exception as e:
            errors.append(f"Could not validate symbols against manifest: {e}")
        
        return errors
    
    def _validate_title_block(self, title_block: Dict[str, Any]) -> List[str]:
        """Validate title block data"""
        errors = []
        
        # Validate date format if present
        if 'date' in title_block:
            date_str = title_block['date']
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                errors.append(f"Title block: invalid date format '{date_str}' (expected YYYY-MM-DD)")
        
        # Validate scale format
        if 'scale' in title_block:
            scale_str = title_block['scale']
            # Should be either "N:M" or decimal
            if ':' in scale_str:
                try:
                    parts = scale_str.split(':')
                    if len(parts) != 2:
                        raise ValueError()
                    float(parts[0])
                    float(parts[1])
                except ValueError:
                    errors.append(f"Title block: invalid scale ratio format '{scale_str}'")
            else:
                try:
                    float(scale_str)
                except ValueError:
                    errors.append(f"Title block: invalid scale format '{scale_str}'")
        
        return errors
    
    def generate_validation_report(self, plan: Dict[str, Any]) -> str:
        """Generate a detailed validation report"""
        is_valid, errors = self.validate_plan(plan)
        
        report = ["=" * 50]
        report.append("DRAWING PLAN VALIDATION REPORT")
        report.append("=" * 50)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"Status: {'VALID' if is_valid else 'INVALID'}")
        report.append("")
        
        if is_valid:
            report.append("✅ Plan validation successful!")
            
            # Add summary statistics
            geometry = plan.get('geometry', {})
            annotations = plan.get('annotations', {})
            
            report.append("\nPlan Summary:")
            report.append(f"  Lines: {len(geometry.get('lines', []))}")
            report.append(f"  Circles: {len(geometry.get('circles', []))}")
            report.append(f"  Arcs: {len(geometry.get('arcs', []))}")
            report.append(f"  Rectangles: {len(geometry.get('rectangles', []))}")
            report.append(f"  Dimensions: {len(annotations.get('dimensions', []))}")
            report.append(f"  Symbols: {len(annotations.get('symbols', []))}")
            report.append(f"  Notes: {len(annotations.get('notes', []))}")
            report.append(f"  Title Block: {'Yes' if 'title_block' in plan else 'No'}")
        else:
            report.append("❌ Plan validation failed!")
            report.append("\nErrors:")
            for i, error in enumerate(errors, 1):
                report.append(f"  {i}. {error}")
        
        report.append("\n" + "=" * 50)
        return "\n".join(report)


def validate_drawing_plan(plan_path: str, schema_path: Optional[str] = None) -> bool:
    """
    Convenience function to validate a drawing plan file
    
    Args:
        plan_path: Path to the JSON plan file
        schema_path: Optional path to custom schema file
        
    Returns:
        True if valid, False otherwise
    """
    validator = DrawingPlanValidator(schema_path)
    
    with open(plan_path, 'r') as f:
        plan = json.load(f)
    
    is_valid, errors = validator.validate_plan(plan)
    
    if not is_valid:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
    
    return is_valid


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python plan_validator.py <plan_file.json>")
        sys.exit(1)
    
    plan_file = sys.argv[1]
    
    if not os.path.exists(plan_file):
        print(f"Error: File '{plan_file}' not found")
        sys.exit(1)
    
    validator = DrawingPlanValidator()
    
    with open(plan_file, 'r') as f:
        plan = json.load(f)
    
    print(validator.generate_validation_report(plan))